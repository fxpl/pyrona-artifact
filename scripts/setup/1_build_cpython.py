#!/usr/bin/env python3
"""Build every (config x variant) CPython in the matrix.

For each build we copy the variant's source snapshot into its own build tree,
then run ``./configure`` with the config's flags followed by ``make``.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import artifact_config as cfg  # noqa: E402


def die(msg: str) -> None:
    sys.exit(f"error: {msg}")


def prepare_build_dir(src: Path, dst: Path) -> None:
    if not src.is_dir():
        die(f"source directory does not exist: {src}")
    print(f"[info] preparing build directory: {dst}")
    # Force a clean tree by replacing any existing build dir.
    shutil.rmtree(dst, ignore_errors=True)
    dst.mkdir(parents=True)
    shutil.copytree(src, dst, dirs_exist_ok=True)


def run_build(build: cfg.Build, jobs: str) -> None:
    dst = build.build_dir
    configure = dst / "configure"
    if not configure.is_file():
        die(f"missing configure script: {configure}")

    print(f"[info] building {build.id} in {dst}")
    subprocess.run(["./configure", *build.configure_flags], cwd=dst, check=True)
    subprocess.run(["make", "clean"], cwd=dst, check=True)
    subprocess.run(["make", "-j", jobs], cwd=dst, check=True)


def resolve_python_bin(build_dir: Path) -> Path:
    """Prefer python.exe to avoid matching a 'Python' dir on case-insensitive FS."""
    exe = build_dir / "python.exe"
    if exe.is_file():
        return exe
    unix = build_dir / "python"
    if unix.is_file():
        return unix
    die(f"built python binary not found in {build_dir} (checked python.exe, python)")
    raise AssertionError  # unreachable


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the CPython build matrix.")
    parser.add_argument("--jobs", default="8", help="make -j job count")
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        metavar="BUILD_ID",
        help="build only these ids (e.g. gil-baseline); repeatable",
    )
    args = parser.parse_args()

    config = cfg.load()
    builds = config.builds
    if args.only:
        wanted = set(args.only)
        builds = [b for b in builds if b.id in wanted]
        unknown = wanted - {b.id for b in builds}
        if unknown:
            die(f"unknown build id(s): {', '.join(sorted(unknown))}")

    for build in builds:
        prepare_build_dir(build.src_dir, build.build_dir)
        run_build(build, args.jobs)
        resolved = resolve_python_bin(build.build_dir)
        if resolved.resolve() != build.python_bin.resolve():
            die(f"{build.id} python mismatch: {resolved} != {build.python_bin}")
        print(f"[ok] {build.id}: {resolved}")

    print(f"[done] built {len(builds)} build(s)")


if __name__ == "__main__":
    main()
