"""Run the frozen F1 inputs and archive every attempt with its canonical bytes."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import tempfile
import time
import zipfile

from freeze_s6_4_wp6b import FREEZE, ROOT


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def write_json(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def frozen_cases():
    cases = []
    for name, count, digest in (
        ("ordinary.jsonl", 960, "7a5c5134685726fa794394be4a5c8c33e2e6a08b1ec6469df283b031c73e14e4"),
        ("supplemental.jsonl", 972, "6181318c2492aba610420b7d81328fd4e9df1e7b698e994b972d491342e2d201"),
    ):
        path = FREEZE / name
        block = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        if len(block) != count or sha(path) != digest:
            raise ValueError(f"frozen case file changed: {name}")
        cases.extend(block)
    if len(cases) != len({c["case"] for c in cases}):
        raise ValueError("duplicate frozen case identity")
    return list(enumerate(cases, 1))


def input_bytes(identity, c):
    mass = c.get("external_food_components_ug", [0, 0, 0, 0])
    if sum(mass) != c["external_food_ug"]:
        raise ValueError("inconsistent resource input")
    header = [identity, c["software_seed"], 1 if c["population"] == "borisovka" else 2,
              c.get("arm", "ordinary"), int(c["care_enabled"]), c["externally_seeded_workers"], c["horizon_ms"], *mass]
    return (" ".join(map(str, header)) + "\n" + "".join(f"{key} {value}\n" for key, value in c["parameters"].items())).encode()


def schema_rejection(case):
    p = case["parameters"]
    return (sum(p[key] for key in ("maternal_lipid", "maternal_protein", "maternal_water", "structural_minimum")) > p["foundress_wet_mass"] or
            p["larva_basal"] < max(p["egg_basal"], p["pupa_basal"]) or p["egg_lipid"] > p["larval_lipid_capacity"])


def run_one(binary, work, identity, case, mode):
    work.mkdir()
    path = work / "parameters.txt"
    path.write_bytes(input_bytes(identity, case))
    write_json(work / "case.json", case)
    start = time.perf_counter()
    with (work / "program.log").open("wb") as log:
        code = subprocess.run([binary, path, work, mode], stdout=log, stderr=subprocess.STDOUT).returncode
    elapsed = (time.perf_counter() - start) * 1_000
    expected = schema_rejection(case)
    summary_path = work / "summary.csv"
    summary = None
    if summary_path.exists():
        with summary_path.open(newline="", encoding="utf-8") as stream:
            summary = next(csv.DictReader(stream), None)
    if expected and code and not summary and (work / "program.log").read_text().startswith("invalid F1 material"):
        status = "INPUT_REJECTED"
    elif not expected and code == 0 and summary:
        status = "COMPLETE"
    else:
        status = "ENGINEERING_FAILURE"
    artifacts = {item.name: {"bytes": item.stat().st_size, "sha256": sha(item)}
                 for item in sorted(work.iterdir()) if item.is_file()}
    receipt = dict(case=case["case"], identity=identity, mode=mode, status=status, exit_code=code, elapsed_ms=elapsed,
                   summary=summary, artifacts=artifacts)
    write_json(work / "receipt.json", receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--case", action="append", default=[])
    parser.add_argument("--mode", choices=("observed", "unobserved", "durable"), default="observed")
    parser.add_argument("--pilot", action="store_true", help="Allow a selected engineering probe on a dirty source tree.")
    args = parser.parse_args()
    cases = frozen_cases()
    if args.case:
        selected = set(args.case)
        cases = [(i, c) for i, c in cases if c["case"] in selected]
        if len(cases) != len(selected):
            raise ValueError("unknown case selection")
    dirty = git("status", "--porcelain", "--", "cpp", "tools/run_s6_4_wp6b.py")
    if dirty and not (args.pilot and args.case):
        raise ValueError("commit the actual source before collecting formal F1 results")
    binary = args.binary.resolve(strict=True)
    args.out.mkdir(parents=True)
    args.scratch.mkdir(parents=True, exist_ok=True)
    write_json(args.out / "run.json", dict(source=git("rev-parse", "HEAD"), cpp_tree=git("rev-parse", "HEAD:cpp"),
               frozen="9e8b0d25f88e6bbfc36f58e9d96b620c390931d2", binary_sha256=sha(binary), binary=binary.name, runner_sha256=sha(Path(__file__)),
               configuration="Release", compiler=subprocess.check_output([args.compiler.resolve(), "--version"], text=True).splitlines(),
               platform=platform.platform(), python=platform.python_version(), started_ns=time.time_ns(), dirty=dirty,
               mode=args.mode, cases=[case["case"] for _, case in cases]))
    all_receipts = []
    batches = []
    for kind in ("founding", "early"):
        items = [(i, c) for i, c in cases if (c["group"] == "early") == (kind == "early")]
        width = 4 if kind == "early" else 24
        batches.extend(items[offset:offset+width] for offset in range(0, len(items), width))
    for index, batch in enumerate(batches):
        destination = args.out / f"raw-{index:03}.zip"
        with zipfile.ZipFile(destination, "x", zipfile.ZIP_DEFLATED, compresslevel=4) as archive:
            for identity, case in batch:
                with tempfile.TemporaryDirectory(dir=args.scratch) as folder:
                    work = Path(folder).resolve() / "case"
                    receipt = run_one(binary, work, identity, case, args.mode)
                    all_receipts.append(receipt)
                    for item in sorted(work.iterdir()):
                        archive.write(item, f"{case['case']}/{item.name}")
                    print(identity, receipt["status"], case["case"], flush=True)
    write_json(args.out / "completed.json", dict(ended_ns=time.time_ns(), attempts=len(all_receipts),
               statuses={r["case"]: r["status"] for r in all_receipts},
               archives={path.name: sha(path) for path in sorted(args.out.glob("raw-*.zip"))}))
    return int(any(r["status"] == "ENGINEERING_FAILURE" for r in all_receipts))


if __name__ == "__main__":
    raise SystemExit(main())
