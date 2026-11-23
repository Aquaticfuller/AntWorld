"""Repeat one measured worker-to-founder transaction from a bounded continuation."""

import argparse
from contextlib import closing
from hashlib import sha256
import json
from math import dist
from pathlib import Path
from tempfile import TemporaryDirectory

from op0 import DAY
from op0.codec import ACTS, CASTES, KINDS, PHASES, checkpoint, require
from op0.live import NativeCore, ROOT, core_path, live_bodies
from tools.compare_m0_worker_rhythm import facts


def verify(binary, trial, scratch=None):
    scratch = scratch or ROOT / "out"
    scratch.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(dir=scratch) as temp, closing(NativeCore(binary, temp)) as core:
        initial = core.call(trial["command"])
        require(sha256(initial).hexdigest() == trial["initial_sha256"], "Different world")
        queen, = [i for i,a in checkpoint(initial)["ants"].items() if CASTES[a["caste"]]=="Queen"]
        sequence = trial.get("step_then_meal", {}).get("queen_to_worker")
        uptake = trial["subsequent_uptake"].get(str(queen))
        candidates = [flow["first_sugar"] for key,flow in trial["mouths"].items()
                      if key.endswith("/Queen") and "first_sugar" in flow]
        require(sequence or uptake or candidates,"No recorded positive sugar meal to replay")
        event_id, time = (sequence["meal"] if sequence else (uptake[0] if uptake else min(candidates)))[:2]
        steps = {}
        for direction,pair in trial.get("step_then_meal",{}).items():
            if pair["meal"][0]!=event_id:
                continue
            start, ended, target, position = pair["step"]
            bout, selected, origin = start
            require(origin!=position and selected[1]<ended[1]<=time, "Invalid approach interval")
            for stamp,phase,point in ((selected,"Selected",origin),(ended,"Completed",position)):
                steps[stamp[0]]=(stamp[1],stamp[2],target,bout,phase,point,direction)
        cuts=set(range(4*DAY,time-1,4*DAY))
        for stamp in steps.values():
            cuts.update((stamp[0]-1,stamp[0]))
        cursor=checkpoint(initial)["cursor"]
        witnessed={}
        for t in sorted(cuts):
            frame=checkpoint(core.call(f"ADVANCE {t}"))
            if any(s[0]==t for s in steps.values()):
                for f in facts(core,frame["cursor"],cursor):
                    if f.id not in steps:
                        continue
                    at,actor,target,bout,phase,point,direction=steps[f.id]
                    require(f.observation and f.actor==actor and f.time==at and
                            PHASES[f.observation[0]]==phase and ACTS[f.observation[1]]=="Approach a nestmate" and
                            f.observation[2:4]==(target,bout) and f.outcome==0 and list(f.position)==point,
                            "Registered partner/position does not match the committed approach")
                    witnessed[f.id]=direction
            cursor=frame["cursor"]
            if int(core.call("HISTORY_STORAGE").split()[2]) >= 32*1024**2:
                core.call("COMPACT_HISTORY")
        require(witnessed.keys()==steps.keys(),"Missing committed approach")
        before_raw = core.call(f"ADVANCE {time-1}")
        before = checkpoint(before_raw)
        bodies = live_bodies(core.call("BODY_STATES"), before)
        access = core.call("MEAL_ACCESS")
        require(core.call("FRAME")==before_raw, "Observation changed the authoritative state")
        slot = "1"*32
        core.call(f"SAVE_SNAPSHOT {slot}")
        size = (Path(temp) / (slot+".awstate")).stat().st_size
        after_raw = core.call(f"ADVANCE {time}")
        after = checkpoint(after_raw)
        batch = list(facts(core, after["cursor"], before["cursor"]))
        meal, = [f for f in batch if f.id==event_id and KINDS[f.kind]=="NutritionTransferred"]
        require(meal.mass[0]>0, "No positive sugar at the registered meal")
        donor, receiver = meal.actor, meal.payload
        require(receiver==queen,"Selected transaction has a different receiver")
        debit = [x-y for x,y in zip(before["ants"][donor]["crop_ug"],after["ants"][donor]["crop_ug"])]
        credit = [y-x for x,y in zip(before["ants"][receiver]["crop_ug"],after["ants"][receiver]["crop_ug"])]
        require(debit==credit==list(meal.mass), "The actual crop changes do not match the meal")
        gap = dist(bodies[str(donor)]["mouth_m"], bodies[str(receiver)]["mouth_m"])
        require(gap<=0.000650001, "Mouths outside contact")
        projected = core.call(f'MEAL_EVENTS {before["cursor"]} {after["cursor"]-before["cursor"]}')
        require(core.call(f'LOAD_SNAPSHOT {slot} {before["world"]}')==before_raw, "Snapshot changed before contact")
        require(core.call("MEAL_ACCESS")==access and core.call(f"ADVANCE {time}")==after_raw and
                core.call(f'MEAL_EVENTS {before["cursor"]} {after["cursor"]-before["cursor"]}')==projected,
                "Continuation diverged at the oral transaction")
        require(core.call("CHECK_LEDGERS")==b"", "Ledger disagreement")
        return dict(seed=trial["seed"],physics=trial["physics"],event=event_id,time_ms=time,
                    donor=donor,receiver=receiver,mouth_gap_mm=1000*gap,debit_ug=debit,credit_ug=credit,
                    approach_events=witnessed, before_sha256=sha256(before_raw).hexdigest(),after_sha256=sha256(after_raw).hexdigest(),
                    snapshot_bytes=size)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt",type=Path)
    parser.add_argument("--physics",type=int,help="Select a world in a JSONL panel")
    parser.add_argument("--seed",type=int)
    parser.add_argument("--supply",choices=("nearby","absent"),default="nearby")
    parser.add_argument("--core",type=Path,default=core_path())
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.receipt.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    matches = [r for r in rows if (args.physics is None or r["physics"]==args.physics) and
               (args.seed is None or r["seed"]==args.seed) and r["supply"]==args.supply]
    require(len(matches)==1,"Select one world with --physics, --seed and --supply")
    print(json.dumps(verify(args.core.resolve(), matches[0])))
