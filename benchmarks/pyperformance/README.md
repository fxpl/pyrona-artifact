# PyPerformance Benchmarks
<!--
// Artifact[Benchmarking]: PyPerformance Benchmarks
-->

This runs the PyPerformance default test suite on baseline and our
patched version and compares the results. Note that the numbers will
likely differ depending on the setup.

The benchmark will take roughly 60 minutes to run.

### Prebuild Wheels

pyperformance, by default downloads the benchmarks. To make this
artifact self contained and reproducible we include some wheelhouses
containing all the needed packages to run pyperformance and all
benchmarks. The `run.sh` script creates its runtime venv automatically
and installs `pyperformance` plus bootstrap packages from the local
wheelhouse.

We can't provide wheelhouses for all platforms and architectures. If your
combination is missing, you can pass the `--online` flag to the `run.sh`
script. Or, manually build a local wheelhouse using:

```
./build_wheelhouse.sh
```

### Trouble Shooting

Running these benchmarks locally on MacOS may produce a popup asking for internet
access from `python.exe` this has to be accepted to complete the benchmarks. Running
this website natively on MacOS sometimes prevents this popup causing the benchmarks
to never finish. To run this benchmark on MacOS you can manually run the following
command:

```
bash -c 'set -a; source snapshots/snapshot-sources.env; set +a; benchmarks/pyperformance/run.sh'
```

