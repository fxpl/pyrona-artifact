#!/usr/bin/env bash

set -euo pipefail

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

require_env "BASELINE_PYTHON_BIN"
require_env "BASELINE_PYTHON_ENV"
require_env "BASELINE_PYTHON_ENV_ACTIVATE"
require_env "PATCHED_PYTHON_BIN"
require_env "PATCHED_PYTHON_ENV"
require_env "PATCHED_PYTHON_ENV_ACTIVATE"
require_env "STABLE_PYTHON_BIN"
require_env "STABLE_PYTHON_ENV"
require_env "STABLE_PYTHON_ENV_ACTIVATE"

require_cmd uv

FROZEN_FLAG="--frozen"
for arg in "$@"; do
    case "$arg" in
        --no-frozen) FROZEN_FLAG="" ;;
        --frozen)    FROZEN_FLAG="--frozen" ;;
        *) die "unknown argument: $arg" ;;
    esac
done

build_snapshot_venv() {
    local label="$1"
    local python_bin="$2"
    local venv_dir="$3"
    local project_dir="$4"

    echo "[info] creating $label venv in: $venv_dir"
    uv venv --python "$python_bin" --clear "$venv_dir"

    echo "[info] syncing $label venv from lockfile at $project_dir"
    UV_PROJECT_ENVIRONMENT="$venv_dir" uv --project "$project_dir" sync --python "$python_bin" $FROZEN_FLAG --all-packages
}

build_snapshot_venv "baseline" "$BASELINE_PYTHON_BIN" "$BASELINE_PYTHON_ENV" "./uv/snapshots/"
build_snapshot_venv "patched"  "$PATCHED_PYTHON_BIN"  "$PATCHED_PYTHON_ENV"  "./uv/snapshots/"
build_snapshot_venv "3.14.3"   "3.14.3"               "$STABLE_PYTHON_ENV"   "./uv/stable/"

[ -f "$BASELINE_PYTHON_ENV_ACTIVATE" ] || die "baseline activate script not found: $BASELINE_PYTHON_ENV_ACTIVATE"
[ -f "$PATCHED_PYTHON_ENV_ACTIVATE" ]  || die "patched activate script not found: $PATCHED_PYTHON_ENV_ACTIVATE"
[ -f "$STABLE_PYTHON_ENV_ACTIVATE" ]  || die "patched activate script not found: $STABLE_PYTHON_ENV_ACTIVATE"

cat <<EOF
[done] venv's have been created
    baseline venv:          $BASELINE_PYTHON_ENV
    baseline venv bin:      $BASELINE_PYTHON_BIN
    baseline venv activate: $BASELINE_PYTHON_ENV_ACTIVATE
    patched venv:           $PATCHED_PYTHON_ENV
    patched venv bin:       $PATCHED_PYTHON_BIN
    patched venv activate:  $PATCHED_PYTHON_ENV_ACTIVATE
    stable venv:            $STABLE_PYTHON_ENV
    stable venv bin:        $STABLE_PYTHON_BIN
    stable venv activate:   $STABLE_PYTHON_ENV_ACTIVATE
EOF
