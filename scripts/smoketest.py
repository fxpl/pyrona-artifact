#!/usr/bin/env python3
"""Smoke test: a fast confidence check that the built artifact works.

Each step runs a command (retried once on failure) with a per-step timeout.
All steps run regardless of earlier failures; the exit code is non-zero if any
step failed. ``--minimal`` skips the longer benchmark trials.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import artifact_config as cfg  # noqa: E402
import console  # noqa: E402

TIMEOUT = float(os.environ.get("SMOKETEST_TIMEOUT_SECONDS", "1200"))
ATTEMPTS = 2
EXPERIMENTS = cfg.ARTIFACT_ROOT / "experiments"


@dataclass
class Step:
    name: str
    cmd: list[str] | None = None
    children: list["Step"] | None = None  # group: run each as a sub-step under a section
    cwd: Path | None = None
    full_only: bool = False  # only run in a non-minimal smoke test


def build_steps(config: cfg.Config) -> list[Step]:
    run_py = [sys.executable, str(EXPERIMENTS / "pyperformance" / "run.py")]
    tests_run = str(EXPERIMENTS / "tests" / "run.py")

    steps = [
        Step(
            "regression tests",
            children=[
                Step(build.id, [sys.executable, tests_run, build.id, "--profile", "smoke"])
                for build in config.builds
            ],
        ),
        Step("pyperformance env check", [*run_py, "--check-env"]),
        Step(
            "benchmark trial: subinterpreters",
            [
                "bash",
                str(EXPERIMENTS / "subinterpreters" / "immutable-matrix-inversion" / "run.sh"),
                "--workers-max", "4",
                "--values-per-worker", "10",
                "--num-trials", "1",
                "--cleanup-results",
            ],
        ),
        Step(
            "benchmark trial: pickling-vs-freezing",
            [
                "bash", str(EXPERIMENTS / "pickling-vs-freeze" / "run.sh"),
                "--size", "10",
                "--num-trials", "1",
                "--cleanup-results",
            ],
        ),
        Step(
            "benchmark trial: pyperformance",
            children=[
                Step(build.id, [*run_py, "--only", build.id, "--mode", "single", "--force"])
                for build in config.builds
            ],
            full_only=True,
        ),
    ]
    return steps


def _attempt(name: str, cmd: list[str], cwd: Path | None = None) -> bool:
    """Run a command up to ATTEMPTS times; True if any attempt succeeds."""
    for attempt in range(1, ATTEMPTS + 1):
        label = name if attempt == 1 else f"{name} (retry {attempt}/{ATTEMPTS})"
        if console.run(label, cmd, cwd=cwd, timeout=TIMEOUT, check=False) == 0:
            return True
    return False


def run_step(index: int, total: int, step: Step) -> bool:
    headline = f"[{index}/{total}] {step.name}"
    if step.children is not None:
        with console.section(headline) as sec:
            results = [_attempt(c.name, c.cmd, c.cwd) for c in step.children]
            if not all(results):
                sec.fail()
        return all(results)
    return _attempt(headline, step.cmd, step.cwd)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--minimal", action="store_true",
        help="skip the longer benchmark trials (pyperformance, tests)",
    )
    args = parser.parse_args()

    config = cfg.load()
    cfg.check_env(config)

    steps = [s for s in build_steps(config) if not (args.minimal and s.full_only)]
    if not args.minimal:
        console.info("this smoke test may take up to 30 minutes")

    passed = 0
    for i, step in enumerate(steps, start=1):
        if run_step(i, len(steps), step):
            passed += 1

    failed = len(steps) - passed
    if failed == 0:
        console.success(f"SUCCESS: {passed} check(s) passed")
    else:
        console.error(f"FAILURE: {failed} check(s) failed, {passed} passed")
        sys.exit(1)


if __name__ == "__main__":
    console.run_main(main)
