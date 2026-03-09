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

require_wheel_in_wheelhouse() {
	local package_name="$1"
	if ! find "$WHEELHOUSE_DIR" -maxdepth 1 -type f -name "${package_name}-*.whl" | grep -q .; then
		die "required wheel for '${package_name}' not found in wheelhouse: $WHEELHOUSE_DIR"
	fi
}

require_env "BASELINE_PYTHON_BIN"
require_env "PATCHED_PYTHON_BIN"

FAST_MODE=0

case "${1:-}" in
	"" )
		;;
	"--help"|"-h")
		echo "usage: $0 [--fast]" >&2
		exit 0
		;;
	"--fast")
		FAST_MODE=1
		;;
	*)
		die "unknown argument: $1"
		;;
esac

if [ "$#" -gt 1 ]; then
	die "too many arguments"
fi

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

WHEELHOUSE_DIR="${PIP_FIND_LINKS:-$SCRIPT_DIR/wheelhouse-$TARGET_OS-$TARGET_ARCH}"
[ -d "$WHEELHOUSE_DIR" ] || die "wheelhouse directory not found: $WHEELHOUSE_DIR"
export PIP_FIND_LINKS="$WHEELHOUSE_DIR"

require_wheel_in_wheelhouse "setuptools"
require_wheel_in_wheelhouse "wheel"
require_wheel_in_wheelhouse "pyperformance"

VENV_DIR="venv"
"$BASELINE_PYTHON_BIN" -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
python -m pip install --disable-pip-version-check --no-index --find-links "$WHEELHOUSE_DIR" \
	--upgrade "setuptools>=18.5" wheel pyperformance

run_pyperformance() {
	local label="$1"
	local bin="$2"
	local output_file="$3"
	local log_file="$4"

	echo "[info] running 'pyperformance' for $label" >&2
	echo "[info]     writing output to: $output_file" >&2
	echo "[info]     writing pyperformance logs to: $log_file" >&2
	echo "[info]     using wheelhouse: $PIP_FIND_LINKS" >&2

	local pyperformance_args=(
		run
		--inherit-environ PIP_DISABLE_PIP_VERSION_CHECK
		--inherit-environ PIP_NO_INDEX
		--inherit-environ PIP_FIND_LINKS
		-p "$bin"
		-o "$output_file"
		--debug-single-value
	)

	if [ "$FAST_MODE" -eq 1 ]; then
		echo "[info]     fast mode: enabled" >&2
		pyperformance_args+=(--fast)
	fi

	pyperformance "${pyperformance_args[@]}" \
		> "$log_file" 2>&1
}

rm -f "$BASELINE_OUTPUT_FILE"
rm -f "$PATCHED_OUTPUT_FILE"

# Run benchmark
run_pyperformance "baseline" "$BASELINE_PYTHON_BIN" "$BASELINE_OUTPUT_FILE" "$BASELINE_LOG_FILE"
run_pyperformance "patched" "$PATCHED_PYTHON_BIN" "$PATCHED_OUTPUT_FILE" "$PATCHED_LOG_FILE"
