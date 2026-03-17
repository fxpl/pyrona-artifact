# Artifact Navigation Guide

This guide contains pointers to different parts of the artifact.
This is the primary place to find points to the different parts.

Note: This file is auto generated based on comments in the code base.

<!-- ARTIFACT_GUIDE:START -->

## Benchmarking

- Microbenchmark: Freezing vs. Pickling and Unpickling:
    - [./benchmarks/pickling-vs-freeze/README.md Line 3](./benchmarks/pickling-vs-freeze/README.md#L3)
- PyPerformance Benchmarks:
    - [./benchmarks/pyperformance/README.md Line 3](./benchmarks/pyperformance/README.md#L3)
- Microbenchmark: Direct Sharing Across Sub-interpreters:
    - [./benchmarks/subinterpreters/immutable-matrix-inversion/README.md Line 3](./benchmarks/subinterpreters/immutable-matrix-inversion/README.md#L3)
- Microbenchmark: Running CPython tests:
    - [./benchmarks/tests/README.md Line 3](./benchmarks/tests/README.md#L3)
- The implementation of immutability related decorators:
    - [./snapshots/cpython-patched/Lib/immutable.py Line 31](./snapshots/cpython-patched/Lib/immutable.py#L31)

## Tests

- The collection of tests for immutability:
    - [./snapshots/cpython-patched/Lib/test/test_freeze/README.md Line 4](./snapshots/cpython-patched/Lib/test/test_freeze/README.md#L4)

## Implementation

- The definition of the `Py_CHECKWRITE` macro:
    - [./snapshots/cpython-patched/Include/refcount.h Line 145](./snapshots/cpython-patched/Include/refcount.h#L145)
- The atomic RC branch for immutable objects in Py_INCREF:
    - [./snapshots/cpython-patched/Include/refcount.h Line 392](./snapshots/cpython-patched/Include/refcount.h#L392)
- The atomic RC branch for immutable objects in Py_DECREF:
    - [./snapshots/cpython-patched/Include/refcount.h Line 564](./snapshots/cpython-patched/Include/refcount.h#L564)
- The implementation of the `InterpreterLocal` type:
    - [./snapshots/cpython-patched/Modules/_immutablemodule.c Line 192](./snapshots/cpython-patched/Modules/_immutablemodule.c#L192)
- The implementation of the `SharedField` type:
    - [./snapshots/cpython-patched/Modules/_immutablemodule.c Line 364](./snapshots/cpython-patched/Modules/_immutablemodule.c#L364)
- The pre-freeze hook of function objects:
    - [./snapshots/cpython-patched/Objects/funcobject.c Line 1208](./snapshots/cpython-patched/Objects/funcobject.c#L1208)
- This turns an existing ModuleObject into a proxy object::
    - [./snapshots/cpython-patched/Objects/moduleobject.c Line 1511](./snapshots/cpython-patched/Objects/moduleobject.c#L1511)
- Explanation how weak references work for immutable objects:
    - [./snapshots/cpython-patched/Objects/weakrefobject.c Line 36](./snapshots/cpython-patched/Objects/weakrefobject.c#L36)
- The branch that allows direct sharing for immutable object across sub-interpreters:
    - [./snapshots/cpython-patched/Python/crossinterp.c Line 491](./snapshots/cpython-patched/Python/crossinterp.c#L491)
- Explanation how a stack is used to implement the DFS based SCC algorithm:
    - [./snapshots/cpython-patched/Python/immutability.c Line 252](./snapshots/cpython-patched/Python/immutability.c#L252)
- The state used to track a single freeze call and construct SCCs:
    - [./snapshots/cpython-patched/Python/immutability.c Line 298](./snapshots/cpython-patched/Python/immutability.c#L298)
- The function that rolls back immutability on failure:
    - [./snapshots/cpython-patched/Python/immutability.c Line 2026](./snapshots/cpython-patched/Python/immutability.c#L2026)
- The entry point to the `freeze()` function in C:
    - [./snapshots/cpython-patched/Python/immutability.c Line 2249](./snapshots/cpython-patched/Python/immutability.c#L2249)

<!-- ARTIFACT_GUIDE:END -->

