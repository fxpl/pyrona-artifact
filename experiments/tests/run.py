#!/usr/bin/env python3
"""Run CPython's regression test suite for one build.

Runs the named build's ``make test`` for the selected profile — a correctness
check (pass/fail), not a performance comparison. ``make test`` runs regrtest in
``--fast-ci`` mode (parallel, extra resources, reruns) rather than a plain
``python -m test``, and rebuilds the interpreter first if it is stale. Exactly
one build is tested per run; the exit code is non-zero if its tests failed.
"""

from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent.parent / "scripts"))
import artifact_config as cfg  # noqa: E402
import console  # noqa: E402

CONFIG_PATH = SCRIPT_DIR / "config.toml"


def load_profile(name: str | None) -> tuple[str, dict]:
    with CONFIG_PATH.open("rb") as fh:
        data = tomllib.load(fh)["tests"]
    profiles = data["profiles"]
    name = name or data["default"]
    if name not in profiles:
        sys.exit(f"error: unknown profile '{name}' (have: {', '.join(sorted(profiles))})")
    return name, profiles[name]


def test_exists(build: cfg.Build, name: str) -> bool:
    """Whether a regrtest test (module or package) is present in a build's stdlib."""
    base = build.build_dir / "Lib" / "test"
    return (base / f"{name}.py").is_file() or (base / name).is_dir()


def test_cmd(profile: dict, select: list[str]) -> list[str]:
    """`make test` command, routing selection through TESTOPTS.

    TESTOPTS is appended after `--fast-ci`'s own flags, so regrtest's selection
    flags work from there. jobs/timeout override `--fast-ci`'s defaults (-j0,
    600s) only when the profile sets a non-zero value.
    """
    testopts = list(select)
    jobs = profile.get("jobs", 0)
    if jobs:
        testopts += ["-j", str(jobs)]
    exclude = profile.get("exclude", [])
    # A dotted name (e.g. test_foo.Class.method) is a single case/method: skip it
    # with -i while the rest of the suite runs. A bare name is a whole module (-x).
    for name in (n for n in exclude if "." in n):
        testopts += ["-i", name]
    modules = [n for n in exclude if "." not in n]
    if modules:
        # -x reads every following name as an exclusion, so it must come last.
        testopts += ["-x", *modules]

    args = ["make", "test"]
    timeout = profile.get("timeout", 0)
    if timeout:
        args.append(f"TESTTIMEOUT={timeout}")
    args.append("TESTOPTS=" + " ".join(testopts))
    return args


def run_build(build: cfg.Build, profile: dict) -> bool:
    """Run the profile's tests for one build; return True if it passed."""
    select = list(profile.get("select", []))

    if not select:
        # No explicit selection: run the whole suite as one step, logs inline.
        rc = console.run(
            build.id, test_cmd(profile, []), cwd=build.build_dir, check=False
        )
        return rc == 0

    # Explicit selection: one sub-step per test, so each collapses to ✓/✗ and
    # tests absent from this build are shown as skipped rather than erroring.
    failed: list[str] = []
    with console.section(build.id, collapse=False) as sec:
        for name in select:
            if not test_exists(build, name):
                console.skip(f"test `{name}` (not in {build.id})")
                continue
            rc = console.run(
                f"test `{name}`", test_cmd(profile, [name]),
                cwd=build.build_dir, check=False,
            )
            if rc != 0:
                failed.append(name)
        if failed:
            sec.fail()
    return not failed


def main() -> None:
    config = cfg.load()
    builds = {b.id: b for b in config.builds}

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "build", choices=sorted(builds), metavar="BUILD_ID",
        help="which build to test, one per run (e.g. gil-regions, nogil-baseline)",
    )
    parser.add_argument("--profile", help="config profile to run (default: config's `default`)")
    args = parser.parse_args()

    cfg.check_env(config)
    build = builds[args.build]
    profile_name, profile = load_profile(args.profile)

    console.info(f"test profile: {profile_name}")
    if run_build(build, profile):
        console.success(f"tests passed for {build.id}")
    else:
        console.error(f"tests failed for {build.id}")
        sys.exit(1)


if __name__ == "__main__":
    console.run_main(main)
