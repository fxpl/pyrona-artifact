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
As described in section "2.1 Support for Immutability in Python" and 
"3.2 Immutability by Construction" of the paper. Prominent examples
are `bool`, `int`, `float` and `str`. In our implementation we
call these objects "shallow immutable" since they only enforce immutability
of themselves. Their types or other objects they reference may still be mutable.

In section "5.3 Immutable By Construction For C-Types" we propose that
shallow immutable objects are automatically frozen if all contained
objects are immutable and a program observes the mutability via `isfrozen()`.

Take this basic example that checks the freezability of different objects:
""")

util.editable_python_block(\
"""
from immutable import isfrozen

print(f"Type of Object  Is it frozen? ")
print(f"Strings:        {isfrozen('A cool string')}")
print(f"Integers:       {isfrozen(1999)}")
print(f"None:           {isfrozen(None)}")
print(f"Booleans:       {isfrozen(True)}")
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
from immutable import isfrozen

print(f"Type of Object    Is it frozen? ")
print(f"Tuple of ints:    {isfrozen((1, 2))}")
print(f"Tuple of strings: {isfrozen(('a', 'b'))}")
print(f"Tuple of dicts:   {isfrozen(({}, {}))}")
""",
"shallow-containers")
