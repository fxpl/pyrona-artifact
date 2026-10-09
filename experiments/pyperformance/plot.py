import argparse
import math
import re
from pathlib import Path

import matplotlib.pyplot as plt


ROW_RE = re.compile(r"^\|\s*(?P<benchmark>[^|]+?)\s*\|\s*(?P<baseline>[^|]+?)\s*\|\s*(?P<patched>[^|]+?)\s*\|\s*(?P<change>[^|]+?)\s*\|\s*(?P<significance>[^|]+?)\s*\|$")
CHANGE_RE = re.compile(r"(?P<value>[\d.]+)x\s+(?P<direction>slower|faster)")


def parse_results(input_path: Path) -> tuple[list[str], list[float], list[bool]]:
    benchmarks: list[str] = []
    normalized_values: list[float] = []
    is_significant: list[bool] = []

    for line in input_path.read_text().splitlines():
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
        significant = "Not significant" not in match.group("significance")

        benchmarks.append(benchmark_name)
        normalized_values.append(normalized)
        is_significant.append(significant)

    if not benchmarks:
        raise ValueError(f"No benchmark rows found in {input_path}")

    return benchmarks, normalized_values, is_significant


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


def plot_results(input_path: Path, output_path: Path, title: str | None) -> None:
    benchmarks, normalized_values, is_significant = parse_results(input_path)

    plt.rcParams["font.size"] = 10
    plt.rcParams["pdf.fonttype"] = 42

    fig, ax = plt.subplots(figsize=(16, 8))

    colors = ["red" if value > 1.0 else "green" for value in normalized_values]
    alphas = [0.8 if significant else 0.3 for significant in is_significant]

    for index, (value, color, alpha) in enumerate(zip(normalized_values, colors, alphas)):
        ax.bar(index, value, color=color, alpha=alpha, edgecolor="black", linewidth=0.5)

    ax.axhline(y=1.0, color="black", linestyle="--", linewidth=1, label="Baseline")
    ax.set_xlabel("Note: Insignificant results shaded light", fontsize=12, fontweight="normal")
    ax.set_ylabel("Normalized Performance (Baseline = 1.0)", fontsize=12, fontweight="bold")
    ax.set_title(title or build_title(normalized_values, is_significant), fontsize=14, fontweight="bold")
    ax.set_xticks(range(len(benchmarks)))
    ax.set_xticklabels(benchmarks, rotation=90, fontsize=9)
    ax.tick_params(axis="y", labelsize=11)
    ax.set_ylim(0.8, 1.2)
    ax.legend()
    ax.grid(axis="y", alpha=0.3, linestyle="--", linewidth=0.5)

    plt.tight_layout()
    plt.savefig(output_path, format=output_path.suffix.lstrip(".") or None, bbox_inches="tight")
    print(f"Plot saved to {output_path} with {len(benchmarks)} benchmarks")


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot pyperformance compare output")
    parser.add_argument("input", help="Path to the text output from pyperformance compare")
    parser.add_argument("output", help="Path to the output plot file")
    parser.add_argument("--title", help="Override the generated plot title")
    args = parser.parse_args()

    plot_results(Path(args.input), Path(args.output), args.title)


if __name__ == "__main__":
    main()