"""Replay paired F1 v1 cases or collect the complete prospective F1-R1 archive."""

import argparse
import json
from pathlib import Path
import platform
import subprocess
from tempfile import TemporaryDirectory
import time
import zipfile

from run_s6_4_wp6b import ROOT, frozen_cases, git, input_bytes, run_one, sha, write_json


BASE = ROOT / "experiments/s6_4_wp6b/formal"
PROTOCOL = ROOT / "research/s6_4_wp6b_r1/FROZEN_R1_PROTOCOL.md"
FREEZE = "809487fd5009c32cfd562e3a822cd5b5730336f7"
NOMINAL = (172_800_000, 750_000)
SENSITIVITY = {"window24h": (86_400_000, 750_000), "window72h": (259_200_000, 750_000),
               "repeat0": (172_800_000, 0), "repeat50": (172_800_000, 500_000), "repeat875": (172_800_000, 875_000)}
EXACT = ("parameters.txt", "initial.chk", "final.frame", "facts.bin", "cuts.csv", "individuals.csv")


def enumerate_cases(model):
    items = frozen_cases()
    if model == "v1":
        return [(identity, c) for identity, c in items if c["group"] in ("primary", "check") or
                c["group"] == "wider" and ("-wider-opening_lay_spacing-low-" in c["case"] or
                                            "-wider-lay_interval-high-" in c["case"])]
    result = [(identity, dict(c, variant="F1-R1", care_memory=list(NOMINAL))) for identity, c in items]
    for identity, c in items:
        if c["group"] != "micro" or c.get("arm") != "nominal":
            continue
        for label, values in SENSITIVITY.items():
            result.append((identity, dict(c, case=f"{c['case']}-r1-{label}", group="r1-sensitivity", variant="F1-R1",
                                          reference_case=c["case"], sensitivity=label, care_memory=list(values))))
    return result


def reference_records():
    index = json.loads((BASE / "completed.json").read_text(encoding="utf-8"))
    result = {}
    for filename, digest in index["archives"].items():
        path = BASE / filename
        if sha(path) != digest:
            raise ValueError(f"accepted F1 archive changed: {filename}")
        with zipfile.ZipFile(path) as reader:
            for name in reader.namelist():
                if name.endswith("/receipt.json"):
                    row = json.loads(reader.read(name))
                    result[row["case"]] = row
    if set(result) != set(index["statuses"]):
        raise ValueError("accepted F1 reference coverage differs")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=("v1", "r1"), required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--case", action="append", default=[])
    args = parser.parse_args()
    source = git("rev-parse", "HEAD")
    if git("status", "--porcelain", "--", "cpp", "tools/run_s6_4_wp6b_r1.py", "tools/run_s6_4_wp6b.py"):
        raise ValueError("commit the measured model and runner before collection")
    cases = enumerate_cases(args.model)
    if args.case:
        cases = [(identity, c) for identity, c in cases if c["case"] in args.case]
        if len(cases) != len(set(args.case)):
            raise ValueError("unknown frozen case selection")
    refs = reference_records() if args.model == "v1" else {}
    binary = args.binary.resolve(strict=True)
    args.out.mkdir(parents=True)
    args.scratch.mkdir(parents=True, exist_ok=True)
    write_json(args.out / "run.json", dict(source=source, cpp_tree=git("rev-parse", "HEAD:cpp"), model=args.model,
               frozen=git("rev-parse", FREEZE), protocol_sha256=sha(PROTOCOL),
               binary_sha256=sha(binary), binary=binary.name, runner_sha256=sha(Path(__file__)),
               configuration="Release", compiler=subprocess.check_output([args.compiler.resolve(), "--version"], text=True).splitlines(),
               platform=platform.platform(), python=platform.python_version(), started_ns=time.time_ns(),
               cases=[case["case"] for _, case in cases], selected_subset=bool(args.case)))
    receipts, archives = {}, {}
    # Limit compressed archive sizes for review and preserve high-load cases individually in small batches.
    for group, width in ((False, 24), (True, 4)):
        items = [(identity, c) for identity, c in cases if (c["group"] == "early") == group]
        for offset in range(0, len(items), width):
            name = f"raw-{len(archives):03}.zip"
            destination = args.out / name
            if args.model == "r1":
                archive = zipfile.ZipFile(destination, "x", zipfile.ZIP_DEFLATED, compresslevel=4)
            try:
                for identity, case in items[offset:offset+width]:
                    with TemporaryDirectory(dir=args.scratch) as folder:
                        path = Path(folder).resolve() / "case"
                        options = tuple(map(str, case.get("care_memory", ())))
                        receipt = run_one(binary, path, identity, case, "observed", options)
                        case_id = case["case"]
                        if args.model == "r1":
                            for item in sorted(path.iterdir()):
                                archive.write(item, f"{case_id}/{item.name}")
                            receipts[case_id] = receipt["status"]
                        else:
                            ref = refs[case_id]
                            exact = receipt["status"] == ref["status"] and all(
                                receipt["artifacts"].get(file) == ref["artifacts"].get(file) for file in EXACT)
                            receipts[case_id] = dict(exact=exact, status=receipt["status"], exit_code=receipt["exit_code"],
                                elapsed_ms=receipt["elapsed_ms"], signature={key: receipt["artifacts"].get(key) for key in EXACT})
                        print(identity, receipt["status"], case_id, flush=True)
            finally:
                if args.model == "r1":
                    archive.close()
                    archives[name] = sha(destination)
    write_json(args.out / "completed.json", dict(ended_ns=time.time_ns(), attempts=len(receipts),
               statuses=receipts, archives=archives, reference_archive_index_sha256=sha(BASE / "completed.json")))
    if args.model == "v1":
        return int(not all(row["exact"] for row in receipts.values()))
    return int("ENGINEERING_FAILURE" in receipts.values())


if __name__ == "__main__":
    raise SystemExit(main())
