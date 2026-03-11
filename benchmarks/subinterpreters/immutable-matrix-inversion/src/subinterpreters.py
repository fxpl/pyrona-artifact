import argparse
import json
import os
from textwrap import dedent
import threading
from timeit import default_timer as timer
import random
from statistics import geometric_mean, mean, stdev

from bocpy import send, receive
from matrix import Matrix, random_matrix

try:
    import _interpreters as interpreters
except ModuleNotFoundError:
    import _xxsubinterpreters as interpreters


def worker(interp, script):
    interpreters.run_string(interp, dedent(script))


def run(batches):
    start = timer()
    for batch in batches:
        send("worker", batch)

    num_results = len(batches)
    result = 0
    for i in range(num_results):
        match receive("result"):
            case ["result", value]:
                result += value

    duration = timer() - start

    return duration


def main():
    parser = argparse.ArgumentParser("Invert 4x4 subinterpreters")
    parser.add_argument("--num-trials", "-t", type=int, default=10, help="Number of trials to run")
    parser.add_argument("--num-workers", "-w", type=int, default=8, help="Number of worker threads")
    parser.add_argument("--num-values", "-n", type=int, default=200000, help="Number of random values to generate")
    parser.add_argument("--scaling-mode", "-s", action="store_true", help="Output in scaling mode")
    parser.add_argument("--batch-per-worker", "-b", type=int, default=4, help="Number of batches per worker")
    parser.add_argument("--freeze", "-f", action="store_true", help="whether to freeze the data")
    parser.add_argument("--verbose", "-v", action="store_true", help="Report individual trial results")
    args = parser.parse_args()

    num_batches = args.num_workers * args.batch_per_worker
    batch_size = args.num_values // num_batches
    if num_batches * batch_size < args.num_values:
        batch_size += 1

    batches = [tuple(random_matrix(-2, 2) for _ in range(batch_size))
               for _ in range(num_batches)]

    if args.freeze:
        from immutable import freeze, isfrozen
        freeze(Matrix)
        for b in batches:
            freeze(b)

        assert isfrozen(batches[0])
        assert isfrozen(batches[0][0])

    with open(os.path.join(os.path.dirname(__file__), "subinterpreters_worker.py")) as file:
        worker_script = file.read()

    workers = []
    worker_threads = []
    for _ in range(args.num_workers):
        interp = interpreters.create()
        t = threading.Thread(target=worker, args=(interp, worker_script))
        workers.append(interp)
        worker_threads.append(t)
        t.start()

    for _ in range(args.num_workers):
        receive("started")

    durations = []
    for i in range(args.num_trials):
        random.shuffle(batches)
        duration = run(batches)
        if args.verbose:
            print(f"Trial {i}: {duration}s")
        durations.append(duration)

        durations.append(duration)

    for _ in range(args.num_workers):
        send("worker", "shutdown")

    for t in worker_threads:
        t.join()

    for interp in workers:
        try:
            interpreters.destroy(interp)
        except RuntimeError:
            pass  # already destroyed

    if args.scaling_mode:
        print(json.dumps({
            "num-workers": args.num_workers,
            "num-batches": num_batches,
            "num-values": num_batches * batch_size,
            "durations": durations,
            "frozen": args.freeze,
        }))
    else:
        dur_mean = mean(durations)
        dur_std = stdev(durations)
        dur_min = min(durations)
        dur_max = max(durations)
        dur_gmean = geometric_mean(durations)
        print(f"| Subinterp | {dur_mean:0.4} | {dur_gmean:0.4} | {dur_std:0.4} | {dur_min:0.4} | {dur_max:0.4} |")


if __name__ == "__main__":
    main()
