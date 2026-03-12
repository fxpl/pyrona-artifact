#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARTIFACT_ROOT="$SCRIPT_DIR/.."
ENV_FILE="$ARTIFACT_ROOT/env.env"
TIMEOUT_SECONDS="${SMOKETEST_TIMEOUT_SECONDS:-300}"
MINIMAL=0

usage() {
    cat <<'EOF'
Usage: smoketest.sh [options]

Options:
  --minimal   Skip longer benchmark checks (benchmark: tests, benchmark: pyperformance)
  -h, --help  Show this help message
EOF
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --minimal)
            MINIMAL=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "error: unknown argument: $1" >&2
            usage
            exit 1
            ;;
    esac
done

[ -f "$ENV_FILE" ] || {
    echo "error: expected env file at $ENV_FILE" >&2
    exit 1
}

# Load the artifact paths so the smoke test can run standalone.
source "$ENV_FILE"

PASS_COUNT=0
FAIL_COUNT=0

pass_step() {
    local step_name="$1"

    echo "[ok] $step_name"
    PASS_COUNT=$((PASS_COUNT + 1))
}

fail_step() {
    local step_name="$1"
    local reason="$2"
    local output_file="$3"

    echo "[fail] $step_name"
    echo "$reason"
    echo "--- command output ---"
    cat "$output_file"
    FAIL_COUNT=$((FAIL_COUNT + 1))
}

expect_contains() {
    local output_file="$1"
    local expected_text="$2"

    grep -qF "$expected_text" "$output_file"
}

expect_fixed_count() {
    local output_file="$1"
    local expected_text="$2"
    local expected_count="$3"

    local actual_count
    actual_count="$(grep -cF "$expected_text" "$output_file" || true)"
    [ "$actual_count" -eq "$expected_count" ]
}

validate_success() {
    return 0
}

run_with_timeout() {
    local timeout_seconds="$1"
    shift

    if command -v timeout >/dev/null 2>&1; then
        timeout "$timeout_seconds" "$@"
        return
    fi

    if command -v gtimeout >/dev/null 2>&1; then
        gtimeout "$timeout_seconds" "$@"
        return
    fi

    python3 - "$timeout_seconds" "$@" <<'PY'
import subprocess
import sys

timeout_seconds = int(sys.argv[1])
command = sys.argv[2:]

try:
    completed = subprocess.run(command, timeout=timeout_seconds, check=False)
except subprocess.TimeoutExpired:
    print(f"error: command timed out after {timeout_seconds} seconds", file=sys.stderr)
    sys.exit(124)

sys.exit(completed.returncode)
PY
}

run_step() {
    local step_name="$1"
    local validator="$2"
    shift 2

    local output_file
    output_file="$(mktemp)"

    if run_with_timeout "$TIMEOUT_SECONDS" "$@" >"$output_file" 2>&1; then
        local failure_reason
        failure_reason=""

        if "$validator" "$output_file" failure_reason; then
            pass_step "$step_name"
        else
            fail_step "$step_name" "$failure_reason" "$output_file"
        fi
    else
        local exit_code="$?"

        if [ "$exit_code" -eq 124 ]; then
            fail_step "$step_name" "command timed out after ${TIMEOUT_SECONDS}s" "$output_file"
        else
            fail_step "$step_name" "command exited with a non-zero status" "$output_file"
        fi
    fi

    rm -f "$output_file"
}

run_step_in_dir() {
    local step_name="$1"
    local validator="$2"
    local work_dir="$3"
    shift 3

    run_step "$step_name" "$validator" bash -c '
        work_dir="$1"
        shift
        cd "$work_dir"
        "$@"
    ' bash "$work_dir" "$@"
}

validate_pyperformance_env_check() {
    local output_file="$1"
    local reason_var="$2"

    if ! expect_contains "$output_file" "[done] Validating virtual environments:"; then
        printf -v "$reason_var" '%s' "missing expected status header"
        return 1
    fi

    if ! expect_fixed_count "$output_file" "(already created)" 2; then
        printf -v "$reason_var" '%s' "expected exactly 2 '(already created)' lines"
        return 1
    fi

    return 0
}

if [ "$MINIMAL" -eq 0 ]; then
    echo "[info] This smoke test may take up to 10 minutes"
fi

run_step_in_dir \
    "immutability tests" \
    validate_success \
    "$PATCHED_BUILD_DIR" \
    "$PATCHED_PYTHON_BIN" -m unittest test.test_freeze

run_step \
    "pyperformance env check" \
    validate_pyperformance_env_check \
    bash "$ARTIFACT_ROOT/benchmarks/pyperformance/run.sh" --check-env


run_step \
    "benchmark: subinterpreters" \
    validate_success \
    bash "$ARTIFACT_ROOT/benchmarks/subinterpreters/immutable-matrix-inversion/run.sh" \
        --workers-max 4 \
        --values-per-worker 10 \
        --num-trials 1 \
        --cleanup-results

run_step \
    "benchmark: pickling-vs-freezing" \
    validate_success \
    bash "$ARTIFACT_ROOT/benchmarks/pickling-vs-freeze/run.sh" \
        --size 10 \
        --num-trials 1 \
        --cleanup-results

if [ "$MINIMAL" -eq 0 ]; then
    run_step \
        "benchmark: pyperformance" \
        validate_success \
        bash "$ARTIFACT_ROOT/benchmarks/pyperformance/run.sh" --mode single --cleanup-results
    run_step \
        "benchmark: tests" \
        validate_success \
        bash "$ARTIFACT_ROOT/benchmarks/tests/run.sh" --cleanup-results
else
    echo "[info] skipping: benchmark: pyperformance"
    echo "[info] skipping: benchmark: tests"
fi

if [ "$FAIL_COUNT" -eq 0 ]; then
    echo "SUCCESS: $PASS_COUNT check(s) passed"
    exit 0
fi

echo "FAILURE: $FAIL_COUNT check(s) failed, $PASS_COUNT passed"
exit 1
