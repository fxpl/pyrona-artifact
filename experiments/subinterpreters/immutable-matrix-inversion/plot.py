import json
import os
import argparse
from statistics import mean, stdev

import matplotlib.pyplot as plt


def throughput_stats(entries):
    workers = []
    means = []
    stds = []
    mins = []
    maxs = []

    for entry in entries:
        workers.append(entry["num-workers"])
        durations = entry["durations"]
        num_values = entry["num-values"]
        throughput = [num_values / d for d in durations]

        means.append(mean(throughput))
        stds.append(stdev(throughput) if len(throughput) > 1 else 0.0)
        mins.append(min(throughput))
        maxs.append(max(throughput))

    return workers, means, stds, mins, maxs


def plot_scaling_results(input_path, output_path):
    with open(input_path, "r") as f:
        results = json.load(f)

    workers, means, stds, mins, maxs = throughput_stats(results["subinterpreters_pickle"])
    plt.errorbar(workers, means, yerr=stds, fmt="-o", label="Subinterpreters (pickle)")
    plt.fill_between(workers, mins, maxs, alpha=0.15)

    workers, means, stds, mins, maxs = throughput_stats(results["subinterpreters_freeze"])
    plt.errorbar(workers, means, yerr=stds, fmt="-o", label="Subinterpreters (--freeze)")
    plt.fill_between(workers, mins, maxs, alpha=0.15)

    single_durations = results["single"]["durations"]
    single_num_values = results["single"]["num_values"]
    single_tp = [single_num_values / d for d in single_durations]
    single_tp_mean = mean(single_tp)
    plt.axhline(y=single_tp_mean, linestyle="--", label="Single-thread")

    plt.xlabel("Number of Subinterpreters")
    plt.ylabel("Throughput (inversions per second)")
    plt.title("Scaling of 4x4 Matrix Inversion")
    plt.legend()
    plt.tight_layout()

    plt.savefig(output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot immutable matrix inversion scaling results")
    experiment_dir = os.path.dirname(__file__)
    parser.add_argument(
        "--input",
        default=os.path.join(experiment_dir, "results/scaling.json"),
        help="Path to benchmark JSON file",
    )
    parser.add_argument(
        "--output",
        default=os.path.join(experiment_dir, "results/scaling_graph.pdf"),
        help="Path to output plot image",
    )
    args = parser.parse_args()
    plot_scaling_results(args.input, args.output)
