"""Inspect real adult positions, crop ownership and action outcomes in a bounded window."""

import argparse
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
from math import dist
from pathlib import Path

from op0 import DAY
from op0.codec import ACTS, CASTES, DEATHS, KINDS, OUTCOMES, PHASES, PROGRAMS, STAGES, checkpoint, require
from op0.live import NativeCore, ROOT, core_path
from tools.compare_m0_worker_rhythm import facts
from tools.measure_first_meal import TREATMENTS, WORLD_BASES
from tools.measure_social_crop import observed_adults


def founder_death(core, trial, lookback_hours=0):
    birth = core.call(trial["command"])
    require(sha256(birth).hexdigest()==trial["initial_sha256"], "Trial identity mismatch")
    event, time, reason = trial["queen_death"]
    start = max(0, time - 1 - lookback_hours * (DAY // 24))
    for t in range(4*DAY,start,4*DAY):
        core.call(f"ADVANCE {t}")
        core.call("COMPACT_HISTORY")
    preceding = []
    if lookback_hours:
        for t in range(start, time, DAY // 48):
            state = checkpoint(core.call(f"ADVANCE {t}"), forager_routes=True)
            preceding.append(dict(time_ms=t, cursor=state["cursor"], routes=state["forager_routes"],
                                  access=core.call("MEAL_ACCESS").decode().splitlines(),
                                  oral=core.call("ORAL_ACCESS").decode().splitlines()))
    raw = core.call(f"ADVANCE {time-1}")
    frame = checkpoint(raw)
    founder, = [i for i,a in frame["ants"].items() if CASTES[a["caste"]]=="Queen"]
    adults = observed_adults(core,frame)
    for i,row in adults.items():
        ant = frame["ants"][i]
        row.update(program=PROGRAMS[ant["program"]], external_load_ug=ant["carried_ug"],
                   physiology_cut=list(map(int,core.call(f"FOUNDING_BALANCE {i}").split())),
                   gap_to_founder_mm=1000*dist(row["mouth_m"],adults[founder]["mouth_m"]))
    access = core.call("MEAL_ACCESS").decode().splitlines()
    pair_fields = ("worker","visible","touching","queen_has_step","worker_has_step","offered_carbs_ug","requested_carbs_ug")
    pairs = [dict(zip(pair_fields,map(int,line.split()),strict=True))
             for line in core.call("ORAL_ACCESS").decode().splitlines()]
    require(core.call("FRAME")==raw,"Read changed world")
    end = checkpoint(core.call(f"ADVANCE {time}"))
    death, = [f for f in facts(core,end["cursor"],frame["cursor"]) if f.id==event]
    require(death.actor==founder and KINDS[death.kind]=="AntDied" and DEATHS[death.payload]==reason,
            "Founder death does not reproduce")
    payments, uptake = [], []
    if preceding:
        for f in facts(core, end["cursor"], preceding[0]["cursor"]):
            kind = KINDS[f.kind]
            if kind == "NutritionTransferred" and f.payload == founder and any(f.mass):
                payments.append(dict(event=f.id,time_ms=f.time,donor=f.actor,dose_ug=f.mass))
            if f.actor == founder and kind in ("PhysiologyUpdated", "FoundingBoundaryUptake") and any(f.mass):
                uptake.append(dict(event=f.id,time_ms=f.time,kind=kind,absorbed_ug=f.mass))
    return dict(physics=trial["physics"],seed=trial["seed"],supply=trial["supply"],
                predeath_sha256=sha256(raw).hexdigest(),death=[event,time,reason],founder=founder,adults=adults,
                pantry_ug=next(iter(frame["colonies"].values()))["stock_ug"],
                sources=frame["sources"],access=access,oral_pairs=pairs,
                **({"half_hour_cuts":preceding, "founder_payments":payments, "founder_uptake":uptake} if lookback_hours else {}))


def inspect(core, model, seed, start, end, wide):
    identity = WORLD_BASES["nearby"] + seed + TREATMENTS.index(model)*2**34 + 2**39
    command = f"NEW_PROVISIONED_NEST {identity} {seed} 250 80 plugged 1955 reachable nearby sheltered mineral {model} wet-wick"
    core.call(command)
    for day in range(4, start, 4):
        core.call(f"ADVANCE {day*DAY}")
        core.call("COMPACT_HISTORY")
    actions, decisions, first = Counter(), Counter(), {}
    partner_actions={}
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
                    if ACTS[act]=="Approach a nestmate":
                        pair=f"{f.actor}/{f.observation[2]}/{PHASES[phase]}/{OUTCOMES[f.outcome]}"
                        record=partner_actions.setdefault(pair,{"count":0,"first":[f.id,f.time]})
                        record["count"]+=1
                        record["last"]=[f.id,f.time]
                if KINDS[f.kind]=="ForagingDecision":
                    decisions[f"{f.actor}/{f.mode}/{f.reason}"]+=1
        previous=frame["cursor"]
    return dict(command=command,physics=frame["physics"],seed=seed,wide=wide,cuts=cuts,
                actions=actions,first=first,partner_actions=partner_actions,foraging_modes_reasons=decisions)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core",type=Path,default=core_path())
    modes=parser.add_subparsers(dest="mode",required=True)
    window=modes.add_parser("window")
    window.add_argument("model",choices=TREATMENTS)
    window.add_argument("seed",type=int)
    window.add_argument("start",type=int)
    window.add_argument("end",type=int)
    window.add_argument("--wide",action="store_true")
    death=modes.add_parser("death")
    death.add_argument("receipt",type=Path)
    death.add_argument("--lookback-hours",type=int,choices=range(1,25),default=0,metavar="1..24")
    args=parser.parse_args()
    if args.mode=="window" and not 0<=args.start<args.end<=args.start+4:
        parser.error("Choose an observation window of at most four days")
    with closing(NativeCore(args.core.resolve(), ROOT/"out")) as core:
        if args.mode=="window":
            result=inspect(core,args.model,args.seed,args.start,args.end,args.wide)
        else:
            result=founder_death(core,json.loads(args.receipt.read_text(encoding="utf-8-sig")),args.lookback_hours)
    print(json.dumps(result,separators=(",",":")))
