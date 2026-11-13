"""Collect the predeclared founding cohort contrasts without dropping a world."""

import argparse
from itertools import product
import json
from pathlib import Path
import platform
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

from founding_qualification_witnesses import COMMAND
from run_ecological_closure import roster as ecological_roster
from run_integrated_founding import DAY
from run_s6_4_wp6b import ROOT, git, run_one, sha, write_json


REFERENCE = "ae1fdfdd0b29c831840f9147ccaabf19e8277f8b"
FREEZE = "b376217f70bbaa3fde2e98cb9470fc724e79fd53"
PROTOCOL = Path("research/s6_4_founding_cohort_release/FROZEN_COHORT_PROTOCOL.md")
WATER = {"n": "absent", "b": "blocked", "r": "reachable"}
COUNTS = {"primary": 384, "hatch": 96, "extended": 292}


def cohort_case(c, name, flags, repeat, horizon):
    first, work, recruit, water, hatch = flags
    label = f"c{first}{work}{recruit}{water}{hatch}"
    return c | dict(case=f"{c['case']}-{name}-{label}-r{repeat}",
                    reference_case=c["case"], cohort_assay=True,
                    arm=f"cohort25-{c['layout']}-{label}-{c['source']}", horizon_ms=horizon * DAY,
                    panel=name, first_meal=first, activity_charge=work, recruitment=recruit,
                    water_access=WATER[water], hatch_cue=hatch, repeat_feeding=repeat)


def arguments(repeat):
    return [COMMAND[0], "750000" if repeat else "0", *COMMAND[2:]]


def roster(panel):
    for identity, c, mode in ecological_roster("joint"):
        if c["treatment"] != "joint":
            continue
        ordinary = c["source"] == "balanced" and c["parameters"]["maternal_lipid"] == 5500
        if panel == "primary" and ordinary and mode == "observed":
            for first, work, recruit, water in product((0, 1), (0, 1), (0, 1), ("b", "r")):
                yield identity, cohort_case(c, panel, (first, work, recruit, water, 1), 1, 55), mode, arguments(1)
        elif panel == "hatch" and ordinary and mode == "observed":
            for hatch, repeat in product((0, 1), repeat=2):
                yield identity, cohort_case(c, panel, (1, 1, 1, "n", hatch), repeat, 55), mode, arguments(repeat)
        elif panel == "extended":
            if mode == "observed":
                yield identity, cohort_case(c, "conservative", (0, 1, 1, "n", 1), 1, 150), mode, arguments(1)
                yield identity, cohort_case(c, "hydrated", (1, 1, 1, "r", 1), 1, 150), mode, arguments(1)
            elif mode == "durable-split" and ((c["population"], c["layout"]) in
                                              {("borisovka", "shaft"), ("st_petersburg", "dogleg")}):
                for name, flags in (("conservative", (0, 1, 1, "n", 1)), ("hydrated", (1, 1, 1, "r", 1))):
                    case = cohort_case(c, name, flags, 1, 150)
                    case["observed_case"] = case["case"].replace("-durable-split", "")
                    yield identity, case, mode, arguments(1)


def manifest(path):
    return [json.loads(line) for line in (path / "archives.jsonl").read_bytes().splitlines()]


def collect(panel, binary, directory, scratch):
    frozen = subprocess.check_output(["git", "show", f"{FREEZE}:{PROTOCOL.as_posix()}"], cwd=ROOT)
    if frozen != (ROOT / PROTOCOL).read_bytes() or git("status", "--porcelain", "--", "cpp", "tools/run_founding_cohort_release.py"):
        raise ValueError("commit the simulation and runner and retain the prospective protocol")
    selected = list(roster(panel))
    names = [case["case"] for _, case, _, _ in selected]
    if len(set(names)) != len(names) or len(names) != COUNTS[panel]:
        raise ValueError("changed frozen roster")
    directory.mkdir(parents=True)
    scratch.mkdir(parents=True, exist_ok=True)
    write_json(directory / "run.json", dict(source=git("rev-parse", "HEAD"), reference=REFERENCE,
               cpp_tree=git("rev-parse", "HEAD:cpp"), protocol_sha256=sha(ROOT / PROTOCOL),
               binary_sha256=sha(binary), collector_sha256=sha(Path(__file__)), python=platform.python_version(),
               platform=platform.platform(), panel=panel, cases=names))
    with (directory / "archives.jsonl").open("x", newline="\n", encoding="utf-8") as index:
        for identity, case, mode, extra in selected:
            with TemporaryDirectory(dir=scratch) as temporary:
                work = Path(temporary) / "case"
                receipt = run_one(binary, work, identity, case, mode, extra)
                archive = directory / f"{case['case']}.zip"
                with ZipFile(archive, "x", ZIP_DEFLATED, compresslevel=4) as bundle:
                    for member in sorted(work.iterdir()):
                        bundle.write(member, member.name)
                print(json.dumps(dict(case=case["case"], archive=archive.name, sha256=sha(archive), receipt=receipt),
                                 sort_keys=True), file=index, flush=True)
                print(case["case"], receipt["status"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("panel", choices=tuple(COUNTS))
    for name in ("binary", "output", "scratch"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    collect(args.panel, args.binary.resolve(strict=True), args.output.resolve(), args.scratch.resolve())
