#!/usr/bin/env python3
"""Pre-build a pyperformance benchmark venv for each build interpreter.

Runs pyperformance from the stable environment (it is the only venv with the
tool installed) against every (config x variant) CPython, so the benchmarks can
later run offline for all six builds.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import artifact_config as cfg  # noqa: E402
import console  # noqa: E402
import pyperf  # noqa: E402

PYPERF_RUN_DIR = cfg.ARTIFACT_ROOT / "build" / "pyperf"


def main() -> None:
    config = cfg.load()
    cfg.check_env(config)
    pyperf_config = pyperf.load_config()
    PYPERF_RUN_DIR.mkdir(parents=True, exist_ok=True)

    for build in config.builds:
        console.run(
            f"pyperformance venv {build.id}",
            [
                str(config.stable_python_bin),
                "-m", "pyperformance", "venv", "recreate",
                "--python", str(build.python_bin),
                f"--benchmarks={pyperf_config.benchmark_filter()}",
            ],
            cwd=PYPERF_RUN_DIR,
        )

    console.success(f"prepared {len(config.builds)} pyperformance venv(s)")


if __name__ == "__main__":
    console.run_main(main)
