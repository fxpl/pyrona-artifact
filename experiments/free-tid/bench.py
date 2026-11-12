#!/usr/bin/env python3
"""Region ownership pipeline: use a separate free-threaded binary for B/R/RT."""

import argparse
import gc
import itertools
import json
import os
from pathlib import Path
import platform
import queue
import random
import subprocess
import sys
import sysconfig
import threading
import time
import traceback

try:
    from immutable import Mutex, TracingRegion, freezable
except ImportError:
    Mutex = TracingRegion = None

    def freezable(cls):
        return cls


@freezable
class Node:
    __slots__ = ("left", "right", "payload", "__weakref__")

    def __init__(self, value):
        self.left = self.right = None
        self.payload = [float(value)]


def make_graph(shape, n):
    if shape == "dict":
        # Mutable leaves prevent tuples being deeply immutable. Keys and floats
        # are runtime allocated, but may be excluded by region immutability rules.
        return {i + 1_000_000: ([float(i)], [float(i + n)]) for i in range(n)}
    nodes = [Node(i) for i in range(n)]
    for i, node in enumerate(nodes):
        if 2 * i + 1 < n:
            node.left = nodes[2 * i + 1]
        if 2 * i + 2 < n:
            node.right = nodes[2 * i + 2]
    return nodes[0]


def walk_dict(root):
    scratch = []
    count = 0
    for key in root:
        value = root[key]
        scratch.append(value)
        for leaf in value:
            scratch.append(leaf)
            scratch.append(leaf[0])
            scratch.pop()
            scratch.pop()
        scratch.pop()
        count += 1
    return count


def walk_tree(root):
    stack = [root]
    scratch = []
    count = 0
    while stack:
        node = stack.pop()
        scratch.append(node.payload)
        scratch.append(node.payload[0])
        scratch.pop()
        scratch.pop()
        if node.right is not None:
            stack.append(node.right)
        if node.left is not None:
            stack.append(node.left)
        count += 1
    return count


WALKS = {"dict": walk_dict, "tree": walk_tree}


def mutate_graph(shape, root):
    if shape == "dict":
        for value in root.values():
            value[0][0] += 0.25
    else:
        stack = [root]
        while stack:
            node = stack.pop()
            node.payload[0] += 0.25
            if node.left is not None:
                stack.append(node.left)
            if node.right is not None:
                stack.append(node.right)


# Close refusals caused by concurrency rather than by the fixture (Mutex.release
# raises RuntimeError). Concurrent closes of unrelated regions can hit these
# spuriously; see region_paper/README.md. Isolation errors are never retried.
CLOSE_FAILURES = ("due to a concurrent access", "concurrent thread accessed it",
                  "tracing attempts")


def is_spurious_close_failure(text):
    return any(marker in text for marker in CLOSE_FAILURES)


def make_packet(config, shape, n):
    if config == "B":
        return make_graph(shape, n)
    packet = Mutex(TracingRegion())
    packet.value.graph = make_graph(shape, n)
    return packet


def flush_cache(buffer):
    # Deliberate eviction pressure, not a guarantee that all cache levels flush.
    for i in range(0, len(buffer), 64):
        buffer[i] = (buffer[i] + 1) & 255


def pin(cpu):
    if cpu is not None:
        os.sched_setaffinity(0, {cpu})


def trial(args, shape, n, k, depth, pipelines):
    """One independent trial; producers and prior owners live until all finish."""
    start_gate = threading.Barrier(pipelines * (depth + 1) + 1)
    finished = threading.Event()
    abort = threading.Event()
    gc_active = threading.Event()
    errors = queue.Queue()
    rows = [{"stages": [None] * depth} for _ in range(pipelines)]
    channels = [[queue.Queue(maxsize=1) for _ in range(depth)]
                for _ in range(pipelines)]
    published = [[threading.Event() for _ in range(depth)]
                 for _ in range(pipelines)]
    completed = [threading.Event() for _ in range(pipelines)]
    gc_events = []
    clock = time.perf_counter_ns

    def wait(event):
        if not event.wait(args.timeout):
            raise TimeoutError("pipeline event timed out")
        if abort.is_set():
            raise RuntimeError("another worker failed")

    def guard(fn, *params):
        try:
            fn(*params)
        except BaseException:
            errors.put(traceback.format_exc())
            abort.set()
            start_gate.abort()
            for events in published:
                for event in events:
                    event.set()
            for event in completed:
                event.set()

    def setup(p, stage):
        index = p * (depth + 1) + stage
        pin(args.cpus[index] if args.cpus else None)
        buffer = bytearray(args.cache_mib * 1024 * 1024)
        flush_cache(buffer)  # Fault pages before timing.
        start_gate.wait(args.timeout)
        return buffer

    def produce(p):
        buffer = setup(p, 0)
        begin = clock()
        packet = make_packet(args.config, shape, n)
        built = clock()
        flush_cache(buffer)
        close_start = clock()
        if args.config != "B":
            packet.release()
        close_end = clock()
        rows[p].update(start_ns=begin, pipeline_start_ns=close_start,
                       build_ns=built - begin,
                       close_ns=close_end - close_start if args.config != "B" else 0)
        channels[p][0].put(packet)
        del packet
        # Consumer cannot retain producer's last graph reference during teardown.
        published[p][0].set()
        finished.wait()

    def consume(p, stage):
        buffer = setup(p, stage + 1)
        wait(published[p][stage])
        packet = channels[p][stage].get(timeout=args.timeout)
        acquire_start = clock()
        if args.config != "B":
            packet.acquire()
            root = packet.value.graph  # Opens and touches the root only.
        else:
            root = packet
        acquire_ns = clock() - acquire_start
        walk = WALKS[shape]
        gc_active.set()
        flush_cache(buffer)
        t0 = clock()
        visited = walk(root)
        first_ns = clock() - t0
        if visited != n:
            raise AssertionError((visited, n))
        flush_cache(buffer)
        t0 = clock()
        for _ in range(k - 1):
            visited = walk(root)
        steady_ns = clock() - t0 if k > 1 else 0
        if visited != n:
            raise AssertionError((visited, n))
        mutation_ns = 0
        if args.mutate:
            flush_cache(buffer)
            t0 = clock()
            mutate_graph(shape, root)
            mutation_ns = clock() - t0
        del root  # Drop all member aliases before release or bridge disposal.
        flush_cache(buffer)
        reclose_ns = teardown_ns = 0
        if stage + 1 < depth:
            t0 = clock()
            if args.config != "B":
                packet.release()
            reclose_ns = clock() - t0 if args.config != "B" else 0
            channels[p][stage + 1].put(packet)
            del packet
            published[p][stage + 1].set()
        else:
            t0 = clock()
            if args.config != "B":
                # Discard the open bridge: no second close hidden in teardown.
                packet.value = None
            del packet
            teardown_ns = clock() - t0
            end = clock()
            rows[p]["end_to_end_ns"] = end - rows[p]["start_ns"]
            rows[p]["pipeline_ns"] = end - rows[p]["pipeline_start_ns"]
        rows[p]["stages"][stage] = {
            "acquire_ns": acquire_ns, "first_pass_ns": first_ns,
            "steady_passes_ns": steady_ns, "steady_passes": k - 1,
            "mutation_ns": mutation_ns, "reclose_ns": reclose_ns,
            "teardown_ns": teardown_ns,
        }
        if stage + 1 == depth:
            completed[p].set()
        finished.wait()

    def collect():
        while not finished.is_set():
            if not gc_active.wait(0.01):
                continue
            if finished.wait(args.gc_ms / 1000):
                break
            t0 = clock()
            count = gc.collect(2)
            gc_events.append({"start_ns": t0, "elapsed_ns": clock() - t0,
                              "collected": count})

    threads = []
    for p in range(pipelines):
        threads.append(threading.Thread(target=guard, args=(produce, p), daemon=True))
        for stage in range(depth):
            threads.append(threading.Thread(target=guard, args=(consume, p, stage), daemon=True))
    if args.gc_ms:
        threads.append(threading.Thread(target=guard, args=(collect,), daemon=True))
    for thread in threads:
        thread.start()
    try:
        start_gate.wait(args.timeout)
        for event in completed:
            wait(event)
    except BaseException:
        if not errors.empty():
            raise RuntimeError(errors.get()) from None
        raise
    finally:
        finished.set()
        for thread in threads:
            thread.join(args.timeout)
    if any(t.is_alive() for t in threads):
        raise TimeoutError("worker did not exit")
    if not errors.empty():
        raise RuntimeError(errors.get())
    first_start = min(r["start_ns"] for r in rows)
    last_end = max(r["start_ns"] + r["end_to_end_ns"] for r in rows)
    for row in rows:
        del row["start_ns"], row["pipeline_start_ns"]
    return {"pipelines": rows, "batch_wall_ns": last_end - first_start,
            "gc_events": gc_events}


def git_info(source):
    if source is None:
        return None
    def git(*parts):
        return subprocess.check_output(["git", "-C", str(source), *parts], text=True).strip()
    return {"path": str(source.resolve()), "revision": git("rev-parse", "HEAD"),
            "tracked_diff": git("diff", "HEAD", "--stat")}


def metadata(args):
    build_git = getattr(sys, "_git", None)
    return {
        "label": args.label, "config": args.config, "python": sys.version,
        "executable": sys.executable, "build_git": build_git,
        "source": git_info(args.source_root),
        "platform": platform.platform(), "machine": platform.machine(),
        "logical_cpus": os.cpu_count(), "affinity": args.cpus,
        "affinity_supported": hasattr(os, "sched_setaffinity"),
        "gil_enabled": sys._is_gil_enabled(),
        "build": {key: sysconfig.get_config_var(key) for key in (
            "CONFIG_ARGS", "CC", "CFLAGS", "PY_CFLAGS", "PY_CFLAGS_NODIST",
            "LDFLAGS", "Py_GIL_DISABLED", "Py_DEBUG", "Py_STATS")},
        "clock": vars(time.get_clock_info("perf_counter")),
        "immutable_available": TracingRegion is not None,
    }


def positive_list(value):
    try:
        result = list(dict.fromkeys(int(v) for v in value.split(",")))
        if not result or min(result) < 1:
            raise ValueError
        return result
    except ValueError:
        raise argparse.ArgumentTypeError("expected comma-separated positive integers") from None


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", choices=("B", "R", "RT"), required=True,
                   help="build identity, not a runtime ownership toggle")
    p.add_argument("--label", required=True)
    p.add_argument("--source-root", type=Path, help="source for THIS binary; never inferred from script")
    p.add_argument("--shape", choices=("dict", "tree", "both"), default="both")
    p.add_argument("--nodes", type=positive_list, default=positive_list("100,1000,10000"))
    p.add_argument("--passes", type=positive_list, default=positive_list("1,2,5,10,20,50,100"))
    p.add_argument("--depth", type=positive_list, default=[1], help="consumer stages per pipeline")
    p.add_argument("--pipelines", type=positive_list, default=[1])
    p.add_argument("--samples", type=int, default=30)
    p.add_argument("--warmups", type=int, default=3)
    p.add_argument("--cache-mib", type=int, default=0,
                   help="per-worker eviction buffer; use a separate cold-phase experiment")
    p.add_argument("--gc-ms", type=float, default=0, help="explicit full-GC interval, 0 disables")
    p.add_argument("--mutate", action="store_true")
    p.add_argument("--cpus", help="distinct Linux CPU IDs: pipeline-major, producer then consumers")
    p.add_argument("--timeout", type=float, default=300)
    p.add_argument("--retries", type=int, default=0,
                   help="re-run a trial whose close was refused, up to this many times; "
                        "refusals are recorded per case in failed_attempts")
    p.add_argument("--seed", type=int, default=20261110)
    p.add_argument("--output", type=Path, required=True)
    return p


def validate(args, p):
    if not sysconfig.get_config_var("Py_GIL_DISABLED") or sys._is_gil_enabled():
        p.error("requires a free-threaded build with the GIL disabled")
    if args.config != "B" and TracingRegion is None:
        p.error("R/RT require immutable.TracingRegion and immutable.Mutex")
    if (args.samples < 1 or args.warmups < 0 or args.cache_mib < 0 or args.retries < 0
            or not 0 <= args.gc_ms < float("inf") or not 0 < args.timeout < float("inf")):
        p.error("invalid samples, warmups, cache size, GC interval, or timeout")
    if args.cpus:
        if not hasattr(os, "sched_setaffinity"):
            p.error("per-thread CPU pinning is unavailable on this platform")
        try:
            args.cpus = [int(v) for v in args.cpus.split(",")]
        except ValueError:
            p.error("--cpus requires comma-separated CPU IDs")
        needed = max(args.pipelines) * (max(args.depth) + 1)
        if len(set(args.cpus)) != len(args.cpus) or len(args.cpus) < needed:
            p.error(f"supply at least {needed} distinct CPU IDs")
        if not set(args.cpus) <= os.sched_getaffinity(0):
            p.error("requested CPUs are outside the process affinity mask")
    else:
        args.cpus = None
    if args.output.exists():
        p.error("output already exists; choose a fresh result path")


def main():
    p = parser()
    args = p.parse_args()
    validate(args, p)
    settings = {key: str(value) if isinstance(value, Path) else value
                for key, value in vars(args).items()}
    result = {"schema": 1, "metadata": metadata(args), "settings": settings, "cases": []}
    shapes = ("dict", "tree") if args.shape == "both" else (args.shape,)
    cases = list(itertools.product(shapes, args.nodes, args.passes, args.depth, args.pipelines))
    random.Random(args.seed).shuffle(cases)
    was_enabled = gc.isenabled()
    gc.disable()
    try:
        for shape, n, k, depth, pipelines in cases:
            print(f"{args.config}: {shape} n={n} k={k} depth={depth} pipelines={pipelines}",
                  file=sys.stderr, flush=True)
            case = {"shape": shape, "nodes": n, "passes": k, "depth": depth,
                    "parallel_pipelines": pipelines, "samples": []}
            case["failed_attempts"] = []
            for index in range(args.warmups + args.samples):
                for attempt in range(args.retries + 1):
                    gc.collect(2)  # Before allocating fresh data, never between close and first touch.
                    try:
                        sample = trial(args, shape, n, k, depth, pipelines)
                        break
                    except RuntimeError as exc:
                        # Only a close the implementation refused is retried,
                        # and every refusal is kept in the result.
                        if attempt == args.retries or not is_spurious_close_failure(str(exc)):
                            raise
                        case["failed_attempts"].append(
                            {"trial": index, "attempt": attempt,
                             "error": str(exc).strip().splitlines()[-1]})
                if index >= args.warmups:
                    case["samples"].append(sample)
            result["cases"].append(case)
    finally:
        if was_enabled:
            gc.enable()
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(args.output)


if __name__ == "__main__":
    main()
