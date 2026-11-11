"""Run the frozen 72-case RM-02 simulation matrix and retain input and sidecar evidence."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import gzip
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
BASE = "6f6a69f45b0fff0ba3227039de36158b0994cbc4"
PROTOCOL = ROOT / "research/s6_4_rm02_sprint/FROZEN_ENGINEERING_PROTOCOL.md"
FILES = ("initial.chk", "final.chk", "observer.sqlite", "configuration.csv", "summary.csv", "cuts.csv", "errors.log")


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def frozen_cases():
    arms = (("ecology", ("depot", "ordinary", "scarce", "empty"), (8, 32)),
            ("window", ("ordinary",), (8, 32)), ("dense", ("dense",), (512, 2048)))
    return [dict(mode=mode, arm=arm, workers=n, seed=seed, case=f"{mode}-{arm}-{n}-{seed}")
            for mode, supplies, populations in arms for arm in supplies
            for n in populations for seed in range(1, 7)]


def git(*args):
    return subprocess.check_output(["git", *args], text=True, cwd=ROOT).strip()


def run_case(args, case):
    leaf = case["case"]
    source = args.scratch / leaf
    export = args.out / "raw" / leaf
    export.mkdir()
    command = [str(args.binary), str(source), case["mode"], case["arm"], str(case["workers"]), str(case["seed"])]
    with (export / "program.log").open("xb") as log:
        status = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=False).returncode
    artifacts = {}
    for name in (*FILES, "program.log"):
        path = (export if name == "program.log" else source) / name
        if not path.is_file():
            continue
        raw_hash = sha256(path)
        raw_size = path.stat().st_size
        if name.endswith((".chk", ".sqlite")):
            target = export / (name + ".gz")
            with (path.open("rb") as f, target.open("xb") as g,
                  gzip.GzipFile(fileobj=g, mode="wb", filename="", mtime=0, compresslevel=6) as packed):
                shutil.copyfileobj(f, packed)
        else:
            target = export / name
            if path != target:
                shutil.copyfile(path, target)
        artifacts[name] = dict(path=target.name, bytes=raw_size, sha256=raw_hash, archived_sha256=sha256(target),
                               archived_bytes=target.stat().st_size)
    summary = {}
    if (export / "summary.csv").exists():
        with (export / "summary.csv").open(encoding="utf-8", newline="") as stream:
            summary, = csv.DictReader(stream)
    receipt = dict(**case, exit_code=status, artifacts=artifacts, summary=summary)
    (export / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(leaf, status, summary.get("events", ""), flush=True)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=2)
    args = parser.parse_args()
    for key in ("binary", "cache", "compiler", "out", "scratch"):
        setattr(args, key, getattr(args, key).resolve())
    assert 1 <= args.jobs <= 4
    assert not git("diff", "--name-only", BASE, "HEAD", "--", "cpp/src", "cpp/include", "cpp/storage")
    assert not git("status", "--porcelain", "--", "cpp")
    settings = args.cache.read_text(encoding="utf-8")
    assert "CMAKE_BUILD_TYPE:STRING=Release" in settings and "ANTWORLD_SANITIZERS:BOOL=OFF" in settings
    assert "ANTWORLD_PROFILE:BOOL=OFF" in settings
    assert not args.scratch.exists() and not args.out.exists()
    (args.out / "raw").mkdir(parents=True)
    args.scratch.mkdir(parents=True)
    cases = frozen_cases()
    config = dict(phase0_commit=BASE, source_commit=git("rev-parse", "HEAD"), cpp_tree=git("rev-parse", "HEAD:cpp"),
                  configuration="Release", compiler=subprocess.check_output([str(args.compiler), "--version"],
                      text=True).splitlines(), executable=args.binary.name, binary_sha256=sha256(args.binary),
                  cache_sha256=sha256(args.cache), protocol_sha256=sha256(PROTOCOL), runner_sha256=sha256(Path(__file__)),
                  host=platform.platform(), python=sys.version.split()[0], jobs=args.jobs, started_utc_ns=time.time_ns(),
                  assay_args="OUTPUT MODE ARM WORKERS SEED", fixture_status="ENGINEERING_FIXTURE", cases=cases)
    (args.out / "freeze.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8", newline="\n")
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        rows = list(pool.map(lambda case: run_case(args, case), cases))
    codes = {r["case"]: r["exit_code"] for r in rows}
    (args.out / "completed.json").write_text(json.dumps(dict(ended_utc_ns=time.time_ns(), exit_codes=codes),
        indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"{sum(code == 0 for code in codes.values())}/{len(cases)} completed")
    sys.exit(1 if any(codes.values()) else 0)


if __name__ == "__main__":
    main()
