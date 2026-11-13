"""Collect every frozen ecological, care and scout-control case."""

import argparse
import json
from pathlib import Path
import platform
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

from founding_qualification_witnesses import COMMAND
from run_integrated_founding import DAY, environments
from run_s6_4_wp6b import ROOT, git, run_one, sha, write_json


PROTOCOL = ROOT / "research/s6_4_ecological_mechanism_closure/FROZEN_ECOLOGICAL_PROTOCOL.md"
REFERENCE = "2bc1f18462378108defea9724f45821fe78bf89e"
SCOUT_ARMS = ("scout", "sham", "disabled", "naive", "existing", "blocked", "depleted")


def roster(panel):
    for identity, c in environments("nominal"):
        source = c["arm"].removeprefix("integrated-")
        if panel == "joint":
            if source == "balanced":
                arms = [(layout, treatment, reserve, "observed") for layout in ("shaft", "dogleg")
                        for treatment, reserve in (("joint", 5500), ("joint", 5250), ("clock", 5500),
                                                   ("silent", 5500), ("legacy", 5500))]
                if c["software_seed"] == 1:
                    arms += [(layout, "joint", 5500, mode) for layout in ("shaft", "dogleg")
                             for mode in ("unobserved", "durable-split")]
            elif source in ("absent", "blocked", "no-protein", "limited"):
                arms = [(layout, "joint", 5500, "observed") for layout in ("shaft", "dogleg")]
            else:
                continue
        elif source == "absent":
            arms = [("shaft", treatment, 5500, "observed") for treatment in ("clock", "first", "water", "wallwater", "cost", "careoff")]
        else:
            continue
        for layout, treatment, reserve, mode in arms:
            name = f"{c['population']}-{c['software_seed']}-{layout}-{treatment}-{source}-{reserve}"
            if mode != "observed":
                name += "-" + mode
            arm = f"ecology-{layout}-{'first' if treatment == 'careoff' else treatment}-{source}"
            yield identity, c | dict(case=name, arm=arm, source=source, layout=layout, treatment=treatment,
                                     care_enabled=treatment != "careoff",
                                     horizon_ms=55*DAY if panel == "care" else 150*DAY,
                                     parameters=c["parameters"] | {"maternal_lipid": reserve}), mode


def scout(binary, work, arm, seed, mode):
    work.mkdir()
    write_json(work/"case.json", dict(arm=arm, seed=seed, horizon_ms=1200000, mode=mode))
    with (work/"program.log").open("wb") as log:
        args = [binary, str(seed), arm, work] + (["durable"] if mode == "durable" else [])
        code = subprocess.run(args, stdout=log, stderr=subprocess.STDOUT).returncode
    receipt = dict(status="COMPLETE" if not code else "ENGINEERING_FAILURE", exit_code=code,
                   artifacts={p.name: dict(bytes=p.stat().st_size, sha256=sha(p)) for p in work.iterdir() if p.is_file()})
    write_json(work/"receipt.json", receipt)
    return receipt


def collect(binary, output, panel, expanded):
    frozen = subprocess.check_output(["git", "show", f"26110c0:{PROTOCOL.relative_to(ROOT).as_posix()}"], cwd=ROOT)
    if frozen != PROTOCOL.read_bytes() or git("status", "--porcelain", "--", "cpp", "tools/run_ecological_closure.py"):
        raise ValueError("commit the collection source and retain the frozen protocol")
    if panel == "scout":
        selected = [(f"{arm}-{seed}-{mode}", (arm, seed, mode)) for arm in SCOUT_ARMS for seed in range(1,13)
                    for mode in (("observed", "durable") if seed == 1 and arm == "scout" else ("observed",))]
    else:
        selected = [(c["case"], (identity, c, mode)) for identity, c, mode in roster(panel)]
        if expanded:
            selected = [(name, (identity, c | dict(arm=c["arm"].replace("ecology-","ecology4-",1)), mode))
                        for name, (identity,c,mode) in selected]
    output.mkdir(parents=True)
    write_json(output/"run.json", dict(reference=REFERENCE, source=git("rev-parse", "HEAD"),
        cpp_tree=git("rev-parse", "HEAD:cpp"), protocol_sha256=sha(PROTOCOL), binary_sha256=sha(binary),
        collector_sha256=sha(Path(__file__)), platform=platform.platform(), python=platform.python_version(),
        panel=panel, expanded=expanded, cases=[name for name, _ in selected], arguments=COMMAND if panel != "scout" else []))
    with (output/"archives.jsonl").open("x", encoding="utf-8", newline="\n") as index:
        for name, args in selected:
            with TemporaryDirectory(dir=output) as temp:
                work = Path(temp)/name
                receipt = scout(binary,work,*args) if panel=="scout" else run_one(binary,work,*args,COMMAND)
                archive = output/f"{name}.zip"
                with ZipFile(archive, "x", ZIP_DEFLATED, compresslevel=4) as bundle:
                    for member in sorted(work.iterdir()):
                        bundle.write(member,member.name)
                print(json.dumps(dict(case=name, archive=archive.name, sha256=sha(archive), receipt=receipt),
                                 sort_keys=True), file=index, flush=True)
                print(name, receipt["status"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("panel", choices=("joint", "care", "scout"))
    parser.add_argument("binary", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--expanded", action="store_true")
    args = parser.parse_args()
    collect(args.binary.resolve(strict=True), args.output.resolve(), args.panel, args.expanded)
