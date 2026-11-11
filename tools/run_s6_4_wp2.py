"""Run and archive the frozen WP-2 fixture matrix with exact identities."""

import argparse
import gzip
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import time

from run_s6_4_rm02 import git, sha256


ROOT = Path(__file__).resolve().parents[1]
BASE = "39b21eae59794dc0d472fea1630f618fe7b90a9b"
PROTOCOL = ROOT / "research/s6_4_wp2/FROZEN_PROTOCOL.md"
FIELDS = ("mode", "arm", "workers", "seed", "layout", "brood", "origin")
ARTIFACTS = ("configuration.csv", "initial_ants.csv", "cuts.csv", "summary.csv",
             "initial.chk", "midpoint.chk", "final.chk", "observer.sqlite", "program.log")
CARE_SEEDS = (7, 19, 43, 71, 101, 137)


def matrix():
    def record(*values):
        return dict(zip(FIELDS, values), case="-".join(map(str, values)))

    for arm in ("depot", "ordinary", "scarce", "empty"):
        for workers in (8, 32):
            for seed in range(1, 7):
                yield record("activity", arm, workers, seed, arm, 0, "balanced" if arm in ("depot", "ordinary") else arm)
    for arm in ("care", "control"):
        for workers in (4, 16):
            for supply in ("balanced", "empty"):
                for seed in CARE_SEEDS[:3]:
                    yield record("integrated", arm, workers, seed, "underground", 4, supply)
    for arm, workers, brood, layout in (("absent", 0, 5, "plain"), ("added", 5, 5, "plain"),
                                        ("removed", 5, 5, "plain"), ("sham", 5, 5, "plain"),
                                        ("no_brood", 0, 0, "plain"), ("barrier", 3, 5, "wall")):
        for seed in CARE_SEEDS:
            yield record("b01", arm, workers, seed, layout, brood, "own")
    layouts = [(layout, 6, origin) for layout in ("line", "split", "far", "wall") for origin in ("own", "foreign")]
    layouts += [("line", count, "own") for count in (0, 1)]
    for arm, workers in (("queen", 0), ("trio", 3)):
        for layout, brood, origin in layouts:
            for seed in CARE_SEEDS:
                yield record("b02", arm, workers, seed, layout, brood, origin)


def write(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")


def run_case(binary, folder, scratch, case):
    folder.mkdir()
    artifacts = {}
    with TemporaryDirectory(prefix="wp2-", dir=scratch) as temp:
        source = Path(temp) / "case"
        with (folder / "program.log").open("xb") as log:
            completed = subprocess.run([binary, source, *(str(case[key]) for key in FIELDS)],
                                       stdout=log, stderr=subprocess.STDOUT, check=False)
        for name in ARTIFACTS:
            original = (folder if name == "program.log" else source) / name
            if not original.is_file():
                continue
            target = folder / name
            if original.suffix in (".chk", ".sqlite"):
                target = folder / (name + ".gz")
                with (original.open("rb") as data, target.open("xb") as packed,
                      gzip.GzipFile(filename="", fileobj=packed, mode="wb", compresslevel=6, mtime=0) as stream):
                    shutil.copyfileobj(data, stream)
            elif original != target:
                shutil.copyfile(original, target)
            artifacts[name] = dict(path=target.name, bytes=original.stat().st_size, sha256=sha256(original),
                                   archived_bytes=target.stat().st_size, archived_sha256=sha256(target))
    status = completed.returncode
    if not status and set(artifacts) != set(ARTIFACTS):
        status = 125
    write(folder / "receipt.json", dict(**case, exit_code=status, program_exit_code=completed.returncode, artifacts=artifacts))
    print(case["case"], status, flush=True)
    return status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--cache", required=True, type=Path)
    parser.add_argument("--compiler", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--scratch", required=True, type=Path)
    parser.add_argument("--stratum", choices=("activity", "integrated", "b01", "b02"))
    args = parser.parse_args()
    cache = args.cache.read_text(encoding="utf-8")
    if not all(value in cache for value in ("CMAKE_BUILD_TYPE:STRING=Release", "ANTWORLD_SANITIZERS:BOOL=OFF",
                                            "ANTWORLD_PROFILE:BOOL=OFF")):
        parser.error("require a Release build with profile and sanitizers off")
    if git("diff", "--name-only", BASE, "--", "cpp/src", "cpp/include", "cpp/storage"):
        raise ValueError("authoritative source changed")
    if git("status", "--porcelain", "--", "cpp"):
        raise ValueError("commit the application sources before archiving")
    raw = args.out / "raw"
    raw.mkdir(parents=True)
    scratch = args.scratch.resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    cases = [case for case in matrix() if args.stratum is None or case["mode"] == args.stratum]
    write(args.out / "freeze.json", dict(source_commit=git("rev-parse", "HEAD"), baseline=BASE,
        cpp_tree=git("rev-parse", "HEAD:cpp"), protocol_sha256=sha256(PROTOCOL), runner_sha256=sha256(Path(__file__)),
        binary_sha256=sha256(args.binary), cache_sha256=sha256(args.cache), executable=args.binary.name,
        compiler=subprocess.check_output([str(args.compiler), "--version"], text=True).splitlines(),
        started_utc_ns=time.time_ns(), host=platform.platform(), python=platform.python_version(),
        selection=args.stratum or "full", cases=cases))
    results = {case["case"]: run_case(args.binary.resolve(), raw / case["case"], scratch, case) for case in cases}
    write(args.out / "completed.json", dict(ended_utc_ns=time.time_ns(), exit_codes=results))
    print(f"{sum(code == 0 for code in results.values())}/{len(cases)} cases completed")
    return int(any(results.values()))


if __name__ == "__main__":
    sys.exit(main())
