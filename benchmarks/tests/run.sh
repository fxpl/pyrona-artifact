#!/usr/bin/env bash

set -euo pipefail

ESTIMATED_RUNTIME="5 minutes"
TESTOPTS="-x test_freeze -x test_ssl"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

require_env() {
	local var_name="$1"
	if [ -z "${!var_name:-}" ]; then
		echo "Missing required environment variable: $var_name" >&2
		exit 1
	fi
}

die() {
	echo "error: $*" >&2
	exit 1
}

require_env "BASELINE_PYTHON_DIR"
require_env "BASELINE_PYTHON_BIN"
require_env "PATCHED_PYTHON_DIR"
require_env "PATCHED_PYTHON_BIN"

# Setup output directory and files
RESULTS_DIR="results"
BASELINE_OUTPUT_FILE="$RESULTS_DIR/baseline-output.txt"
PATCHED_OUTPUT_FILE="$RESULTS_DIR/patched-output.txt"
mkdir -p "$RESULTS_DIR"

run_make_test() {
	local label="$1"
	local dir="$2"
	local output_file="$3"

	[ -d "$dir" ] || die "$label directory does not exist: $dir"
	[ -f "$dir/Makefile" ] || die "missing Makefile in $label directory: $dir"

	echo "[info] running 'make test' for $label in: $dir" >&2
	echo "[info]     writing output to: $output_file" >&2
	echo "[info]     with TESTOPTS='$TESTOPTS'" >&2
	echo "[info]         '-x test_freeze'  to ignore tests added by us" >&2
	echo "[info]         '-x test_ssl'     because test_ssl is flaky on baseline" >&2
	echo "[info]         '-j1' to use a single worker" >&2

	(
		cd "$dir"
		{ time make test TESTOPTS="$TESTOPTS"; } > "$SCRIPT_DIR/$output_file" 2>&1
	)
}

echo "[info] This benchmark can take $ESTIMATED_RUNTIME to run" >&2
echo "" >&2
run_make_test "baseline" "$BASELINE_PYTHON_DIR" "$BASELINE_OUTPUT_FILE"
run_make_test "patched" "$PATCHED_PYTHON_DIR" "$PATCHED_OUTPUT_FILE"

python3 "$SCRIPT_DIR/compare.py" \
	--baseline "$BASELINE_OUTPUT_FILE" \
	--patched "$PATCHED_OUTPUT_FILE"

