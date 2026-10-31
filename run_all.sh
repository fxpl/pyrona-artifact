#!/usr/bin/env bash
set -euo pipefail

# Bootstrap interpreter (needs Python 3.11+). Override on systems whose default
# python3 is too old, e.g. PYTHON=python3.14 scripts/setup/run_all.sh
PYTHON="${PYTHON:-python3}"

scripts/setup/run_all.sh

"$PYTHON" "scripts/smoketest.py"

"$PYTHON" "experiments/pyperformance/run.py"
"$PYTHON" "experiments/closing-cost/run.py"
