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

USE_PREMADE_VENV=1
for arg in "$@"; do
	case "$arg" in
		--no-premade-venv)
			USE_PREMADE_VENV=0
			;;
		--help|-h)
			echo "usage: $0 [--no-premade-venv]" >&2
			exit 0
			;;
		*)
			die "unknown argument: $arg"
			;;
	esac
done

detect_target_os() {
	local host_os_raw
	host_os_raw="$(uname -s)"
	case "$host_os_raw" in
		Darwin)
			echo "macos"
			;;
		Linux)
			echo "linux"
			;;
		*)
			echo "$host_os_raw" | tr '[:upper:]' '[:lower:]'
			;;
	esac
}

detect_target_arch() {
	local host_arch_raw
	host_arch_raw="$(uname -m)"
	case "$host_arch_raw" in
		arm64|aarch64)
			echo "arm64"
			;;
		x86_64|amd64)
			echo "x86_64"
			;;
		*)
			die "unsupported host architecture: $host_arch_raw"
			;;
	esac
}

# Setup output directory and files
RESULTS_DIR="$SCRIPT_DIR/results"
BASELINE_LOG_FILE="$RESULTS_DIR/baseline-output.txt"
BASELINE_OUTPUT_FILE="$RESULTS_DIR/baseline.json"
PATCHED_LOG_FILE="$RESULTS_DIR/patched-output.txt"
PATCHED_OUTPUT_FILE="$RESULTS_DIR/patched.json"
mkdir -p "$RESULTS_DIR"

export PIP_DISABLE_PIP_VERSION_CHECK=1
export PIP_NO_INDEX=1

TARGET_OS="$(detect_target_os)"
TARGET_ARCH="$(detect_target_arch)"
PREMADE_VENV_DIR="$SCRIPT_DIR/venv-$TARGET_OS-$TARGET_ARCH"

if [ "$USE_PREMADE_VENV" -eq 1 ] && [ -x "$PREMADE_VENV_DIR/bin/python" ]; then
	echo "[info] using premade pyperformance environment: $PREMADE_VENV_DIR" >&2
	source "$PREMADE_VENV_DIR/bin/activate"
	command -v pyperformance >/dev/null 2>&1 || die "pyperformance not found in premade venv: $PREMADE_VENV_DIR"
else
	if [ "$USE_PREMADE_VENV" -eq 1 ]; then
		echo "[info] premade venv not found, creating fresh environment at: $SCRIPT_DIR/venv" >&2
	else
		echo "[info] --no-premade-venv set, creating fresh environment at: $SCRIPT_DIR/venv" >&2
	fi

	python3 -m venv "$SCRIPT_DIR/venv"
	source "$SCRIPT_DIR/venv/bin/activate"
	python -m pip install --disable-pip-version-check --upgrade pip
	python -m pip install --disable-pip-version-check pyperformance
fi

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
		--inherit-environ PIP_NO_INDEX \
		-p "$bin" \
		-o "$output_file" \
		> "$log_file" 2>&1
}

# Run benchmark
run_pyperformance "baseline" "$BASELINE_PYTHON_BIN" "$BASELINE_OUTPUT_FILE" "$BASELINE_LOG_FILE"
run_pyperformance "patched" "$PATCHED_PYTHON_BIN" "$PATCHED_OUTPUT_FILE" "$PATCHED_LOG_FILE"
