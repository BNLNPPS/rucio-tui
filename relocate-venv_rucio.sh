#!/usr/bin/env bash
# ============================================================
#  Make a Python venv portable and isolated for rucio-tui:
#
#  1. Convert absolute symlinks in bin/ to relative ones
#  2. Replace activate with ./activate2, which hides this venv
#     from other active virtual environments
#  3. Remove non-POSIX / Windows activation scripts
#  4. Fix shebangs: absolute python path → /usr/bin/env python
#  5. Wrap rucio* scripts to use the local Python 3
#     (prepends shellWrapper-for-python3-I.sh)
#
#  Requires in the current directory:
#    activate2                      – replacement activate script
#    shellWrapper-for-python3-I.sh  – wrapper prepended to rucio* scripts
#
#  Run directly or source in bash / zsh:
#    relocate-venv_rucio.sh <binDir>
#    source relocate-venv_rucio.sh <binDir>
# ============================================================

print_help() {
    cat << EOF
Usage:
    relocate-venv_rucio.sh <binDir>
    source relocate-venv_rucio.sh <binDir>

    binDir  Bin directory of a Python virtual environment (e.g. .venv/bin).
            Must contain an "activate" script.

Actions performed on <binDir>:
  1. Convert absolute symlinks to relative ones
  2. Replace activate with ./activate2  (isolates venv from other environments)
  3. Remove non-POSIX / Windows activation scripts  (activate.*, *.bat)
  4. Fix shebangs: absolute python path → /usr/bin/env python
  5. Prepend shellWrapper-for-python3-I.sh to all rucio* scripts

Files required in the current directory:
    activate2                      – replacement activate script
    shellWrapper-for-python3-I.sh  – wrapper prepended to rucio* scripts

Options:
    -h, --help    Show this help message and exit
EOF
}

main() {
    local BIN_DIR
    # Resolve to an absolute path before any cd so later references stay valid
    BIN_DIR="$(cd -- "$1" 2>/dev/null && pwd)" || {
        echo "Error: cannot enter directory '$1'" >&2
        return 1
    }

    # Run in a subshell so the caller's working directory is unchanged when sourced
    (
        set -euo pipefail
        wrapper=$(pwd)/shellWrapper-for-python3-I.sh
        activate=$(pwd)/activate2
        cd "$BIN_DIR"

        # Enable null-glob so unmatched patterns expand to nothing instead of erroring
        shopt -s nullglob 2>/dev/null || true  # bash
        setopt NULL_GLOB  2>/dev/null || true  # zsh

        # ── make symlinks in bin/ relative for portability ────────
        echo "Making symlinks in ${BIN_DIR}/ relative …"
        for link in *; do
            [[ -L "${link}" ]] || continue
            target="$(readlink "${link}")"
            # If target is absolute, replace it with a relative path
            if [[ "${target}" == /* ]]; then
                rel_target="$(realpath --relative-to="." "${target}")"
                ln -snf "${rel_target}" "${link}"
            fi
        done

        # ── copy the special "activate" script  ────────────────────
        # which hides this virtual env from other existing virtual env
        #  and makes it to works without interference with the current env
        echo "Copying script activate"
        cp -f $activate ./activate

        # ── remove non-POSIX and Windows activation scripts ───────
        echo "Removing unnecessary activation scripts …"
        find . -maxdepth 1 \( -name 'activate.*' -o -name '*.bat' \) -delete

        # ── fix shebangs in bin/ scripts ──────────────────────────
        # Replace #!/absolute/path/to/python with #!/usr/bin/env python
        echo "Fixing shebangs in ${BIN_DIR}/ for portability …"
        while IFS= read -r script_file; do
            [[ -n "$script_file" ]] || continue
            sed -i "1,3 s%${BIN_DIR}/python%/usr/bin/env python%" "$script_file"
        done < <(file * 2>/dev/null | grep "Python script" | cut -d: -f1)

        # ── Wrap all rucio-related Python scripts ──────────────────────────
        # So they would use the Python3 under the same directory
        echo "Wrapping rucio scripts"
        sed -i -e "1r/${wrapper}" -e "1d" -e "/coding:/d" rucio*
        # sed -i -e '1d' -e "1r/${wrapper}" rucio*
    )
}

# ── help ──────────────────────────────────────────────────────
if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    print_help
    return 0 2>/dev/null || exit 0
fi

# ── argument validation ───────────────────────────────────────
if [[ $# -ne 1 ]]; then
    echo "Error: exactly one argument required." >&2
    print_help >&2
    return 1 2>/dev/null || exit 1
fi

if [[ ! -f "${1}/activate" ]]; then
    echo "Error: '${1}/activate' not found – is '${1}' a virtualenv bin directory?" >&2
    return 1 2>/dev/null || exit 1
fi

main "$1"
