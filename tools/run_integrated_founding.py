"""Run and archive the frozen protected founding environments."""

import argparse
from collections import Counter
import json
from pathlib import Path
import platform
import subprocess
from tempfile import TemporaryDirectory
import time
import zipfile

from run_s6_4_wp6b import ROOT, frozen_cases, git, run_one, sha, write_json
from run_s6_4_wp6b_r1 import NOMINAL


PROTOCOL = ROOT / "research/s6_4_integrated_founding/FROZEN_INTEGRATION_PROTOCOL.md"
FREEZE = "1e57c9a"
DAY = 86_400_000
STOCKS = {
    "balanced": (6000, 3000, 18000), "limited": (752, 376, 2252),
    "water": (0, 0, 18000), "carbohydrate": (6000, 0, 0),
    "no-protein": (6000, 0, 18000), "blocked": (6000, 3000, 18000), "absent": (0, 0, 0),
}
PROFILES = {0, 10, 21, 31}
MODELS = {
    "r2": (), "provision": ("1", "1000000"), "sugar": ("0", "8000000"), "both": ("1", "8000000"),
    "low-yield": ("1", "4000000"), "high-yield": ("1", "12000000"),
    "nest": ("1", "8000000", "1"), "eggs": ("1", "8000000", "2"), "diet": ("1", "8000000", "3"),
    "diet-low": ("1", "4000000", "3"), "diet-high": ("1", "12000000", "3"),
}
PROVISIONING_FREEZE = "bec5a01"
PROVISIONING_PROTOCOL = PROTOCOL.with_name("PROVISIONING_AND_YIELD_FREEZE.md")
DIETARY_FREEZE = "b1a0d96"
DIETARY_PROTOCOL = PROTOCOL.with_name("DIETARY_FOUNDRESS_FREEZE.md")
SENSITIVITIES = ("low-yield","high-yield","diet-low","diet-high")


def environments(matrix):
    if matrix == "closed":
        return [(identity,case) for identity,case in frozen_cases() if case["group"] in ("primary","check")]
    cases = []
    for identity, original in frozen_cases():
        if matrix == "nominal":
            selected = original["group"] == "micro" and original["arm"] == "nominal"
        else:
            selected = original["group"] == "primary" and original["care_enabled"] and original["profile_index"] in PROFILES
        if not selected:
            continue
        # Paired treatments have the same world, parameter inputs and RNG keys.
        for arm, stock in STOCKS.items():
            if matrix == "factorial" and arm not in ("balanced", "limited", "blocked", "absent"):
                continue
            case = dict(original, case=f"{original['case']}-{arm}", reference_case=original["case"],
                        arm=f"integrated-{arm}", group=matrix, horizon_ms=150*DAY,
                        external_food_ug=sum(stock), external_food_components_ug=[*stock, 0])
            cases.append((100_000 + identity, case))
    if len(cases) != {"nominal": 84, "factorial": 192}[matrix]:
        raise ValueError(f"wrong frozen case count for {matrix}")
    return cases


def collect(args):
    original = subprocess.check_output(["git", "show", f"{FREEZE}:{PROTOCOL.relative_to(ROOT).as_posix()}"], cwd=ROOT)
    if original != PROTOCOL.read_bytes() or git("status", "--porcelain", "--", "cpp", "tools"):
        raise ValueError("commit the measured source and retain the prospective protocol")
    if args.model != "r2":
        original = subprocess.check_output(["git", "show", f"{PROVISIONING_FREEZE}:{PROVISIONING_PROTOCOL.relative_to(ROOT).as_posix()}"], cwd=ROOT)
        if original != PROVISIONING_PROTOCOL.read_bytes():
            raise ValueError("provisioning ablations differ from their prospective freeze")
    if len(MODELS[args.model])>=3:
        original = subprocess.check_output(["git", "show", f"{DIETARY_FREEZE}:{DIETARY_PROTOCOL.relative_to(ROOT).as_posix()}"], cwd=ROOT)
        if original != DIETARY_PROTOCOL.read_bytes():
            raise ValueError("dietary ablations differ from their prospective freeze")
    selected = environments(args.matrix)
    if args.model in SENSITIVITIES:
        if args.matrix != "nominal":
            raise ValueError("yield sensitivities use the twelve nominal balanced worlds")
        selected = [(identity, case) for identity, case in selected if case["arm"] == "integrated-balanced"]
    if args.case:
        selected = [(identity, case) for identity, case in selected if case["case"] in args.case]
        if len(selected) != len(set(args.case)):
            raise ValueError("unknown frozen case selection")
    args.out.mkdir(parents=True)
    args.scratch.mkdir(parents=True, exist_ok=True)
    binary = args.binary.resolve(strict=True)
    arguments = (*map(str, NOMINAL), "0", "3", *MODELS[args.model])
    write_json(args.out / "run.json", dict(
        source=git("rev-parse", "HEAD"), cpp_tree=git("rev-parse", "HEAD:cpp"), frozen=FREEZE,
        protocol_sha256=sha(PROTOCOL), binary=binary.name, binary_sha256=sha(binary), mode=args.mode,
        arguments=list(arguments), matrix=args.matrix, model=args.model, selected_subset=bool(args.case), runner_sha256=sha(Path(__file__)),
        candidate_protocol_sha256=sha(DIETARY_PROTOCOL) if len(MODELS[args.model])>=3 else
            sha(PROVISIONING_PROTOCOL) if args.model != "r2" else None,
        configuration="Release", compiler=subprocess.check_output([args.compiler.resolve(), "--version"], text=True).splitlines(),
        platform=platform.platform(), python=platform.python_version(), started_ns=time.time_ns(),
        cases=[case["case"] for _, case in selected]))
    statuses, archives = {}, {}
    for offset in range(0, len(selected), 12):
        path = args.out / f"raw-{offset//12:03}.zip"
        with zipfile.ZipFile(path, "x", zipfile.ZIP_DEFLATED, compresslevel=4) as archive:
            for identity, case in selected[offset:offset+12]:
                with TemporaryDirectory(dir=args.scratch) as location:
                    work = Path(location).resolve() / "case"
                    receipt = run_one(binary, work, identity, case, args.mode, arguments)
                    name = case["case"]
                    for item in sorted(work.iterdir()):
                        archive.write(item, f"{name}/{item.name}")
                    statuses[name] = receipt["status"]
                    print(name, receipt["status"], receipt["elapsed_ms"], flush=True)
        archives[path.name] = sha(path)
    write_json(args.out / "completed.json", dict(ended_ns=time.time_ns(), attempts=len(statuses),
                                               statuses=statuses, archives=archives))
    print(json.dumps(Counter(statuses.values())), flush=True)
    return int("ENGINEERING_FAILURE" in statuses.values())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("binary", "compiler", "out", "scratch"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--matrix", choices=("nominal", "factorial", "closed"), required=True)
    parser.add_argument("--model", choices=MODELS, default="r2")
    parser.add_argument("--mode", choices=("observed", "durable", "unobserved"), default="observed")
    parser.add_argument("--case", action="append", default=[])
    raise SystemExit(collect(parser.parse_args()))
