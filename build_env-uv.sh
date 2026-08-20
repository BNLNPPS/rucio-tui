#!/usr/bin/env bash
# ============================================================
#  build_env-uv.sh  —  build a virtual Python environment
#                      for rucio-TUI
#
#  The selected CPython (default 3.11; 3.12, 3.13, 3.14, … also work)
#  is downloaded and installed INSIDE venv/, making the whole
#  directory fully self-contained & portable.
#
#  Directory layout after building:
#    venv/
#    ├── bin/          ← python3.x, pip, activate …
#    ├── etc/          ← VOMS config and certificates
#    ├── lib/          ← installed packages
#    ├── python/       ← standalone CPython runtime
#    ├── pyvenv.cfg
#    ├── buildStamp.txt
#    └── setupMe.sh    ← setup script
#
#  Must be run directly — do NOT source this script:
#    bash build_env-uv.sh
#    ./build_env-uv.sh --python 3.12
# ============================================================

print_help() {
    cat << EOF
Usage:
    bash build_env-uv.sh [OPTIONS]
    ./build_env-uv.sh [OPTIONS]

This script creates a reproducible Python environment for rucio-TUI.
    The selected CPython is downloaded and installed INSIDE venv/.
    Python 3.11 is the default; 3.12, 3.13, 3.14, and other 3.10+ versions work too.

NOTE: Run directly — do NOT source this script.
      Sourcing would pollute your current shell environment.

Options:
  -h, --help              Show this help message and exit
  -p, --python VERSION    CPython version to install (default: 3.11)
                          Examples: 3.11, 3.12, 3.13, 3.14
EOF
}

# ── Reject sourcing ──────────────────────────────────────────
# Detect sourcing in bash (BASH_SOURCE[0] != $0) and zsh (ZSH_EVAL_CONTEXT contains ":file")
if [[ -n "${BASH_VERSION:-}"  && "${BASH_SOURCE[0]}" != "${0}" ]] ||
   [[ -n "${ZSH_VERSION:-}"   && "${ZSH_EVAL_CONTEXT:-}" == *:file* ]]; then
    echo "Warning: build_env-uv.sh must be run directly, not sourced." >&2
    echo "         Sourcing pollutes your shell environment with build-time settings." >&2
    echo "" >&2
    print_help >&2
    return 1
fi

# ── main ──────────────────────────────────────────────────────
main() {
    set -euo pipefail

    # ── configuration ────────────────────────────────────────────
    local PYTHON_VERSION="${1:-3.11}"
    local VENV_DIR="venv"

    # Resolve script location robustly in both bash and zsh
    local SCRIPT_DIR
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
    local VENV_PATH="${SCRIPT_DIR}/${VENV_DIR}"

    # ── colour helpers ────────────────────────────────────────────
    _green()  { printf '\033[0;32m%s\033[0m\n' "$*"; }
    _yellow() { printf '\033[0;33m%s\033[0m\n' "$*"; }
    _red()    { printf '\033[0;31m%s\033[0m\n' "$*"; }
    _bold()   { printf '\033[1m%s\033[0m\n'   "$*"; }

    # ── 1. ensure uv is installed (bootstrap only) ───────────────
    if ! command -v uv &>/dev/null; then
        _yellow "uv not found — installing via the official installer …"
        curl -LsSf https://astral.sh/uv/install.sh | if [[ -f /usr/bin/python3 ]]; then sh; else sh /dev/stdin --no-modify-path; fi
        export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
        if ! command -v uv &>/dev/null; then
            _red "uv installation failed. Please install manually:"
            _red "  https://docs.astral.sh/uv/getting-started/installation/"
            return 1
        fi
        _green "uv installed: $(uv --version)"
    else
        _green "uv found: $(uv --version)"
    fi

    # ── 2. download CPython into venv/python/ ───────
    #    Do this BEFORE creating the venv so --clear cannot touch it.
    #    Skip if already present.
    _bold "Installing CPython ${PYTHON_VERSION} into ${VENV_DIR}/python/ …"
    UV_PYTHON_INSTALL_DIR="${VENV_PATH}/python" \
        uv python install "${PYTHON_VERSION}"

    # ── 3. create venv, preserving venv/python/ ──────────
    #    Remove only the venv-owned files/dirs, not python/, before
    #    re-creating — this avoids --clear wiping the interpreter.
    _bold "Creating virtual environment at ${VENV_DIR}/ …"
    for item in bin lib lib64 include share pyvenv.cfg; do
        rm -rf "${VENV_PATH:?}/${item}"
    done

    # Locate the interpreter (works whether just installed or pre-existing)
    # We do this AFTER deleting the old venv dirs to ensure we don't pick up a stale path.
    local PYTHON_BIN
    PYTHON_BIN="$(
        UV_PYTHON_INSTALL_DIR="${VENV_PATH}/python" \
        uv python find "${PYTHON_VERSION}"
    )"
    _green "Python interpreter: ${PYTHON_BIN}"

    uv venv "${VENV_PATH}" --python "${PYTHON_BIN}" --seed --allow-existing
    _green "Virtual environment created."

    # ── shorthand: use uv to install packages into the venv ───
    _uv_pip() { env VIRTUAL_ENV="${VENV_PATH}" uv pip "$@"; }

    # ── install the packages ──────────────────
    _uv_pip install .
    _green "All packages installed."

    # ── Make the virtual env relocatable ──
    # . "${SCRIPT_DIR}/relocate-venv.sh" "${VENV_PATH}/bin"
    . "${SCRIPT_DIR}/relocate-venv_rucio.sh" "${VENV_PATH}/bin"

    echo ""
    _bold "Final layout:"
    printf '  %s/\n' "${VENV_DIR}"
    printf '  ├── bin/python%s  →  self-contained CPython runtime (relative symlink)\n' "${PYTHON_VERSION}"
    printf '  ├── bin/activate    →  relocatable activation script\n'
    printf '  ├── bin/jupyter     →  portable shebang (#!/usr/bin/env python3)\n'
    printf '  ├── etc/            →  VOMS config and certificates\n'
    printf '  ├── lib/            →  all installed packages\n'
    printf '  ├── buildStamp.txt  →  build timestamp\n'
    printf '  ├── python/         →  standalone CPython %s build\n' "${PYTHON_VERSION}"
    printf '  └── setupMe.sh      →  setup script\n'

    # ── copy setupMe.sh to venv directory ────────────────────
    _bold "Copying setupMe.sh to ${VENV_DIR} …"
    cp "${SCRIPT_DIR}/setupMe.sh" "${VENV_PATH}/setupMe.sh"

    # ── copy voms config to venv directory ───────────────────
    _bold "Copying voms config to ${VENV_DIR}/etc/ …"
    mkdir -p "${VENV_PATH}/etc"
    GRID_DIR=/cvmfs/grid.cern.ch/etc/grid-security
    cp -pR ${GRID_DIR}/vomses "${VENV_PATH}/etc/"
    cp -pR ${GRID_DIR}/vomsdir "${VENV_PATH}/etc/"
    cp -pR ${GRID_DIR}/certificates "${VENV_PATH}/etc/"
    cp -p "${SCRIPT_DIR}/rucio.cfg" "${VENV_PATH}/etc/"

    # ── create build stamp ───────────────────────────────────
    _bold "Creating build stamp …"
    date -u +"%Y-%m-%dT%H%M%S-GMT" > "${VENV_PATH}/buildStamp.txt"
}


# ── argument parsing ──────────────────────────────────────────
PYTHON_VERSION="3.11"
while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            print_help
            exit 0
            ;;
        -p|--python)
            if [[ $# -lt 2 || -z "${2:-}" || "${2:-}" == -* ]]; then
                echo "Error: $1 requires a Python version argument (e.g. 3.12)" >&2
                echo "Try './build_env-uv.sh --help' for more information." >&2
                exit 1
            fi
            PYTHON_VERSION="$2"
            shift 2
            ;;
        *)
            echo "Error: Unknown option: $1" >&2
            echo "Try './build_env-uv.sh --help' for more information." >&2
            exit 1
            ;;
    esac
done

main "${PYTHON_VERSION}"
