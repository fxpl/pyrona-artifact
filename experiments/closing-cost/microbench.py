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

DEFAULT_SEED = 1
DEFAULT_KEY_LEN = 8
DEFAULT_TUPLE_LEN = 8
WARMUP = 5

# Oversized so striding through it evicts the working set from the CPU caches.
_FLUSH_BYTES = 128 * 1024 * 1024
_FLUSH_STRIDE = 32  # one byte per cache line
_flush_buf = bytearray(_FLUSH_BYTES)
_flush_fill = bytes((_FLUSH_BYTES + _FLUSH_STRIDE - 1) // _FLUSH_STRIDE)

def flush_cpu_cache():
    _flush_buf[::_FLUSH_STRIDE] = _flush_fill

def from_immutable_import(name: str):
    try:
        mod = importlib.import_module("immutable")
        return getattr(mod, name, None)
    except ImportError:
        return None

deep_freeze = from_immutable_import("deep_freeze")
set_freezable = from_immutable_import("set_freezable")
FREEZABLE_YES = from_immutable_import("FREEZABLE_YES")
TRegion = from_immutable_import("TracingRegion")

def assert_defined(name: str):
    if globals()[name] is None:
        raise RuntimeError(
            "the name {name} is undefined, ensure you're running the right version"
        )

def close_region(r):
    TRegion.close(r)
    return r

###############################################################################
# Data definition and generation
###############################################################################

def rand_key(r):
    return ''.join(r.choices(string.ascii_lowercase, k=DEFAULT_KEY_LEN))

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

    def __str__(self):
        parts = []
        if self.left is not None:
            parts.append(str(self.left))
        parts.append(self.val)
        if self.right is not None:
            parts.append(str(self.right))
        return " ".join(parts)

def gen_user_defined(seed, size):
    """This builds a binary tree with {size} nodes. The keys are random strings
    with {DEFAULT_KEY_LEN} characters"""
    r = Random(seed)
    tree = TreeNode(rand_key(r))

    for _ in range(size - 1):
        val = rand_key(r)
        tree.insert(val)

    return tree

def gen_builtin_objects(seed, size):
    """This builds a dictionary of size {size} with random string of size
    {DEFAULT_KEY_LEN} as keys mapping to tuples of {DEFAULT_TUPLE_LEN} integers"""
    r = Random(seed)

    def gen_tuple(r):
        return tuple(r.randint(0, 100) for _ in range(DEFAULT_TUPLE_LEN))

    objects = {
        rand_key(r): gen_tuple(r)
        for _ in range(size)
    }

    while len(objects) < size:
        objects[rand_key(r)] = gen_tuple(r)

    return objects


###############################################################################
# Benchmark
###############################################################################

def snapshot(data):
    # Regions keep their payload in `.data`; compare that, not the wrapper.
    if TRegion is not None and isinstance(data, TRegion):
        return str(data.data)
    return str(data)


def experiment(trials, seed, size, gen_data, steps, validate=False):
    results = [[] for _ in steps]

    for trial in range(trials):
        if size > 10000:
            print(".", end="", flush=True)
        data = gen_data(seed, size)

        check = validate and trial == 0
        before = snapshot(data) if check else None

        for step_idx in range(len(steps)):
            # Prep
            gc.collect()
            flush_cpu_cache()

            # Benchmark
            start = timer()
            data = steps[step_idx](data)
            time = timer() - start

            # Record
            results[step_idx].append(time)

        if check:
            ok = snapshot(data) == before and data is not None
            print(f"[validate] output equivalent to input: {ok}")
            if not ok:
                raise RuntimeError("validation failed: output differs from input")

    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser("microbenchmark")
    parser.add_argument("--trials", "-t", type=int, default=10, help="Number of trials to run")
    parser.add_argument("--size", "-s", type=int, required=True, help="Size of the data structure to generate")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="The inital Seed")
    parser.add_argument("--data", choices=["built-in", "user-defined"], required=True, help="The data that should be processed")
    parser.add_argument("--operation", choices=["pickling", "freeze", "close", "reclose"], required=True, help="The operation that should be used")
    parser.add_argument("--output", "-o", type=str, default=None, help="Path to the output JSON file")
    parser.add_argument("--silent", type=bool, default=False, help="Makes the run silent, no info will be printed")
    args = parser.parse_args()

    seed = args.seed
    size = args.size

    if args.data == "built-in":
        gen_data = gen_builtin_objects
    elif args.data == "user-defined":
        gen_data = gen_user_defined

    if args.operation != "pickling":
        set_freezable(TreeNode, FREEZABLE_YES)

    match args.operation:
        case "pickling":
            run_trials = lambda trials, validate=False: experiment(trials, seed, size, gen_data, [pickle.dumps, pickle.loads], validate)
        case "freeze":
            assert_defined("deep_freeze")
            run_trials = lambda trials, validate=False: experiment(trials, seed, size, gen_data, [deep_freeze], validate)
        case "close":
            assert_defined("TRegion")
            def gen_open_region(seed, size):
                r = TRegion()
                r.data = gen_data(seed, size)
                return r
            run_trials = lambda trials, validate=False: experiment(trials, seed, size, gen_open_region, [close_region], validate)
        case "reclose":
            assert_defined("TRegion")
            def gen_reopened_region(seed, size):
                r = TRegion()
                r.data = gen_data(seed, size)

                # Reopen it again
                TRegion.close(r)
                assert r.data is not None

                # Ensure the reopen succeeded
                assert not TRegion.is_closed(r)
                return r
            run_trials = lambda trials, validate=False: experiment(trials, seed, size, gen_reopened_region, [close_region], validate)

    _ignore = run_trials(WARMUP, validate=True)
    results = run_trials(args.trials)

    if args.output is not None:
        parent = os.path.dirname(args.output)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(args.output, "w") as f:
            json.dump({
                "operation": args.operation,
                "data": args.data,
                "trials": args.trials,
                "seed": seed,
                "size": size,
                "results": results,
            }, f)

    if not args.silent:
        print()
        for step_idx, row in enumerate(results):
            print(
                f"step {step_idx}: "
                f"mean={mean(row):.6g} "
                f"stddev={stdev(row) if len(row) > 1 else 0.0:.6g} "
                f"min={min(row):.6g} "
                f"max={max(row):.6g}"
            )
