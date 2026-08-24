#!/usr/bin/env bash

# Resolve script location robustly in both bash and zsh
if [[ -n "${BASH_SOURCE[0]:-}" ]]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && command pwd)"
else
    # zsh: $0 is the script path when sourced
    SCRIPT_DIR="$(cd "$(dirname "$0")" >/dev/null 2>&1 && command pwd)"
fi

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    echo "Usage: source setupMe.sh [OPTIONS]"
    echo ""
    echo "This script activates the self-contained virtual environment for rucio-TUI."
    echo "It wraps the standard python virtual environment activation script."
    echo ""
    echo "Options:"
    echo "  -h, --help            Show this help message and exit"
    echo "  --buildStamp          Print the build stamp and exit"
    echo "  --voms, --vo SERVER"
    echo "                        Specify the voms server to use with voms-proxy-init"
    echo "                        (default: atlas)"
    return 0 2>/dev/null || exit 0
fi

if [[ "${1:-}" == "--buildStamp" ]]; then
    if [[ -f "${SCRIPT_DIR}/buildStamp.txt" ]]; then
        cat "${SCRIPT_DIR}/buildStamp.txt"
    else
        echo "Error: Could not find ${SCRIPT_DIR}/buildStamp.txt"
    fi
    return 0 2>/dev/null || exit 0
fi

# Parse remaining options
VOMS_SERVER="atlas"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --voms|--vo)
            if [[ $# -lt 2 ]]; then
                echo "Error: $1 requires a voms server argument" >&2
                return 1 2>/dev/null || exit 1
            fi
            VOMS_SERVER="$2"
            shift 2
            ;;
        *)
            echo "Error: Unknown option: $1" >&2
            echo "Try 'source setupMe.sh --help' for more information." >&2
            return 1 2>/dev/null || exit 1
            ;;
    esac
done

if [[ -f "${SCRIPT_DIR}/bin/activate" ]]; then
    # No existing venv — source the standard activation script
    source "${SCRIPT_DIR}/bin/activate"

    export VOMS_USERCONF="${SCRIPT_DIR}/etc/vomses"
    export X509_VOMS_DIR="${SCRIPT_DIR}/etc/vomsdir"
    if [[ -d "/cvmfs/grid.cern.ch/etc/grid-security/certificates" ]]; then
        export X509_CERT_DIR="/cvmfs/grid.cern.ch/etc/grid-security/certificates"
    else
        export X509_CERT_DIR="${SCRIPT_DIR}/etc/certificates"
    fi
    export RUCIO_CONFIG="${SCRIPT_DIR}/etc/rucio.cfg"

    if command -v voms-proxy-info >/dev/null 2>&1; then
        if ! voms-proxy-info -exists -valid 6:00 >/dev/null 2>&1; then
            [ -t 0 ] && voms-proxy-init -voms "$VOMS_SERVER" -valid 192:00
        fi
        PROXY_PATH=$(voms-proxy-info -path 2>/dev/null || true)
        if [[ -n "$PROXY_PATH" ]]; then
            export X509_USER_PROXY="$PROXY_PATH"
        fi
    fi

    _red=$(tput setaf 1 2>/dev/null || echo '')
    _reset=$(tput sgr0 2>/dev/null || echo '')

    echo "============================================================"
    echo "  rucio-TUI virtual environment activated!"
    echo "============================================================"
    echo "  The command ${_red}rucio-tui${_reset} is ready to use"
    echo ""
    echo "  To exit this environment, type: ${_red}deactivate2${_reset}"
    echo "============================================================"
else
    echo "Error: Could not find ${SCRIPT_DIR}/bin/activate"
    echo "Please ensure the virtual environment was created successfully."
    return 1 2>/dev/null || exit 1
fi
