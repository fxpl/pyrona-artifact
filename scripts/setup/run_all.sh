#!/usr/bin/env bash
#
# Run the full setup phase: build every CPython in the matrix, create the
# virtual environments, and prepare pyperformance. Extra arguments are
# forwarded to the CPython build step (e.g. --jobs 8).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Bootstrap interpreter (needs Python 3.11+). Override on systems whose default
# python3 is too old, e.g. PYTHON=python3.14 scripts/setup/run_all.sh
PYTHON="${PYTHON:-python3}"

# 1_build_cpython rebuilds only the builds whose inputs changed; pass --force to
# rebuild everything.
"$PYTHON" "$SCRIPT_DIR/1_build_cpython.py" "$@"
"$PYTHON" "$SCRIPT_DIR/2_build_venv.py"
"$PYTHON" "$SCRIPT_DIR/3_pyperformance_setup.py"
