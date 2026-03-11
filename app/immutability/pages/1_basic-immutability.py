import streamlit as st
import util

st.set_page_config(
    page_title="Artifact: Benchmarks",
    page_icon="🐍",
    layout="wide",
)

st.title("Basic Immutability")

st.markdown(\
"""
This page shows some basic use cases of our immutability design.

Remember that you can always edit the code snippets and test things.

### Basic Freezing

""")

util.editable_python_block(\
"""
from immutable import freeze, isfrozen

# This creates a new dictionary
dict = {"a": "A new dict"}

# Dictionaries are mutable by default
dict["x"] = 42

# This freezes the dictionary
freeze(dict)
print(f"Is `dict` frozen? {isfrozen(dict)}\\n")

# Any attempts to modify the dict should fail. Try uncommenting this:
# dict["y"] = "A new value"
""",
"freeze-basics")

st.markdown(\
"""
### Immutability is Deep

Freezing makes an object deeply immutable, meaning that all contained objects
will also be frozen.
""")

util.editable_python_block(\
"""
from immutable import freeze, isfrozen

# This creates a simple dictionary containing another dictionary
child = {}
dict = {"child": child}

# Freezing `dict` will also freeze the child
freeze(dict)

# Check that both dict and child are frozen
print(f"Is `dict`  frozen? {isfrozen(dict)}")
print(f"Is `child` frozen? {isfrozen(child)}")

# Any attempts to modify the dict and child should fail.
# Try uncommenting this:
# dict["y"] = "A new value"
# child["y"] = "A new value"
""",
"freeze-deep")
