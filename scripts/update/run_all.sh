#!/usr/bin/env bash
#
# Run the update phase (maintainers only): regenerate env.env, re-create the
# CPython source snapshots, and rebuild the navigation guide. Extra arguments
# are forwarded to the snapshot step (e.g. --no-force).
#
# Snapshots and build outputs are wiped first so the update starts clean; run
# the setup phase afterwards to compile the fresh snapshots. Refreshing the uv
# lockfiles (3_update_uvlock.py) is intentionally left out: run it on demand
# after a setup build when dependencies actually change.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARTIFACT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

rm -rf "$ARTIFACT_ROOT/snapshots" "$ARTIFACT_ROOT/build"

python3 "$SCRIPT_DIR/0_generate_env.py"
python3 "$SCRIPT_DIR/1_create_cpython_snapshots.py" "$@"
python3 "$SCRIPT_DIR/2_build_navigation_guide.py" --root "$ARTIFACT_ROOT"
