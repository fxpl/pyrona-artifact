import streamlit as st
import util

title = "Pre-Freeze Hook"
st.set_page_config(
    page_title=f"Artifact: {title}",
    page_icon="🐍",
    layout="wide",
)

st.title(title)

st.markdown(\
"""
TODO
""")

util.editable_python_block(\
"""
from immutable import freeze, isfrozen
""",
"prefreeze-1")