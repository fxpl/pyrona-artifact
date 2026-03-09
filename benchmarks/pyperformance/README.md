# PyPerformance Benchmarks
<!--
// Artifact[Benchmarking]: PyPerformance Benchmarks
-->

This runs the PyPerformance default test suite on baseline and our
patched version and compares the results. Note that the numbers will
likely differ depending on the setup.

The benchmark will take roughly 30 minutes to run.

For bundled artifact use, run `./build-venv.sh` to create a
host os/architecture-specific environment
(`venv-macos-arm64`, `venv-macos-x86_64`, `venv-linux-arm64`, or
`venv-linux-x86_64`) and prebuild all PyPerformance benchmark environments with
`pyperformance run --debug-single-value`.

To prepare all target bundles, run the script on each relevant OS and
architecture combination.
