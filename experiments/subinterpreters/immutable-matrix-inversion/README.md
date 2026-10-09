# PyPerformance Benchmarks
<!--
// Artifact[Benchmarking]: Microbenchmark: Direct Sharing Across Sub-interpreters
-->

This test shows that immutable data can be shared across Sub-interpreters
and that this can outperform the baseline and Sub-interpreters that use
pickling for communication.

The microbenchmark is in the `src` folder and has the following files:
- [`./src/matrix.py`](./src/matrix.py): The matrix file used by all benchmarks
- [`./src/baseline.py`](./src/baseline.py): A single threaded sequential
    implementation inverting the number of requested matrices
- [`./src/subinterpreters.py`](./src/subinterpreters.py):
    The script running on the main interpreter scheduling work for other
    sub-interpreters called workers.
- [`./src/subinterpreters_worker.py`](./src/subinterpreters_worker.py):
    The script running on worker sub-interpreters. It receives matrices
    from the main interpreter inverts them and then sends them back.
