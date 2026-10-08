#!/usr/bin/env bash
#
# Run the full setup phase: build every CPython in the matrix, create the
# virtual environments, and prepare pyperformance. Extra arguments are
# forwarded to the CPython build step (e.g. --jobs 8).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARTIFACT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Start from a clean build tree to avoid stale artifacts.
rm -rf "$ARTIFACT_ROOT/build"

python3 "$SCRIPT_DIR/1_build_cpython.py" "$@"
python3 "$SCRIPT_DIR/2_build_venv.py"
python3 "$SCRIPT_DIR/3_pyperformance_setup.py"
