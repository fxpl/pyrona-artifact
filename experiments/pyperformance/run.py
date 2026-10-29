#!/usr/bin/env python3
"""Run the pyperformance benchmarks across the six-build matrix.

Each build is benchmarked with the stable environment's pyperformance; a result
is skipped when a cached result with a matching stamp already exists (see
scripts/pyperf.py). Results are then compared per config, baseline-relative:
within gil and within nogil, immutability and regions are compared against that
config's baseline.

All heavy lifting (pyperformance, plotting) is delegated to the stable venv's
Python, so this script only needs the standard library.
"""

from __future__ import annotations

import argparse
import dataclasses
import os
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent.parent / "scripts"))
import artifact_config as cfg  # noqa: E402
import console  # noqa: E402
import pyperf  # noqa: E402
import results  # noqa: E402

RUN_DIR = cfg.ARTIFACT_ROOT / "build" / "pyperf"
COMPARE_DIR = pyperf.RESULTS_DIR / "_compare"
PLOT_PY = SCRIPT_DIR / "plot.py"
SEPARATOR_RE = re.compile(r"^\+[-+]+\+$")

MODE_FLAGS = {
    "single": ["--debug-single-value"],
    "fast": ["--fast"],
    "default": [],
    "rigorous": ["--rigorous"],
}


def run_build(config: cfg.Config, pc: pyperf.PyperfConfig, build: cfg.Build, force: bool) -> Path | None:
    stamp = pyperf.result_stamp(build, pc)
    out = pyperf.result_path(build, stamp)
    # The stamp sidecar is written only after a fully successful run, so it is
    # the completion marker: a partial result left by a failed run has no
    # sidecar and is therefore re-run rather than reused.
    complete = out.exists() and pyperf.stamp_path(build, stamp).exists()
    if complete and not force:
        console.success(f"run {build.id} (cached)")
        return out

    out.parent.mkdir(parents=True, exist_ok=True)
    pyperf.stamp_path(build, stamp).unlink(missing_ok=True)
    out.unlink(missing_ok=True)  # pyperformance refuses to overwrite its -o target
    args = [
        str(config.stable_python_bin), "-m", "pyperformance", "run",
        "--python", str(build.python_bin),
        "-o", str(out),
        "--inherit-environ", "PIP_DISABLE_PIP_VERSION_CHECK",
        f"--benchmarks={pc.benchmark_filter()}",
        *MODE_FLAGS[pc.mode],
    ]
    env = dict(os.environ)
    if not pc.online:
        env["PIP_NO_INDEX"] = "1"
        args += ["--inherit-environ", "PIP_NO_INDEX"]
    if pc.timeout >= 1:
        args += ["--timeout", str(pc.timeout)]

    console.run(f"run {build.id}", args, cwd=RUN_DIR, env=env)
    pyperf.write_stamp(build, pc, stamp)
    return out


def compare(config: cfg.Config, baseline: Path, candidate: Path, label: str, out_dir: Path) -> Path:
    result = subprocess.run(
        [
            str(config.stable_python_bin), "-m", "pyperformance", "compare",
            str(baseline), str(candidate), "--output_style", "table",
        ],
        check=True, text=True, capture_output=True,
    )
    table = "\n".join(
        line for line in result.stdout.splitlines() if not SEPARATOR_RE.match(line)
    )
    txt = out_dir / f"{label}.txt"
    txt.write_text(table + "\n")
    return txt


def compare_all(config: cfg.Config, build_results: dict[str, Path], out_dir: Path) -> None:
    for config_name in config.configs:
        baseline = build_results.get(f"{config_name}-baseline")
        if baseline is None:
            console.info(f"no baseline result for {config_name}; skipping comparison")
            continue
        for snapshot in config.snapshots:
            if snapshot.name == "baseline":
                continue
            candidate = build_results.get(f"{config_name}-{snapshot.name}")
            if candidate is None:
                continue
            label = f"{config_name}-{snapshot.name}"
            console.run(
                f"plot {label}",
                [
                    str(config.stable_python_bin), str(PLOT_PY),
                    str(baseline), str(candidate), str(out_dir / f"{label}.pdf"),
                ],
            )


def check_env(config: cfg.Config) -> None:
    for build in config.builds:
        console.run(
            f"venv show {build.id}",
            [
                str(config.stable_python_bin), "-m", "pyperformance", "venv", "show",
                "--python", str(build.python_bin),
            ],
            cwd=RUN_DIR,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=sorted(MODE_FLAGS), help="override config mode")
    parser.add_argument("--timeout", type=int, help="override per-benchmark timeout (s)")
    parser.add_argument("--online", action="store_true", help="allow benchmark downloads")
    parser.add_argument(
        "--only", action="append", default=[], metavar="BUILD_ID",
        help="run only these build ids (repeatable)",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="re-run even if cached, replacing that build's stamped result",
    )
    parser.add_argument("--list", action="store_true", help="list benchmarks and exit")
    parser.add_argument("--check-env", action="store_true", help="validate venvs and exit")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = cfg.load()
    cfg.check_env(config)
    RUN_DIR.mkdir(parents=True, exist_ok=True)

    if args.list:
        subprocess.run(
            [str(config.stable_python_bin), "-m", "pyperformance", "list"], check=True
        )
        return
    if args.check_env:
        check_env(config)
        return

    pc = pyperf.load_config()
    overrides = {}
    if args.mode:
        overrides["mode"] = args.mode
    if args.timeout is not None:
        overrides["timeout"] = args.timeout
    if args.online:
        overrides["online"] = True
    if overrides:
        pc = dataclasses.replace(pc, **overrides)

    builds = config.builds
    if args.only:
        wanted = set(args.only)
        builds = [b for b in builds if b.id in wanted]
        unknown = wanted - {b.id for b in builds}
        if unknown:
            sys.exit(f"error: unknown build id(s): {', '.join(sorted(unknown))}")

    build_results: dict[str, Path] = {}
    for build in builds:
        out = run_build(config, pc, build, args.force)
        if out is not None:
            build_results[build.id] = out

    # The per-config comparison tables/plots are regenerated every run, so stage
    # them in a timestamped archive dir and only copy up to _compare on success.
    output = results.RunOutput(COMPARE_DIR)
    compare_all(config, build_results, output.start())
    output.publish()
    console.success(f"benchmarked {len(build_results)} build(s)")


if __name__ == "__main__":
    console.run_main(main)
