#!/usr/bin/env bash
#
# Run the full setup phase: build every CPython in the matrix, create the
# virtual environments, and prepare pyperformance. Extra arguments are
# forwarded to the CPython build step (e.g. --jobs 8).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1_build_cpython rebuilds only the builds whose inputs changed; pass --force to
# rebuild everything.
python3 "$SCRIPT_DIR/1_build_cpython.py" "$@"
python3 "$SCRIPT_DIR/2_build_venv.py"
python3 "$SCRIPT_DIR/3_pyperformance_setup.py"
