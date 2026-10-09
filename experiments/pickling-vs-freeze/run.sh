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

usage() {
	echo "Usage: $0 [--size N] [--num-trials N] [--cleanup-results]"
}

SIZE_ARGS=()
TRIAL_ARGS=()
CLEANUP_RESULTS=0

while [ "$#" -gt 0 ]; do
	case "$1" in
		--size)
			if [ "$#" -lt 2 ]; then
				echo "Missing value for --size" >&2
				usage >&2
				exit 1
			fi
			SIZE_ARGS=(--size "$2")
			shift 2
			;;
		--num-trials)
			if [ "$#" -lt 2 ]; then
				echo "Missing value for --num-trials" >&2
				usage >&2
				exit 1
			fi
			TRIAL_ARGS=(--num-trials "$2")
			shift 2
			;;
		--cleanup-results)
			CLEANUP_RESULTS=1
			shift
			;;
		-h|--help)
			usage
			exit 0
			;;
		*)
			echo "Unknown argument: $1" >&2
			usage >&2
			exit 1
			;;
	esac
	done

RESULTS_DIR="results"
FREEZE_RESULTS="$RESULTS_DIR/freeze.json"
PICKLE_RESULTS="$RESULTS_DIR/pickle.json"

mkdir -p "$RESULTS_DIR"

pickle_cmd=(
	"$BASELINE_PYTHON_BIN"
	"$SCRIPT_DIR/microbenchmark.py"
	--collect
	pickle
)
if [ "${#SIZE_ARGS[@]}" -gt 0 ]; then
	pickle_cmd+=("${SIZE_ARGS[@]}")
fi
if [ "${#TRIAL_ARGS[@]}" -gt 0 ]; then
	pickle_cmd+=("${TRIAL_ARGS[@]}")
fi
pickle_cmd+=(--output "$PICKLE_RESULTS")

echo "Collecting pickle timings with baseline Python: $BASELINE_PYTHON_BIN"
"${pickle_cmd[@]}"

freeze_cmd=(
	"$PATCHED_PYTHON_BIN"
	"$SCRIPT_DIR/microbenchmark.py"
	--collect
	freeze
)
if [ "${#SIZE_ARGS[@]}" -gt 0 ]; then
	freeze_cmd+=("${SIZE_ARGS[@]}")
fi
if [ "${#TRIAL_ARGS[@]}" -gt 0 ]; then
	freeze_cmd+=("${TRIAL_ARGS[@]}")
fi
freeze_cmd+=(--output "$FREEZE_RESULTS")

echo "Collecting freeze timings with patched Python: $PATCHED_PYTHON_BIN"
"${freeze_cmd[@]}"

echo "Comparing freeze vs pickle results"
"$BASELINE_PYTHON_BIN" "$SCRIPT_DIR/compare.py" \
	--freeze "$FREEZE_RESULTS" \
	--pickle "$PICKLE_RESULTS"

if [ "$CLEANUP_RESULTS" -eq 1 ]; then
	rm -rf "$RESULTS_DIR"
fi
