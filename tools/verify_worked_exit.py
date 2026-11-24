"""Compare oral planners on an unchanged reference cut and replay two old excavators."""

import argparse
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from op0 import DAY
from op0.codec import KINDS, checkpoint, require
from op0.live import NativeCore, ROOT, core_path
from tools.compare_m0_worker_rhythm import facts
from tools.inspect_first_meal_window import inspect


def verify_private_trip(binary, trial, scratch):
    """Validate a real worker's extraction, first intake and exact save continuation."""
    collection = trial["first"]["FoodCollected"]
    actor, source = collection[2:4]
    ingest = trial["first"]["CargoIngested"]
    require(ingest[2:4] == [actor,source] and ingest[1] >= collection[1], "Wrong consumer or source")
    with TemporaryDirectory(dir=scratch) as temp, closing(NativeCore(binary,temp)) as core:
        raw = core.call(trial["command"])
        before = core.call(f"ADVANCE {collection[1]-1}")
        cut = checkpoint(before)
        soil = [f for f in facts(core,cut["cursor"],0) if f.actor==actor and KINDS[f.kind]=="SoilDropped"]
        start = [f for f in facts(core,cut["cursor"],soil[-1].id if soil else 0)
                 if f.actor==actor and KINDS[f.kind]=="ForagingStarted"]
        require(soil and start and soil[0].time <= start[-1].time, "Private work/departure not witnessed")
        require(not any(cut["ants"][actor]["carried_ug"]), "Worker was loaded before its first collection")
        slot="3"*32
        core.call(f"SAVE {slot}")
        core.call(f"SAVE_SNAPSHOT {slot}")
        after = core.call(f"ADVANCE {ingest[1]}")
        frame = checkpoint(after)
        receipts = [f for f in facts(core,frame["cursor"],cut["cursor"]) if f.actor==actor]
        pickup, = [f for f in receipts if f.id==collection[0] and KINDS[f.kind]=="FoodCollected"]
        sip, = [f for f in receipts if f.id==ingest[0] and KINDS[f.kind]=="CargoIngested"]
        require(pickup.mass[0]>0 and pickup.mass[2]>0 and not pickup.mass[1] and not pickup.mass[3]
                and sip.mass[0]>0 and sip.resource==pickup.resource, "Unsupported private liquid payment")
        require(core.call("CHECK_LEDGERS")==b"", "Unbalanced payment")
        for cmd in ("LOAD","LOAD_SNAPSHOT"):
            require(core.call(f'{cmd} {slot} {cut["world"]}')==before and
                    core.call(f"ADVANCE {ingest[1]}")==after, "Trip continuation changed")
        return dict(seed=trial["seed"],worker=actor,source=source,soil_fact=soil[0].id,
                    departure=start[-1].id,collection=collection,intake=ingest,
                    before_sha256=sha256(before).hexdigest(),after_sha256=sha256(after).hexdigest())


def terminal_probe(core, trial, expected):
    raw = core.call(trial["command"])
    require(sha256(raw).hexdigest() == trial["initial_sha256"], "Reference input changed")
    time = trial["queen_death"][1] - 1
    for t in range(4 * DAY, time, 4 * DAY):
        core.call(f"ADVANCE {t}")
        core.call("COMPACT_HISTORY")
    cut = core.call(f"ADVANCE {time}")
    require(sha256(cut).hexdigest() == expected["predeath_sha256"], "Terminal cut changed")
    def pairs(command):
        return [list(map(int, line.split())) for line in core.call(command).splitlines()]
    original = pairs("ORAL_ACCESS")
    candidate = pairs("ORAL_ALIGNMENT_PROBE")
    require(cut == core.call("FRAME"), "Reading a counterfactual changed the world")
    require([r[:3]+r[5:] for r in original] == [r[:3]+r[5:] for r in candidate],
            "A geometry probe changed visibility, contact or payable carbohydrate")
    for actor in (8,21):
        before, = [r for r in original if r[0] == actor]
        after, = [r for r in candidate if r[0] == actor]
        require(before[1:5] == [1,0,0,0] and min(before[5:]) > 0 and after[3:5] == [1,1],
                "The reference terminal donor no longer diagnoses bilateral access")
    return dict(sha256=expected["predeath_sha256"], time_ms=time, fields=[
        "donor", "visible", "in_contact", "founder_has_step", "donor_has_step",
        "offered_carbs_ug", "requested_carbs_ug"], original=original, candidate=candidate)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, default=core_path())
    parser.add_argument("--panel", type=Path, help="Check a complete candidate panel against the frozen reference")
    args = parser.parse_args()
    repo = ROOT / "research/single_nest"
    cuts = {r["purpose"]:r["record"] for r in map(json.loads, (repo/"FIRST_MEAL_LOCAL_CUTS.jsonl").read_text().splitlines())}
    trials = list(map(json.loads, (repo/"FIRST_MEAL_TRIALS.jsonl").read_text().splitlines()))
    if args.panel:
        from tools.summarize_first_meals import outcome
        from tools.verify_first_meal import verify_inputs
        reference = [x for x in trials if x["physics"] == 62]
        candidate = list(map(json.loads,args.panel.read_text(encoding="utf-8-sig").splitlines()))
        expected = {(s,"nearby") for s in (1,2,3,17,29)} | {(2,"absent")}
        for rows,physics,model in ((reference,62,"local-crop-return"),(candidate,63,"worked-exit")):
            require(len(rows)==len(expected) and {(r["seed"],r["supply"]) for r in rows}==expected,
                    "Missing or duplicated paired case")
            for r in rows:
                parts = r["command"].split()
                require(r["physics"]==physics and parts[2:]==[str(r["seed"]),"250","80","plugged","1955",
                    "reachable",r["supply"],"sheltered","mineral",model,"wet-wick"], "Different treatment or supply")
                require(r["census"][-1]["day"]==730,"Interrupted run")
                summary = outcome(r)
                if r["supply"]=="absent":
                    require(summary["first_sugar_day"] is None,"Absent source produced sugar")
                print(json.dumps(summary),flush=True)
        print(json.dumps(verify_inputs(args.core.resolve(), reference+candidate)),flush=True)
    trial = next(r for r in trials if r["physics"] == 62 and r["seed"] == 2 and r["supply"] == "nearby")
    with TemporaryDirectory(dir=ROOT/"out") as temp, closing(NativeCore(args.core.resolve(), temp)) as core:
        print(json.dumps(terminal_probe(core,trial,cuts["candidate-founder-last-ms"])),flush=True)
        for seed in (17,29):
            result = inspect(core,"local-crop-return",seed,46,48,False)
            old = cuts[f"post-dig-pre-forage-{seed}"]
            require(json.loads(json.dumps(result)) == old,
                    "Old post-dig world no longer reproduces")
            print(json.dumps(dict(seed=seed, cuts=[c["frame_sha256"] for c in result["cuts"]])),flush=True)


if __name__ == "__main__":
    main()
