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
Some objects need to be prepared before they can be frozen. Our design adds
the option to define a `__pre_freeze__` method that is called before an object
is frozen as described in Section "5.4 Pre-Freeze Hook" of the paper.

### Simple Pre-Freeze Hook
""")

util.editable_python_block(\
"""
from immutable import freeze, is_frozen, freezable

@freezable
class A:
    def __pre_freeze__(self):
        print("Pre-freeze hook of A was called")
        print(f"Is self frozen? {is_frozen(self)}")

a = A()

# Freezing a will call the pre-freeze hook with `a` as `self`
freeze(a)

# a is now frozen
print(f"Is a frozen? {is_frozen(a)}")
""",
"prefreeze-1")

st.markdown(\
"""
### Figure 18: Pre-Freeze Enables Explicit Freezing

This recreates Figure 18 from the paper. The class and field have been
renamed here:
""")

util.editable_python_block(\
"""
from immutable import freeze, is_frozen, freezable, explicitlyFreezable

@explicitlyFreezable
class Settings:
    def __init__(self, version):
        self.version = version

# Freeze the `Settings` type
freeze(Settings)

@freezable
class App:
    def __init__(self, version):
        self.settings = Settings(version)

    def __pre_freeze__(self):
        # Manually freeze the explicitly freezable settings object
        freeze(self.settings)

app = App("1.0")

# Freezing calls the pre-freeze hook, thereby freezing the internal
# `Settings` instance that would otherwise cause a problem.
freeze(app)

# app is now frozen
print(f"Is app frozen? {is_frozen(app)}")
print(f"Is app.settings frozen? {is_frozen(app.settings)}")
""",
"prefreeze-2")

st.markdown(\
"""
### Pre-Freeze and Stop Freezing

Exceptions thrown in a pre-freeze hook will cause the freeze to be aborted
""")

util.editable_python_block(\
"""
from immutable import freeze, is_frozen, freezable

@freezable
class D:
    def __pre_freeze__(self):
        raise ValueError("D.__pre_freeze__ says: STOP THE FREEZE")

d = D()

# Freezing calls the pre-freeze hook, which will fail due to
# the raised exception
try:
    freeze(d)
except ValueError as exc:
    print(f"freeze(d) failed as expected: {exc}")

# d is still mutable
print(f"Is d frozen? {is_frozen(d)}")
""",
"prefreeze-3")

st.markdown(\
"""
### Pre-Freeze Hooks Handle Cycles

Each pre-freeze hook is only called once. This enables us to handle cycles:
""")

util.editable_python_block(\
"""
from immutable import freeze, is_frozen, freezable

@freezable
class Echo:
    def __init__(self, value):
        self.field = value
    def __pre_freeze__(self):
        freeze(self.field)

# Create a cycle of objects with pre-freeze hooks calling freeze on each other:
e1 = Echo(None)
e2 = Echo(e1)
e1.field = e2

# Freezing succeeds
freeze(e1)

# Check that e1 and e2 are frozen
print(f"Is e1 frozen? {is_frozen(e1)}")
print(f"Is e2 frozen? {is_frozen(e2)}")
""",
"prefreeze-4")
