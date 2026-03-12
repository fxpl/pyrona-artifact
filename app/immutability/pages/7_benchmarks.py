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

During testing we noticed that some tests are OS and platform sensitive.
For the paper we used a Ubuntu 22.04.5 LTS machine with 32-Cores and
256 GB ram.
""")

with st.expander("Detailed CPU Specification", expanded=True):
    st.markdown(\
"""
Vendor ID:                AuthenticAMD
  Model name:             AMD Ryzen Threadripper 3970X 32-Core Processor
    CPU family:           23
    Model:                49
    Thread(s) per core:   2
    Core(s) per socket:   32
    Socket(s):            1
    Stepping:             0
    Frequency boost:      enabled
    CPU max MHz:          4549,1211
    CPU min MHz:          2200,0000
    BogoMIPS:             7386.05
    Flags:                fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush mmx fxsr sse sse2 ht syscall nx mmxext fxsr_opt pdpe1gb rdtscp lm con
                          stant_tsc rep_good nopl nonstop_tsc cpuid extd_apicid aperfmperf rapl pni pclmulqdq monitor ssse3 fma cx16 sse4_1 sse4_2 movbe popcnt aes xsave avx f
                          16c rdrand lahf_lm cmp_legacy svm extapic cr8_legacy abm sse4a misalignsse 3dnowprefetch osvw ibs skinit wdt tce topoext perfctr_core perfctr_nb bpex
                          t perfctr_llc mwaitx cpb cat_l3 cdp_l3 hw_pstate ssbd mba ibpb stibp vmmcall fsgsbase bmi1 avx2 smep bmi2 cqm rdt_a rdseed adx smap clflushopt clwb s
                          ha_ni xsaveopt xsavec xgetbv1 xsaves cqm_llc cqm_occup_llc cqm_mbm_total cqm_mbm_local clzero irperf xsaveerptr rdpru wbnoinvd amd_ppin arat npt lbrv
                           svm_lock nrip_save tsc_scale vmcb_clean flushbyasid decodeassists pausefilter pfthreshold avic v_vmsave_vmload vgif v_spec_ctrl umip rdpid overflow_
                          recov succor smca sev sev_es ibpb_exit_to_user
Virtualisation features:
  Virtualisation:         AMD-V
Caches (sum of all):
  L1d:                    1 MiB (32 instances)
  L1i:                    1 MiB (32 instances)
  L2:                     16 MiB (32 instances)
  L3:                     128 MiB (8 instances)
""")


st.markdown(\
"""
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

util.editable_bash_block("""benchmarks/tests/run.sh""", "bench-tests", output_lines=30)

st.markdown(\
"""
### Freezing vs. Pickling and Unpickling

This microbenchmarks compares the time required to freeze 1'000'000 objects
with the time needed to pickle and unpickle them instead.

The execution may take up to 5 minutes.
""")
util.editable_bash_block("""benchmarks/pickling-vs-freeze/run.sh""", "bench-pickle", output_lines=25)

st.markdown(\
"""
### Direct Sharing Across Sub-interpreters

This benchmark uses sub-interpreters to invert 4x4 matrices.
The graph shows the comparison of using pickling vs freezing
as a sharing mechanism.

The execution may take up to 10 minutes.
""")
util.editable_bash_block("""benchmarks/subinterpreters/immutable-matrix-inversion/run.sh""", "bench-direct-sharing", output_lines=25)
