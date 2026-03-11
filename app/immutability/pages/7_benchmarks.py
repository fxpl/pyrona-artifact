import streamlit as st
import util

st.set_page_config(
    page_title="Artifact: Benchmarks",
    page_icon="🐍",
    layout="wide",
)

st.title("Benchmarks")

st.markdown(\
"""
This pages attempts to recreated the benchmarks shown in the paper.
The GUIDE.md file in the artifact root has links to the scripts
implementing these benchmarks.

Note that this artifact runs the benchmarks in a docker container. It
is likely that this reproduction is less stable and may differ from
a run outside a container. And other processes running on your machine
during benchmarking may also effect the results.

Almost all of these scripts are configurable. Try the help command to
see all possible options.
""")

st.markdown(\
"""
### PyPerformance Benchmarks

This runs the default pyperformance benchmarking suite and reports the result.
The script has an optional `--mode` argument with the following options:

- `single`:   Run a single iteration (For debugging)
- `fast`:     Fast but rough answers
- `default`:  Well the default
- `rigorous`: Spend longer running tests to get more accurate resultsF

This benchmark may take:
- 60 minutes on normal mode
- 20 minutes on fast mode

PyPerformance sadly has no simple progress indicator besides the generated logs
that are too big for this website. The logs are instead written to a log file
in the docker container and can be inspected.
""")

util.editable_bash_block(
    """bash benchmarks/pyperformance/run.sh --mode fast""",
    "bench-pyperf",
    output_lines=30,
    on_finished=util.make_pdf_display_callback(
        "benchmarks/pyperformance/results/results.pdf",
    ),
)

st.markdown(\
"""
### Running the Python Test Suite

This microbenchmark runs the test suite of baseline and our patched
python. By default it executes with multiple agents. We use the user
time reported by the `time` command to get the used time across all
cores.

The execution may take up to 10 minutes:
""")

util.editable_bash_block("""bash benchmarks/tests/run.sh""", "bench-tests", output_lines=30)

st.markdown(\
"""
### Freezing vs. Pickling and Unpickling

This microbenchmarks compares the time required to freeze 1'000'000 objects
with the time needed to pickle and unpickle them instead.

The execution may take up to 5 minutes.
""")
util.editable_bash_block("""bash benchmarks/pickling-vs-freeze/run.sh""", "bench-pickle", output_lines=25)

st.markdown(\
"""
### Direct Sharing Across Sub-interpreters

This benchmark uses sub-interpreters to invert 4x4 matrices.
The graph shows the comparison of using pickling vs freezing
as a sharing mechanism.

The execution may take up to 10 minutes.
""")
util.editable_bash_block("""benchmarks/subinterpreters/immutable-matrix-inversion/run.sh""", "bench-direct-sharing", output_lines=25)
