#!/usr/bin/env python3
"""Render the closing-cost microbenchmark results as standalone LaTeX tables.

Reads the raw per-trial JSON files written by ``run.py`` under
``build/closing-cost`` and emits one standalone, compilable table per interpreter
config (``gil`` and ``nogil``). Each table is written as ``closing-cost-<config>.tex``
and, unless ``--no-compile`` is given, compiled to ``closing-cost-<config>.pdf`` so it
can be ``\\includegraphics``'d into the paper.

Numbers are reported as mean ± sample standard deviation. Each row picks a single
time unit (written in the Objects column) so the values read cleanly. The fastest
operation in each row is highlighted in bold; pickling is compared as the sum of
pickle and unpickle.
"""

from __future__ import annotations

import argparse
import json
import shutil
import statistics
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent.parent / "scripts"))
import artifact_config as cfg  # noqa: E402

RUN_DIR = cfg.ARTIFACT_ROOT / "build" / "closing-cost"

CONFIGS = ["gil", "nogil"]
DATA_ORDER = ["built-in", "user-defined"]
DATA_LABEL = {"built-in": "Built-in types", "user-defined": "User-defined types"}
SIZES = [100, 1_000, 100_000]
SIZE_LABEL = {100: "100", 1_000: "1k", 100_000: "100k"}

@dataclass(frozen=True)
class Column:
    key: str
    header: str
    snapshot: str   # the build that implements this measurement
    operation: str  # the microbench operation that produces it
    steps: tuple[str, ...] = ()  # labels for a split column, in step order


# Columns in display order. Each is fed by exactly one (snapshot, operation).
# `steps` names the sub-measurements of a split column; their count must match
# the arrays the benchmark records.
COLUMNS = [
    Column("pickling", "Pickling", "baseline", "pickling", steps=("pickle", "unpickle")),
    Column("freeze", "Freezing", "immutability", "freeze"),
    Column("close", "Closing", "regions", "close"),
    Column("reclose", "Reclosing", "regions", "reclose"),
    Column("close_tid", "Closing (TID)", "regions_freetid", "close"),
    Column("reclose_tid", "Reclosing (TID)", "regions_freetid", "reclose"),
]

BY_SOURCE = {(c.snapshot, c.operation): c for c in COLUMNS}

# Fixed display unit (factor applied to seconds, label) and decimal places.
UNIT = (1e9, "ns")
DECIMALS = 2

# Width of the (word-wrapping) Data column.
DATA_WIDTH = "1.2cm"

TEMPLATE = r"""\documentclass[border=2pt]{standalone}
\usepackage{booktabs}
\usepackage{multirow}
\usepackage{makecell}
\usepackage{amsmath}
\renewcommand{\cellalign}{tr}
\begin{document}
\begin{tabular}{__COLSPEC__}
\toprule
__HEADER__ \\
\midrule
__ROWS__
\bottomrule
\end{tabular}
\end{document}
"""


@dataclass
class Measure:
    """One measurement: per-step (mean, std), plus the per-trial-summed total.

    A single-step measurement has one step and ``total == steps[0]``; a split
    measurement (e.g. pickling) sums the steps element-wise per trial so the
    total's std captures their covariance.
    """
    steps: list[tuple[float, float]]
    total: tuple[float, float]

    @property
    def is_split(self) -> bool:
        return len(self.steps) > 1


Table = dict[tuple[str, int], dict[str, Measure]]


def mean_std(samples: list[float]) -> tuple[float, float]:
    return statistics.mean(samples), (statistics.stdev(samples) if len(samples) > 1 else 0.0)


def load(config: str) -> Table:
    """Return {(data, size): {column key: Measure}} in seconds for one config."""
    table: Table = {}
    for path in sorted(RUN_DIR.glob(f"{config}-*.json")):
        payload = json.loads(path.read_text())
        operation, data, size = payload["operation"], payload["data"], payload["size"]
        # Strip "<config>-" and the "_<op>_<data>_<size>" suffix to get the snapshot.
        build_id = path.stem[: path.stem.index(f"_{operation}_")]
        snapshot = build_id[len(config) + 1:]
        column = BY_SOURCE.get((snapshot, operation))
        if column is None:
            continue
        arrays = payload["results"]
        raw_steps = [mean_std(a) for a in arrays]
        raw_total = mean_std([sum(trial) for trial in zip(*arrays)]) if len(arrays) > 1 else raw_steps[0]
        # Report per-object cost: dividing mean and std by size is exact, since
        # both scale linearly with the samples.
        steps = [(m / size, s / size) for m, s in raw_steps]
        total = (raw_total[0] / size, raw_total[1] / size)
        table.setdefault((data, size), {})[column.key] = Measure(steps, total)
    return table


def int_digits(value_s: float, factor: float) -> int:
    return len(f"{value_s * factor:.{DECIMALS}f}".split(".")[0])


def pad(value_s: float, factor: float, width: int) -> str:
    """Scaled, fixed-decimal number left-padded with phantom zeros to ``width``
    integer digits, so decimal points and the following $\\pm$ align down a column."""
    text = f"{value_s * factor:.{DECIMALS}f}"
    missing = width - len(text.split(".")[0])
    return (r"\phantom{0}" * missing) + text


def fmt_pm(mean_std_s: tuple[float, float], factor: float, bold: bool, widths: tuple[int, int]) -> str:
    mean, std = mean_std_s
    body = f"{pad(mean, factor, widths[0])} \\pm {pad(std, factor, widths[1])}"
    return rf"{{\boldmath$\mathbf{{{body}}}$}}" if bold else f"${body}$"


def fmt_measure(measure: Measure, factor: float, bold: bool, widths: tuple[int, int]) -> str:
    """Total on top; for a split measurement, the step means below as (a + b)."""
    total = fmt_pm(measure.total, factor, bold, widths)
    if not measure.is_split:
        return total
    breakdown = " + ".join(f"{mean * factor:.{DECIMALS}f}" for mean, _ in measure.steps)
    return rf"\makecell[tr]{{{total} \\ {{\footnotesize ({breakdown})}}}}"


def col_header(column: Column) -> str:
    if not column.steps:
        return column.header
    labels = " + ".join(column.steps)
    return rf"\makecell{{{column.header}\\{{\footnotesize ({labels})}}}}"


def fastest_keys(cell: dict[str, Measure]) -> set[str]:
    """Column keys to bold: the lowest-mean op and any statistically tied with it.

    Scored on each measurement's (possibly summed) total. An op ties the leader
    when its printed error bar overlaps the leader's, i.e. its mean minus its
    stddev falls within the leader's mean plus its stddev; bolding the whole
    group avoids claiming a winner where the spread does not support one.
    """
    if not cell:
        return set()
    best_mean, best_std = min((m.total for m in cell.values()), key=lambda t: t[0])
    threshold = best_mean + best_std
    return {k for k, m in cell.items() if m.total[0] - m.total[1] <= threshold}


def build_tex(table: Table) -> str:
    """Fill the template, including only columns that have data for this config.

    The freetid build is nogil-only, so its TID columns are dropped entirely
    (not left blank) from a config that never measured them.
    """
    factor = UNIT[0]
    columns = [c for c in COLUMNS if any(c.key in cell for cell in table.values())]
    colspec = f"p{{{DATA_WIDTH}}} r " + "r " * len(columns)
    header = " & ".join(["Data", "Objects"] + [col_header(c) for c in columns])

    # Per-column integer-digit widths for the total's mean and std, so the $\pm$
    # lines up down each column regardless of each value's magnitude.
    widths = {
        c.key: (
            max(int_digits(m.total[0], factor) for m in totals),
            max(int_digits(m.total[1], factor) for m in totals),
        )
        for c in columns
        if (totals := [cell[c.key] for cell in table.values() if c.key in cell])
    }

    blocks: list[str] = []
    for data in DATA_ORDER:
        if not any((data, size) in table for size in SIZES):
            continue
        rows: list[str] = []
        for i, size in enumerate(SIZES):
            cell = table.get((data, size), {})
            winners = fastest_keys(cell)

            values = [
                fmt_measure(cell[c.key], factor, c.key in winners, widths[c.key]) if c.key in cell else ""
                for c in columns
            ]
            label = rf"\multirow{{3}}{{=}}{{{DATA_LABEL[data]}}}" if i == 0 else ""
            rows.append(f"{label} & {SIZE_LABEL[size]} & " + " & ".join(values) + r" \\")
        blocks.append("\n".join(rows))

    return (
        TEMPLATE.replace("__COLSPEC__", colspec.strip())
        .replace("__HEADER__", header)
        .replace("__ROWS__", "\n\\midrule\n".join(blocks))
    )


def compile_pdf(tex_path: Path) -> bool:
    """Compile into a scratch dir so only the .pdf lands next to the .tex."""
    tool = shutil.which("latexmk") or shutil.which("pdflatex")
    if tool is None:
        print(f"warning: no LaTeX found; wrote {tex_path.name} but skipped PDF", file=sys.stderr)
        return False
    aux_dir = tex_path.parent / f".{tex_path.stem}-latex"
    aux_dir.mkdir(exist_ok=True)
    common = [f"-output-directory={aux_dir.name}", "-interaction=nonstopmode"]
    if tool.endswith("latexmk"):
        command = [tool, "-pdf", *common, tex_path.name]
    else:
        command = [tool, *common, "-halt-on-error", tex_path.name]
    result = subprocess.run(command, cwd=tex_path.parent, capture_output=True, text=True)
    pdf = aux_dir / tex_path.with_suffix(".pdf").name
    if result.returncode != 0 or not pdf.exists():
        print(result.stdout[-2000:], file=sys.stderr)
        sys.exit(f"error: LaTeX compilation failed for {tex_path.name}")
    shutil.move(str(pdf), str(tex_path.with_suffix(".pdf")))
    shutil.rmtree(aux_dir)
    return True


def generate(configs: list[str] = CONFIGS, output_dir: Path = RUN_DIR, compile: bool = True) -> None:
    """Write (and, unless disabled, compile) one table per config with data."""
    output_dir.mkdir(parents=True, exist_ok=True)
    for config in configs:
        table = load(config)
        if not table:
            print(f"warning: no closing-cost data for config {config!r}, skipping", file=sys.stderr)
            continue
        tex_path = output_dir / f"closing-cost-{config}.tex"
        tex_path.write_text(build_tex(table))
        if not compile:
            print(f"wrote {tex_path}")
        elif compile_pdf(tex_path):
            print(f"wrote {tex_path.with_suffix('.pdf')}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--configs", nargs="+", choices=CONFIGS, default=CONFIGS)
    parser.add_argument("--output-dir", type=Path, default=RUN_DIR)
    parser.add_argument("--no-compile", action="store_true", help="only write .tex")
    args = parser.parse_args()
    generate(args.configs, args.output_dir, compile=not args.no_compile)


if __name__ == "__main__":
    main()
