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

die() {
	echo "error: $*" >&2
	exit 1
}

require_env "BASELINE_PYTHON_BIN"
require_env "PATCHED_PYTHON_BIN"

# Setup output directory and files
RESULTS_DIR="$SCRIPT_DIR/results"
BASELINE_LOG_FILE="$RESULTS_DIR/baseline-output.txt"
BASELINE_OUTPUT_FILE="$RESULTS_DIR/baseline.json"
PATCHED_LOG_FILE="$RESULTS_DIR/patched-output.txt"
PATCHED_OUTPUT_FILE="$RESULTS_DIR/patched.json"
mkdir -p "$RESULTS_DIR"

export PIP_DISABLE_PIP_VERSION_CHECK=1

# Setup virtual environment and pyperformance
python3 -m venv venv
source ./venv/bin/activate
python -m pip install --disable-pip-version-check --upgrade pip
python -m pip install --disable-pip-version-check pyperformance

run_pyperformance() {
	local label="$1"
	local bin="$2"
	local output_file="$3"
	local log_file="$4"

	echo "[info] running 'pyperformance' for $label" >&2
	echo "[info]     writing output to: $output_file" >&2
	echo "[info]     redirecting console output to: $log_file" >&2
	pyperformance run \
		--inherit-environ PIP_DISABLE_PIP_VERSION_CHECK \
		-p "$bin" \
		-o "$output_file" \
		> "$log_file" 2>&1
}

# Run benchmark
run_pyperformance "baseline" "$BASELINE_PYTHON_BIN" "$BASELINE_OUTPUT_FILE" "$BASELINE_LOG_FILE"
run_pyperformance "patched" "$PATCHED_PYTHON_BIN" "$PATCHED_OUTPUT_FILE" "$PATCHED_LOG_FILE"
