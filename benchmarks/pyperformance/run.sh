#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

require_env() {
    local var_name="$1"
    if [ -z "${!var_name:-}" ]; then
        echo "Missing required environment variable: $var_name" >&2
        exit 1
    fi
}

die() {
    echo "error: $*" >&2
    exit 1
}

require_wheel_in_wheelhouse() {
    local package_name="$1"
    if ! find "$WHEELHOUSE_DIR" -maxdepth 1 -type f -name "${package_name}-*.whl" | grep -q .; then
        die "required wheel for '${package_name}' not found in wheelhouse: $WHEELHOUSE_DIR"
    fi
}

require_env "BASELINE_PYTHON_BIN"
require_env "PATCHED_PYTHON_BIN"

FAST_MODE=0
ONLINE_MODE=0
LOG_TO_FILE=0

for arg in "$@"; do
    case "$arg" in
        "--help"|"-h")
            echo "usage: $0 [--fast] [--online] [--log-file]" >&2
            exit 0
            ;;
        "--fast")
            FAST_MODE=1
            ;;
        "--online")
            ONLINE_MODE=1
            ;;
        "--log-file")
            LOG_TO_FILE=1
            ;;
        *)
            die "unknown argument: $arg"
            ;;
    esac
done

detect_target_os() {
    local host_os_raw
    host_os_raw="$(uname -s)"
    case "$host_os_raw" in
        Darwin)
            echo "macos"
            ;;
        Linux)
            echo "linux"
            ;;
        *)
            echo "$host_os_raw" | tr '[:upper:]' '[:lower:]'
            ;;
    esac
}

detect_target_arch() {
    local host_arch_raw
    host_arch_raw="$(uname -m)"
    case "$host_arch_raw" in
        arm64|aarch64)
            echo "arm64"
            ;;
        x86_64|amd64)
            echo "x86_64"
            ;;
        *)
            die "unsupported host architecture: $host_arch_raw"
            ;;
    esac
}

# Setup output directory and files
RESULTS_DIR="$SCRIPT_DIR/results"
BASELINE_LOG_FILE="$RESULTS_DIR/baseline-output.txt"
BASELINE_OUTPUT_FILE="$RESULTS_DIR/baseline.json"
PATCHED_LOG_FILE="$RESULTS_DIR/patched-output.txt"
PATCHED_OUTPUT_FILE="$RESULTS_DIR/patched.json"
mkdir -p "$RESULTS_DIR"

export PIP_DISABLE_PIP_VERSION_CHECK=1

if [ "$ONLINE_MODE" -eq 0 ]; then
    export PIP_NO_INDEX=1
fi

TARGET_OS="$(detect_target_os)"
TARGET_ARCH="$(detect_target_arch)"

if [ "$ONLINE_MODE" -eq 0 ]; then
    WHEELHOUSE_DIR="${PIP_FIND_LINKS:-$SCRIPT_DIR/wheelhouse-$TARGET_OS-$TARGET_ARCH}"
    [ -d "$WHEELHOUSE_DIR" ] || die "wheelhouse directory not found: $WHEELHOUSE_DIR"
    export PIP_FIND_LINKS="$WHEELHOUSE_DIR"

    require_wheel_in_wheelhouse "setuptools"
    require_wheel_in_wheelhouse "wheel"
    require_wheel_in_wheelhouse "pyperformance"
fi

VENV_DIR="venv"
"$BASELINE_PYTHON_BIN" -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

pip_install_args=(
    --disable-pip-version-check
    --upgrade
    "setuptools>=18.5"
    wheel
    pyperformance
)

if [ "$ONLINE_MODE" -eq 0 ]; then
    pip_install_args=(
        --disable-pip-version-check
        --upgrade
        --no-index
        --find-links "$WHEELHOUSE_DIR"
        "setuptools>=18.5"
        wheel
        pyperformance
    )
fi

python -m pip install "${pip_install_args[@]}"

run_pyperformance() {
    local label="$1"
    local bin="$2"
    local output_file="$3"
    local log_file="$4"

    echo "[info] running 'pyperformance' for $label" >&2
    echo "[info]     writing output to: $output_file" >&2
    if [ "$LOG_TO_FILE" -eq 1 ]; then
        echo "[info]     writing pyperformance logs to: $log_file" >&2
    fi
    if [ "$ONLINE_MODE" -eq 0 ]; then
        echo "[info]     using wheelhouse: $PIP_FIND_LINKS" >&2
    else
        echo "[info]     online mode: enabled (wheelhouse bypassed)" >&2
    fi

    local pyperformance_args=(
        run
        --inherit-environ PIP_DISABLE_PIP_VERSION_CHECK
        -p "$bin"
        -o "$output_file"
        --debug-single-value
    )

    if [ "$ONLINE_MODE" -eq 0 ]; then
        pyperformance_args+=(
            --inherit-environ PIP_NO_INDEX
            --inherit-environ PIP_FIND_LINKS
        )
    fi

    if [ "$FAST_MODE" -eq 1 ]; then
        echo "[info]     fast mode: enabled" >&2
        pyperformance_args+=(--fast)
    fi

    if [ "$LOG_TO_FILE" -eq 1 ]; then
        pyperformance "${pyperformance_args[@]}" \
            > "$log_file" 2>&1
    else
        pyperformance "${pyperformance_args[@]}"
    fi
}

rm -f "$BASELINE_OUTPUT_FILE"
rm -f "$PATCHED_OUTPUT_FILE"

if [ "$LOG_TO_FILE" -eq 1 ]; then
    rm -f "$BASELINE_LOG_FILE"
    rm -f "$PATCHED_LOG_FILE"
fi

# Run benchmark
run_pyperformance "baseline" "$BASELINE_PYTHON_BIN" "$BASELINE_OUTPUT_FILE" "$BASELINE_LOG_FILE"
run_pyperformance "patched" "$PATCHED_PYTHON_BIN" "$PATCHED_OUTPUT_FILE" "$PATCHED_LOG_FILE"
