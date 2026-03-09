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
This website provides a simple interface to interact with our modified
version of Python and to recreate parts of the paper. All bash commands
and Python scripts shown here can also manually be executed in the docker
container to on your local machine.

## Verify Environment

This website expects certain environment variables to be set and binaries
to be present. The following is a dynamic status check:
""")

util.validate_required_envs(util.EXPECTED_ENV, [util.BASELINE_BIN_ENV, util.PATCHED_BIN_ENV])

st.markdown(\
"""
## Tutorial

This artifact uses interactive code blocks to show bash commands or
python scripts before executing them. The run button in the corner
of the code block can be used to run the script in the root of the
docker container. The output is displayed as part of the website.

You can modify the scripts before running them. Be aware that all
modifications will be lost when the website reloads. So make sure
to safe important scripts before changing pages.

Note that these scripts have destructive powers. Deleting files may
break the artifact and require a restart. But all changes should be
contained to the docker container, since we don't mount external files.

Here is an example of a bash script
""")

util.editable_bash_block("echo 'Hello Bash'", "hello-bash", output_lines=2)

st.markdown(\
"""
And this is an editable python script:
"""
)

util.editable_python_block("""print("Howdy, from Python")""", "hello-python", output_lines=2)

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
While a script is running you can change tabs in your browser but closing
the website will stop any running commands.

This website doesn't support standard input for scripts. If you
need this you can always run the commands and python scripts manually
in the docker container.
"""
)
