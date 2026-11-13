"""Measure real-archive import, cached opening and read-only OP0 queries."""

from argparse import ArgumentParser
import ctypes
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import sqlite3
from statistics import median
import sys
from time import perf_counter

from op0 import DAY
from op0.cli import api_get, default_catalog
from op0.index import META
from op0.query import ReadAPI


def peak_rss_bytes():
    if os.name != "nt":
        from resource import RUSAGE_SELF, getrusage
        scale = 1 if sys.platform == "darwin" else 1024
        return getrusage(RUSAGE_SELF).ru_maxrss * scale
    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("faults", wintypes.DWORD)] + [
            (field, ctypes.c_size_t) for field in ("peak_working_set", "working_set", "peak_paged", "paged", "peak_nonpaged",
                                                  "nonpaged", "pagefile", "peak_pagefile")]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    measure = ctypes.WinDLL("psapi", use_last_error=True).GetProcessMemoryInfo
    measure.argtypes = (wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD)
    counters = Counters()
    counters.size = ctypes.sizeof(counters)
    if not measure(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.size):
        raise ctypes.WinError(ctypes.get_last_error())
    return counters.peak_working_set


def measure(query, count):
    durations = []
    for i in range(count):
        start = perf_counter()
        query(i)
        durations.append(round((perf_counter() - start)*1000, 3))
    return dict(samples_ms=durations, median_ms=round(median(durations), 3), max_ms=max(durations))


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("cache", type=Path, help="Use a fresh directory for a cold index measurement")
    parser.add_argument("report", type=Path)
    parser.add_argument("--demo", type=int, choices=range(1, 6), default=1)
    args = parser.parse_args()
    receipt = dict(python=sys.version.split()[0], sqlite=sqlite3.sqlite_version, platform=platform.platform(),
                   cpu=platform.processor(), date_utc=datetime.now(timezone.utc).isoformat())
    started = perf_counter()
    catalog = default_catalog(args.cache)
    receipt["catalog_fingerprint_ms"] = round((perf_counter() - started)*1000, 2)
    api = ReadAPI(catalog)
    key = catalog.list()[args.demo - 1]["key"]
    receipt["cold_index"] = not (catalog.root / key / META).is_file()
    worlds, _, elapsed = catalog.browse(key)
    world = worlds[0]
    receipt.update(title=world["title"], world_id=world["world_id"], facts=world["facts"],
                   archive_sha256=world["archive_sha256"], browse_ms=round(elapsed, 2),
                   indexed_at=world["timings"], peak_rss_after_import_bytes=peak_rss_bytes())
    route = f"world/{world['key']}/"
    days = (0, 1, 20, 45, 90, 120, 150)
    stamp = lambda i: days[i % len(days)] * DAY
    queen = world["initial_queens"][0]
    receipt["cached_open"] = measure(lambda _: catalog.browse(key), 21)
    receipt["seek_state"] = measure(lambda i: api_get(api, route + "state", time_ms=stamp(i)), 21)
    receipt["individual"] = measure(lambda i: api_get(api, route + "ant", id=queen, time_ms=stamp(i)), 21)
    receipt["soil_orientations"] = measure(lambda i: api_get(api, route + "geometry", time_ms=stamp(i),
                                                            axis="xyz"[i % 3], clearance=1), 21)
    receipt["events_page"] = measure(lambda i: api_get(api, route + "events", since_ms=stamp(i), limit=50), 21)
    receipt["peak_rss_bytes"] = peak_rss_bytes()
    args.report.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in receipt.items() if not isinstance(v, dict)}, indent=2))


if __name__ == "__main__":
    main()
