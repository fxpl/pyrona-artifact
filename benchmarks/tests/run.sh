#!/usr/bin/env bash

set -euo pipefail

TESTOPTS="-x test_freeze -x test_ssl -x test_embed"
CLEANUP_RESULTS=0

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

while [ "$#" -gt 0 ]; do
	case "$1" in
		--cleanup-results)
			CLEANUP_RESULTS=1
			shift
			;;
		-h|--help)
			echo "Usage: $0 [--cleanup-results]" >&2
			exit 0
			;;
		*)
			die "unknown argument: $1"
			;;
	esac
done

require_env "BASELINE_BUILD_DIR"
require_env "BASELINE_PYTHON_BIN"
require_env "PATCHED_BUILD_DIR"
require_env "PATCHED_PYTHON_BIN"

# Setup output directory and files
RESULTS_DIR="$SCRIPT_DIR/results"
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
	echo "[info]         '-x test_embed'   because test_embed is flaky on baseline" >&2

	(
		cd "$dir"
		{ time make test TESTOPTS="$TESTOPTS"; } > "$output_file" 2>&1
	)
}

run_make_test "baseline" "$BASELINE_BUILD_DIR" "$BASELINE_OUTPUT_FILE"
run_make_test "patched" "$PATCHED_BUILD_DIR" "$PATCHED_OUTPUT_FILE"

python3 "$SCRIPT_DIR/compare.py" \
	--baseline "$BASELINE_OUTPUT_FILE" \
	--patched "$PATCHED_OUTPUT_FILE"

if [ "$CLEANUP_RESULTS" -eq 1 ]; then
	rm -rf "$RESULTS_DIR"
fi
