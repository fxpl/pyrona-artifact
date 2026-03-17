import streamlit as st
import util

title = "Sub-Interpreters"
st.set_page_config(
    page_title=f"Artifact: {title}",
    page_icon="🐍",
    layout="wide",
)

st.title(title)

st.markdown(\
"""
Sub-interpreters are still not officially stable, but they are available using
the unstable `_interpreters` module.

### Creating a Sub-Interpreter:

Sub-interpreters take their Python program as a string. The shared argument of
`interp.run_string` can be used to pass arguments to the interpreter. By default
these are pickled and unpickled. This works great for strings
""")

util.editable_python_block(\
'''
import _interpreters as interp

# Define a function that will be pickled and send to the sub-interpreter
def sub_program():
    # Interpreters need to import modules again
    import _interpreters as interp
    print(f"Hello from interpreter {interp.get_current()[0]}.")

# Print the ID of the main interpreter
print(f"Main interpreter ID: {interp.get_current()[0]}")

# This creates a new interpreter
sub = interp.create()
print(f"Created new sub-interpreter: {sub}")

# The `run_func` function takes the function as a string and schedules
# it on the sub-interpreter
interp.run_func(sub, sub_program)

# Clean up the interpreter
interp.destroy(sub)
''',
"subs-1")

st.markdown(\
"""
### Sharing Objects

Sub-interpreters in stable Python can take arguments by setting the
`shared` argument of `run_func`. These are then pickled send to the
other interpreter and unpickled. Our design for immutable objects
enables safe sharing of these objects across sub-interpreters:
""")

util.editable_python_block(\
'''
import _interpreters as interp
from immutable import freeze

# Define a function to run on the interpreter
def sub_program():
    # Get the current interpreter ID
    import _interpreters as interp
    ip_id = interp.get_current()[0]
    # The `id` function returns the memory address of the object.
    print(f"IP {ip_id}: Received {input}")
    print(f"IP {ip_id}: The received object has the ID {hex(id(input))}")

# This creates a new interpreter
sub1 = interp.create()
sub2 = interp.create()
print(f"Created new sub-interpreters: {sub1, sub2}")

# shared can only take a very limited range of types, basically only
# types we defined as shallow-immutable.
obj = (1, 2, 3)

# This `obj` is "mutable" until the immutability is observed. Sending
# it right now will result in different IDs being printed
interp.run_func(sub1, sub_program, shared={"input": obj})
interp.run_func(sub2, sub_program, shared={"input": obj})

# Freezing it, allows the object to be shared, without pickling it.
# The IDs are now the same, since it's the same object:
freeze(obj)
interp.run_func(sub1, sub_program, shared={"input": obj})
interp.run_func(sub2, sub_program, shared={"input": obj})

# Clean up the interpreter
interp.destroy(sub1)
interp.destroy(sub2)
''',
"subs-2")

# FIXME: WHY IS `interp.run_func` BLOCKING??? MatJ
# st.markdown(\
# """
# ### Shared Objects and Shared Fields

# Sub-interpreters in stable Python can take arguments by setting the
# `shared` argument of `run_func`. These are then pickled send to the
# other interpreter and unpickled. Our design for immutable objects
# enables safe sharing of these objects across sub-interpreters:
# """)

# util.editable_python_block(\
# '''
# import _interpreters as interp
# from immutable import freeze, is_frozen, SharedField

# # Define a function to run on the interpreter
# def sub_program():
#     # Get the current interpreter ID
#     import _interpreters as interp
#     ip_id = interp.get_current()[0]
#     # The `id` function returns the memory address of the object.
#     print(f"IP {ip_id}: Started")
#     print(f"IP {ip_id}: Waiting on {input}")

#     # This uses a shared-field as a spin-lock
#     counter = 0
#     while input.get():
#         counter += 1

#     print(f"IP {ip_id}: Counted until {counter}")

# # This creates a new interpreter
# sub1 = interp.create()
# sub2 = interp.create()

# # Create a shared field
# obj = SharedField(True)
# freeze(obj)

# # Have both sub-interpreters spin on obj
# interp.run_func(sub1, sub_program, shared={"input": obj})
# interp.run_func(sub2, sub_program, shared={"input": obj})

# # Send the stop signal to sub-interpreters
# obj.set(False)

# # Clean up the interpreter
# interp.destroy(sub1)
# interp.destroy(sub2)
# ''',
# "subs-2")