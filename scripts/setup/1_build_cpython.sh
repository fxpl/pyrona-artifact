#!/usr/bin/env bash

set -euo pipefail

MAKE_JOBS_DEFAULT="8"

MAKE_JOBS="$MAKE_JOBS_DEFAULT"

SCRIPT_NAME="$(basename "$0")"

usage() {
    cat <<EOF
Usage: $SCRIPT_NAME [options]

Build baseline and patched CPython snapshots by running in each directory:
    ./configure
    make -j

Options:
    --jobs <n>              Pass explicit job count to make (uses plain -j when omitted)
    -h, --help              Show this help

Examples:
    $SCRIPT_NAME
    $SCRIPT_NAME --jobs 8
EOF
}

die() {
    echo "error: $*" >&2
    exit 1
}

require_env() {
    local var_name="$1"
    if [ -z "${!var_name:-}" ]; then
        die "environment variable $var_name is undefined"
    fi
}

require_cmd() {
    command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

require_env "BASELINE_PYTHON_DIR"
require_env "BASELINE_BUILD_DIR"
require_env "BASELINE_PYTHON_BIN"
require_env "PATCHED_PYTHON_DIR"
require_env "PATCHED_BUILD_DIR"
require_env "PATCHED_PYTHON_BIN"

prepare_baseline_build_dir() {
    local src_dir="$1"
    local build_dir="$2"

    [ -d "$src_dir" ] || die "baseline source directory does not exist: $src_dir"

    echo "[info] preparing baseline build directory: $build_dir"

    # Force a clean baseline build tree by replacing any existing build dir.
    rm -rf "$build_dir"
    mkdir -p "$build_dir"
    cp -R "$src_dir/." "$build_dir/"
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

canonicalize_existing_path() {
    local path="$1"
    local dir_part
    local base_part
    local abs_dir

    [ -e "$path" ] || die "path does not exist: $path"

    dir_part="$(dirname "$path")"
    base_part="$(basename "$path")"
    abs_dir="$(cd "$dir_part" && pwd -P)" || die "failed to resolve path: $path"

    printf '%s/%s' "$abs_dir" "$base_part"
}

assert_bin_matches_expected() {
    local label="$1"
    local resolved_bin="$2"
    local expected_bin="$3"
    local resolved_abs
    local expected_abs

    resolved_abs="$(canonicalize_existing_path "$resolved_bin")"
    expected_abs="$(canonicalize_existing_path "$expected_bin")"

    if [ "$resolved_abs" != "$expected_abs" ]; then
        die "$label python mismatch: resolved=$resolved_abs expected=$expected_abs"
    fi

    echo "[info] $label binary found at the expected location"
}

while [ "$#" -gt 0 ]; do
    case "$1" in
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

require_cmd cp
require_cmd make
require_cmd mkdir
require_cmd rm

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

prepare_baseline_build_dir "$BASELINE_PYTHON_DIR" "$BASELINE_BUILD_DIR"
prepare_baseline_build_dir "$PATCHED_PYTHON_DIR" "$PATCHED_BUILD_DIR"
run_build "baseline" "$BASELINE_BUILD_DIR"
run_build "patched" "$PATCHED_BUILD_DIR"

BASELINE_RESOLVED_BIN="$(resolve_python_bin "$BASELINE_BUILD_DIR")"
PATCHED_RESOLVED_BIN="$(resolve_python_bin "$PATCHED_BUILD_DIR")"

assert_bin_matches_expected "baseline" "$BASELINE_RESOLVED_BIN" "$BASELINE_PYTHON_BIN"
assert_bin_matches_expected "patched" "$PATCHED_RESOLVED_BIN" "$PATCHED_PYTHON_BIN"

cat <<EOF
[done] builds completed
    baseline snapshot: $BASELINE_PYTHON_DIR
    baseline build: $BASELINE_BUILD_DIR
    baseline python executable: $BASELINE_RESOLVED_BIN
    patched snapshot:  $PATCHED_PYTHON_DIR
    patched build:  $PATCHED_BUILD_DIR
    patched python:  $PATCHED_RESOLVED_BIN
EOF
