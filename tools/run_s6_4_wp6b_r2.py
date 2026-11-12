"""Collect the frozen R2 factorial and finite-water cases, or replay reviewed controls."""

import argparse
from collections import Counter
from contextlib import nullcontext
import json
from pathlib import Path
import platform
import subprocess
from tempfile import TemporaryDirectory
import time
import zipfile

from run_s6_4_wp6b import ROOT, frozen_cases, git, run_one, sha, write_json
from run_s6_4_wp6b_r1 import BASE, EXACT, NOMINAL, reference_records


FREEZE = "d227dc2495b8c71802c1b829816df0d420729697"
PROTOCOL = ROOT / "research/s6_4_wp6b_r2/FROZEN_R2_PROTOCOL.md"
REFERENCES = {"v1": BASE, "r1": ROOT / "experiments/s6_4_wp6b_r1/formal"}
MASKS = {"h1": 1, "h2": 2, "both": 3, "water-r1": 0, "water-both": 3}
MICRO = {"nominal", "care-off", "contact-blocked", "maternal_lipid-low", "maternal_protein-low",
         "maternal_water-low", "queen_basal-high", "egg_lipid-low", "coherent-rates-2"}


def declared_cases(model):
    items = frozen_cases()
    if model.startswith("water-"):
        selected = [(10_000 + 4 * identity + i, dict(c, case=f"{c['case']}-water-{arm}",
                    group="water", arm=f"water-{arm}", reference_case=c["case"],
                    external_food_ug=amount, external_food_components_ug=[0, 0, amount, 0]))
                    for identity, c in items if c["group"] == "micro" and c["arm"] == "nominal"
                    for i, (arm, amount) in enumerate((("reachable", 200_000), ("blocked", 200_000), ("absent", 0)))]
        assert len(selected) == 36
    else:
        selected = [(identity, c) for identity, c in items if c["group"] in ("primary", "check") or
                    c["group"] in ("micro", "wider") and c["arm"] in MICRO]
        assert Counter(c["group"] for _, c in selected) == {"primary": 768, "check": 192, "micro": 36, "wider": 72}
        # Keep both inherited wider spacing families, including the five v1 successes.
        wider = [(identity, c) for identity, c in items if c["group"] == "wider" and
                 c["arm"] in ("opening_lay_spacing-low", "lay_interval-high")]
        assert len(wider) == 24
        selected.extend(wider)
        if model == "both":
            references = [(identity, c) for identity, c in items if c["group"] == "early" and
                          c["software_seed"] == 1 and c["arm"] in ("depot", "empty")]
            assert len(references) == 8
            selected.extend(references)
    return [(identity, dict(c, model=model, model_version=1 if model == "v1" else 3 if MASKS.get(model) else 2,
                            care_memory=[] if model == "v1" else list(NOMINAL), early_access_mask=MASKS.get(model, 0)))
            for identity, c in selected]


def app_args(case):
    args = tuple(map(str, case["care_memory"]))
    return (*args, "0", str(case["early_access_mask"])) if case["early_access_mask"] else args


def manifest(args, cases, binary):
    frozen = subprocess.check_output(["git", "show", f"{FREEZE}:{PROTOCOL.relative_to(ROOT).as_posix()}"], cwd=ROOT)
    if frozen != PROTOCOL.read_bytes():
        raise ValueError("R2 prospective protocol differs from its frozen commit")
    paths = [Path(__file__), Path(__file__).with_name("run_s6_4_wp6b.py"), Path(__file__).with_name("run_s6_4_wp6b_r1.py")]
    return dict(source=git("rev-parse", "HEAD"), cpp_tree=git("rev-parse", "HEAD:cpp"), model=args.model,
                frozen=FREEZE, protocol_sha256=sha(PROTOCOL), binary=binary.name, binary_sha256=sha(binary),
                runner_sources={p.name: sha(p) for p in paths}, selected_subset=bool(args.case),
                configuration="Release", compiler=subprocess.check_output([args.compiler.resolve(), "--version"], text=True).splitlines(),
                platform=platform.platform(), python=platform.python_version(), started_ns=time.time_ns(),
                cases=[c["case"] for _, c in cases])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=(*REFERENCES, *MASKS), required=True)
    for name in ("binary", "compiler", "out", "scratch"):
        parser.add_argument("--" + name, type=lambda p: Path(p).resolve(), required=True)
    parser.add_argument("--case", action="append", default=[])
    args = parser.parse_args()
    if git("status", "--porcelain", "--", "cpp", "tools/run_s6_4_wp6b.py", "tools/run_s6_4_wp6b_r1.py", "tools/run_s6_4_wp6b_r2.py"):
        raise ValueError("commit the model and frozen runner before collection")
    cases = declared_cases(args.model)
    if args.case:
        cases = [(identity, c) for identity, c in cases if c["case"] in args.case]
        if len(cases) != len(set(args.case)):
            raise ValueError("unknown frozen case selection")
    reference_root = REFERENCES.get(args.model)
    refs = reference_records(reference_root) if reference_root else None
    binary = args.binary.resolve(strict=True)
    args.out.mkdir(parents=True)
    args.scratch.mkdir(parents=True, exist_ok=True)
    write_json(args.out / "run.json", manifest(args, cases, binary))
    statuses, archives = {}, {}
    for offset in range(0, len(cases), 16):
        path = args.out / f"raw-{offset // 16:03}.zip"
        with (nullcontext() if refs is not None else zipfile.ZipFile(path, "x", zipfile.ZIP_DEFLATED, compresslevel=4)) as archive:
            for identity, case in cases[offset:offset+16]:
                with TemporaryDirectory(dir=args.scratch) as folder:
                    work = Path(folder) / "case"
                    receipt = run_one(binary, work, identity, case, "observed", app_args(case))
                    name = case["case"]
                    if archive is not None:
                        for item in sorted(work.iterdir()):
                            archive.write(item, f"{name}/{item.name}")
                        statuses[name] = receipt["status"]
                    else:
                        ref = refs[name]
                        signature = {key: receipt["artifacts"].get(key) for key in EXACT}
                        exact = (receipt["status"], receipt["exit_code"], signature) == (
                            ref["status"], ref["exit_code"], {key: ref["artifacts"].get(key) for key in EXACT})
                        statuses[name] = dict(exact=exact, status=receipt["status"], exit_code=receipt["exit_code"],
                                              elapsed_ms=receipt["elapsed_ms"], signature=signature)
                    print(identity, receipt["status"], name, flush=True)
        if refs is None:
            archives[path.name] = sha(path)
    write_json(args.out / "completed.json", dict(ended_ns=time.time_ns(), attempts=len(statuses), statuses=statuses,
               archives=archives, reference_archive_index_sha256=sha(reference_root / "completed.json") if reference_root else None))
    return int(any(not r["exact"] for r in statuses.values()) if refs is not None else "ENGINEERING_FAILURE" in statuses.values())


if __name__ == "__main__":
    raise SystemExit(main())
