#!/usr/bin/env python3
"""Pre-build a pyperformance benchmark venv for each build interpreter.

Runs pyperformance from the stable environment (it is the only venv with the
tool installed) against every configured CPython build, so the benchmarks can
later run offline for all builds.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import artifact_config as cfg  # noqa: E402
import console  # noqa: E402
import pyperf  # noqa: E402

PYPERF_RUN_DIR = cfg.ARTIFACT_ROOT / "build" / "pyperf"


def pyperf_pin(stable_python: Path) -> str:
    """The exact ``pyperf==X`` spec pyperformance pins for a benchmark run.

    ``venv recreate`` installs ``pyperformance==N``, whose own dependency on
    pyperf is unpinned, so it pulls whatever is latest on PyPI. The run then
    installs the frozen pin and, offline, cannot downgrade a newer pyperf to
    match. We pin the common venv here so the two agree.
    """
    out = subprocess.run(
        [
            str(stable_python), "-c",
            "from pyperformance.venv import REQUIREMENTS_FILE, Requirements; "
            "print(Requirements.from_file(REQUIREMENTS_FILE).get('pyperf'))",
        ],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    if not out or not out.startswith("pyperf=="):
        raise RuntimeError(f"could not resolve pinned pyperf spec (got {out!r})")
    return out


def common_venv_python(stable_python: Path, build_python: Path) -> Path:
    """Path to the shared benchmark venv's interpreter for a build."""
    out = subprocess.run(
        [
            str(stable_python), "-m", "pyperformance", "venv", "show",
            "--python", str(build_python),
        ],
        capture_output=True, text=True, check=True, cwd=PYPERF_RUN_DIR,
    ).stdout
    for line in out.splitlines():
        if line.startswith("Virtual environment path:"):
            root = Path(line.split(": ", 1)[1].rsplit(" (", 1)[0].strip())
            return root / "bin" / "python"
    raise RuntimeError(f"could not resolve common venv path:\n{out}")


def main() -> None:
    config = cfg.load()
    cfg.check_env(config)
    pyperf_config = pyperf.load_config()
    PYPERF_RUN_DIR.mkdir(parents=True, exist_ok=True)

    pin = pyperf_pin(config.stable_python_bin)

    for build in config.builds:
        with console.section(f"pyperformance venv {build.id}"):
            console.run(
                "recreate",
                [
                    str(config.stable_python_bin),
                    "-m", "pyperformance", "venv", "recreate",
                    "--python", str(build.python_bin),
                    f"--benchmarks={pyperf_config.benchmark_filter()}",
                ],
                cwd=PYPERF_RUN_DIR,
            )
            console.run(
                f"pin {pin}",
                [
                    str(common_venv_python(config.stable_python_bin, build.python_bin)),
                    "-m", "pip", "install", pin,
                ],
                cwd=PYPERF_RUN_DIR,
            )

    console.success(f"prepared {len(config.builds)} pyperformance venv(s)")


if __name__ == "__main__":
    console.run_main(main)
