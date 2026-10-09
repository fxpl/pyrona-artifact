import argparse
import json
import random
from statistics import geometric_mean, mean, stdev
from timeit import default_timer as timer
from typing import List
from matrix import Matrix, random_matrix


def run(values: List[Matrix]):
    start = timer()
    matrix_inverse = Matrix()
    num_invertible = 0
    for matrix in values:
        if matrix.invert(matrix_inverse):
            num_invertible += 1

    return timer() - start


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Invert 4x4 baseline")
    parser.add_argument("--num-trials", "-t", type=int, default=10, help="Number of trials to run")
    parser.add_argument("--num-values", "-n", type=int, default=200000, help="Number of random values to generate")
    parser.add_argument("--scaling-mode", action="store_true", help="Enable scaling mode")
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true", help="Report individual trial results")
    args = parser.parse_args()

    values = [random_matrix(-2, 2) for _ in range(args.num_values)]

    if args.freeze:
        from immutable import freeze, is_frozen
        freeze(Matrix)
        for m in values:
            freeze(m)

        assert is_frozen(values[0])

    durations = []
    for i in range(args.num_trials):
        random.shuffle(values)
        duration = run(values)
        if args.verbose:
            print(f"Trial {i}: {duration}s")
        durations.append(duration)

    if args.scaling_mode:
        print(json.dumps({
            "num_values": args.num_values,
            "durations": durations,
        }))
    else:
        dur_mean = mean(durations)
        dur_std = stdev(durations)
        dur_min = min(durations)
        dur_max = max(durations)
        dur_gmean = geometric_mean(durations)
        print(f"| Baseline | {dur_mean:0.4} | {dur_gmean:0.4} | {dur_std:0.4} | {dur_min:0.4} | {dur_max:0.4} |")