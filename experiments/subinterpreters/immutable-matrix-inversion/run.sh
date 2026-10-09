#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

WORKERS_MAX=16
VALUES_PER_WORKER=200000
NUM_TRIALS=10
BATCH_PER_WORKER=4
RESULTS_DIR="$SCRIPT_DIR/results"
OUTPUT_PATH="$RESULTS_DIR/scaling.json"
PLOT_OUTPUT_PATH="$RESULTS_DIR/scaling_graph.pdf"
CLEANUP_RESULTS=0

die() {
    echo "error: $*" >&2
    exit 1
}

require_nonempty_output() {
    local label="$1"
    local output="$2"
    if [ -z "${output//[[:space:]]/}" ]; then
        die "$label produced empty output"
    fi
}

require_valid_json_output() {
    local label="$1"
    local output="$2"
    if ! printf '%s' "$output" | python -c 'import json, sys; json.load(sys.stdin)' >/dev/null; then
        die "$label produced invalid JSON output"
    fi
}

require_env() {
    local var_name="$1"
    if [ -z "${!var_name:-}" ]; then
        die "environment variable $var_name is undefined"
    fi
}

require_cmd() {
    command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

require_executable() {
    local bin_path="$1"
    [ -x "$bin_path" ] || die "python executable not found or not executable: $bin_path"
}

usage() {
    cat <<'EOF'
Usage: run.sh [options]

Options:
  --workers-max <N>         Max workers for scaling run (default: 16)
  --values-per-worker <N>   Values per worker (default: 200000)
  --num-trials <N>          Trials per configuration (default: 10)
  --output <PATH>           JSON output path
  --plot-output <PATH>      Plot output path
  --cleanup-results         Removes generated benchmark results before exiting
  -h, --help                Show this help message
EOF
}

require_env "PATCHED_PYTHON_ENV_ACTIVATE"
require_env "STABLE_PYTHON_ENV_ACTIVATE"
require_cmd "source"

while [ "$#" -gt 0 ]; do
    case "$1" in
        --workers-max)
            WORKERS_MAX="$2"
            shift 2
            ;;
        --values-per-worker)
            VALUES_PER_WORKER="$2"
            shift 2
            ;;
        --num-trials)
            NUM_TRIALS="$2"
            shift 2
            ;;
        --output)
            OUTPUT_PATH="$2"
            shift 2
            ;;
        --plot-output)
            PLOT_OUTPUT_PATH="$2"
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
            die "unknown argument: $1"
            ;;
    esac
done

mkdir -p "$RESULTS_DIR"
mkdir -p "$(dirname "$OUTPUT_PATH")"
mkdir -p "$(dirname "$PLOT_OUTPUT_PATH")"

run_baseline_single() {
    local venv="$1"

    source $venv

    echo "[info] running baseline.py: values=$VALUES_PER_WORKER" >&2

    local output
    output="$(
        python "$SCRIPT_DIR/src/baseline.py" \
            --scaling-mode \
            --num-values "$VALUES_PER_WORKER" \
            --num-trials "$NUM_TRIALS"
    )"

    require_nonempty_output "baseline.py" "$output"
    require_valid_json_output "baseline.py" "$output"

    deactivate

    echo "$output"
}

# There seems to be a memory leak in BocPy 0.2.0
# BocPy 0.2.1 was supposed to fix this, but then we get other memory
# corruption errors on ARM machines. So, we take 0.2.0, accept the
# memory leak since it happens for both pickling and freezing tests.
# This just filters out the warning, really not ideal, but no time
# to fix it now.
filter_subinterpreters_stderr() {
    local line
    while IFS= read -r line; do
        if [[ "$line" == *"Recycling xidata created on interpeter 0 after the interpreter has shut down may result in cown leak."* ]]; then
            continue
        fi
        echo "$line" >&2
    done
}

run_subinterpreters_series() {
    local venv="$1"
    local with_freeze="$2"

    source $venv

    local first=1
    echo "["
    for num_workers in $(seq 1 "$WORKERS_MAX"); do
        local num_values=$((num_workers * VALUES_PER_WORKER))
        local cmd=(
            python "$SCRIPT_DIR/src/subinterpreters.py"
            --scaling-mode
            --num-workers "$num_workers"
            --num-values "$num_values"
            --num-trials "$NUM_TRIALS"
        )
        if [ "$with_freeze" -eq 1 ]; then
            cmd+=(--freeze)
        fi

        echo "[info] running subinterpreters: workers=$num_workers values=$num_values freeze=$with_freeze" >&2
        local output
        if ! output="$("${cmd[@]}" 2> >(filter_subinterpreters_stderr))"; then
            deactivate
            die "subinterpreters.py failed: workers=$num_workers values=$num_values freeze=$with_freeze"
        fi

        require_nonempty_output "subinterpreters.py" "$output"
        require_valid_json_output "subinterpreters.py" "$output"

        if [ "$first" -eq 0 ]; then
            echo ","
        fi
        first=0
        echo "$output"
    done
    echo "]"

    deactivate
}

SEQUENTIAL_JSON="$(run_baseline_single "$PATCHED_PYTHON_ENV_ACTIVATE")"
SUBINTERPRETERS_PICKLE_JSON="$(run_subinterpreters_series "$PATCHED_PYTHON_ENV_ACTIVATE" 0)"
SUBINTERPRETERS_FROZEN_JSON="$(run_subinterpreters_series "$PATCHED_PYTHON_ENV_ACTIVATE" 1)"

cat > "$OUTPUT_PATH" <<EOF
{
  "experiment": "Invert 4x4 Subinterpreters",
  "config": {
    "workers_max": $WORKERS_MAX,
    "values_per_worker": $VALUES_PER_WORKER,
    "num_trials": $NUM_TRIALS
  },
  "single": $SEQUENTIAL_JSON,
  "subinterpreters_pickle": $SUBINTERPRETERS_PICKLE_JSON,
  "subinterpreters_freeze": $SUBINTERPRETERS_FROZEN_JSON
}
EOF

echo "[done] wrote benchmark results: $OUTPUT_PATH" >&2

source "$STABLE_PYTHON_ENV_ACTIVATE"
if ! python -c 'import json, sys; json.load(open(sys.argv[1], "r", encoding="utf-8"))' "$OUTPUT_PATH" >/dev/null; then
    deactivate
    die "results JSON is invalid: $OUTPUT_PATH"
fi
echo "[info] generating plot" >&2
python "$SCRIPT_DIR/plot.py" --input "$OUTPUT_PATH" --output "$PLOT_OUTPUT_PATH"
echo "[done] wrote plot: $PLOT_OUTPUT_PATH" >&2
deactivate

if [ "$CLEANUP_RESULTS" -eq 1 ]; then
	rm -rf "$RESULTS_DIR"
fi
