import streamlit as st
import util

st.set_page_config(
    page_title="Artifact: Shallow Immutability",
    page_icon="🐍",
    layout="wide",
)

st.title("Shallow Immutability")

st.markdown(\
"""
Python already has a several objects that are immutable after construction.
As described in Section "2.1 Support for Immutability in Python" and 
"3.2 Immutability by Construction" of the paper. Prominent examples
are `bool`, `int`, `float` and `str`. In our implementation we
call these objects "shallow immutable" since they only enforce immutability
of themselves. Their types or other objects they reference may still be mutable.

In Section "5.3 Immutable By Construction For C-Types" we propose that
shallow immutable objects are automatically frozen if all contained
objects are immutable and a program observes the mutability via `is_frozen()`.

Take this basic example that checks the freezability of different objects:
""")

util.editable_python_block(\
"""
from immutable import is_frozen

print(f"Type of Object  Is it frozen? ")
print(f"Strings:        {is_frozen('A cool string')}")
print(f"Integers:       {is_frozen(1999)}")
print(f"None:           {is_frozen(None)}")
print(f"Booleans:       {is_frozen(True)}")
""",
"shallow-base")

st.markdown(\
"""
Python also has shallow immutable objects that act like containers.
These follow the same rules, meaning that they will be marked as
immutable if all contained objects are immutable and their mutability
is observed.

This example shows this behavior with tuples:
""")

util.editable_python_block(\
"""
from immutable import is_frozen

print(f"Type of Object    Is it frozen? ")
print(f"Tuple of ints:    {is_frozen((1, 2))}")
print(f"Tuple of strings: {is_frozen(('a', 'b'))}")
print(f"Tuple of dicts:   {is_frozen(({}, {}))}")
""",
"shallow-containers")
