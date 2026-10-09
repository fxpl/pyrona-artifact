# Artifact Navigation Guide

This guide contains pointers to different parts of the artifact.
This is the primary place to find points to the different parts.

Note: This file is auto generated based on comments in the code base.

<!-- ARTIFACT_GUIDE:START -->

## Benchmarking

- Microbenchmark: Freezing vs. Pickling and Unpickling:
    - [./experiments/pickling-vs-freeze/README.md Line 3](./experiments/pickling-vs-freeze/README.md#L3)
- PyPerformance Benchmarks:
    - [./experiments/pyperformance/README.md Line 3](./experiments/pyperformance/README.md#L3)
- Microbenchmark: Direct Sharing Across Sub-interpreters:
    - [./experiments/subinterpreters/immutable-matrix-inversion/README.md Line 3](./experiments/subinterpreters/immutable-matrix-inversion/README.md#L3)
- The implementation of immutability related decorators:
    - [./snapshots/cpython-immutability/Lib/immutable.py Line 53](./snapshots/cpython-immutability/Lib/immutable.py#L53)
- The implementation of immutability related decorators:
    - [./snapshots/cpython-regions/Lib/immutable.py Line 56](./snapshots/cpython-regions/Lib/immutable.py#L56)

## Tests

- CPython's regression test suite across the build matrix:
    - [./experiments/tests/README.md Line 3](./experiments/tests/README.md#L3)
- The collection of tests for immutability:
    - [./snapshots/cpython-immutability/Lib/test/test_freeze/README.md Line 4](./snapshots/cpython-immutability/Lib/test/test_freeze/README.md#L4)
- The collection of tests for immutability:
    - [./snapshots/cpython-regions/Lib/test/test_freeze/README.md Line 4](./snapshots/cpython-regions/Lib/test/test_freeze/README.md#L4)

## Implementation

- The definition of the `Py_CHECKWRITE` macro:
    - [./snapshots/cpython-immutability/Include/refcount.h Line 235](./snapshots/cpython-immutability/Include/refcount.h#L235)
- The implementation of the `InterpreterLocal` type:
    - [./snapshots/cpython-immutability/Modules/_immutablemodule.c Line 269](./snapshots/cpython-immutability/Modules/_immutablemodule.c#L269)
- The implementation of the `SharedField` type:
    - [./snapshots/cpython-immutability/Modules/_immutablemodule.c Line 441](./snapshots/cpython-immutability/Modules/_immutablemodule.c#L441)
- The pre-freeze hook of function objects:
    - [./snapshots/cpython-immutability/Objects/funcobject.c Line 1208](./snapshots/cpython-immutability/Objects/funcobject.c#L1208)
- This turns an existing ModuleObject into a proxy object::
    - [./snapshots/cpython-immutability/Objects/moduleobject.c Line 1511](./snapshots/cpython-immutability/Objects/moduleobject.c#L1511)
- The atomic RC branch for immutable objects in Py_INCREF:
    - [./snapshots/cpython-immutability/Objects/object.c Line 369](./snapshots/cpython-immutability/Objects/object.c#L369)
- Explanation how weak references work for immutable objects:
    - [./snapshots/cpython-immutability/Objects/weakrefobject.c Line 36](./snapshots/cpython-immutability/Objects/weakrefobject.c#L36)
- The branch that allows direct sharing for immutable object across sub-interpreters:
    - [./snapshots/cpython-immutability/Python/crossinterp.c Line 493](./snapshots/cpython-immutability/Python/crossinterp.c#L493)
- The definition of the `Py_CHECKWRITE` macro:
    - [./snapshots/cpython-regions/Include/refcount.h Line 237](./snapshots/cpython-regions/Include/refcount.h#L237)
- The implementation of the `InterpreterLocal` type:
    - [./snapshots/cpython-regions/Modules/_immutablemodule.c Line 270](./snapshots/cpython-regions/Modules/_immutablemodule.c#L270)
- The implementation of the `SharedField` type:
    - [./snapshots/cpython-regions/Modules/_immutablemodule.c Line 442](./snapshots/cpython-regions/Modules/_immutablemodule.c#L442)
- The pre-freeze hook of function objects:
    - [./snapshots/cpython-regions/Objects/funcobject.c Line 1208](./snapshots/cpython-regions/Objects/funcobject.c#L1208)
- This turns an existing ModuleObject into a proxy object::
    - [./snapshots/cpython-regions/Objects/moduleobject.c Line 1511](./snapshots/cpython-regions/Objects/moduleobject.c#L1511)
- The atomic RC branch for immutable objects in Py_INCREF:
    - [./snapshots/cpython-regions/Objects/object.c Line 369](./snapshots/cpython-regions/Objects/object.c#L369)
- Explanation how weak references work for immutable objects:
    - [./snapshots/cpython-regions/Objects/weakrefobject.c Line 46](./snapshots/cpython-regions/Objects/weakrefobject.c#L46)
- The branch that allows direct sharing for immutable object across sub-interpreters:
    - [./snapshots/cpython-regions/Python/crossinterp.c Line 493](./snapshots/cpython-regions/Python/crossinterp.c#L493)

<!-- ARTIFACT_GUIDE:END -->

