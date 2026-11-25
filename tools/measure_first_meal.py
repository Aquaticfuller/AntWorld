"""Follow real first trips, meetings, funded meals and worker survival in a bounded native run."""

import argparse
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import sys

from op0 import DAY
from op0.codec import CASTES, DEATHS, KINDS, PHASES, STAGES, U32, checkpoint, decode_fact, require
from op0.live import NativeCore, ROOT, core_path
from tools.measure_single_nest_lifecycle import COMPACT_BYTES, TREATMENTS, WORLD_BASES, census


def run(core, seed, model, supply, days, progress=False, feeding_continuity=False, trace_flux=False):
    identity = WORLD_BASES[supply] + seed + TREATMENTS.index(model) * 2**34 + 2**39
    command = f"NEW_PROVISIONED_NEST {identity} {seed} 250 80 plugged 1955 reachable {supply} sheltered mineral {model} wet-wick"
    raw = core.call(command)
    frame = checkpoint(raw)
    result = dict(command=command, physics=frame["physics"], seed=seed, supply=supply,
                  initial_sha256=sha256(raw).hexdigest(), census=[])
    queen, = [i for i, a in frame["ants"].items() if CASTES[a["caste"]] == "Queen"]
    lives, first, mouths, paired_uptake, pending, approaches = {}, {}, {}, {}, {}, {}
    encounters = Counter()
    witnesses = {}
    last_contact_step = {}
    meal_sequences = {}
    founder_days = {}
    flux = {}
    previous_cut = None
    previous = 0
    checkpoints = {d for d in (30,45,60,73,90,150,365,730,days) if d <= days}
    for day in sorted(checkpoints | set(range(4, days, 4))):
        try:
            raw = core.call(f"ADVANCE {day * DAY}")
        except ValueError as error:
            cut = checkpoint(core.call("FRAME"))
            raise RuntimeError(f"{model}/{seed}/{supply}: last committed time {cut['time_ms']} ms, "
                               f"event {cut['cursor']}, advancing to day {day}: {error}") from error
        frame = checkpoint(raw)
        if previous_cut and "last_living_founder_cut" not in result and not census(frame)["queen_alive"]:
            result["last_living_founder_cut"] = previous_cut
        if census(frame)["queen_alive"]:
            previous_cut = {
                "day": day, "depot_ug": next(iter(frame["colonies"].values()))["stock_ug"],
                "adults": {i: [a["energy_nj"], a["hydration_ug"], a["crop_ug"], a["position_m"]]
                           for i, a in frame["ants"].items() if STAGES[a["stage"]]=="Adult"}
            }
        if day in checkpoints:
            result["census"].append(census(frame))
            if progress:
                print(day, frame["cursor"], result["census"][-1]["workers"],
                      result["census"][-1]["queen_alive"], file=sys.stderr, flush=True)
        while previous < frame["cursor"]:
            size = min(frame["cursor"] - previous, 8192)
            events = core.call(f"MEAL_EVENTS {previous} {size}")
            offset, last = 0, previous
            while offset < len(events):
                extent = U32.unpack_from(events, offset)[0]
                offset += U32.size
                _, f = decode_fact(events[offset:offset+extent])
                offset += extent
                require(last < f.id <= previous + size, "Sparse facts out of canonical order")
                last = f.id
                kind = KINDS[f.kind]
                stamp = [f.id, f.time, f.actor]
                if trace_flux and f.mass[0] and kind in (
                    "FoodCollected", "FoodDelivered", "CargoIngested", "FoundressNestMeal",
                    "NutritionTransferred", "PhysiologyUpdated", "FoundingBoundaryUptake",
                ):
                    recipient = f.payload if kind == "NutritionTransferred" else f.actor
                    key = f"{kind}/{f.actor}/{recipient}"
                    entry = flux.setdefault(key, dict(count=0, sugar_ug=0, before_founder_death_ug=0,
                                                      first=stamp[:2], last=stamp[:2]))
                    entry["count"] += 1
                    entry["sugar_ug"] += f.mass[0]
                    entry["last"] = stamp[:2]
                    if "queen_death" not in result:
                        entry["before_founder_death_ug"] += f.mass[0]
                if kind == "AntBorn":
                    lives[f.actor] = {"birth": stamp[:2]}
                if kind == "StageChanged":
                    stage = STAGES[f.stage]
                    lives[f.actor][stage] = stamp[:2]
                    first.setdefault(stage, stamp)
                if kind == "AntDied":
                    death = [f.id, f.time, DEATHS[f.payload]]
                    if f.actor == queen:
                        result["queen_death"] = death
                    else:
                        lives[f.actor]["death"] = death
                if kind in ("ForagingStarted", "SoilExcavated", "SoilDropped") or (kind=="Moved" and f.actor!=queen):
                    first.setdefault(kind if kind!="Moved" else "surface", stamp)
                if kind in ("FoodCollected", "FoodDelivered", "CargoIngested") and f.mass[0]:
                    first.setdefault(kind, [*stamp, f.resource, list(f.mass)])
                if kind == "BiologicalObservation":
                    phase, _, target, bout, *_ = f.observation
                    label = PHASES[phase]
                    if f.actor == queen or target == queen:
                        direction = "queen_to_worker" if f.actor == queen else "worker_to_queen"
                        encounters[f"{direction}/{label}"] += 1
                        if label == "Selected":
                            approaches[f.actor] = [bout, stamp, list(f.position)]
                        if label == "Completed":
                            start = approaches.pop(f.actor, None)
                            if start and start[0]==bout and f.outcome==0 and list(f.position)!=start[2]:
                                encounters[direction+"/moved"] += 1
                                step = [start, stamp, target, list(f.position)]
                                witnesses.setdefault(direction, step)
                                last_contact_step[(f.actor, target)] = step
                if kind == "NutritionTransferred" and sum(f.mass):
                    dst = f.payload
                    if dst == queen:
                        role = "Queen"
                    elif "Adult" not in lives[dst]:
                        role = "Larva"
                    else:
                        role = "Callow" if f.time-lives[dst]["Adult"][1] < 7*DAY else "OlderWorker"
                    key = f"{f.actor}/{dst}/{role}"
                    entry = mouths.setdefault(key, {"first":stamp[:2], "count":0, "mass_ug":[0]*4})
                    entry["last"], entry["count"] = stamp[:2], entry["count"]+1
                    for index, value in enumerate(f.mass):
                        entry["mass_ug"][index] += value
                    if feeding_continuity and f.mass[0] and dst == queen:
                        meal_day = f.time // DAY
                        bucket = founder_days.setdefault(meal_day, dict(first_ms=f.time, last_ms=f.time, count=0, sugar_ug=0, max_internal_gap_ms=0))
                        bucket["max_internal_gap_ms"] = max(bucket["max_internal_gap_ms"], f.time-bucket["last_ms"])
                        bucket["last_ms"] = f.time
                        bucket["count"] += 1
                        bucket["sugar_ug"] += f.mass[0]
                    if f.mass[0] and role=="Queen":
                        entry.setdefault("first_sugar",stamp[:2])
                        for pair, direction in (((queen,f.actor),"queen_to_worker"), ((f.actor,queen),"worker_to_queen")):
                            step = last_contact_step.get(pair)
                            if step and f.time-step[1][1]<=DAY//2:
                                meal_sequences.setdefault(direction, dict(step=step, meal=[*stamp,dst,list(f.mass)]))
                    if f.mass[0]:
                        pending.setdefault(dst, [*stamp, f.mass[0]])
                if kind in ("PhysiologyUpdated","FoundingBoundaryUptake") and f.mass[0] and f.actor in pending:
                    gift = pending.pop(f.actor)
                    paired_uptake.setdefault(f.actor, [gift, stamp, f.mass[0]])
            require(offset==len(events), "Bad projection extent")
            previous += size
        if int(core.call("HISTORY_STORAGE").split()[2]) >= COMPACT_BYTES:
            core.call("COMPACT_HISTORY")
            require(core.call("FRAME")==raw, "Compaction changed state")
    require(core.call("CHECK_LEDGERS")==b"", "Native food or soil ledger failure")
    born = min((l["birth"][1] for l in lives.values()), default=0)
    cohorts = {}
    for group in ("first", "later"):
        adults = [l for l in lives.values() if "Adult" in l and (l["birth"][1]<=born+DAY)==(group=="first")]
        cohorts[group] = [len(adults),sum("death" not in l for l in adults)]
    require(sum(x[1] for x in cohorts.values())==result["census"][-1]["workers"], "Individual census mismatch")
    result.update(first=first, lives=lives, mouths=mouths, subsequent_uptake=paired_uptake, encounters=encounters,
                  movements=witnesses, step_then_meal=meal_sequences, cohorts_emerged_alive=cohorts, final_sha256=sha256(raw).hexdigest(), facts=previous)
    if feeding_continuity:
        result["founder_feeding_by_day"] = founder_days
    if trace_flux:
        result["sugar_flux"] = flux
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=TREATMENTS, required=True)
    parser.add_argument("--core", type=Path, default=core_path())
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--supply", choices=("nearby","absent"), default="nearby")
    parser.add_argument("--days", type=int, choices=range(1,731), metavar="1..730", default=730)
    parser.add_argument("--feeding-continuity", action="store_true", help="Record positive sugar payments to the founder by day")
    parser.add_argument("--progress", action="store_true", help="Report milestone day, cursor, workers and founder survival on stderr")
    parser.add_argument("--trace-flux", action="store_true", help="Account for collected, transferred and absorbed sugar by actor")
    args = parser.parse_args()
    executable_hash = sha256(args.core.read_bytes()).hexdigest()
    with closing(NativeCore(args.core.resolve(), ROOT / "out")) as native:
        receipt = run(native,args.seed,args.model,args.supply,args.days,args.progress,args.feeding_continuity,args.trace_flux)
    receipt["executable_sha256"] = executable_hash
    print(json.dumps(receipt,separators=(",",":")))
