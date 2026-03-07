#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

require_env() {
	local var_name="$1"
	if [ -z "${!var_name:-}" ]; then
		echo "Missing required environment variable: $var_name" >&2
		exit 1
	fi
}

require_env "BASELINE_PYTHON_BIN"
require_env "PATCHED_PYTHON_BIN"

RESULTS_DIR="results"
FREEZE_RESULTS="$RESULTS_DIR/freeze.json"
PICKLE_RESULTS="$RESULTS_DIR/pickle.json"

mkdir -p "$RESULTS_DIR"

echo "Collecting pickle timings with baseline Python: $BASELINE_PYTHON_BIN"
"$BASELINE_PYTHON_BIN" "$SCRIPT_DIR/microbenchmark.py" \
	--collect pickle \
	--output "$PICKLE_RESULTS"

echo "Collecting freeze timings with patched Python: $PATCHED_PYTHON_BIN"
"$PATCHED_PYTHON_BIN" "$SCRIPT_DIR/microbenchmark.py" \
	--collect freeze \
	--output "$FREEZE_RESULTS"

echo "Comparing freeze vs pickle results"
"$BASELINE_PYTHON_BIN" "$SCRIPT_DIR/compare.py" \
	--freeze "$FREEZE_RESULTS" \
	--pickle "$PICKLE_RESULTS"
