import streamlit as st
import util

title = "Types and Decorators"
st.set_page_config(
    page_title=f"Artifact: {title}",
    page_icon="🐍",
    layout="wide",
)

st.title(title)

st.markdown(\
"""
Python represents types as mutable type objects. This poses several challenges for
immutability as described in Section "4.2 Shared Mutable Type Objects". Our design
allows types to be mutable until they are frozen.

In Section "5.2 Decorators: @frozen, @freezable, @explicitlyFreezable, and @unfreezable"
we introduce decorators to adjust the mutability and freezability directly after construction

### `@frozen`

The `@frozen` decorator freezes a class directly after construction.
""")

util.editable_python_block(\
"""
from immutable import frozen, is_frozen

@frozen
class A:
    pass

print(f"Is A frozen? {is_frozen(A)}")
""",
"types-1")


st.markdown(\
"""
### `@freezable`

The `@freezable` decorator makes a class freezable
""")

util.editable_python_block(\
"""
from immutable import freeze, freezable, is_frozen

@freezable
class B:
    pass

# B is mutable and freezable
print(f"Is B frozen? {is_frozen(B)}")
B.field = "B is mutable"

# B and instances of B can be frozen, since B is freezable:
b = B()
freeze(b)

# B and the instance of B are now frozen
print(f"Is b frozen? {is_frozen(b)}")
print(f"Is B frozen? {is_frozen(B)}")
""",
"types-2")

st.markdown(\
"""
### `@unfreezable`

The `@unfreezable` decorator makes a class and all instances unfreezable.
""")

util.editable_python_block(\
"""
from immutable import freeze, unfreezable, is_frozen

@unfreezable
class C:
    pass

# C is mutable and not freezable
print(f"Is C frozen? {is_frozen(C)}")
C.field = "C is mutable"

# C and instances of c can't be frozen:
c = C()
try:
    freeze(c)
except TypeError as exc:
    print(f"freeze(c) failed as expected: {exc}")

# C is still mutable and not freezable
print(f"Is c frozen? {is_frozen(c)}")
print(f"Is C frozen? {is_frozen(C)}")
""",
"types-3")

st.markdown(\
"""
### `@explicitlyFreezable`

The `@explicitlyFreezable` decorator makes a class and all instances explicitly freezable
""")

util.editable_python_block(\
"""
from immutable import freeze, explicitlyFreezable, is_frozen

@explicitlyFreezable
class D:
    pass

# D is mutable after construction
print(f"Is D frozen? {is_frozen(D)}")

# D can be explicitly frozen
freeze(D)

# Instances of D are explicitly freezable
d = D()
instances = [d]
try:
    freeze(instances)
except TypeError as exc:
    print(f"freeze(instances) failed as expected: {exc}")

# Explicitly freezing d succeeds
freeze(instances, d)

# Instance d is now frozen:
print(f"Is d frozen? {is_frozen(d)}")
""",
"types-4")

st.markdown(\
"""
### Functions and Decorators

All of these decorators also work on functions:
""")

util.editable_python_block(\
"""
from immutable import freeze, is_frozen, frozen, freezable, unfreezable, explicitlyFreezable

@frozen
def frozen_func():
    return "cool"

# `frozen_func` is frozen directly after construction
print(f"Is frozen_func frozen? {is_frozen(frozen_func)}")

@explicitlyFreezable
def explicit_func():
    return "this is explicitly freezable"

@freezable
def call_explicitly_freezable():
    return explicit_func()

# `explicit_func` is mutable after construction but freezable
print(f"Is explicit_func frozen? {is_frozen(explicit_func)}")

# Freezing `call_explicitly_freezable` will fail since `explicit_func`
# needs to be explicitly frozen
try:
    freeze(call_explicitly_freezable)
except TypeError as exc:
    print(f"freeze(call_explicitly_freezable) failed as expected: {exc}")

# Explicitly freezing `explicit_func` will succeed
freeze(call_explicitly_freezable, explicit_func)
print(f"Is explicit_func frozen? {is_frozen(explicit_func)}")

""",
"types-5")
