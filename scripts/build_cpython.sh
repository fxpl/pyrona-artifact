#!/usr/bin/env bash

set -euo pipefail

ENV_FILE_DEFAULT="snapshots/snapshot-sources.env"
MAKE_JOBS_DEFAULT=""

ENV_FILE="$ENV_FILE_DEFAULT"
MAKE_JOBS="$MAKE_JOBS_DEFAULT"

SCRIPT_NAME="$(basename "$0")"

usage() {
    cat <<EOF
Usage: $SCRIPT_NAME [options]

Build baseline and patched CPython snapshots by running in each directory:
    ./configure
    make -j

Then write built interpreter paths back into the env file:
    BASELINE_PYTHON_BIN
    PATCHED_PYTHON_BIN

Options:
    --env-file <path>       Env file with BASELINE_SNAPSHOT_DIR and PATCHED_SNAPSHOT_DIR
                               (default: $ENV_FILE_DEFAULT)
    --jobs <n>              Pass explicit job count to make (uses plain -j when omitted)
    -h, --help              Show this help

Examples:
    $SCRIPT_NAME
    $SCRIPT_NAME --env-file snapshots/snapshot-sources.env
    $SCRIPT_NAME --jobs 8
EOF
}

die() {
    echo "error: $*" >&2
    exit 1
}

require_cmd() {
    command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

resolve_python_bin() {
    local dir="$1"
    local -a candidates
    local candidate
    local os_name

    os_name="$(uname -s 2>/dev/null || true)"

    case "$os_name" in
        CYGWIN*|MINGW*|MSYS*|Windows_NT)
            candidates=("python.exe" "python")
            ;;
        *)
            # Prefer native unix name first, but still support .exe artifacts.
            candidates=("python" "python.exe")
            ;;
    esac

    for candidate in "${candidates[@]}"; do
        if [ -x "$dir/$candidate" ] || [ -f "$dir/$candidate" ]; then
            printf '%s' "$dir/$candidate"
            return 0
        fi
    done

    die "built python binary not found in $dir (checked: ${candidates[*]})"
}

upsert_env_var() {
    local key="$1"
    local value="$2"
    local file="$3"
    local tmp

    tmp="$(mktemp -t snapshot-sources-XXXXXX)"
    awk -v key="$key" -v value="$value" '
        BEGIN { updated = 0 }
        $0 ~ "^" key "=" {
            print key "=" value
            updated = 1
            next
        }
        { print }
        END {
            if (!updated) {
                print key "=" value
            }
        }
    ' "$file" > "$tmp"
    mv "$tmp" "$file"
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --env-file)
            [ "$#" -ge 2 ] || die "missing value for $1"
            ENV_FILE="$2"
            shift 2
            ;;
        --jobs)
            [ "$#" -ge 2 ] || die "missing value for $1"
            MAKE_JOBS="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            die "unknown option: $1"
            ;;
    esac
done

require_cmd make

[ -f "$ENV_FILE" ] || die "sources file not found: $ENV_FILE"

# shellcheck disable=SC1090
source "$ENV_FILE"

[ -n "${BASELINE_SNAPSHOT_DIR:-}" ] || die "BASELINE_SNAPSHOT_DIR is missing in $ENV_FILE"
[ -n "${PATCHED_SNAPSHOT_DIR:-}" ] || die "PATCHED_SNAPSHOT_DIR is missing in $ENV_FILE"

run_build() {
    local label="$1"
    local dir="$2"

    [ -d "$dir" ] || die "$label snapshot directory does not exist: $dir"
    [ -x "$dir/configure" ] || die "missing executable configure script: $dir/configure"

    echo "[info] building $label snapshot in: $dir"

    (
        cd "$dir"
        ./configure --enable-optimizations
        if [ -n "$MAKE_JOBS" ]; then
            make -j "$MAKE_JOBS"
        else
            make -j
        fi
    )
}

run_build "baseline" "$BASELINE_SNAPSHOT_DIR"
run_build "patched" "$PATCHED_SNAPSHOT_DIR"

BASELINE_PYTHON_BIN="$(resolve_python_bin "$BASELINE_SNAPSHOT_DIR")"
PATCHED_PYTHON_BIN="$(resolve_python_bin "$PATCHED_SNAPSHOT_DIR")"

upsert_env_var "BASELINE_PYTHON_BIN" "$BASELINE_PYTHON_BIN" "$ENV_FILE"
upsert_env_var "PATCHED_PYTHON_BIN" "$PATCHED_PYTHON_BIN" "$ENV_FILE"

cat <<EOF
[done] builds completed
    baseline: $BASELINE_SNAPSHOT_DIR
    patched:  $PATCHED_SNAPSHOT_DIR
    baseline python: $BASELINE_PYTHON_BIN
    patched python:  $PATCHED_PYTHON_BIN
    env file: $ENV_FILE
EOF
