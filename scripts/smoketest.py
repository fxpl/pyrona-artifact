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
BENCH = cfg.ARTIFACT_ROOT / "experiments"


@dataclass
class Step:
    name: str
    cmd: list[str]
    cwd: Path | None = None
    full_only: bool = False  # only run in a non-minimal smoke test


def build_steps(config: cfg.Config) -> list[Step]:
    builds = {b.id: b for b in config.builds}
    immut = builds["gil-immutability"]
    run_py = [sys.executable, str(BENCH / "pyperformance" / "run.py")]

    return [
        Step(
            "immutability tests",
            [str(immut.python_bin), "-m", "unittest", "test.test_freeze"],
            cwd=immut.build_dir,
        ),
        Step("pyperformance env check", [*run_py, "--check-env"]),
        Step(
            "benchmark trial: subinterpreters",
            [
                "bash",
                str(BENCH / "subinterpreters" / "immutable-matrix-inversion" / "run.sh"),
                "--workers-max", "4",
                "--values-per-worker", "10",
                "--num-trials", "1",
                "--cleanup-results",
            ],
        ),
        Step(
            "benchmark trial: pickling-vs-freezing",
            [
                "bash", str(BENCH / "pickling-vs-freeze" / "run.sh"),
                "--size", "10",
                "--num-trials", "1",
                "--cleanup-results",
            ],
        ),
        Step(
            "benchmark trial: pyperformance",
            [*run_py, "--mode", "single", "--force"],
            full_only=True,
        ),
        Step(
            "benchmark trial: tests",
            ["bash", str(BENCH / "tests" / "run.sh"), "--cleanup-results"],
            full_only=True,
        ),
    ]


def run_step(index: int, total: int, step: Step) -> bool:
    headline = f"[{index}/{total}] {step.name}"
    for attempt in range(1, ATTEMPTS + 1):
        rc = console.run(headline, step.cmd, cwd=step.cwd, timeout=TIMEOUT, check=False)
        if rc == 0:
            return True
        if attempt < ATTEMPTS:
            console.info(f"retrying {step.name} (attempt {attempt + 1}/{ATTEMPTS})")
    return False


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
