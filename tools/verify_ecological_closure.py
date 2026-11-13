"""Rebuild ecological mechanisms and negative controls from original bytes."""

import argparse
from collections import Counter, defaultdict
import csv
from hashlib import sha256
from itertools import groupby
import json
import math
from pathlib import Path
from statistics import median
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from analyze_integrated_founding import located_facts, observe_chain
from analyze_s6_4_wp6b import assess, check, facts, rows, RANGES
from run_integrated_founding import DAY
from run_s6_4_wp6b import input_bytes, sha, write_json
from s6_4_wp5_geometry import Grid
from verify_final_core_integration import check_identity, verify_midpoint


DELIVERED, COLLECTED, MOVED, DECISION, BEHAVIOR = 12, 5, 4, 11, 17
CUE, EXPOSED, ACTIVATED, ACTIVITY, WATER = range(54, 59)
ZERO = (0, 0, 0, 0)


def write_csv(path, data):
    keys = tuple(dict.fromkeys(key for row in data for key in row))
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, keys, lineterminator="\n")
        writer.writeheader()
        writer.writerows(data)


def read_archives(path, witnesses_only):
    for line in (path/"archives.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        archive = path/row["archive"]
        if witnesses_only and not archive.exists():
            continue
        check(sha(archive)==row["sha256"], f"archive changed: {archive}")
        with ZipFile(archive) as bundle:
            members = {name: bundle.read(name) for name in bundle.namelist()}
        check(json.loads(members["receipt.json"])==row["receipt"], "archive receipt differs")
        for name, value in row["receipt"]["artifacts"].items():
            check(len(members[name])==value["bytes"] and sha256(members[name]).hexdigest()==value["sha256"],
                  f"original member changed: {archive.name}/{name}")
        yield row, members


def scout_chain(raw, receivers):
    """The policy event changes a baseline choice. Physical milestones remain separate."""
    cue = {}
    observed, activations = {}, {}
    chain = {actor: {} for actor in receivers}
    prior_outside = set()
    markers, seen = 0, 0
    for e, resource, position in located_facts(raw, WATER):
        i, time, source, kind, actor, payload, value, _, _, mass, _ = e
        if kind == CUE:
            check(payload in prior_outside, "local signal has no earlier loaded delivery")
            cue[i] = actor
            markers += 1
        elif kind == EXPOSED:
            check(cue.get(value)==payload, "observation without committed scout signal")
            observed[(actor, source)] = (i, value)
            seen += 1
            if actor in chain:
                chain[actor].setdefault("first_exposure_ms", time)
        elif kind == ACTIVATED:
            check(observed[(actor, source)]==(i-1, value), "activation without same-decision exposure")
            activations[actor] = (source, time)
            if actor in chain:
                chain[actor].setdefault("activation_ms", time)
                chain[actor].setdefault("scout_id", payload)
                chain[actor].setdefault("cue_id", value)
        elif kind == BEHAVIOR and actor in chain and payload == 3:
            chain[actor].setdefault("first_forage_ms", time)
            if activations.get(actor)==(source,time):
                chain[actor].setdefault("confirmed_choice_ms", time)
        elif kind == MOVED and actor in chain and math.dist(position,(0.,0.,0.)) > .002:
            chain[actor].setdefault("first_departure_ms", time)
            if "confirmed_choice_ms" in chain[actor]:
                chain[actor].setdefault("recruited_departure_ms", time)
        elif kind == DECISION and actor in chain and resource:
            chain[actor].setdefault("first_discovery_ms", time)
            if "recruited_departure_ms" in chain[actor]:
                chain[actor].setdefault("recruited_discovery_ms", time)
        elif kind == COLLECTED and actor in chain and sum(mass):
            chain[actor].setdefault("first_collection_ms", time)
            if "recruited_discovery_ms" in chain[actor]:
                chain[actor].setdefault("recruited_collection_ms", time)
        elif kind == DELIVERED:
            prior_outside.add(i)
            if actor in chain:
                chain[actor].setdefault("first_delivery_ms", time)
                if "recruited_collection_ms" in chain[actor]:
                    chain[actor].setdefault("recruited_delivery_ms", time)
    return markers, seen, chain


def material_and_activity(raw, cuts, case, edits):
    available, release, cargo, poses, opened = {}, {}, {}, {}, {}
    soil_travel, soil = {}, {}
    selected = {}
    totals = Counter()
    larvae, offered, chosen, started, fed, absorbed = set(), set(), set(), set(), set(), set()
    care_rows = defaultdict(dict)
    layout = (((12,6,14),(25,10,18)),((21,6,14),(25,10,27)),((21,6,23),(25,16,27))) if case["layout"]=="dogleg" else (
        ((14,6,14),(18,16,18)),)
    if case["treatment"]=="wallwater":
        layout += (((19,7,15),(21,9,17)),)
    boxes = [("solid", (0,0,0), (32,16,32)), *(("void",a,b) for a,b in layout)]
    grid = Grid([dict(kind=kind, **{f"{edge}_{axis}_q":value for edge,point in (("min",low),("max",high))
                                   for axis,value in zip("xyz",point,strict=True)}) for kind,low,high in boxes])
    edits = {int(row["event"]): row for row in edits}
    remaining, carried, deposited = len(grid.soil), 0, 0
    cuts = iter(cuts)
    cut = next(cuts)
    terminal = case["horizon_ms"]

    def reconciled(cursor):
        nonlocal cut
        while cut and int(cut["cursor"])<cursor:
            check(tuple(sum(a[i] for a in available.values()) for i in range(4))==
                  tuple(int(cut[f"available_{k}"]) for k in "cpwo"), "source inventory differs at cut")
            check((remaining,carried,deposited)==tuple(int(cut[k]) for k in ("remaining_q3","carried_q3","deposited_q3")),
                  "soil accounting differs at cut")
            cut = next(cuts,None)

    def change(store, key, dose, sign=1):
        value = tuple(a+sign*b for a,b in zip(store.get(key,ZERO),dose,strict=True))
        check(min(value)>=0, "an individual or a source spent more than its owned stock")
        store[key] = value

    def close(actor, time, source=None):
        bout, begin = opened.pop(actor)
        check(source is None or bout==source, "wrong action closed the paid interval")
        totals["paid_ms"] += time-begin
        return begin

    for e, resource, position in located_facts(raw,WATER):
        i,time,source,kind,actor,payload,aux,stage,_,mass,obs=e
        reconciled(i)
        if kind in (2,35,43):
            poses[actor]=position
        if kind in (3,28):
            check(resource not in available,"source identity reused")
            available[resource]=mass
        elif kind==36:
            release[resource]=mass
        elif kind==37:
            change(release,resource,mass,-1)
            change(available,resource,mass)
        elif kind in (COLLECTED,WATER):
            check(resource in available,"undocumented source debit")
            change(available,resource,mass,-1)
            if kind==COLLECTED:
                change(cargo,actor,mass)
                totals["collection"] += 1
            else:
                check(mass[2] and sum(mass)==mass[2],"invalid pure water dose")
                totals["water_sipped_ug"] += mass[2]
                totals["water_sips"] += 1
        elif kind in (DELIVERED,19):
            change(cargo,actor,mass,-1)
        elif kind==23:
            check(payload not in soil,"parcel identity reused")
            edit=edits.pop(i)
            amount=int(edit["volume_q3"])
            check((int(edit["source"]),int(edit["actor"]),int(edit["parcel"]))==(source,actor,payload) and
                  grid.edit(edit,True)==amount,"soil geometry and fact disagree")
            soil[payload]=(actor,amount)
            remaining -= amount
            carried += amount
            soil_travel[actor]=payload
            totals["excavated_q3"] += amount
        elif kind==24:
            miner, amount=soil[payload]
            check(miner==actor and abs(soil_travel.get(actor,0))==payload,"soil drop lacks original excavator")
            carried -= amount
            deposited += amount
            if soil_travel.pop(actor,None)==-payload:
                totals["soil_parcels"] += 1
        elif kind==OBSERVATION_KIND:
            phase,act,target,bout,begin,known,*destination=obs
            if phase==1 and act==1:
                selected[bout]=(actor,begin,tuple(destination))
            if target in larvae:
                if phase==0:
                    offered.add(target)
                    care_rows[target].setdefault("first_opportunity_ms",time)
                if phase==1 and act==7:
                    chosen.add(target)
                    care_rows[target].setdefault("first_feed_selected_ms",time)
                if phase==2 and act==7:
                    started.add(target)
                    care_rows[target].setdefault("first_feed_started_ms",time)
            if phase in (3,4) and known and act!=0:
                totals["timed_care_ms"] += time-begin
        elif kind==MOVED:
            origin=poses[actor]
            distance=math.dist(position,origin)
            totals["path_m"] += distance
            poses[actor]=position
            parcel=soil_travel.get(actor,0)
            if distance and parcel>0:
                soil_travel[actor]=-parcel
            planned=selected.pop(source,None)
            if planned and case["treatment"]!="legacy" and distance:
                _,begin,destination=planned
                # Historical care moves share the kind but have different action IDs.
                check(destination==position,"move did not end at its selected waypoint")
                loaded=sum(cargo.get(actor,ZERO))>0 or bool(parcel)
                rate=.0025 if loaded else .005
                predicted=distance*1000/rate
                check(-1e-7<=time-begin-predicted<=1+1e-7,"distance/load and elapsed movement disagree")
                q=lambda p: tuple(round((v+.008)/.0005) for v in p)
                check(all(abs(v-(n*.0005-.008))<1e-11 for p in (origin,position) for v,n in zip(p,q(p),strict=True)) and
                      grid.swept(q(origin),q(position),2 if loaded else 1),"actual move crosses original or edited geometry")
                totals["loaded_move_ms" if loaded else "unloaded_move_ms"] += time-begin
                totals["loaded_moves" if loaded else "unloaded_moves"] += 1
        elif kind==ACTIVITY:
            if payload:
                check(actor not in opened,"overlapping work intervals")
                opened[actor]=(source,time)
            else:
                close(actor,time,source)
        elif kind==8:
            if actor in opened:
                close(actor,time)
                totals["paid_interrupted_by_death"] += 1
            if actor in larvae:
                care_rows[actor].update(terminal_ms=time,death_cause=payload)
                larvae.remove(actor)
        elif kind==7 and stage==1:
            larvae.add(actor)
            care_rows[actor]["hatch_ms"]=time
        elif kind==7 and stage==2:
            larvae.discard(actor)
            care_rows[actor].update(terminal_ms=time,pupated=1)
        elif kind==48 and mass[1]:
            fed.add(payload)
            care_rows[payload].setdefault("first_maternal_protein_ms",time)
        elif kind==16 and stage==1 and mass[1]:
            absorbed.add(actor)
            care_rows[actor].setdefault("first_protein_absorption_ms",time)
        elif kind==16 and stage==3 and mass[2]:
            totals["adult_water_absorption_ug"] += mass[2]
    reconciled(2**64)
    check(cut is None and not edits,"unreconciled ecology cut or geometry edit")
    for actor in tuple(opened):
        close(actor,terminal)
        totals["paid_right_censored"] += 1
    for actor in larvae:
        care_rows[actor].update(terminal_ms=terminal,censored=1)
    return (dict(totals) | dict(contacted=len(offered), feeding_selected=len(chosen), feeding_started=len(started),
           maternal_protein_receivers=len(fed), assimilated_larvae=len(absorbed), unfed_contacted=len(offered-fed)),
           [dict(ant=k,**v) for k,v in care_rows.items()])


OBSERVATION_KIND = 42


def run(panel, directory, output, witnesses_only):
    output.mkdir(parents=True)
    worlds, larvae, receivers = [], [], []
    references, midpoints = {}, []
    failures = []
    for row, blobs in read_archives(directory,witnesses_only):
        name, receipt = row["case"], row["receipt"]
        if receipt["status"]!="COMPLETE":
            failures.append(dict(case=name, status=receipt["status"], message=blobs["program.log"].decode(errors="replace")))
            continue
        case = json.loads(blobs["case.json"])
        mode = receipt.get("mode",case.get("mode"))
        if mode not in ("observed",):
            if panel=="scout":
                prior=references[name.removesuffix("-durable")+"-observed"]
                check(all(prior["artifacts"][key]==receipt["artifacts"][key] for key in ("initial.chk","final.frame","facts.bin")),
                      "scout recovery changed canonical authority")
            else:
                prior, cuts, summary, raw = references[name.removesuffix("-"+mode)]
                check_identity(prior,receipt,name)
                if mode=="durable-split":
                    with TemporaryDirectory(dir=output) as scratch:
                        midpoints.append(dict(case=name,**verify_midpoint(blobs["midpoint.sqlite"],raw,summary,cuts,Path(scratch),fact_schema=9)))
            continue
        raw=blobs["facts.bin"]
        if panel=="scout":
            references[name]=receipt
            ids=[int(r["id"]) for r in rows(blobs["identities.csv"]) if r["role"]=="receiver"]
            signals, exposures, chain=scout_chain(raw,ids)
            for actor, result in chain.items():
                receivers.append(dict(case=name,actor=actor,observation_end_ms=case["horizon_ms"],**result))
            worlds.append(dict(case=name,arm=case["arm"],seed=case["seed"],signals=signals,exposures=exposures,
                               activated=sum("activation_ms" in r for r in chain.values()),
                               deliveries=sum("first_delivery_ms" in r for r in chain.values()),
                               complete=sum("recruited_delivery_ms" in r for r in chain.values()),
                               collections=sum(e[3]==COLLECTED for e in facts(raw,WATER))))
            continue
        check(blobs["parameters.txt"]==input_bytes(receipt["identity"],case),"wrong frozen input")
        summary = receipt["summary"]
        sample = case | dict(arm="integrated-"+case["source"],early_access_mask=3,carbohydrate_yield_nj_per_ug=8_000_000)
        cuts = rows(blobs["cuts.csv"])
        result, stages, paths, cohorts=assess(sample,summary,raw,blobs["cuts.csv"],blobs["individuals.csv"],7,ecological=True)
        activity, care_rows=material_and_activity(raw,cuts,case,rows(blobs["geometry_edits.csv"]))
        if panel=="joint" and case["treatment"]=="joint" and case["software_seed"]==1 and case["source"]=="balanced" and case["parameters"]["maternal_lipid"]==5500:
            references[name]=(receipt,cuts,summary,raw)
        by_id={r["ant"]: r for r in paths}
        larvae.extend(dict(case=name,**r,first_ration_event=by_id[r["ant"]]["first_positive_protein_ration_event"])
                      for r in care_rows)
        if panel=="joint":
            snapshots=defaultdict(list)
            for ant in rows(blobs["individuals.csv"]):
                time=int(ant["time_ms"])
                if time in (120*DAY,150*DAY):
                    snapshots[time//DAY].append(ant)
            chain, _, _, _=observe_chain(raw,sample,int(summary["queen"]),paths,snapshots,maximum=WATER)
            if case["source"]=="no-protein":
                check(chain["worker_protein_assimilated_lower_bound_ug"]==0,"protein entered a protein-free arm")
            result |= dict(chain) | dict(joint=int(chain["complete"] and activity.get("soil_parcels",0)>0))
        result |= activity
        result |= {f"{c['rule']}_{key}":c[key] for c in cohorts for key in ("k","egg_d","larva_d","pupa_d","total_d")}
        result |= {f"{c['rule']}_timing_match": int(all(c[key] is not None and low<=c[key]<=high
            for key,(low,high) in zip(("egg_d","larva_d","pupa_d","total_d"),RANGES[case["population"]],strict=True))) for c in cohorts}
        worlds.append(dict(case=name,population=case["population"],seed=case["software_seed"],source=case["source"],
                           layout=case["layout"],treatment=case["treatment"],reserve=case["parameters"]["maternal_lipid"],**result))
    write_csv(output/"worlds.csv",worlds)
    if receivers:
        write_csv(output/"receivers.csv",receivers)
    if larvae:
        write_csv(output/"larvae.csv",larvae)
    write_json(output/"midpoints.json",midpoints)
    write_json(output/"failures.json",failures)
    keys = ("arm",) if panel=="scout" else ("population","layout","treatment","source","reserve")
    groups=[]
    for values, group in groupby(sorted(worlds,key=lambda r:tuple(r[k] for k in keys)),lambda r:tuple(r[k] for k in keys)):
        data=list(group)
        counts = ("complete","collections","activated","deliveries","signals","exposures") if panel=="scout" else (
            "joint","complete","hatch","pupation","eclosed","collection","soil_parcels","maternal_protein_receivers",
            "water_sipped_ug","paid_ms","loaded_move_ms","unloaded_move_ms","exact_timing_match","at_least_timing_match")
        groups.append(dict(zip(keys,values,strict=True))|dict(worlds=len(data))|{f"sum_{k}":sum(r.get(k,0) for r in data)
            for k in counts}|{f"median_{k}":median(r.get(k,0) for r in data) for k in counts})
    write_csv(output/"groups.csv",groups)
    print(f"{panel}: {len(worlds)} observed, {len(failures)} failed, {len(midpoints)} SQLite prefix checks")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("panel",choices=("scout","care","joint"))
    parser.add_argument("input",type=Path)
    parser.add_argument("output",type=Path)
    parser.add_argument("--witnesses-only",action="store_true")
    args=parser.parse_args()
    run(args.panel,args.input,args.output,args.witnesses_only)
