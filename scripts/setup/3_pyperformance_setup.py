#!/usr/bin/env python3
"""Prepare the pyperformance virtual environments used by the benchmarks."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import artifact_config as cfg  # noqa: E402

RUN_SH = cfg.ARTIFACT_ROOT / "benchmarks" / "pyperformance" / "run.sh"


def main() -> None:
    subprocess.run(["bash", str(RUN_SH), "--build-env"], check=True)


if __name__ == "__main__":
    main()
