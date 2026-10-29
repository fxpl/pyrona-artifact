#!/usr/bin/env python3
"""Run the closing-cost microbenchmarks across interpreters and write raw results.

Each operation is benchmarked with the interpreter(s) whose snapshot implements
it: pickling on baseline, freeze on immutability, and close/reclose on both
regions and regions_freetid. Every run dumps its raw per-trial numbers (plus the
configuration) to its own JSON file under ``build/closing-cost``; the plotting script
computes mean/stddev/etc. from those. Unlike pyperformance, these benchmarks are
cheap, so there is no result caching — a run always re-measures.

gil and nogil become separate tables in the paper, so they are the outermost
loop and never compared against each other here.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent.parent / "scripts"))
import artifact_config as cfg  # noqa: E402
import console  # noqa: E402
import results  # noqa: E402

sys.path.insert(0, str(SCRIPT_DIR))
import table  # noqa: E402

MICROBENCH = SCRIPT_DIR / "microbench.py"
RUN_DIR = cfg.ARTIFACT_ROOT / "build" / "closing-cost"

DATA = ["built-in", "user-defined"]
SIZES = [100, 1_000, 100_000]
DEFAULT_TRIALS = 100

# Each operation is run on the snapshot(s) that implement it, in this order.
OP_SNAPSHOTS = {
    "pickling": ["baseline"],
    "freeze": ["immutability"],
    "close": ["regions", "regions_freetid"],
    "reclose": ["regions", "regions_freetid"],
}


def run_one(build: cfg.Build, operation: str, data: str, size: int, out_dir: Path, args: argparse.Namespace) -> None:
    out = out_dir / f"{build.id}_{operation}_{data}_{size}.json"
    console.run(
        f"{operation} size={size} [{build.snapshot}]",
        [
            str(build.python_bin), str(MICROBENCH),
            "--operation", operation,
            "--data", data,
            "--size", str(size),
            "--trials", str(args.trials),
            "--seed", str(args.seed),
            "--output", str(out),
            "--silent", "true",
        ],
    )


def run_data(builds: dict[str, cfg.Build], cfg_name: str, data: str, out_dir: Path, args: argparse.Namespace) -> None:
    for size in args.sizes:
        for operation in args.operations:
            for snapshot in OP_SNAPSHOTS[operation]:
                build = builds.get(f"{cfg_name}-{snapshot}")
                if build is None or not build.python_bin.exists():
                    continue
                run_one(build, operation, data, size, out_dir, args)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", "-t", type=int, default=DEFAULT_TRIALS, help="trials per run")
    parser.add_argument("--seed", type=int, default=1, help="data generation seed")
    parser.add_argument("--sizes", type=int, nargs="+", default=SIZES, help="object counts to sweep")
    parser.add_argument("--configs", nargs="+", help="build configs to run (default: all)")
    parser.add_argument("--data", nargs="+", choices=DATA, default=DATA, help="data kinds to sweep")
    parser.add_argument("--operations", nargs="+", choices=list(OP_SNAPSHOTS), help="operations to run (default: all)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = cfg.load()
    cfg.check_env(config)

    builds = {b.id: b for b in config.builds}
    configs = args.configs or list(config.configs)
    unknown = set(configs) - set(config.configs)
    if unknown:
        sys.exit(f"error: unknown config(s): {', '.join(sorted(unknown))}")
    args.operations = args.operations or list(OP_SNAPSHOTS)

    output = results.RunOutput(RUN_DIR)
    out_dir = output.start()

    for cfg_name in configs:
        with console.section(f"config {cfg_name}"):
            for data in args.data:
                with console.section(data):
                    run_data(builds, cfg_name, data, out_dir, args)

    output.publish()

    with console.section("tables"):
        table.generate()

    console.success(f"closing-cost results written to {RUN_DIR}")


if __name__ == "__main__":
    console.run_main(main)
