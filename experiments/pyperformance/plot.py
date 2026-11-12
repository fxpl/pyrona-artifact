import argparse
import json
import math
import re
import statistics
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch


ROW_RE = re.compile(r"^\|\s*(?P<benchmark>[^|]+?)\s*\|\s*(?P<baseline>[^|]+?)\s*\|\s*(?P<patched>[^|]+?)\s*\|\s*(?P<change>[^|]+?)\s*\|\s*(?P<significance>[^|]+?)\s*\|$")
CHANGE_RE = re.compile(r"(?P<value>[\d.]+)x\s+(?P<direction>slower|faster)")
START_DATE_RE = re.compile(r"^Start date:\s+(?P<date>\d{4}-\d{2}-\d{2})\b")
Y_AXIS_MIN = 0.7
Y_AXIS_MAX = 1.3
SEPARATOR_RE = re.compile(r"^\+[-+=]+\+$")
STAMP_KEYS_TO_MATCH = (
    "pyperf_config",
    "machine.arch",
    "machine.cores",
    "machine.cpu",
    "machine.freq",
    "machine.os",
)


def _stamp_path(result_path: Path) -> Path:
    return result_path.with_suffix(".stamp.txt")


def _read_stamp(result_path: Path) -> dict[str, str]:
    stamp_path = _stamp_path(result_path)
    if not stamp_path.exists():
        raise FileNotFoundError(
            f"Missing stamp file for {result_path}: expected {stamp_path}"
        )

    stamp_data: dict[str, str] = {}
    for line in stamp_path.read_text().splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        stamp_data[key] = value
    return stamp_data


def validate_results_compatible(baseline_path: Path, candidate_path: Path) -> None:
    baseline_stamp = _read_stamp(baseline_path)
    candidate_stamp = _read_stamp(candidate_path)

    mismatches: list[str] = []
    for key in STAMP_KEYS_TO_MATCH:
        baseline_value = baseline_stamp.get(key)
        candidate_value = candidate_stamp.get(key)
        if baseline_value != candidate_value:
            mismatches.append(
                f"{key}: {baseline_value!r} != {candidate_value!r}"
            )

    if mismatches:
        details = "; ".join(mismatches)
        raise ValueError(
            "Refusing to compare incompatible pyperformance results: "
            f"{details}"
        )


def _extract_benchmark_samples(result_path: Path) -> dict[str, list[float]]:
    data = json.loads(result_path.read_text())
    samples: dict[str, list[float]] = {}

    for benchmark in data["benchmarks"]:
        name = benchmark["metadata"]["name"]
        values = [
            sample
            for run in benchmark.get("runs", [])
            for sample in run.get("values", [])
        ]
        if values:
            samples[name] = values

    return samples


def _standard_error(samples: list[float]) -> float:
    if len(samples) < 2:
        return 0.0
    return statistics.stdev(samples) / math.sqrt(len(samples))


def build_compare_table(python_bin: Path, baseline_path: Path, candidate_path: Path) -> str:
    result = subprocess.run(
        [
            str(python_bin),
            "-m",
            "pyperformance",
            "compare",
            str(baseline_path),
            str(candidate_path),
            "--output_style",
            "table",
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    return "\n".join(
        line for line in result.stdout.splitlines() if not SEPARATOR_RE.match(line)
    )


def parse_results(compare_table: str, baseline_path: Path, candidate_path: Path) -> tuple[list[str], list[float], list[float], list[bool]]:
    benchmarks: list[str] = []
    normalized_values: list[float] = []
    error_values: list[float] = []
    is_significant: list[bool] = []
    baseline_samples = _extract_benchmark_samples(baseline_path)
    patched_samples = _extract_benchmark_samples(candidate_path)

    for line in compare_table.splitlines():
        match = ROW_RE.match(line)
        if not match:
            continue

        benchmark_name = match.group("benchmark").strip()
        if benchmark_name == "Benchmark":
            continue

        change_match = CHANGE_RE.search(match.group("change"))
        if not change_match:
            continue

        value = float(change_match.group("value"))
        direction = change_match.group("direction")
        normalized = value if direction == "slower" else 1.0 / value
        significance_text = match.group("significance").strip()
        significant = significance_text.startswith("Significant")
        baseline_values = baseline_samples.get(benchmark_name)
        patched_values = patched_samples.get(benchmark_name)
        if not baseline_values or not patched_values:
            continue

        baseline_mean = statistics.fmean(baseline_values)
        patched_mean = statistics.fmean(patched_values)
        baseline_error = _standard_error(baseline_values)
        patched_error = _standard_error(patched_values)
        propagated_error = normalized * math.sqrt(
            (baseline_error / baseline_mean) ** 2 + (patched_error / patched_mean) ** 2
        )

        benchmarks.append(benchmark_name)
        normalized_values.append(normalized)
        error_values.append(propagated_error)
        is_significant.append(significant)

    if not benchmarks:
        raise ValueError(
            f"No benchmark rows found when comparing {baseline_path} against {candidate_path}"
        )

    return benchmarks, normalized_values, error_values, is_significant


def extract_start_dates(compare_table: str) -> tuple[str, str] | None:
    dates = [
        match.group("date")
        for line in compare_table.splitlines()
        if (match := START_DATE_RE.match(line.strip()))
    ]
    if len(dates) >= 2:
        return dates[0], dates[1]
    return None


def geometric_mean(values: list[float]) -> float:
    return math.exp(sum(math.log(value) for value in values) / len(values))


def build_title(normalized_values: list[float], is_significant: list[bool]) -> str:
    all_geomean = geometric_mean(normalized_values)
    significant_values = [value for value, significant in zip(normalized_values, is_significant) if significant]
    if significant_values:
        significant_geomean = geometric_mean(significant_values)
        return (
            "PyPerformance Benchmark Results (Normalized). "
            f"Geomean: {significant_geomean:.3f}x significant; {all_geomean:.3f}x all"
        )
    return f"PyPerformance Benchmark Results (Normalized). Geomean: {all_geomean:.3f}x all"


@dataclass
class Comparison:
    compare_table: str
    benchmarks: list[str]
    normalized_values: list[float]
    error_values: list[float]
    is_significant: list[bool]

    def geomeans(self) -> tuple[float | None, float]:
        significant = [v for v, s in zip(self.normalized_values, self.is_significant) if s]
        return (
            geometric_mean(significant) if significant else None,
            geometric_mean(self.normalized_values),
        )


def compare_results(baseline_path: Path, candidate_path: Path) -> Comparison:
    validate_results_compatible(baseline_path, candidate_path)
    compare_table = build_compare_table(Path(sys.executable), baseline_path, candidate_path)
    return Comparison(compare_table, *parse_results(compare_table, baseline_path, candidate_path))


def draw_bars(
    ax,
    positions: list[int],
    comparison: Comparison,
    *,
    linewidth: float,
    error_kw: dict,
    y_min: float | None = None,
    y_max: float | None = None,
    clip_fontsize: float | None = None,
) -> None:
    """Draw one bar per benchmark, growing from the 1.0 baseline.

    When ``y_min``/``y_max`` are given, bars beyond them are clipped at the
    axis edge and labelled with their true value so outliers are not hidden.
    """
    for index, value, error, significant in zip(
        positions,
        comparison.normalized_values,
        comparison.error_values,
        comparison.is_significant,
    ):
        clipped = (y_min is not None and value < y_min) or (y_max is not None and value > y_max)
        shown = min(max(value, y_min if y_min is not None else value), y_max if y_max is not None else value)
        ax.bar(
            index,
            shown - 1.0,
            bottom=1.0,
            yerr=None if clipped else error,
            color="red" if value > 1.0 else "green",
            alpha=0.8 if significant else 0.3,
            edgecolor="black",
            linewidth=linewidth,
            error_kw=error_kw,
        )
        if clipped and clip_fontsize is not None:
            below = value < 1.0
            ax.annotate(
                f"{value:.2f}",
                xy=(index, shown),
                xytext=(1.5, 1.5 if below else -1.5),
                textcoords="offset points",
                ha="left",
                va="bottom" if below else "top",
                fontsize=clip_fontsize,
                clip_on=False,
            )


def plot_results(
    baseline_path: Path,
    candidate_path: Path,
    output_path: Path,
) -> None:
    comparison = compare_results(baseline_path, candidate_path)
    compare_table = comparison.compare_table
    start_dates = extract_start_dates(compare_table)
    resolved_table_output_path = output_path.with_suffix(".txt")
    resolved_table_output_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_table_output_path.write_text(compare_table + "\n", encoding="utf-8")

    benchmarks = comparison.benchmarks
    normalized_values = comparison.normalized_values
    is_significant = comparison.is_significant

    plt.rcParams["font.size"] = 10
    plt.rcParams["pdf.fonttype"] = 42

    fig, ax = plt.subplots(figsize=(16, 8))

    draw_bars(
        ax,
        list(range(len(benchmarks))),
        comparison,
        linewidth=0.5,
        error_kw={"elinewidth": 0.8, "capsize": 2, "capthick": 0.8, "ecolor": "black"},
    )

    ax.axhline(y=1.0, color="black", linestyle="--", linewidth=1)
    ax.set_xlabel("Note: Insignificant results shaded light", fontsize=12, fontweight="normal")
    ax.set_ylabel("Normalized Performance (Baseline = 1.0)", fontsize=12, fontweight="bold")
    ax.set_title(build_title(normalized_values, is_significant), fontsize=14, fontweight="bold")
    ax.set_xticks(range(len(benchmarks)))
    ax.set_xticklabels(benchmarks, rotation=90, fontsize=9)
    ax.tick_params(axis="y", labelsize=11)
    ax.set_ylim(Y_AXIS_MIN, Y_AXIS_MAX)
    ax.legend(
        handles=[
            Patch(facecolor="red", edgecolor="black", label="Slower"),
            Patch(facecolor="green", edgecolor="black", label="Faster"),
            Line2D(
                [0],
                [0],
                color="black",
                linewidth=0,
                marker="|",
                markersize=12,
                markeredgewidth=1,
                label="Error bars: propagated standard error",
            ),
            Line2D([0], [0], color="black", linestyle="--", linewidth=1, label="Baseline"),
        ]
    )
    ax.grid(axis="y", alpha=0.3, linestyle="--", linewidth=0.5)

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, format=output_path.suffix.lstrip(".") or None, bbox_inches="tight")
    print(f"Plot saved to {output_path} with {len(benchmarks)} benchmarks")
    if start_dates is not None:
        baseline_date, candidate_date = start_dates
        print("Benchmark start dates:")
        print(f"  baseline={baseline_date}")
        print(f"  candidate={candidate_date}")


@dataclass
class Panel:
    group: str
    label: str
    comparison: Comparison


COMBINED_Y_MIN = 0.9
COMBINED_Y_MAX = 1.2


def plot_combined(
    panels: list[Panel],
    output_path: Path,
    width: float,
    height: float,
) -> None:
    """Stack all comparisons into one paper-sized figure with a shared x-axis.

    Drawn at the final printed size (inches), so font sizes are real points.
    Benchmark names are printed once under the bottom panel; each panel gets
    a rotated label on the left and its geomeans in the corner.
    """
    benchmarks: list[str] = []
    for panel in panels:
        benchmarks += [b for b in panel.comparison.benchmarks if b not in benchmarks]
    position = {name: index for index, name in enumerate(benchmarks)}

    plt.rcParams.update({"font.size": 6, "pdf.fonttype": 42, "axes.linewidth": 0.5})

    fig, axes = plt.subplots(
        len(panels), 1,
        sharex=True,
        figsize=(width, height),
        gridspec_kw={"hspace": 0.16},
    )
    if len(panels) == 1:
        axes = [axes]

    geomean_labels = []
    for ax, panel in zip(axes, panels):
        comparison = panel.comparison
        draw_bars(
            ax,
            [position[b] for b in comparison.benchmarks],
            comparison,
            linewidth=0.2,
            error_kw={"elinewidth": 0.3, "capsize": 0.6, "capthick": 0.3, "ecolor": "black"},
            y_min=COMBINED_Y_MIN,
            y_max=COMBINED_Y_MAX,
            clip_fontsize=4.5,
        )
        ax.axhline(y=1.0, color="black", linestyle="--", linewidth=0.5)
        ax.set_ylim(COMBINED_Y_MIN, COMBINED_Y_MAX)
        ax.set_xlim(-0.75, len(benchmarks) - 0.25)
        # Ticks every 0.1 within the limits; set_yticks would otherwise widen the axis.
        ax.set_yticks([
            round(COMBINED_Y_MIN + 0.1 * step, 1)
            for step in range(round((COMBINED_Y_MAX - COMBINED_Y_MIN) / 0.1) + 1)
        ])
        ax.tick_params(axis="y", labelsize=5, length=2, width=0.4, pad=1)
        ax.tick_params(axis="x", length=0)
        ax.grid(axis="y", alpha=0.3, linestyle="--", linewidth=0.3)
        ax.set_ylabel(panel.label, fontsize=7, labelpad=2)

        significant_geomean, all_geomean = comparison.geomeans()
        geomean_text = f"geomean: {all_geomean:.3f}× all"
        if significant_geomean is not None:
            geomean_text = f"geomean: {significant_geomean:.3f}× significant; {all_geomean:.3f}× all"
        geomean_labels.append(ax.text(
            1.0, 1.01, geomean_text,
            transform=ax.transAxes, ha="right", va="bottom", fontsize=5.5,
        ))

    # Group labels (e.g. GIL / free-threaded), spanning their panels on the far left.
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    to_figure = fig.transFigure.inverted()
    label_bottoms = [label.get_window_extent(renderer).transformed(to_figure).y0 for label in geomean_labels]
    label_x = min(
        ax.yaxis.get_tightbbox(renderer).transformed(fig.transFigure.inverted()).x0
        for ax in axes
    ) - 0.012
    groups: list[tuple[str, list]] = []
    for ax, panel in zip(axes, panels):
        if groups and groups[-1][0] == panel.group:
            groups[-1][1].append(ax)
        else:
            groups.append((panel.group, [ax]))
    for index, (group, group_axes) in enumerate(groups):
        top = group_axes[0].get_position().y1
        bottom = group_axes[-1].get_position().y0
        fig.add_artist(Line2D(
            [label_x, label_x], [bottom, top],
            transform=fig.transFigure, color="black", linewidth=0.6,
        ))
        fig.text(
            label_x - 0.008, (top + bottom) / 2, group,
            rotation=90, ha="right", va="center", fontsize=7.5, fontweight="bold",
        )
        if index > 0:
            # Separate groups with a rule in the gap between them, below the
            # first panel's geomean label so the two don't overlap.
            above = groups[index - 1][1][-1].get_position().y0
            label_bottom = label_bottoms[list(axes).index(group_axes[0])]
            fig.add_artist(Line2D(
                [label_x, axes[0].get_position().x1], [(above + label_bottom) / 2] * 2,
                transform=fig.transFigure, color="black", linewidth=0.4, linestyle=":",
            ))

    bottom_ax = axes[-1]
    bottom_ax.set_xticks(range(len(benchmarks)))
    bottom_ax.set_xticklabels(benchmarks, rotation=90, fontsize=3.5)
    bottom_ax.tick_params(axis="x", pad=1)

    fig.legend(
        handles=[
            Patch(facecolor="red", alpha=0.8, edgecolor="black", linewidth=0.3, label="Slower"),
            Patch(facecolor="green", alpha=0.8, edgecolor="black", linewidth=0.3, label="Faster"),
            Patch(facecolor="grey", alpha=0.3, edgecolor="black", linewidth=0.3, label="Not significant"),
            Line2D([0], [0], color="black", linewidth=0, marker="|", markersize=5,
                   markeredgewidth=0.5, label="Propagated std. error"),
            Line2D([0], [0], color="black", linestyle="--", linewidth=0.5, label="Baseline = 1.0"),
        ],
        loc="lower center",
        # Sit above the top panel's geomean label.
        bbox_to_anchor=(0.5, geomean_labels[0].get_window_extent(renderer).transformed(to_figure).y1 + 0.004),
        ncol=5,
        fontsize=6,
        frameon=False,
        handlelength=1.2,
        columnspacing=1.2,
        borderaxespad=0,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, format=output_path.suffix.lstrip(".") or None, bbox_inches="tight", pad_inches=0.01)
    print(f"Combined plot saved to {output_path} with {len(panels)} panels, {len(benchmarks)} benchmarks")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare pyperformance result files and plot the normalized output. "
        "Either pass BASELINE CANDIDATE OUTPUT for a single comparison, or "
        "--combined OUTPUT with one --panel per comparison for the stacked paper figure.",
    )
    parser.add_argument("baseline", nargs="?", help="Path to the baseline pyperformance JSON result")
    parser.add_argument("candidate", nargs="?", help="Path to the candidate pyperformance JSON result")
    parser.add_argument("output", nargs="?", help="Path to the output plot file")
    parser.add_argument("--combined", metavar="OUTPUT", help="Write a stacked multi-panel figure")
    parser.add_argument(
        "--panel", nargs=4, action="append", default=[],
        metavar=("GROUP", "LABEL", "BASELINE", "CANDIDATE"),
        help="One panel of the combined figure (repeatable, drawn top to bottom)",
    )
    parser.add_argument("--width", type=float, default=6.3, help="Combined figure width in inches")
    parser.add_argument("--height", type=float, default=8.2, help="Combined figure height in inches")
    args = parser.parse_args()

    if args.combined:
        if not args.panel:
            parser.error("--combined needs at least one --panel")
        panels = [
            Panel(group, label, compare_results(Path(baseline), Path(candidate)))
            for group, label, baseline, candidate in args.panel
        ]
        plot_combined(panels, Path(args.combined), args.width, args.height)
        return

    if not (args.baseline and args.candidate and args.output):
        parser.error("expected BASELINE CANDIDATE OUTPUT (or --combined)")
    plot_results(
        Path(args.baseline),
        Path(args.candidate),
        Path(args.output),
    )


if __name__ == "__main__":
    main()