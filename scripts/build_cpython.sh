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
    --env-file <path>       Env file with BASELINE_PYTHON_DIR and PATCHED_PYTHON_DIR
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
    local abs_dir
    local unix_candidate
    local exe_candidate

    abs_dir="$(cd "$dir" && pwd -P)" || die "failed to resolve absolute path: $dir"
    unix_candidate="$abs_dir/python"
    exe_candidate="$abs_dir/python.exe"

    # Prefer python.exe first to avoid false positives from case-insensitive
    # filesystems where a 'Python' directory can match 'python'.
    if [ -f "$exe_candidate" ]; then
        printf '%s' "$exe_candidate"
        return 0
    fi

    if [ -f "$unix_candidate" ] && [ -x "$unix_candidate" ]; then
        printf '%s' "$unix_candidate"
        return 0
    fi

    # Last resort for uncommon builds that emit a non-executable python file.
    if [ -f "$unix_candidate" ]; then
        printf '%s' "$unix_candidate"
        return 0
    fi

    die "built python binary not found in $abs_dir (checked: python, python.exe)"
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

[ -n "${BASELINE_PYTHON_DIR:-}" ] || die "BASELINE_PYTHON_DIR is missing in $ENV_FILE"
[ -n "${PATCHED_PYTHON_DIR:-}" ] || die "PATCHED_PYTHON_DIR is missing in $ENV_FILE"

run_build() {
    local label="$1"
    local dir="$2"

    [ -d "$dir" ] || die "$label snapshot directory does not exist: $dir"
    [ -x "$dir/configure" ] || die "missing executable configure script: $dir/configure"

    echo "[info] building $label snapshot in: $dir"

    (
        cd "$dir"
        ./configure --enable-optimizations
        make clean
        if [ -n "$MAKE_JOBS" ]; then
            make -j "$MAKE_JOBS"
        else
            make -j
        fi
    )
}

run_build "baseline" "$BASELINE_PYTHON_DIR"
run_build "patched" "$PATCHED_PYTHON_DIR"

BASELINE_PYTHON_BIN="$(resolve_python_bin "$BASELINE_PYTHON_DIR")"
PATCHED_PYTHON_BIN="$(resolve_python_bin "$PATCHED_PYTHON_DIR")"

cat <<EOF
[done] builds completed
    baseline: $BASELINE_PYTHON_DIR
    baseline python: $BASELINE_PYTHON_BIN
    patched:  $PATCHED_PYTHON_DIR
    patched python:  $PATCHED_PYTHON_BIN
EOF
