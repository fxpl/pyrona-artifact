# CPython regression tests
<!--
// Artifact[Tests]: CPython's regression test suite across the build matrix
-->

This runs CPython's own regression test suite on every build in the matrix
(gil/nogil x baseline/immutability/regions) as a correctness check — each build
runs its own `python -m test`.

You must name exactly one build to test (one config per run); this keeps it
explicit and makes it easy to also run the baseline for comparison.

Which tests run is controlled by profiles in [`config.toml`](./config.toml):

- `full` (default) runs the whole suite, excluding a couple of tests that are
  flaky on the baseline build.
- `quick` runs a small common subset for fast confidence.

```bash
# the evaluated version, full suite
python experiments/tests/run.py gil-regions

# a specific profile / another build
python experiments/tests/run.py nogil-regions --profile quick
python experiments/tests/run.py gil-baseline
```

