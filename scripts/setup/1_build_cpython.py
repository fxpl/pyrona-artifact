#!/usr/bin/env python3
"""Build every (config x variant) CPython in the matrix.

For each build we copy the variant's source snapshot into its own build tree,
then run ``./configure`` with the config's flags followed by ``make``.

Builds are incremental: a build is skipped when its tree is already up to date,
i.e. the source snapshot commit and configure flags match the stamp written by
the previous successful build. Pass ``--force`` to rebuild regardless.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import artifact_config as cfg  # noqa: E402
import console  # noqa: E402

STAMP_NAME = ".artifact-build"


def die(msg: str) -> None:
    sys.exit(f"error: {msg}")


def variant_commit(variant: str) -> str | None:
    """The resolved snapshot commit for a variant, from snapshots/info.txt."""
    info = cfg.ARTIFACT_ROOT / "snapshots" / "info.txt"
    if not info.exists():
        return None
    prefix = f"{variant.upper()}_COMMIT="
    for line in info.read_text().splitlines():
        if line.startswith(prefix):
            return line[len(prefix):].strip()
    return None


def build_stamp(build: cfg.Build) -> str | None:
    """Identity of a build's inputs, or None when it can't be determined."""
    commit = variant_commit(build.variant)
    if commit is None:
        return None
    return f"{commit} {' '.join(build.configure_flags)}"


def is_up_to_date(build: cfg.Build, stamp: str | None) -> bool:
    if stamp is None or not build.python_bin.exists():
        return False
    try:
        return (build.build_dir / STAMP_NAME).read_text().strip() == stamp
    except OSError:
        return False


def prepare_build_dir(src: Path, dst: Path) -> None:
    if not src.is_dir():
        die(f"source directory does not exist: {src}")
    # Force a clean tree by replacing any existing build dir.
    shutil.rmtree(dst, ignore_errors=True)
    dst.mkdir(parents=True)
    shutil.copytree(src, dst, dirs_exist_ok=True)


def run_build(build: cfg.Build, jobs: str) -> None:
    dst = build.build_dir
    configure = dst / "configure"
    if not configure.is_file():
        die(f"missing configure script: {configure}")

    console.run(f"configure {build.id}", ["./configure", *build.configure_flags], cwd=dst)
    console.run(f"make clean {build.id}", ["make", "clean"], cwd=dst)
    console.run(f"make {build.id}", ["make", "-j", jobs], cwd=dst)


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
    parser.add_argument(
        "--force",
        action="store_true",
        help="rebuild even when a build is already up to date",
    )
    args = parser.parse_args()

    config = cfg.load()
    cfg.check_env(config)
    builds = config.builds
    if args.only:
        wanted = set(args.only)
        builds = [b for b in builds if b.id in wanted]
        unknown = wanted - {b.id for b in builds}
        if unknown:
            die(f"unknown build id(s): {', '.join(sorted(unknown))}")

    built = 0
    for build in builds:
        stamp = build_stamp(build)
        if not args.force and is_up_to_date(build, stamp):
            console.success(f"build {build.id} (up to date)")
            continue
        with console.section(f"build {build.id}"):
            prepare_build_dir(build.src_dir, build.build_dir)
            run_build(build, args.jobs)
            resolved = resolve_python_bin(build.build_dir)
            if resolved.resolve() != build.python_bin.resolve():
                die(f"{build.id} python mismatch: {resolved} != {build.python_bin}")
            if stamp is not None:
                (build.build_dir / STAMP_NAME).write_text(stamp + "\n")
        built += 1

    console.success(f"built {built} build(s), {len(builds) - built} up to date")


if __name__ == "__main__":
    console.run_main(main)
