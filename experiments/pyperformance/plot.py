import argparse
import json
import math
import re
import statistics
import subprocess
import sys
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


def plot_results(
    baseline_path: Path,
    candidate_path: Path,
    output_path: Path,
) -> None:
    validate_results_compatible(baseline_path, candidate_path)
    compare_table = build_compare_table(Path(sys.executable), baseline_path, candidate_path)
    start_dates = extract_start_dates(compare_table)
    resolved_table_output_path = output_path.with_suffix(".txt")
    resolved_table_output_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_table_output_path.write_text(compare_table + "\n", encoding="utf-8")

    benchmarks, normalized_values, error_values, is_significant = parse_results(
        compare_table,
        baseline_path,
        candidate_path,
    )

    plt.rcParams["font.size"] = 10
    plt.rcParams["pdf.fonttype"] = 42

    fig, ax = plt.subplots(figsize=(16, 8))

    colors = ["red" if value > 1.0 else "green" for value in normalized_values]
    alphas = [0.8 if significant else 0.3 for significant in is_significant]

    for index, (value, error, color, alpha) in enumerate(zip(normalized_values, error_values, colors, alphas)):
        ax.bar(
            index,
            value - 1.0,
            bottom=1.0,
            yerr=error,
            color=color,
            alpha=alpha,
            edgecolor="black",
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare two pyperformance result files and plot the normalized output")
    parser.add_argument("baseline", help="Path to the baseline pyperformance JSON result")
    parser.add_argument("candidate", help="Path to the candidate pyperformance JSON result")
    parser.add_argument("output", help="Path to the output plot file")
    args = parser.parse_args()

    plot_results(
        Path(args.baseline),
        Path(args.candidate),
        Path(args.output),
    )


if __name__ == "__main__":
    main()