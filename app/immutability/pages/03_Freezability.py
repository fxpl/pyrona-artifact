import streamlit as st
import util

title = "Freezability"
st.set_page_config(
    page_title=f"Artifact: {title}",
    page_icon="🐍",
    layout="wide",
)

st.title(title)

st.markdown(\
"""
A lot of Python code relies on mutable state. When talking to the
community, a common concern was that objects could be turned immutable
under foot. Our design proposes a notion of freezability as described
in Section "5 Freezability".

The `set_freezable(obj, freezability)` function takes an object and
a freezability status. The main values are:
- `FREEZABLE_YES`: freezing allowed
- `FREEZABLE_NO`: freezing denied
- `FREEZABLE_EXPLICIT`: only direct `freeze(obj)` allowed

### YES vs NO

Almost all values are freezable by default but can be made unfreezable.
Take this example:
""")

util.editable_python_block(\
"""
from immutable import freeze, is_frozen, set_freezable, FREEZABLE_NO

x = {}
y = {}

# Prevent y from being frozen
set_freezable(y, FREEZABLE_NO)

# Freezing x will succeed since it's freezable
freeze(x)
print(f"is x frozen? {is_frozen(x)}")

# Freezing y will fail since it's unfreezable
try:
    freeze(y)
except TypeError as exc:
    print(f"freeze(y) failed as expected: {exc}")

# y is still mutable
print(f"is y frozen? {is_frozen(y)}")
y["x"] = x
""",
"freezability-yes-no")

st.markdown(\
"""
### Freezing is an all-or-nothing operation

When freezing a group of objects, freeze either succeeds for all reachable objects,
or fails and leaves all of them mutable.
""")

util.editable_python_block(\
"""
from immutable import freeze, is_frozen, set_freezable, FREEZABLE_YES, FREEZABLE_NO

x = {}
y = {}
z = {}
items = [x, y, z]

# Disable freezing for only one object
set_freezable(y, FREEZABLE_NO)

# Attempting to freeze items will fail and all objects stay mutable
try:
    freeze(items)
except TypeError as exc:
    print(f"freeze(items) failed as expected: {exc}")

# All objects should still be mutable:
print(f"is items frozen? {is_frozen(items)}")
print(f"is x frozen? {is_frozen(x)}")
print(f"is y frozen? {is_frozen(y)}")
print(f"is z frozen? {is_frozen(z)}")

# Making y freezable will allow items to be frozen
set_freezable(y, FREEZABLE_YES)

freeze(items)
print(f"is items frozen? {is_frozen(items)}")
""",
"freezability-all-or-nothing")

st.markdown(\
"""
### EXPLICIT

For some objects, it makes sense to allow freezing, but at the
same time users may want to prevent freezing from accidentally
propagating to these objects. Objects that are explicitly
freezable can be frozen, but only if they are explicitly passed
in as an argument to `freeze()`.

Take this example:
""")

util.editable_python_block(\
"""
from immutable import freeze, is_frozen, set_freezable, FREEZABLE_EXPLICIT

x = {}
y = {}
z = {}
items = [x, y, z]

# Make y explicitly freezable
set_freezable(y, FREEZABLE_EXPLICIT)

# Attempting to freeze items will fail because of y
try:
    freeze(items)
except TypeError as exc:
    print(f"freeze(items) failed as expected: {exc}")

# y is still mutable
y["mutate"] = True
print(f"is y frozen? {is_frozen(y)}")

# Freezing items and explicitly passing y will succeed
freeze(items, y)
print(f"is items frozen? {is_frozen(items)}")
print(f"is y frozen? {is_frozen(y)}")
""",
"freezability-explicit")
