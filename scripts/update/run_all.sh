#!/usr/bin/env bash
#
# Run the update phase (maintainers only): regenerate env.env, re-create the
# CPython source snapshots, and rebuild the navigation guide. Extra arguments
# are forwarded to the snapshot step (e.g. --no-force).
#
# Snapshots are wiped so stale variants are pruned and re-exported; build trees
# are left in place because the setup phase rebuilds incrementally (only the
# builds whose source commit actually changed). Refreshing the uv lockfiles
# (3_update_uvlock.py) is intentionally left out: run it on demand after a setup
# build when dependencies actually change.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARTIFACT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

rm -rf "$ARTIFACT_ROOT/snapshots"

python3 "$SCRIPT_DIR/0_generate_env.py"
python3 "$SCRIPT_DIR/1_create_cpython_snapshots.py" "$@"
python3 "$SCRIPT_DIR/2_build_navigation_guide.py" --root "$ARTIFACT_ROOT"
