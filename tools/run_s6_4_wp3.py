"""Run the complete frozen WP-3 case matrix and retain hashed raw evidence."""

import argparse
from dataclasses import asdict
import gzip
from pathlib import Path
import platform
import subprocess
import sys
import tarfile
from tempfile import TemporaryDirectory
import time

from read_s6_4_rm02_sidecar import require
from run_s6_4_rm02 import git, sha256
from run_s6_4_wp2 import write
from run_s6_4_wp3_performance import BASE, PROTOCOL
from s6_4_wp3_cases import matrix


COMMON = ("configuration.csv", "program.log")
LIVE = (*COMMON, "layout.csv", "inputs.csv", "cuts.csv", "actors.csv", "routes.csv",
        "local_steps.csv", "food_cues.csv", "field.csv", "resources.csv", "summary.csv",
        "observer.sqlite", "midpoint.sqlite", "initial.chk", "midpoint.chk", "final.chk", "canonical.bin")
PREPARED = (*COMMON, "prepared.csv")


def archive(source, folder, expected, program_status):
    files = {item.name: item for item in source.iterdir()} if source.exists() else {}
    files["program.log"] = folder / "program.log"
    artifacts = {}
    destination = folder / "raw.tar.gz"
    with (destination.open("xb") as compressed,
          gzip.GzipFile(filename="", fileobj=compressed, mode="wb", compresslevel=6, mtime=0) as stream,
          tarfile.open(fileobj=stream, mode="w|", format=tarfile.USTAR_FORMAT) as bundle):
        for name, original in sorted(files.items()):
            require(original.is_file() and not original.is_symlink(), "unexpected case evidence type")
            info = tarfile.TarInfo(name)
            info.size = original.stat().st_size
            info.mode = 0o644
            with original.open("rb") as data:
                bundle.addfile(info, data)
            artifacts[name] = dict(bytes=info.size, sha256=sha256(original))
    complete = set(artifacts) == set(expected)
    return dict(exit_code=program_status or (0 if complete else 125), program_exit_code=program_status,
                archive_bytes=destination.stat().st_size, archive_sha256=sha256(destination), artifacts=artifacts)


def run_case(binary, folder, scratch, case):
    folder.mkdir()
    with TemporaryDirectory(prefix="wp3-", dir=scratch) as temp:
        source = Path(temp) / "case"
        with (folder / "program.log").open("xb") as log:
            process = subprocess.run([binary, source, *case.arguments()], stdout=log, stderr=subprocess.STDOUT)
        result = archive(source, folder, PREPARED if case.family == "prepared" else LIVE, process.returncode)
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
    parser.add_argument("--case", action="append", help="Select an exact frozen case for a smoke run.")
    args = parser.parse_args()
    cache = args.cache.read_text(encoding="utf-8")
    require(all(value in cache for value in ("CMAKE_BUILD_TYPE:STRING=Release", "ANTWORLD_SANITIZERS:BOOL=OFF",
                                             "ANTWORLD_PROFILE:BOOL=OFF")), "require a clean Release build")
    require(not git("diff", "--name-only", BASE, "--", "cpp/src", "cpp/include", "cpp/storage"),
            "authoritative source changed")
    require(not git("status", "--porcelain", "--", "cpp"), "commit application changes before collecting")
    all_cases = list(matrix())
    chosen = set(args.case or ())
    cases = [case for case in all_cases if not chosen or case.key in chosen]
    require(not chosen - {case.key for case in cases}, "unknown frozen case")
    raw = args.out / "raw"
    raw.mkdir(parents=True)
    args.scratch.mkdir(parents=True, exist_ok=True)
    binary = args.binary.resolve()
    write(args.out / "freeze.json", dict(baseline=BASE, source_commit=git("rev-parse", "HEAD"),
          cpp_tree=git("rev-parse", "HEAD:cpp"), protocol_sha256=sha256(PROTOCOL),
          case_matrix_sha256=sha256(Path(__file__).with_name("s6_4_wp3_cases.py")),
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
    sys.exit(main())
