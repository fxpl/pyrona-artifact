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

This section shows the solution described in
"4.4.1 Challenge: Modules are Stateful and Mutable."

### Freezing the random module
""")

util.editable_python_block(\
"""
import random
from immutable import freeze, is_frozen

# Freezing the random module will turn it into a proxy object
freeze(random)

# The proxy mode keeps the internal state of the module mutable:
print(f"is random frozen? {is_frozen(random)}")
print(f"is random.randint frozen? {is_frozen(random.randint)}")

# We can still modify the module via the proxy
random.new_field = "We're mutating the interpreter-local state"
print(f"random.new_field is now: {random.new_field}")
""",
"modules-1")

st.markdown(\
"""
### Mutable State and Auto-Imports

The mutable state of modules is stored in `sys.mut_modules`. If neither
`sys.modules` nor `sys.mut_modules` has a mutable version of the module,
it will be imported automatically:
""")

util.editable_python_block(\
"""
import sys
import random
from immutable import freeze, is_frozen

# Freezing the random module will turn it into a proxy object
freeze(random)

# Check that the state in `sys.mut_modules` is mutable
mut_random1 = sys.mut_modules['random']
print(f"is mut_random1 frozen? {is_frozen(mut_random1)}")

# Deleting the module from `sys.mut_modules` will unimport the module
del sys.mut_modules['random']

# The frozen `random` module object is still available.
# Accessing a field will automatically import the random module:
print(f"random.random() returns: {random.random()}")

# Check that `sys.mut_modules` has a new mutable object
mut_random2 = sys.mut_modules['random']
print(f"The random module was reimported, the two instances have different IDs:")
print(f"ID of mut_random1: {hex(id(mut_random1))}")
print(f"ID of mut_random2: {hex(id(mut_random2))}")
""",
"modules-2")
