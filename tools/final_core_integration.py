"""Collect exact protected founding, soil, and trail assay witnesses."""

import argparse
import json
from pathlib import Path
import platform
import subprocess
from tempfile import TemporaryDirectory
from time import time_ns
from zipfile import ZIP_DEFLATED, ZipFile

from founding_qualification_witnesses import COMMAND
from run_integrated_founding import environments
from run_s6_4_wp6b import ROOT, git, run_one, sha, write_json


PROTOCOL = ROOT / "research/s6_4_final_core_readiness/FROZEN_FINAL_PROTOCOL.md"
FREEZE = "d107384"
REFERENCE = "73e801946a2419bf33eb78e5240f8af0923ff31a"
ARMS = {
    "roomy": "balanced", "compact-silent": "balanced", "compact-marked": "balanced",
    "compact-blind": "balanced", "compact-blocked": "blocked", "compact-no-protein": "no-protein",
    "compact-absent": "absent",
}
SEEDS = (1, 7, 19, 42, 43, 97)
POPULATIONS = ("borisovka", "st_petersburg")
WITNESSES = {
    ("borisovka", 1, "compact-marked"), ("st_petersburg", 1, "compact-marked"),
    ("borisovka", 1, "compact-blocked"), ("st_petersburg", 1, "compact-no-protein"),
    ("borisovka", 1, "compact-absent"),
}


def cases():
    base = environments("nominal")
    by_arm = {(c["population"], c["software_seed"], c["arm"]): (i, c) for i, c in base}
    for population in POPULATIONS:
        for seed in SEEDS:
            for arm, source in ARMS.items():
                identity, standard = by_arm[population, seed, "integrated-" + source]
                case = standard | dict(case=f"{population}-{seed}-{arm}", arm="readiness-" + arm,
                                       authority_reference=standard["case"], supply_arm=standard["arm"])
                yield identity, case, "observed"
    for population in POPULATIONS:
        for identity, case, mode in cases_observed_marked(base, population):
            yield identity, case, mode


def cases_observed_marked(base, population):
    identity, standard = next((i, c) for i, c in base if c["population"] == population
                              and c["software_seed"] == SEEDS[0] and c["arm"] == "integrated-balanced")
    for mode in ("unobserved", "durable-split"):
        case = standard | dict(case=f"{population}-{SEEDS[0]}-compact-marked-{mode}", arm="readiness-compact-marked",
                               authority_reference=standard["case"], supply_arm=standard["arm"])
        yield identity, case, mode


def collect(binary, compiler, output):
    frozen = subprocess.check_output(["git", "show", f"{FREEZE}:{PROTOCOL.relative_to(ROOT).as_posix()}"], cwd=ROOT)
    if frozen != PROTOCOL.read_bytes() or git("status", "--porcelain", "--", "cpp", "tools/final_core_integration.py"):
        raise ValueError("the protocol and collection source must be frozen before the run")
    roster = list(cases())
    output.mkdir(parents=True)
    write_json(output / "run.json", dict(source=git("rev-parse", "HEAD"), reference=REFERENCE,
        cpp_tree=git("rev-parse", "HEAD:cpp"), binary_sha256=sha(binary), arguments=COMMAND,
        configuration="Release", python=platform.python_version(), platform=platform.platform(),
        compiler=subprocess.check_output([compiler, "--version"], text=True).splitlines(), started_ns=time_ns(),
        collector_sha256=sha(Path(__file__)), protocol_sha256=sha(PROTOCOL),
        roster=[dict(case=c["case"], identity=i, mode=m) for i, c, m in roster]))
    with (output / "archives.jsonl").open("x", encoding="utf-8", newline="\n") as receipts:
        for identity, case, mode in roster:
            name = case["case"]
            with TemporaryDirectory(dir=output) as scratch:
                work = Path(scratch).resolve() / name
                receipt = run_one(binary, work, identity, case, mode, COMMAND)
                archive = output / f"{name}.zip"
                with ZipFile(archive, "x", ZIP_DEFLATED, compresslevel=4) as bundle:
                    for member in sorted(work.iterdir()):
                        bundle.write(member, f"{name}/{member.name}")
                print(json.dumps(dict(archive=archive.name, archive_sha256=sha(archive), receipt=receipt),
                                 sort_keys=True), file=receipts, flush=True)
                print(name, receipt["status"], receipt["summary"]["events"] if receipt["summary"] else "", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    collect(args.binary.resolve(strict=True), args.compiler.resolve(strict=True), args.output.resolve())
