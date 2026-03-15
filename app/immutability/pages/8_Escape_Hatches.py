import streamlit as st
import util

title = "Escape Hatches"
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
"escape-1")