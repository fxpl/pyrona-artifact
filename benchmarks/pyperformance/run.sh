
#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

MODE="default"
TIMEOUT=180
ONLINE=0
BENCHMARKS_LIST=""
LIST_ONLY=0
BUILD_ENV=0
CHECK_ENV=0
ONLY_PRINT_ARGS=0
CLEANUP_RESULTS=0

PYPERF_RUN_DIR="$REPO_ROOT/build/pyperf"
RESULTS_DIR="$SCRIPT_DIR/results"
BASELINE_OUTPUT="$RESULTS_DIR/baseline.json"
PATCHED_OUTPUT="$RESULTS_DIR/patched.json"
COMPARE_OUTPUT="$RESULTS_DIR/compare.txt"
PLOT_OUTPUT_PATH="$RESULTS_DIR/results.pdf"

die() {
    echo "error: $*" >&2
    exit 1
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

require_env "STABLE_PYTHON_ENV_ACTIVATE"
require_env "BASELINE_PYTHON_BIN"
require_env "PATCHED_PYTHON_BIN"
require_cmd "source"
require_cmd "mkdir"
require_cmd "pwd"
require_cmd "cd"

usage() {
cat <<'EOF'
Usage: run.sh [options]

Options:
--mode <single|fast|default|rigorous>   Benchmark mode (default: default)
--timeout <number>                      Timeout in seconds (default: 180)
--benchmarks <LIST>                     Comma-separated benchmark selectors
                                        NOTE: `fastapi` is disabled by default since it
                                           is not compatible with our baseline CPython
                                        NOTE: `2to3` requires some external C libraries
--list                                  List pyperformance benchmarks and exits
-h, --help                              Show this help message
--build-env                             Pre-downloads benchmarks to allow offline execution
--online                                Allows pyperformance to download benchmarks
                                        (Off by default for the artifact)
--check-env                             Checks the status of virtual environments
--only-print-args                       Print pyperformance args instead of running it
--cleanup-results                       Remove generated benchmark results before exiting
EOF
}

build_benchmarks_filter() {
    local final_filter="$BENCHMARKS_LIST"

    # Always exclude:
    #   fastapi because it is incompatible with Python 3.15.
    #   2to3 because it requires some external C libraries
    local default_excludes="-fastapi,-2to3"

    if [ "$(uname -s)" = "Darwin" ]; then
        # Exclude dask as it requires additional permissions on MacOS
        default_excludes="$default_excludes,-dask"
    fi

    if [ -n "$final_filter" ]; then
        final_filter="$final_filter,$default_excludes"
    else
        final_filter="$default_excludes"
    fi

    printf '%s' "$final_filter"
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --mode)
            [ "$#" -ge 2 ] || die "missing value for --mode"
            case "$2" in
                single|fast|default|rigorous)
                    MODE="$2"
                    ;;
                *)
                    die "invalid --mode '$2' (expected: single, fast, default, rigorous)"
                    ;;
            esac
            shift 2
            ;;
        --timeout)
            [ "$#" -ge 2 ] || die "missing value for --timeout"
            case "$2" in
                ''|*[!0-9]*)
                    die "--timeout must be a non-negative integer"
                    ;;
                *)
                    TIMEOUT="$2"
                    ;;
            esac
            shift 2
            ;;
        --benchmarks)
            [ "$#" -ge 2 ] || die "missing value for --benchmarks"
            [ -n "$2" ] || die "--benchmarks cannot be empty"
            BENCHMARKS_LIST="$2"
            shift 2
            ;;
        --list)
            LIST_ONLY=1
            shift
            ;;
        --online)
            ONLINE=1
            shift
            ;;
        --build-env)
            BUILD_ENV=1
            CHECK_ENV=1
            shift
            ;;
        --check-env)
            CHECK_ENV=1
            shift
            ;;
        --only-print-args)
            ONLY_PRINT_ARGS=1
            shift
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

mkdir -p "$PYPERF_RUN_DIR"
mkdir -p "$RESULTS_DIR"

ORIGINAL_DIR="$(pwd)"
cd "$PYPERF_RUN_DIR"

if [ "$LIST_ONLY" -eq 1 ]; then
    source "$STABLE_PYTHON_ENV_ACTIVATE"
    pyperformance list
    deactivate
    exit 0
fi

if [ "$BUILD_ENV" -eq 1 ]; then
    source "$STABLE_PYTHON_ENV_ACTIVATE"
    pyperformance venv recreate --python "$BASELINE_PYTHON_BIN" "--benchmarks=-fastapi"
    pyperformance venv recreate --python "$PATCHED_PYTHON_BIN" "--benchmarks=-fastapi"
    deactivate
fi

if [ "$CHECK_ENV" -eq 1 ]; then
    source "$STABLE_PYTHON_ENV_ACTIVATE"
    echo "[done] Validating virtual environments:" >&2
    pyperformance venv show --python "$BASELINE_PYTHON_BIN"
    pyperformance venv show --python "$PATCHED_PYTHON_BIN"
    exit 0
fi

run_pyperformance() {
    local label="$1"
    local bin="$2"
    local output_file="$3"

    if [ -f "$output_file" ]; then
        rm -f "$output_file"
    fi

    echo "[info] running 'pyperformance' for $label" >&2
    echo "[info]     writing output to: $output_file" >&2
    if [ "$ONLINE" -eq 1 ]; then
        echo "[info]     online mode: enabled" >&2
    fi

    local pyperformance_args=(
        run
        --inherit-environ PIP_DISABLE_PIP_VERSION_CHECK
        --python "$bin"
        -o "$output_file"
    )

    if [ "$ONLINE" -eq 0 ]; then
        export PIP_NO_INDEX=1
        pyperformance_args+=(--inherit-environ PIP_NO_INDEX)
    fi

    local benchmarks_filter
    benchmarks_filter="$(build_benchmarks_filter)"
    pyperformance_args+=("--benchmarks=$benchmarks_filter")

    case "$MODE" in
        single)
            pyperformance_args+=(--debug-single-value)
            ;;
        fast)
            pyperformance_args+=(--fast)
            ;;
        default)
            ;;
        rigorous)
            pyperformance_args+=(--rigorous)
            ;;
    esac

    if [ "$TIMEOUT" -ge 1 ]; then
        pyperformance_args+=(--timeout)
        pyperformance_args+=("$TIMEOUT")
    fi

    echo "[info]     using the following args: ${pyperformance_args[@]}" >&2

    if [ "$ONLY_PRINT_ARGS" -eq 0 ]; then
        pyperformance "${pyperformance_args[@]}"
    fi
}

source "$STABLE_PYTHON_ENV_ACTIVATE"

run_pyperformance "baseline" "$BASELINE_PYTHON_BIN" "$BASELINE_OUTPUT"
run_pyperformance "patched" "$PATCHED_PYTHON_BIN" "$PATCHED_OUTPUT"

pyperformance compare "$BASELINE_OUTPUT" "$PATCHED_OUTPUT" --output_style table \
    | awk '!/^\+-+(\+-+)+\+$/' \
    > "$COMPARE_OUTPUT"
cat "$COMPARE_OUTPUT"
python "$SCRIPT_DIR/plot.py" "$COMPARE_OUTPUT" "$PLOT_OUTPUT_PATH"

deactivate

if [ "$CLEANUP_RESULTS" -eq 1 ]; then
	rm -rf "$RESULTS_DIR"
fi
