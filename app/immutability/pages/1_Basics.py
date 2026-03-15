import streamlit as st
import util

st.set_page_config(
    page_title="Artifact: Basic Immutability",
    page_icon="🐍",
    layout="wide",
)

st.title("Basic Immutability")

st.markdown(\
"""
Our paper proposes an immutability design that should be backward
compatible with Python. This artifact will show different aspects
of our design and implementation.

We will gradually build up concepts and show different aspects of
the design as described in the paper. You're welcome to edit the
code blocks and experiment with the implementation.

### Basic functions:

Our design adds an `immutable` module to Python. The two main functions for
this page are:
- `isfrozen(obj) -> bool`: Returns `True` if the object is immutable,
    `False` otherwise
- `freeze(obj, ...) -> obj`: Turns the given object immutable and returns
    the first argument.

### Basic Freezing
""")

util.editable_python_block(\
"""
from immutable import freeze, isfrozen

# This creates a new dictionary
data = {"a": "A new dict"}

# Dictionaries are mutable by default
print(f"Is `data` immutable? {isfrozen(data)}")
data["x"] = 42

# This freezes the dictionary
freeze(data)
print(f"Is `data` immutable? {isfrozen(data)}")

# Any attempts to modify the dictionary will fail. Try uncommenting this:
# data["y"] = "A new value"
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
data = {"child": child}

# Freezing `data` will also freeze the child
freeze(data)

# Check that both data and child are frozen
print(f"Is `data` immutable? {isfrozen(data)}")
print(f"Is `child` immutable? {isfrozen(child)}")

# Any attempts to modify data or child will fail.
# Try uncommenting these statements:
# data["y"] = "A new value"
# child["y"] = "A new value"
""",
"freeze-deep")
