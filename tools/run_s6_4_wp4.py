"""Run frozen WP-4 assays and retain every case with hashed raw evidence."""

import argparse
from dataclasses import asdict
from pathlib import Path
import platform
import subprocess
from tempfile import TemporaryDirectory
import time

from read_s6_4_rm02_sidecar import require
from run_s6_4_rm02 import git, sha256
from run_s6_4_wp2 import write
from run_s6_4_wp3 import archive
from run_s6_4_wp4_performance import BASE, PROTOCOL
from s6_4_wp4_cases import matrix


ARTIFACTS = ("configuration.csv", "initial_food.csv", "inputs.csv", "cuts.csv", "lineage_inputs.csv",
             "lineage.csv", "summary.csv", "observer.sqlite", "midpoint.sqlite", "initial.chk",
             "midpoint.chk", "final.chk", "canonical.bin", "program.log")
PROTECTED = ("cpp/src", "cpp/include", "cpp/storage")


def run_case(binary, folder, scratch, case):
    folder.mkdir()
    with TemporaryDirectory(prefix="wp4-", dir=scratch) as temp:
        source = Path(temp) / "case"
        with (folder / "program.log").open("xb") as log:
            process = subprocess.run([binary, source, *case.arguments()], stdout=log, stderr=subprocess.STDOUT)
        result = archive(source, folder, ARTIFACTS, process.returncode)
    (folder / "program.log").unlink()
    write(folder / "receipt.json", dict(case=case.key, **asdict(case), **result))
    return result["exit_code"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--cache", required=True, type=Path)
    parser.add_argument("--compiler", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--scratch", required=True, type=Path)
    parser.add_argument("--case", action="append", help="Select an exact case for a separately recorded smoke run.")
    args = parser.parse_args()
    cache = args.cache.read_text(encoding="utf-8")
    require(all(value in cache for value in ("CMAKE_BUILD_TYPE:STRING=Release", "ANTWORLD_SANITIZERS:BOOL=OFF",
                                             "ANTWORLD_PROFILE:BOOL=OFF")), "require a Release build")
    require(not git("diff", "--name-only", BASE, "--", *PROTECTED), "authoritative source changed")
    require(not git("status", "--porcelain", "--", "cpp"), "commit application changes before collection")
    full = list(matrix())
    chosen = set(args.case or ())
    require(len(full) == len({case.key for case in full}) == 104, "frozen matrix changed")
    require(chosen <= {case.key for case in full}, "unknown frozen case")
    cases = [case for case in full if not chosen or case.key in chosen]
    raw = args.out / "raw"
    raw.mkdir(parents=True)
    args.scratch.mkdir(parents=True, exist_ok=True)
    binary = args.binary.resolve()
    write(args.out / "freeze.json", dict(baseline=BASE, source_commit=git("rev-parse", "HEAD"),
          cpp_tree=git("rev-parse", "HEAD:cpp"), authority={p: git("rev-parse", f"HEAD:{p}") for p in PROTECTED},
          protocol_sha256=sha256(PROTOCOL), case_matrix_sha256=sha256(Path(__file__).with_name("s6_4_wp4_cases.py")),
          runner_sha256=sha256(Path(__file__)), compiler=subprocess.check_output([str(args.compiler), "--version"],
          text=True).splitlines(), binary_sha256=sha256(binary), executable=binary.name,
          cache_sha256=sha256(args.cache), started_utc_ns=time.time_ns(), host=platform.platform(),
          python=platform.python_version(), selection="smoke" if chosen else "full",
          cases=[dict(case=case.key, **asdict(case)) for case in cases]))
    results = {}
    for case in cases:
        results[case.key] = run_case(binary, raw / case.key, args.scratch.resolve(), case)
        print(case.key, results[case.key], flush=True)
    write(args.out / "completed.json", dict(ended_utc_ns=time.time_ns(), exit_codes=results))
    print(f"{sum(code == 0 for code in results.values())}/{len(cases)} cases completed")
    return int(any(results.values()))


if __name__ == "__main__":
    raise SystemExit(main())
