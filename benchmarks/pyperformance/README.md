# PyPerformance Benchmarks
<!--
// Artifact[Benchmarking]: PyPerformance Benchmarks
-->

This runs the PyPerformance default test suite on baseline and our
patched version and compares the results. Note that the numbers will
likely differ depending on the setup.

The benchmark will take roughly 60 minutes to run.

For bundled artifact use, run `./build_wheelhouse.sh` to create a
host os/architecture-specific wheelhouse
(`wheelhouse-macos-arm64`, `wheelhouse-macos-x86_64`,
`wheelhouse-linux-arm64`, or `wheelhouse-linux-x86_64`).

The `run.sh` script will create its runtime venv automatically and install
`pyperformance` plus bootstrap packages from the local wheelhouse.

To prepare all target bundles, run the script on each relevant OS and
architecture combination.

Running these benchmarks locally on MacOS may produce a popup asking for internet
access from `python.exe` this has to be accepted to complete the benchmarks. Running
this website natively on MacOS sometimes prevents this popup causing the benchmarks
to never finish. To run this benchmark on MacOS you can manually run the following
command:

```
bash -c 'set -a; source snapshots/snapshot-sources.env; set +a; benchmarks/pyperformance/run.sh'
```

