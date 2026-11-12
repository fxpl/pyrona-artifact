#!/usr/bin/env python3
"""Time full GC collections with part of the heap in closed regions.

Builds REGIONS containers holding OBJECTS small objects each. On a region
build (--config R) the containers are TracingRegion bridges and the first
CLOSED of them are closed; on B they are plain objects. Automatic GC is
disabled, so only the explicit collections below run: a few warm-ups, then
COLLECTIONS timed gc.collect() calls. Prints one JSON line. Run one fresh
process per measurement (sweep.py does)."""

import argparse
import gc
import json
import sys
import time

try:
    from immutable import TracingRegion, freezable
except ImportError:  # B: no regions
    TracingRegion = None

    def freezable(cls):
        return cls


@freezable
class Obj:
    __slots__ = ("value",)

    def __init__(self, value):
        self.value = value


class Box:
    """B's stand-in for a region bridge: holds the same list, never closed."""


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", choices=("B", "R"), required=True)
    p.add_argument("--regions", type=int, default=10)
    p.add_argument("--objects", type=int, default=100_000, help="objects per region")
    p.add_argument("--closed", type=int, default=0, help="regions to close (R only)")
    p.add_argument("--warmups", type=int, default=2)
    p.add_argument("--collections", type=int, default=10)
    a = p.parse_args()
    if a.config == "R" and TracingRegion is None:
        p.error("R needs a region build (immutable.TracingRegion)")
    if a.config == "B" and a.closed:
        p.error("B has no regions to close")
    if a.regions < 0 or a.objects < 0 or not 0 <= a.closed <= a.regions:
        p.error("need regions >= 0, objects >= 0 and 0 <= closed <= regions")

    gc.disable()  # no automatic collections: only the ones timed below
    base_objects = len(gc.get_objects())  # the interpreter's own tracked heap

    heap = []
    for _ in range(a.regions):
        bridge = TracingRegion() if a.config == "R" else Box()
        bridge.objects = [Obj(None) for _ in range(a.objects)]
        heap.append(bridge)
    for bridge in heap[:a.closed]:
        TracingRegion.close(bridge)

    for _ in range(a.warmups):
        gc.collect()
    times = []
    for _ in range(a.collections):
        t0 = time.perf_counter_ns()
        gc.collect()
        times.append(time.perf_counter_ns() - t0)

    print(json.dumps({
        "config": a.config, "regions": a.regions, "objects": a.objects,
        "closed": a.closed, "base_objects": base_objects, "gc_ns": times,
        "python": sys.version, "executable": sys.executable,
    }))
    del heap


if __name__ == "__main__":
    main()
