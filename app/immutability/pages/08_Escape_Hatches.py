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
Immutable objects sometimes still need mutable state. Section "6.2 Escape Hatches"
introduces two mechanisms for this:

- `SharedField`: one shared value visible across interpreters
- `InterpreterLocal`: one value per interpreter

These examples mirror the behavior exercised in the tests and show how both
escape hatches can still be used from frozen object graphs.

### SharedField in Frozen Objects

`SharedField` keeps mutable shared state behind an immutable indirection.
The value itself must remain freezable/immutable.
""")

util.editable_python_block(\
"""
from immutable import freeze, is_frozen, SharedField

class Counter:
    # Shared mutable location, but only immutable values can be stored
    count = SharedField(0)

    def __init__(self):
        while True:
            current = self.count.get()
            if self.count.compare_and_swap(current, current + 1):
                break

    @classmethod
    def instances(cls):
        return cls.count.get()

c1 = Counter()
c2 = Counter()
print(f"instances before freeze: {Counter.instances()}")

freeze(Counter)
print(f"is Counter frozen? {is_frozen(Counter)}")

# Counter still updates shared immutable integers through SharedField
c3 = Counter()
print(f"instances after freeze: {Counter.instances()}")
""",
"escape-2")

st.markdown(\
"""
### InterpreterLocal in Frozen Objects

`InterpreterLocal` provides per-interpreter state. A frozen object can hold an
`InterpreterLocal` field and still mutate that interpreter-local value.
""")

util.editable_python_block(\
"""
from immutable import freeze, is_frozen, InterpreterLocal

class SessionState:
    def __init__(self):
        # A fresh list is created lazily per interpreter
        self.events = InterpreterLocal(lambda: [])

state = SessionState()
freeze(state)

print(f"is state frozen? {is_frozen(state)}")

# Still mutable through the interpreter-local escape hatch
state.events.get().append("open")
state.events.get().append("click")
print(f"events in this interpreter: {state.events.get()}")

state.events.set(["reset"])
print(f"events after set: {state.events.get()}")
""",
"escape-3")

st.markdown(\
"""
### SharedField vs InterpreterLocal

- Use `SharedField` when interpreters need to coordinate on one shared value.
- Use `InterpreterLocal` when each interpreter should have isolated local state.

Both are escape hatches: they permit useful mutation patterns while preserving
the immutability guarantees of the surrounding object graph.
""")
