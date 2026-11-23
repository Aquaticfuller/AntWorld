"""Inspect real adult positions, crop ownership and action outcomes in a bounded window."""

import argparse
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json

from op0 import DAY
from op0.codec import ACTS, KINDS, OUTCOMES, PHASES, PROGRAMS, STAGES, checkpoint
from op0.live import NativeCore, ROOT, core_path
from tools.compare_m0_worker_rhythm import facts
from tools.measure_first_meal import TREATMENTS, WORLD_BASES
from tools.measure_social_crop import observed_adults


def inspect(core, model, seed, start, end, wide):
    identity = WORLD_BASES["nearby"] + seed + TREATMENTS.index(model)*2**34 + 2**39
    command = f"NEW_PROVISIONED_NEST {identity} {seed} 250 80 plugged 1955 reachable nearby sheltered mineral {model} wet-wick"
    core.call(command)
    for day in range(4, start, 4):
        core.call(f"ADVANCE {day*DAY}")
        core.call("COMPACT_HISTORY")
    actions, decisions, first = Counter(), Counter(), {}
    cuts = []
    previous = None
    for day in (start,end):
        raw = core.call(f"ADVANCE {day*DAY}")
        frame = checkpoint(raw)
        rows = observed_adults(core,frame)
        for actor,r in rows.items():
            ant = frame["ants"][actor]
            r.update(program=PROGRAMS[ant["program"]],carried_ug=ant["carried_ug"],
                     physiology_cut=core.call(f"FOUNDING_BALANCE {actor}").decode().split())
        access = core.call("MEAL_ACCESS_WIDE" if wide else "MEAL_ACCESS").decode().splitlines()
        cuts.append(dict(day=day,frame_sha256=sha256(raw).hexdigest(),adults=rows,access=access,
                         pantry_ug=next(iter(frame["colonies"].values()))["stock_ug"]))
        if previous is not None:
            for f in facts(core,frame["cursor"],previous):
                if STAGES[f.stage]!="Adult":
                    continue
                if f.observation:
                    phase,act = f.observation[:2]
                    key=f"{f.actor}/{ACTS[act]}/{PHASES[phase]}/{OUTCOMES[f.outcome]}"
                    actions[key]+=1
                    first.setdefault(key,[f.id,f.time,list(f.position)])
                if KINDS[f.kind]=="ForagingDecision":
                    decisions[f"{f.actor}/{f.mode}/{f.reason}"]+=1
        previous=frame["cursor"]
    return dict(command=command,physics=frame["physics"],seed=seed,wide=wide,cuts=cuts,
                actions=actions,first=first,foraging_modes_reasons=decisions)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model",choices=TREATMENTS)
    parser.add_argument("seed",type=int)
    parser.add_argument("start",type=int)
    parser.add_argument("end",type=int)
    parser.add_argument("--wide",action="store_true")
    args=parser.parse_args()
    if not 0<=args.start<args.end<=args.start+4:
        parser.error("Choose an observation window of at most four days")
    with closing(NativeCore(core_path(), ROOT/"out")) as core:
        result=inspect(core,args.model,args.seed,args.start,args.end,args.wide)
    print(json.dumps(result,separators=(",",":")))
