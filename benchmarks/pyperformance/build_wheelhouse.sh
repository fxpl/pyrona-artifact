#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"

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
            echo "$host_arch_raw"
            ;;
    esac
}

TARGET_OS="$(detect_target_os)"
TARGET_ARCH="$(detect_target_arch)"
WHEELHOUSE_DIR="${WHEELHOUSE_DIR:-$SCRIPT_DIR/wheelhouse-$TARGET_OS-$TARGET_ARCH}"

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
    cat <<'EOF'
Usage: build_wheelhouse.sh

Environment variables:
  PYTHON_BIN      Python used to create helper venv (default: python3)
  WHEELHOUSE_DIR  Output wheelhouse directory
                                    (default: ./wheelhouse-<os>-<arch>)

This script downloads wheels for:
- bootstrap packages used by pyperformance benchmark venvs
- pyperformance itself
- all benchmark requirement files shipped with pyperformance
EOF
    exit 0
fi

require_cmd() {
    local cmd="$1"
    command -v "$cmd" >/dev/null 2>&1 || {
        echo "error: required command not found: $cmd" >&2
        exit 1
    }
}

require_cmd "$PYTHON_BIN"

TMP_DIR="$(mktemp -d)"
cleanup() {
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT

VENV_DIR="$TMP_DIR/venv"
"$PYTHON_BIN" -m venv "$VENV_DIR"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -m pip install --disable-pip-version-check --upgrade pip
python -m pip install --disable-pip-version-check pyperformance

mkdir -p "$WHEELHOUSE_DIR"

PYPERF_DIR="$(python - <<'PY'
import pathlib
import pyperformance
print(pathlib.Path(pyperformance.__file__).resolve().parent)
PY
)"

REQ_ROOT="$PYPERF_DIR/requirements/requirements.txt"
BENCH_REQ_DIR="$PYPERF_DIR/data-files/benchmarks"

echo "[info] wheelhouse output: $WHEELHOUSE_DIR" >&2
echo "[info] pyperformance package: $PYPERF_DIR" >&2

# Bootstrap packages are required when pyperformance creates per-benchmark venvs.
python -m pip download --disable-pip-version-check --dest "$WHEELHOUSE_DIR" \
    pip setuptools wheel pyperformance

if [ -f "$REQ_ROOT" ]; then
    echo "[info] downloading requirements from: $REQ_ROOT" >&2
    python -m pip download --disable-pip-version-check --dest "$WHEELHOUSE_DIR" -r "$REQ_ROOT"
fi

while IFS= read -r req_file; do
    echo "[info] downloading requirements from: $req_file" >&2
    python -m pip download --disable-pip-version-check --dest "$WHEELHOUSE_DIR" -r "$req_file"
done < <(find "$BENCH_REQ_DIR" -type f -name requirements.txt | sort)

echo "[done] wheelhouse prepared at: $WHEELHOUSE_DIR" >&2
