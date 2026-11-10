"""Run the frozen S6.3.4 workloads and preserve each raw measurement."""

import argparse
import csv
import ctypes
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import time


PERFORMANCE = ("timed-legacy", "timed-continuous", "integrated-legacy",
               "integrated-continuous", "facts-10000", "facts-100000", "facts-1000000")
SCIENCE = tuple((case, seed) for seed in (7, 19, 43)
                for case in ("ecology-4-balanced-care", "ecology-16-empty-care"))
SCIENCE += (("ecology-4-balanced-control", 7), ("ecology-16-empty-control", 7))
SCIENCE += tuple(("long", seed) for seed in (1, 2, 3))
ROOT = Path(__file__).resolve().parents[1]


def utc_now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds")


def write_json(path, content):
    path.write_bytes((json.dumps(content, indent=2) + "\n").encode("utf-8"))


def file_hash(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def output(*command):
    return subprocess.run(command, check=True, capture_output=True, cwd=ROOT).stdout.decode(
        "utf-8", errors="replace").strip()


def processor():
    if os.name != "nt":
        return platform.processor() or platform.machine()
    import winreg
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as cpu:
        return winreg.QueryValueEx(cpu, "ProcessorNameString")[0].strip()


def power_plan():
    if os.name == "nt":
        plan = re.search(r"[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}",
                         output("powercfg", "/GETACTIVESCHEME"))
        if plan:
            return plan.group(0)
    return "NOT MEASURED"


def cpu_ticks():
    if os.name != "nt":
        return None
    from ctypes.wintypes import FILETIME
    fields = [FILETIME() for _ in range(3)]
    if not ctypes.windll.kernel32.GetSystemTimes(*(ctypes.byref(field) for field in fields)):
        raise OSError("GetSystemTimes failed")
    return [(field.dwHighDateTime << 32) | field.dwLowDateTime for field in fields]


def cpu_window(first, last):
    if first is None or last is None:
        return None
    idle, kernel, user = (stop - start for start, stop in zip(first, last))
    total = kernel + user
    if total <= 0 or not 0 <= idle <= total or user < 0:
        raise ValueError("Invalid system CPU time window")
    return {"start_ticks_100ns": first, "end_ticks_100ns": last,
            "busy_percent": 100 * (total - idle) / total}


def schedule(mode):
    if mode == "science":
        yield from (("ecology", 1, case, seed) for case, seed in SCIENCE)
        return
    for repetition in range(6):
        # Rotate the same case order each round to spread position effects.
        for case in PERFORMANCE[repetition:] + PERFORMANCE[:repetition]:
            yield ("warmup" if repetition == 0 else "retained", repetition, case, 7)


def run_trial(binary, scratch, evidence, index, entry):
    role, repetition, case, seed = entry
    run_id = f"{index:02d}-{case}-{seed}"
    logs = evidence / run_id
    logs.mkdir()
    target = scratch / run_id
    start_utc, start, first = utc_now(), time.monotonic(), cpu_ticks()
    with (logs / "console.log").open("wb") as log:
        process = subprocess.run([binary, target, case, str(seed)], stdout=log, stderr=subprocess.STDOUT)
    finish_utc, last = utc_now(), cpu_ticks()
    files = {}
    for name in ("cuts.csv", "sample.csv", "console.log"):
        if name != "console.log" and (target / name).is_file():
            shutil.copyfile(target / name, logs / name)
        if (logs / name).is_file():
            files[name] = file_hash(logs / name)
    record = {"id": run_id, "index": index, "role": role, "repetition": repetition, "case": case, "seed": seed,
              "started_utc": start_utc, "finished_utc": finish_utc, "elapsed_seconds": time.monotonic() - start,
              "system_cpu_during_process": cpu_window(first, last), "exit_code": process.returncode, "files": files}
    write_json(logs / "attempt.json", record)
    print(f"{run_id}: exit {process.returncode}", flush=True)
    return process.returncode == 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("scratch", type=Path, help="New directory for databases")
    parser.add_argument("evidence", type=Path, help="New directory for CSVs and receipts")
    parser.add_argument("--mode", required=True, choices=("science", "performance"))
    parser.add_argument("--compiler", required=True, type=Path, help="Release C++ compiler used for the executable")
    args = parser.parse_args()
    binary = args.executable.resolve(strict=True)
    args.scratch.mkdir(parents=True)
    args.evidence.mkdir(parents=True)
    settings = {"mode": args.mode, "started_utc": utc_now(), "executable_sha256": file_hash(binary),
                "compiler": output(str(args.compiler.resolve(strict=True)), "--version").splitlines()[0],
                "source_commit": output("git", "rev-parse", "HEAD"),
                "cpp_tree": output("git", "rev-parse", "HEAD:cpp"),
                "cpp_matches_commit": not output("git", "status", "--porcelain", "--", "cpp"),
                "os": platform.system(), "os_release": platform.release(), "os_version": platform.version(),
                "machine": platform.machine(), "processor": processor(), "logical_cpus": os.cpu_count(),
                "power_plan": power_plan(), "cpu_frequency": "NOT MEASURED", "temperature": "NOT MEASURED",
                "package_power": "NOT MEASURED", "cache": "Uncontrolled OS cache; each case is a new process",
                "cpu_source": "Windows GetSystemTimes (idle, kernel including idle, user)",
                "pre_run_windows": [], "admission": "NOT APPLICABLE"}
    if args.mode == "performance":
        for _ in range(2):
            first = cpu_ticks()
            start = time.monotonic()
            time.sleep(5)
            window = cpu_window(first, cpu_ticks())
            if window is not None:
                window["seconds"] = time.monotonic() - start
                settings["pre_run_windows"].append(window)
        windows = settings["pre_run_windows"]
        settings["admission"] = ("ADMITTED" if len(windows) == 2
                                 and all(row["busy_percent"] <= 25 for row in windows)
                                 and settings["cpp_matches_commit"] else "REJECTED")
    write_json(args.evidence / "host.json", settings)
    if settings["admission"] == "REJECTED":
        print("No timing started: the frozen host/source admission was rejected.", flush=True)
        return 2

    trials = tuple(schedule(args.mode))
    with (args.evidence / "schedule.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("index", "role", "repetition", "case", "seed"))
        writer.writerows((i, *entry) for i, entry in enumerate(trials))
    success = [run_trial(binary, args.scratch, args.evidence, i, entry) for i, entry in enumerate(trials)]
    return 0 if all(success) else 1


if __name__ == "__main__":
    raise SystemExit(main())
