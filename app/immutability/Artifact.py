import streamlit as st
import util

st.set_page_config(
    page_title="Artifact: Overview",
    page_icon="🐍",
    layout="wide",
)

st.title("Artifact Overview")

st.markdown(\
"""

Our paper is a design paper, describing how deep immutability can
be added to Python using dynamic checks. The design aims to be
backwards compatible and allow sharing of immutable objects across
sub-interpreters. The paper describes several problems and presents
our solutions.

In this artifact we want to show our working implementation of the
proposed design.

## This website

This website provides a simple interface to interact with our modified
version of Python and to recreate parts of the paper. All bash commands
and Python scripts shown here can also be executed manually in the Docker
container or on your local machine.

## Smoke Test

### Verify Environment

This website expects certain environment variables to be set and binaries
to be present. The following is a dynamic status check:
""")

util.validate_required_envs(util.EXPECTED_ENV, [util.PATCHED_PYTHON_BIN, util.STABLE_PYTHON_BIN])

st.markdown(\
"""
### Minimal Smoke Test

You can click the "Run" button in the corner to run a minimal smoke test.

This minimal version checks that our patched Python version and all scripts
are available and seem to be work as expected.
""")

util.editable_bash_block("scripts/smoketest.sh --minimal", "smoketest-minimal")


st.markdown(\
"""
### Full Smoke Test

You can click the "Run" button in the corner to run a full smoke test. This
may take up to 10 minutes.

This full version includes all checks from the minimum smoke test. Additionally
it runs the full CPython test-suite of our patched CPython and a trial run of
pyperformance. The entire artifact is in a good state, if this passes.
""")

util.editable_bash_block("scripts/smoketest.sh", "smoketest")


st.markdown(\
"""
## Tutorial

This artifact uses interactive code blocks to show bash commands or
Python scripts. You can run them using the "Run" button in the top-right
corner of each code block. You can also modify a code block before running it.

Be aware that all modifications will be lost when the website reloads.

Note that these scripts have destructive powers. Deleting files may
break the artifact and require a restart. However, all changes should remain
inside the Docker container because we do not mount external files.

Here is an example of a Bash script:
""")

util.editable_bash_block("echo 'Hello Bash'", "hello-bash")

st.markdown(\
"""
And this is an editable Python script:
"""
)

util.editable_python_block("""print("Howdy, from Python")""", "hello-python")

st.markdown(\
"""
Some commands might take a long time to execute. The "Kill Process"
button can be used to terminate the script early. Take this Python
script as an example:
""")

util.editable_python_block(\
"""
import time

for i in range(60):
    print(f"Processing: {i}/60")
    time.sleep(1)
""", "slow-python")

st.markdown(\
"""
While a script is running, you can change tabs in your browser, but closing
the website will stop any running commands.

This website doesn't support standard input for scripts. If you
need this, you can always run the commands and Python scripts manually
in the Docker container.
""")
