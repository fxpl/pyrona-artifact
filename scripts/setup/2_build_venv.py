#!/usr/bin/env python3
"""Create a uv virtual environment for every build plus the stable interpreter."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import artifact_config as cfg  # noqa: E402

SNAPSHOT_PROJECT = cfg.ARTIFACT_ROOT / "uv" / "snapshots"
STABLE_PROJECT = cfg.ARTIFACT_ROOT / "uv" / "stable"


def die(msg: str) -> None:
    sys.exit(f"error: {msg}")


def build_venv(label: str, python: str, venv_dir: Path, project: Path, frozen: bool) -> None:
    print(f"[info] creating {label} venv in {venv_dir}")
    subprocess.run(["uv", "venv", "--python", python, "--clear", str(venv_dir)], check=True)

    print(f"[info] syncing {label} venv from {project}")
    cmd = ["uv", "--project", str(project), "sync", "--python", python, "--all-packages"]
    if frozen:
        cmd.append("--frozen")
    env = {**os.environ, "UV_PROJECT_ENVIRONMENT": str(venv_dir)}
    subprocess.run(cmd, check=True, env=env)

    activate = venv_dir / "bin" / "activate"
    if not activate.is_file():
        die(f"{label} activate script not found: {activate}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create uv venvs for the build matrix.")
    parser.add_argument(
        "--no-frozen",
        dest="frozen",
        action="store_false",
        help="allow uv to update the lockfile instead of requiring it frozen",
    )
    args = parser.parse_args()

    if shutil.which("uv") is None:
        die("required command not found: uv")

    config = cfg.load()

    for build in config.builds:
        build_venv(
            build.id,
            str(build.python_bin),
            build.venv_dir,
            SNAPSHOT_PROJECT,
            args.frozen,
        )

    build_venv(
        f"stable ({config.stable_python})",
        config.stable_python,
        config.stable_venv_dir,
        STABLE_PROJECT,
        args.frozen,
    )

    print(f"[done] created {len(config.builds) + 1} venv(s)")


if __name__ == "__main__":
    main()
