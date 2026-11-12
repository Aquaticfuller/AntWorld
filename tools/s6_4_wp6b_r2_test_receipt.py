"""Bind the R2 Windows test and build logs to the exact source tree."""

import argparse
from pathlib import Path
import platform
import re
import subprocess

from run_s6_4_wp6b import git, sha, write_json


def record(log, configuration, jobs):
    data = log.read_text(encoding="utf-8-sig")
    status = re.search(r"(\d+)% tests passed, (\d+) tests failed out of (\d+)", data)
    elapsed = re.search(r"Total Test time \(real\)\s*=\s*([\d.]+) sec", data)
    if not status or not elapsed:
        raise ValueError(f"incomplete CTest log: {log}")
    path = f"build/s6_3_4-{configuration}"
    return dict(command=["ctest", "--test-dir", path, "--output-on-failure", f"-j{jobs}"], tests=int(status[3]),
                failed=int(status[2]), exit_code=8 if int(status[2]) else 0, seconds=float(elapsed[1]), sha256=sha(log))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("logs", type=Path)
    parser.add_argument("compiler", type=Path)
    parser.add_argument("--build-logs", type=Path, default=Path("out"))
    parser.add_argument("--exit-codes", type=int, nargs=3, required=True, metavar=("RELEASE", "DEBUG", "SANITIZER"))
    parser.add_argument("--initial-sanitizer-exit", type=int, required=True)
    args = parser.parse_args()
    logs, builds = {}, {}
    for (flavor, jobs), code in zip((("release", 2), ("debug", 2), ("sanitizer", 1)), args.exit_codes, strict=True):
        logs[flavor] = record(args.logs / f"{flavor}.log", flavor, jobs)
        if code != logs[flavor]["exit_code"]:
            raise ValueError(f"CTest process status and log disagree: {flavor}")
        source = args.build_logs / f"wp6b-r2-{flavor}-build.log"
        builds[flavor] = dict(command=["cmake", "--build", f"build/s6_3_4-{flavor}", "--parallel", "4"],
                              source_log_sha256=sha(source))
    initial_sanitizer = args.logs / "sanitizer-missing-runtime.log"
    initial = record(initial_sanitizer, "sanitizer", 1)
    if args.initial_sanitizer_exit != initial["exit_code"] or "0xc0000135" not in initial_sanitizer.read_text(encoding="utf-8-sig"):
        raise ValueError("initial sanitizer loader result is missing")
    write_json(args.logs / "local_receipt.json", dict(source=git("rev-parse", "HEAD"), cpp_tree=git("rev-parse", "HEAD:cpp"),
               compiler=subprocess.check_output([args.compiler.resolve(), "--version"], text=True).splitlines(),
               python=platform.python_version(), platform=platform.platform(), builds=builds, ctest=logs,
               initial_sanitizer=initial, sanitizer_path="LLVM runtime bin directory prepended for the full successful repeat.",
               asan="halt_on_error=1", ubsan="halt_on_error=1:print_stacktrace=1"))
