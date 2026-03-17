import streamlit as st
import util

title = "Freezing Modules"
st.set_page_config(
    page_title=f"Artifact: {title}",
    page_icon="🐍",
    layout="wide",
)

st.title(title)

st.markdown(\
"""
Python modules are stateful objects. Every top-level declaration in a module
is stored in the module object and can normally be reassigned.

Section "4.4 Mutable Module State and C Extensions" describes why this is
challenging for immutability:
- Some modules mostly expose constants and pure functions.
- Other modules keep mutable runtime state to work correctly.

The examples below show how module freezing interacts with both cases.

### TODO
""")

util.editable_python_block(\
"""
from immutable import freeze, is_frozen
import random
""",
"modules-1")
