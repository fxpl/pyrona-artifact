import streamlit as st
import util

title = "Freezing Functions"
st.set_page_config(
    page_title=f"Artifact: {title}",
    page_icon="🐍",
    layout="wide",
)

st.title(title)

st.markdown(\
"""
Functions in Python code are turned into function object. These are used
everywhere in Python and our immutability design needs to handle them.
Newly constructed objects or received arguments can be mutable without
a problem. However, every function also captures mutable state, usually
in two common ways:
- Every function captures a reference to the globals dictionary of the
    defining module
- Functions can capture state from the enclosing scope.

This section shows how we handle function object as described in section
"4.3 Python’s Reliance of Mutable Global State" of the paper.

### Figure 9: Only Freeze Reachable Global State

This is a recreation of Figure 9 from the paper.
""")

util.editable_python_block(\
"""
from immutable import freeze, is_frozen

x = [1, 2]
y = [4, 5]

def read_x(idx):
    return x[idx]

def mod_y(o):
    y.append(o)

# `read_x` can be used to access global state
print(f"mutable read_x(0) returns: {read_x(0)}")
print(f"`y` accessed via `read_x`: {read_x.__globals__["y"]}")

# Freezing `read_x` propagates to `x`
freeze(read_x)
print(f"is read_x frozen? {is_frozen(read_x)}")
print(f"is x frozen? {is_frozen(x)}")

# `read_x` can be used to access global state
print(f"frozen read_x(0) returns: {read_x(0)}")
print(f"frozen read_x(1) returns: {read_x(1)}")

# `y`, `mod_y` and `globals()` and remain mutable
print(f"is y frozen? {is_frozen(y)}")
print(f"is mod_y frozen? {is_frozen(y)}")
print(f"is globals() frozen? {is_frozen(globals())}")
""",
"functions-1")

st.markdown(\
"""
### Figure 11: Freezing locks captured state

This recreates Figure 11 from the paper:

""")

util.editable_python_block(\
"""
from immutable import freeze, is_frozen

x = [1, 2, 3]
def tally():
    sum = 0
    for v in x:
        sum += v
    return sum

# Freezing tally succeeds and propagates to x
freeze(tally)
print(f"tally() returns: {tally()}")

# The outer scope can reassign `x`
x = [1, 2]

# A reassignment of x no-longer effects `tally()`:
print(f"tally() returns: {tally()}")
""",
"functions-2")

st.markdown(\
"""
### Figure 12: State Captured From Enclosing Context

This recreates Figure 12 from the paper:

""")

util.editable_python_block(\
"""
from immutable import freeze, is_frozen

def outer():
    x = 0
    y = 100
    def inner_read():
        return x
    def inner_inc():
        nonlocal x
        x = x + 1
        return x
    return (inner_read, inner_inc)

read, inc = outer()

# This shows how the mutable functions interact
print(f"inc() modifies x: {inc()}")
print(f"read() returns: {read()}")

# Freezing `read` stores the current value of `x`
freeze(read)
print(f"inc() modifies x: {inc()}")
print(f"read() returns: {read()}")

# Freezing `inc` prevents further modification of `x`
freeze(inc)
try:
    inc()
except TypeError as exc:
    print(f"calling frozen inc() failed: {type(exc).__name__}")
""",
"functions-3")
