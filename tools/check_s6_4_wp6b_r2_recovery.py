"""Reopen representative R2 and water worlds using their archived inputs."""

import argparse
import csv
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile

from run_s6_4_wp6b import sha, write_json
from run_s6_4_wp6b_r2 import app_args
from verify_s6_4_wp6b_r2 import frozen
from verify_s6_4_wp6b_r1 import verify


CASES = {
    "h1": ("borisovka-03-primary-1-on", "st_petersburg-00-primary-1-off"),
    "h2": ("borisovka-micro-nominal-0-1",),
    "both": ("borisovka-03-primary-1-on", "st_petersburg-00-primary-1-off"),
    "water-r1": ("borisovka-micro-nominal-0-1-water-blocked",),
    "water-both": ("borisovka-micro-nominal-0-1-water-reachable", "borisovka-micro-nominal-0-1-water-absent"),
}
FILES = ("initial.chk", "final.frame", "facts.bin")


def receipt(root, name, work):
    archives = json.loads((root / "completed.json").read_text(encoding="utf-8"))["archives"]
    for filename in archives:
        with zipfile.ZipFile(root / filename) as source:
            if f"{name}/receipt.json" not in source.namelist():
                continue
            parameters = work / "parameters.txt"
            parameters.write_bytes(source.read(f"{name}/parameters.txt"))
            return (parameters, json.loads(source.read(f"{name}/case.json")),
                    json.loads(source.read(f"{name}/receipt.json")))
    raise ValueError(f"missing recovery case: {name}")


def run(root, binary, scratch, output):
    scratch.mkdir(parents=True, exist_ok=True)
    results = []
    for mode, names in CASES.items():
        directory = root / mode
        verify(directory, subset=names, r2=frozen)
        for name in names:
            with tempfile.TemporaryDirectory(dir=scratch) as location:
                work = Path(location)
                parameters, case, reference = receipt(directory, name, work)
                expected = {key: reference["artifacts"][key]["sha256"] for key in FILES}
                for treatment in ("durable", "unobserved"):
                    dest = work / treatment
                    subprocess.run([binary, parameters, dest, treatment, *app_args(case)], check=True)
                    actual = {key: sha(dest / key) for key in FILES}
                    with (dest / "summary.csv").open(encoding="utf-8", newline="") as stream:
                        record, = csv.DictReader(stream)
                    if actual != expected or any(record[k] != reference["summary"][k] for k in ("state_hash", "trace_hash", "rng", "events")):
                        raise ValueError(f"recovery or observer changed canonical authority: {name}/{treatment}")
                    results.append(dict(mode=mode, case=name, treatment=treatment, hashes=actual,
                                        midpoint_sqlite_bytes=(dest / "midpoint.sqlite").stat().st_size if treatment == "durable" else None))
    write_json(output, dict(binary_sha256=sha(binary), cases=results))
    print(f"{len(results)} exact midpoint or observation-disabled runs")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("archive", "binary", "scratch", "out"):
        parser.add_argument("--" + name, type=lambda p: Path(p).resolve(), required=True)
    args = parser.parse_args()
    run(args.archive, args.binary, args.scratch, args.out)
