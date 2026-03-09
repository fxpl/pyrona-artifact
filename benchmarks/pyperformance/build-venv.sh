#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

die() {
    echo "error: $*" >&2
    exit 1
}

require_cmd() {
    local cmd="$1"
    command -v "$cmd" >/dev/null 2>&1 || die "required command not found: $cmd"
}

prepare_arch_venv() {
    local target_os="$1"
    local target_arch="$2"
    local venv_dir="$SCRIPT_DIR/venv-$target_os-$target_arch"
    local venv_python="$venv_dir/bin/python"

    echo "[info] preparing pyperformance environment for os/arch: $target_os/$target_arch" >&2
    echo "[info]     environment path: $venv_dir" >&2

    python3 -m venv "$venv_dir" --copies
    source "$venv_dir/bin/activate"
    python -m pip install --disable-pip-version-check --upgrade pip
    python -m pip install --disable-pip-version-check pyperformance

    echo "[info] prebuilding pyperformance benchmarks for: $target_os/$target_arch" >&2
    python -m pyperformance run --debug-single-value

    # Only remove .gitignore when running in CI.
    if [ "${CI:-}" = "true" ]; then
        rm -f "$venv_dir/.gitignore"
    fi
}

require_cmd "python3"
HOST_OS_RAW="$(uname -s)"
case "$HOST_OS_RAW" in
    Darwin)
        TARGET_OS="macos"
        ;;
    Linux)
        TARGET_OS="linux"
        ;;
    *)
        TARGET_OS="$(echo "$HOST_OS_RAW" | tr '[:upper:]' '[:lower:]')"
        ;;
esac

HOST_ARCH_RAW="$(uname -m)"
case "$HOST_ARCH_RAW" in
    arm64|aarch64)
        TARGET_ARCH="arm64"
        ;;
    x86_64|amd64)
        TARGET_ARCH="x86_64"
        ;;
    *)
        die "unsupported host architecture: $HOST_ARCH_RAW"
        ;;
esac

prepare_arch_venv "$TARGET_OS" "$TARGET_ARCH"

echo "[info] done: benchmark environment prepared at: $SCRIPT_DIR/venv-$TARGET_OS-$TARGET_ARCH" >&2
