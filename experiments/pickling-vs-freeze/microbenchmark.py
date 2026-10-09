import argparse
import gc
import importlib
import json
import os
import string
from random import Random
from statistics import geometric_mean, mean, stdev
from timeit import default_timer as timer
import pickle

def load_freeze():
    try:
        return importlib.import_module("immutable").freeze
    except ImportError:
        return None


freeze = load_freeze()

SAMPLE_SIZE = 100000
SEED = 1
VAL_LEN = 8
EXPERIMENTS = ["dict-int", "dict-student", "tuple", "binary-tree"]

class Student:
    def __init__(self, name, age):
        self.name = name
        self.age = age

class TreeNode:
    def __init__(self, key):
        self.left = None
        self.right = None
        self.val = key

    def insert(self, key):
        if key < self.val:
            if self.left is None:
                self.left = TreeNode(key)
            else:
                self.left.insert(key)
        else:
            if self.right is None:
                self.right = TreeNode(key)
            else:
                self.right.insert(key)

    def print(self):
        if self.left is not None:
            self.left.print()

        print(self.val, end=" ")

        if self.right is not None:
            self.right.print()

def prep_imm():
    """
    This pre-freezes types and objects, which will be frozen by default
    later. The paper also states that these are frozen by default.
    """

    if freeze is None:
        return

    freeze(True)
    freeze(False)
    freeze(None)
    freeze(dict())
    freeze((0, 1, 2, 3, 4, 5, 6, 0.0, 1.0)) # Tuple with numbers
    freeze("Strings are cool")
    freeze(["a list"])
    freeze(prep_imm) # A function

def rand_val(r):
    return ''.join(r.choices(string.ascii_lowercase, k=VAL_LEN))

def rand_student(r):
    return Student(''.join(r.choices(string.ascii_lowercase, k=VAL_LEN)), r.randint(6, 19))

def gen_dict(seed, val_gen):
    r = Random(seed)

    d = {
        rand_val(r): val_gen(r)
        for _ in range(SAMPLE_SIZE)
    }

    it = 0
    while len(d) < SAMPLE_SIZE:
        k =  rand_val(r)
        v = val_gen(r)
        d[k] = v

        it += 1
        if (it > SAMPLE_SIZE/2):
            raise Exception("Failed to generate a dict of size " + str(SAMPLE_SIZE))

    if not len(d) == SAMPLE_SIZE:
        raise Exception("Failed to generate correct dict")

    return d

def gen_tuple(seed):
    r = Random(seed)

    return tuple(rand_val(r) for _ in range(SAMPLE_SIZE))

def gen_tree(seed):
    r = Random(seed)
    tree = TreeNode(rand_val(r))

    for _ in range(SAMPLE_SIZE - 1):
        val = rand_val(r)
        tree.insert(val)

    return tree


def bench_func(func, data):
    # Prep
    gc.collect()

    # Benchmark
    start = timer()
    res = func(data)
    return (res, timer() - start)

def summarize(durations_ms):
    if not durations_ms:
        raise ValueError("Cannot summarize empty measurements")

    dur_mean = mean(durations_ms)
    dur_std = stdev(durations_ms) if len(durations_ms) > 1 else 0.0
    dur_min = min(durations_ms)
    dur_max = max(durations_ms)
    dur_gmean = geometric_mean(durations_ms)
    return {
        "mean": dur_mean,
        "gmean": dur_gmean,
        "std": dur_std,
        "min": dur_min,
        "max": dur_max,
    }


def print_summary_row(name, bench_type, durations_ms):
    summary = summarize(durations_ms)
    print(
        f"| {name:23} | {bench_type:8} | {summary['mean']:7.2f} | {summary['gmean']:7.2f} | "
        f"{summary['std']:7.2f} | {summary['min']:7.2f} | {summary['max']:7.2f} |"
    )


def bench_freeze(name, trials, gen_data):
    if freeze is None:
        raise RuntimeError(
            "Freeze benchmarking requires the 'immutable' module. "
            "Install it or run with --collect pickle."
        )

    global SEED
    durations = []
    for _ in range(trials):
        (_, t) = bench_func(freeze, gen_data(SEED))
        durations.append(t * 1000)
        SEED += 1

    print_summary_row(name, "freeze", durations)
    return {
        "freeze_ms": durations,
    }

def bench_pickle(name, trials, gen_data):
    global SEED
    durations_pickle = []
    durations_unpickle = []
    for _ in range(trials):
        (data, time) = bench_func(pickle.dumps, gen_data(SEED))
        durations_pickle.append(time * 1000)
        SEED += 1

        (_, time) = bench_func(pickle.loads, data)
        durations_unpickle.append(time * 1000)

    durations = [x + y for x, y in zip(durations_pickle, durations_unpickle)]
    print_summary_row(name, "pickle", durations_pickle)
    print_summary_row(name, "unpickle", durations_unpickle)
    print_summary_row(name, "pickling", durations)
    return {
        "pickle_ms": durations_pickle,
        "unpickle_ms": durations_unpickle,
    }


def gen_data_for_experiment(name, seed):
    if name == "dict-int":
        return gen_dict(seed, lambda r: r.randint(0, 10000))
    if name == "dict-student":
        return gen_dict(seed, rand_student)
    if name == "tuple":
        return gen_tuple(seed)
    if name == "binary-tree":
        return gen_tree(seed)
    raise ValueError(f"Unknown experiment: {name}")


def ensure_parent_dir(path):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def run_collection(mode, num_trials):
    results = {}
    for experiment_name in EXPERIMENTS:
        gen_data = lambda seed, name=experiment_name: gen_data_for_experiment(name, seed)
        if mode == "freeze":
            results[experiment_name] = bench_freeze(experiment_name, num_trials, gen_data)
        else:
            results[experiment_name] = bench_pickle(experiment_name, num_trials, gen_data)
    return results


def write_results(path, mode, args, results):
    payload = {
        "benchmark": "pickling-vs-freeze",
        "mode": mode,
        "dict_size": SAMPLE_SIZE,
        "num_trials": args.num_trials,
        "initial_seed": args.seed,
        "value_length": VAL_LEN,
        "results": results,
    }
    ensure_parent_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")

if __name__ == '__main__':
    parser = argparse.ArgumentParser("microbenchmark")
    parser.add_argument("--num-trials", "-t", type=int, default=10, help="Number of trials to run")
    parser.add_argument("--size", "-s", type=int, default=1000000, help="Size of the data structure to generate")
    parser.add_argument("--seed", type=int, default=1, help="The inital Seed")
    parser.add_argument("--collect", choices=["freeze", "pickle"], required=True, help="Collect only freeze or only pickle+unpickle timings")
    parser.add_argument("--output", "-o", type=str, default=None, help="Path to the output JSON file")
    parser.add_argument("--no-info", type=bool, default=False, help="Prevents info from being printed at the end")
    args = parser.parse_args()
    SAMPLE_SIZE = args.size
    SEED = args.seed

    if args.collect == "freeze":
        if freeze is None:
            raise RuntimeError(
                "--collect freeze requires the 'immutable' module. "
                "Install it or use --collect pickle."
            )
        prep_imm()

    print("| Experiment              | Type     | Mean    | GeoMean | StdDev  | Min     | Max     |")
    print("| ----------------------- | -------- | ------- | ------- | ------- | ------- | ------- |")
    results = run_collection(args.collect, args.num_trials)

    output_path = args.output or f"results/{args.collect}.json"
    write_results(output_path, args.collect, args, results)
    print()
    print(f"Wrote raw timing data to: {output_path}")


    if not args.no_info:
        r = Random(SEED)

        print()
        print(f"Items per data structure: {SAMPLE_SIZE}")
        print(f"Trials per structure: {args.num_trials}")
        print(f"Initial Seed: {args.seed}")
        print(f"Used keys/values: Strings of length {VAL_LEN} (Examples: '{rand_val(r)}', '{rand_val(r)}', '{rand_val(r)}')")
        print(f"Mode: {args.collect}")
        print(f"Time in MS")
