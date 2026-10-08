#!/usr/bin/env python3
"""Materialise the per-variant CPython source snapshots from builds.toml.

For each variant the repository is cloned, the configured ref resolved to a
commit, and that commit exported into ``snapshots/cpython-<variant>``.

The baseline variant uses ``resolve = "merge-base"``: its pinned commit is the
common ancestor of ``ref`` and every other variant, so the committed baseline
is exactly the upstream point the patched branches fork from.
"""

from __future__ import annotations

import argparse
import datetime as dt
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import artifact_config as cfg  # noqa: E402
import console  # noqa: E402


def die(msg: str) -> None:
    sys.exit(f"error: {msg}")


def git(*args: str, cwd: Path | None = None, capture: bool = False, quiet: bool = False) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.DEVNULL if quiet else None,
    )
    return (result.stdout or "").strip()


def resolve_commit(repo_dir: Path, ref: str) -> str:
    # Probe the common ref forms; failed probes are expected, so keep them quiet.
    for candidate in (ref, f"refs/tags/{ref}", f"refs/heads/{ref}", f"refs/remotes/origin/{ref}"):
        try:
            return git(
                "rev-parse", "--verify", f"{candidate}^{{commit}}",
                cwd=repo_dir, capture=True, quiet=True,
            )
        except subprocess.CalledProcessError:
            continue
    die(f"could not resolve ref '{ref}' in {repo_dir}")
    raise AssertionError  # unreachable


def export_commit(repo_dir: Path, commit: str, target: Path) -> None:
    shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True)
    archive = subprocess.Popen(
        ["git", "-C", str(repo_dir), "archive", "--format=tar", commit],
        stdout=subprocess.PIPE,
    )
    extract = subprocess.Popen(["tar", "-xf", "-", "-C", str(target)], stdin=archive.stdout)
    archive.stdout.close()  # let archive receive SIGPIPE if extract dies
    extract.communicate()
    archive.wait()
    if archive.returncode or extract.returncode:
        die(f"failed to export {commit} into {target}")


def commit_date(repo_dir: Path, commit: str) -> str:
    return git("show", "-s", "--format=%cI", commit, cwd=repo_dir, capture=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create CPython source snapshots.")
    parser.add_argument(
        "--no-force",
        dest="force",
        action="store_false",
        help="fail if a snapshot directory already exists",
    )
    args = parser.parse_args()

    for tool in ("git", "tar"):
        if shutil.which(tool) is None:
            die(f"required command not found: {tool}")

    config = cfg.load()
    output_dir = cfg.ARTIFACT_ROOT / "snapshots"
    output_dir.mkdir(exist_ok=True)

    if not args.force:
        for variant in config.variants:
            if variant.src_dir.exists():
                die(f"{variant.src_dir} exists; remove it or rerun without --no-force")

    with tempfile.TemporaryDirectory(prefix="cpython-snapshots-") as tmp_str:
        tmp = Path(tmp_str)

        # One clone per distinct repository URL (immutability/regions share a repo).
        clones: dict[str, Path] = {}
        for variant in config.variants:
            if variant.repo not in clones:
                dest = tmp / f"repo-{len(clones)}"
                console.run(
                    f"clone {variant.repo}",
                    ["git", "clone", "--no-checkout", "--progress", variant.repo, str(dest)],
                )
                clones[variant.repo] = dest

        commits: dict[str, str] = {}
        for variant in config.variants:
            if variant.resolve is None:
                commits[variant.name] = resolve_commit(clones[variant.repo], variant.ref)

        for variant in config.variants:
            if variant.resolve == "merge-base":
                clone = clones[variant.repo]
                upstream = resolve_commit(clone, variant.ref)
                inputs = [upstream]
                for other in config.variants:
                    if other.name == variant.name:
                        continue
                    # Make the other variant's commit reachable in this clone.
                    git("fetch", "--quiet", other.repo, commits[other.name], cwd=clone)
                    inputs.append(commits[other.name])
                console.info(f"resolving {variant.name} as merge-base of {len(inputs)} commits")
                commits[variant.name] = git("merge-base", *inputs, cwd=clone, capture=True)
            elif variant.resolve is not None:
                die(f"unknown resolve strategy for {variant.name}: {variant.resolve}")

        for variant in config.variants:
            commit = commits[variant.name]
            console.info(f"exporting {variant.name} ({commit[:12]}) -> {variant.src_dir}")
            export_commit(clones[variant.repo], commit, variant.src_dir)

        run_at = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        lines = [f"# Generated by {Path(__file__).name} at {run_at}"]
        for variant in config.variants:
            commit = commits[variant.name]
            date = commit_date(clones[variant.repo], commit)
            name = variant.name.upper()
            lines += [
                f"{name}_REPO={variant.repo}",
                f"{name}_REF={variant.ref}",
                f"{name}_COMMIT={commit}",
                f"{name}_DATE={date}",
            ]
        (output_dir / "info.txt").write_text("\n".join(lines) + "\n")

    console.success("snapshots created")
    for variant in config.variants:
        print(f"  {variant.name}: {variant.src_dir} ({commits[variant.name][:12]})")


if __name__ == "__main__":
    console.run_main(main)
