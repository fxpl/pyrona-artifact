# PyPerformance Benchmarks
<!--
// Artifact[Benchmarking]: PyPerformance Benchmarks
-->

This runs the PyPerformance default test suite on baseline and our
patched version and compares the results. Note that the numbers will
likely differ depending on the setup.

The benchmark will take roughly 60 minutes to run.

The `fastapi` benchmark includes a C-extension that is not yet
compatible with the baseline or our patch. That benchmark is therefore
disabled.
