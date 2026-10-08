#!/usr/bin/env python3
"""Refresh the uv lockfiles by rebuilding the venvs without --frozen."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import artifact_config as cfg  # noqa: E402

BUILD_VENV = cfg.ARTIFACT_ROOT / "scripts" / "setup" / "2_build_venv.py"


def main() -> None:
    for lock in (
        cfg.ARTIFACT_ROOT / "uv" / "snapshots" / "uv.lock",
        cfg.ARTIFACT_ROOT / "uv" / "stable" / "uv.lock",
    ):
        lock.unlink(missing_ok=True)

    subprocess.run([sys.executable, str(BUILD_VENV), "--no-frozen"], check=True)


if __name__ == "__main__":
    main()
