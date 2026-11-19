"""Reproduce the single-nest controls without writing a full event archive."""

from argparse import ArgumentParser
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from time import perf_counter

from op0 import DAY
from op0.codec import checkpoint
from op0.live import NativeCore, core_path
from tools.compare_m0_worker_rhythm import facts


CASES = tuple((model, seed, "finite") for model in ("reference", "anatomical") for seed in (1, 2, 3))
CASES += (("reference", 2, "absent"), ("anatomical", 2, "absent"))
CUTS = (0, 10, 30, 60, 90, 120, 150)
WATCH = {"AntBorn", "BroodMoved", "FoundingRation", "AntDied", "SoilExcavated", "SoilDropped",
         "FoodCollected", "FoodDelivered", "FoundressNestMeal", "RecruitmentActivated"}
CARE = {"Pick up brood", "Transport brood", "Place brood", "Clean brood", "Inspect brood", "Feed brood"}
SCAN_DAYS = 60
SCAN_LIMIT = 131_072


def summarize(core, model, seed, supply):
    command = "NEW_ANATOMICAL_NEST" if model == "anatomical" else "NEW_SINGLE_NEST"
    identity = 9100 + seed + 100 * (model == "anatomical") + 10 * (supply == "absent")
    request = f"{command} {identity} {seed} 250 80 plugged 1955 reachable {supply}"
    initial = core.call(request)
    init = checkpoint(initial)
    result = dict(request=request, world_id=init["world"], physics=init["physics"], settings=init["flags"],
                  seed_geometry=init["geometry"], sources_at_start=list(init["sources"].values()),
                  initial_frame_sha256=sha256(initial).hexdigest(), cuts=[])
    scan_end = None
    for day in CUTS:
        started = perf_counter()
        frame = initial if day == 0 else core.call(f"ADVANCE {day*DAY}")
        elapsed = perf_counter()-started
        cut = checkpoint(frame)
        queen = cut["ants"][2]
        ants = cut["ants"].values()
        ledger = core.call("R0_BALANCES 2").decode("ascii").split()
        labels = ("body_energy_nj", "body_water_ug", "crop_carb_ug", "crop_protein_ug", "crop_water_ug",
                  "lipid_ug", "mobile_protein_ug", "unreleased_carbs_ug", "unreleased_protein_ug",
                  "unreleased_water_ug", "resident_event_bytes", "packed_event_bytes")
        result["cuts"].append(dict(day=day, cursor=cut["cursor"], frame_sha256=sha256(frame).hexdigest(),
                                   advance_seconds=round(elapsed, 6), stages=dict(Counter(str(a["stage"]) for a in ants)),
                                   workers=sum(a["stage"] == 3 and a["caste"] == 0 for a in ants),
                                   queen=queen, balances=dict(zip(labels, map(int, ledger), strict=True)),
                                   soil_ledger_q3=cut["soil"], soil_piles=cut["soil_piles"][:8],
                                   edit_count=len(cut["edits"]), stock_ug=cut["stored"]))
        if day == SCAN_DAYS:
            scan_end = cut["cursor"]
    result["native_memory_bytes"] = list(map(int, core.call("MEMORY").split()))
    core.call("CHECK_LEDGERS")
    result["ledgers"] = "PASS"
    counts, first, youth = Counter(), {}, {}
    # The day-60 cut bounds this observation window before any later sampling.
    # The receipt reports where it ended. All day-150 states are actual cuts.
    observed_tip = min(scan_end, SCAN_LIMIT)
    for f in facts(core, observed_tip):
        if f.id > observed_tip:
            break
        e = f.packet()
        kind = e["kind"]
        action = e.get("action")
        if kind == "StageChanged":
            mark = e["stage"]
        elif action and action["act"] in CARE and action["phase"] in ("Completed", "Interrupted"):
            mark = action["act"] + " " + e["outcome"]
        elif kind in WATCH:
            mark = kind
        else:
            continue
        counts[mark] += 1
        first.setdefault(mark, e)
        if kind == "AntBorn" and len(youth) < 4:
            youth[e["actor"]] = []
        target = e["related"] if kind == "FoundingRation" else e["actor"]
        if target in youth and (kind in ("AntBorn", "StageChanged", "FoundingRation", "AntDied")):
            youth[target].append(e)
    result.update(scan_through_id=observed_tip, scan_day_ceiling=SCAN_DAYS,
                  scan_counts=dict(counts), first_evidence=first, first_four_brood=youth)
    return result


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, default=core_path())
    parser.add_argument("--scratch", type=Path, default=Path("out"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--model", choices=("reference", "anatomical"), help="Run only the selected physics version")
    args = parser.parse_args()
    args.scratch.mkdir(parents=True, exist_ok=True)
    binary = args.core.resolve()
    result = dict(assay="single-nest-physical-assay-v1", binary_sha256=sha256(binary.read_bytes()).hexdigest(), cases=[])
    with TemporaryDirectory(dir=args.scratch, prefix="single-nest-assay-") as temporary:
        for model, seed, supply in CASES:
            if args.model and model != args.model:
                continue
            print(f"{model} seed {seed}, {supply}", file=sys.stderr, flush=True)
            with closing(NativeCore(binary, Path(temporary))) as core:
                result["cases"].append(summarize(core, model, seed, supply))
    report = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8", newline="\n")
    else:
        print(report, end="")


if __name__ == "__main__":
    main()
