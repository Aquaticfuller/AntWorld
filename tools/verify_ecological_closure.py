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
from struct import unpack_from
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from analyze_integrated_founding import located_facts, observe_chain
from analyze_s6_4_wp6b import assess, check, facts, rows, RANGES
from final_core_b06_cohorts import stage_occupancy
from run_ecological_closure import SCOUT_ARMS, roster
from run_integrated_founding import DAY
from run_s6_4_wp6b import input_bytes, sha, write_json
from s6_4_wp5_geometry import Grid
from verify_final_core_integration import check_identity, verify_midpoint


DELIVERED, COLLECTED, MOVED, DECISION, BEHAVIOR = 12, 5, 4, 11, 17
CUE, EXPOSED, ACTIVATED, ACTIVITY, WATER = range(54, 59)
ZERO = (0, 0, 0, 0)
POPULATIONS = ("borisovka", "st_petersburg")
LAYOUTS = ("shaft", "dogleg")
SCOUT_MILESTONES = ("confirmed_choice", "recruited_departure", "recruited_discovery",
                    "recruited_collection", "recruited_loaded_return", "recruited_delivery")


def write_csv(path, data):
    keys = tuple(dict.fromkeys(key for row in data for key in row))
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, keys, lineterminator="\n")
        writer.writeheader()
        writer.writerows(data)


def fixed_witnesses(panel):
    if panel == "scout":
        return {f"{arm}-1-observed" for arm in SCOUT_ARMS} | {"scout-1-durable"}
    if panel == "care":
        return {f"{population}-1-shaft-{arm}-absent-5500" for population in POPULATIONS
                for arm in ("water", "wallwater", "first", "cost", "careoff")}
    return {f"{population}-1-{layout}-joint-balanced-5500" for population in POPULATIONS for layout in LAYOUTS} | {
        "borisovka-1-shaft-joint-blocked-5500", "borisovka-1-shaft-joint-absent-5500",
        "borisovka-1-shaft-joint-balanced-5250", "borisovka-1-shaft-joint-no-protein-5500",
        "st_petersburg-1-dogleg-joint-limited-5500", "borisovka-1-shaft-joint-balanced-5500-durable-split",
        "st_petersburg-1-dogleg-joint-balanced-5500-durable-split"}


def frozen_names(panel):
    if panel == "scout":
        return [f"{arm}-{seed}-{mode}" for arm in SCOUT_ARMS for seed in range(1, 13)
                for mode in (("observed", "durable") if seed == 1 and arm == "scout" else ("observed",))]
    return [case["case"] for _, case, _ in roster(panel)]


def read_archives(path, witnesses_only, panel, selection=None):
    manifest = [json.loads(line) for line in (path/"archives.jsonl").read_text(encoding="utf-8").splitlines()]
    names = frozen_names(panel)
    run_receipt = json.loads((path/"run.json").read_bytes())
    portable = run_receipt.get("portable_field",False)
    check(run_receipt["cases"] == names and [row["case"] for row in manifest] == names and
          all(r["archive"] == r["case"] + ".zip" for r in manifest), "frozen roster identity or denominator changed")
    if witnesses_only:
        selected = fixed_witnesses(panel) if selection is None else selection
        check({archive.stem for archive in path.glob("*.zip")} == selected, "published witness panel changed")
    for row in manifest:
        archive = path/row["archive"]
        if witnesses_only and not archive.exists():
            continue
        check(sha(archive)==row["sha256"], f"archive changed: {archive}")
        with ZipFile(archive) as bundle:
            members = {name: bundle.read(name) for name in bundle.namelist()}
            check(len(bundle.namelist()) == len(members) and set(members) == {"receipt.json", *row["receipt"]["artifacts"]},
                  "archive member roster differs")
        check(json.loads(members["receipt.json"]) == row["receipt"], "archive receipt differs")
        for name, value in row["receipt"]["artifacts"].items():
            check(len(members[name])==value["bytes"] and sha256(members[name]).hexdigest()==value["sha256"],
                  f"original member changed: {archive.name}/{name}")
        if "initial.chk" in members:
            header = members["initial.chk"]
            if "-legacy-" in row["case"]:
                check(header[:7]!=b"AWCKPTM","legacy control has ecological physics")
            else:
                check(header[:7]==b"AWCKPTM" and unpack_from("<II",header,8)==(22,25 if portable else 24),
                      "archive uses the wrong ecological arithmetic version")
        yield row, members


def scout_chain(raw, receivers, depot=(0.,0.,0.)):
    """Link consecutive behavior and material facts through the same recruitment episode."""
    cue = {}
    observed, activations, active = {}, {}, {}
    chain = {actor: {} for actor in (receivers or ())}
    partial = defaultdict(dict)
    returns = {}
    markers, seen = 0, 0

    def record(record_row, milestone, time, event):
        record_row.setdefault(milestone+"_ms", time)
        record_row.setdefault(milestone+"_event", event)

    def stop(actor, reason):
        episode = active.pop(actor,None)
        if episode is not None and len(episode)>len(partial[actor]):
            partial[actor] = episode | {"recruitment_end":reason}

    for e, resource, position in located_facts(raw, WATER):
        i, time, source, kind, actor, payload, value, _, _, mass, _ = e
        if kind == CUE:
            check(returns.get(payload)==(actor,time,source,position), "local cue lacks the scout's positive return")
            cue[i] = (actor,time,position,payload)
            markers += 1
        elif kind == EXPOSED:
            signal = cue[value]
            check(signal[0]==payload and signal[1]<=time and math.dist(signal[2],position)<=.002+1e-14,
                  "observation without a nearby committed scout signal")
            observed[(actor, source)] = (i, value)
            seen += 1
            if actor in chain:
                record(chain[actor],"first_exposure",time,i)
        elif kind == ACTIVATED:
            check(observed[(actor, source)]==(i-1, value), "activation without same-decision exposure")
            episode = dict(scout_id=payload,cue_id=value,scout_delivery_event=cue[value][3],
                           activation_event=i,activation_ms=time)
            activations[actor] = (source,time,episode)
            if actor in chain:
                for key, data in episode.items():
                    chain[actor].setdefault(key,data)
        elif kind == 7 and e[7]==3 and receivers is None:
            chain[actor]={}
        elif kind == BEHAVIOR and actor in chain:
            if payload != 3:
                stop(actor,"PROGRAM_ENDED")
                continue
            record(chain[actor],"first_forage",time,i)
            started = activations.pop(actor,None)
            if started and started[:2]==(source,time):
                active[actor] = started[2]
                record(active[actor],"confirmed_choice",time,i)
                record(chain[actor],"first_confirmed_choice",time,i)
        elif kind == MOVED and actor in chain:
            outside = math.dist(position,depot) > .002
            if outside:
                record(chain[actor],"first_departure",time,i)
            if actor in active:
                episode = active[actor]
                if "recruited_collection_event" in episode:
                    record(episode,"recruited_loaded_return",time,i)
                elif outside:
                    record(episode,"recruited_departure",time,i)
        elif kind == DECISION and actor in chain and resource:
            record(chain[actor],"first_discovery",time,i)
            if actor in active and "recruited_departure_ms" in active[actor]:
                record(active[actor],"recruited_discovery",time,i)
                active[actor].setdefault("recruited_source",resource)
        elif kind == COLLECTED and actor in chain and sum(mass):
            record(chain[actor],"first_collection",time,i)
            if actor in active and active[actor].get("recruited_source")==resource:
                record(active[actor],"recruited_collection",time,i)
        elif kind == DELIVERED and sum(mass):
            returns[i] = (actor,time,source,position)
            if actor in chain:
                record(chain[actor],"first_delivery",time,i)
                episode = active.get(actor)
                if episode and all(k+"_event" in episode for k in SCOUT_MILESTONES[:-1]) and "recruited_delivery_ms" not in chain[actor]:
                    record(episode,"recruited_delivery",time,i)
                    ordered = [episode[k+"_event"] for k in SCOUT_MILESTONES]
                    check(all(a<b for a,b in zip(ordered,ordered[1:])),"recruitment episode is out of order")
                    chain[actor].update(episode | {"recruitment_end":"DELIVERED"})
                stop(actor,"UNLINKED_DELIVERY")
        elif kind == 8 and actor in chain:
            record(chain[actor],"death",time,i)
            stop(actor,"DEATH")
    for actor in tuple(active):
        stop(actor,"RIGHT_CENSORED")
    for actor, result in chain.items():
        if "recruitment_end" not in result:
            if actor in partial:
                result.update(partial[actor])
            elif receivers is not None:
                result["recruitment_end"]="CHOICE_NOT_OBSERVED" if "activation_ms" in result else "NO_ACTIVATION"
    return markers, seen, chain


def verify_scout_material(raw):
    stocks, loads = {}, defaultdict(lambda: ZERO)
    for e, resource, position in located_facts(raw, WATER):
        _, _, _, kind, actor, _, _, _, _, amount, _ = e
        if kind == 3:
            check(resource not in stocks and abs(position[0]) == .02, "wrong scout source")
            stocks[resource] = amount
        elif kind == COLLECTED:
            check(resource in stocks and abs(position[0]) == .02, "collection outside scout source")
            stocks[resource] = tuple(a-b for a,b in zip(stocks[resource],amount,strict=True))
            check(min(stocks[resource])>=0,"overdrawn scout source")
            loads[actor] = tuple(a+b for a,b in zip(loads[actor],amount,strict=True))
        elif kind == DELIVERED:
            check(math.dist(position,(0.,0.,0.))<=.002 and amount==loads[actor] and sum(amount),
                  "return without the same actor's positive scout load")
            loads[actor] = ZERO


def material_and_activity(raw, cuts, case, edits, *, check_sources=False):
    available, release, cargo, poses, opened = {}, {}, {}, {}, {}
    soil_travel, soil, programs = {}, {}, {}
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
    stock = tuple(case["external_food_components_ug"])
    expected_sources = int(any(stock)) + int(case["treatment"] in {"water","wallwater"})
    daily_release = (188,94,563,0) if case["source"]=="limited" else tuple(m//4 for m in stock)
    food_positions = {}

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
        totals["paid_intervals"] += 1
        return time-begin

    for e, resource, position in located_facts(raw,WATER):
        i,time,source,kind,actor,payload,aux,stage,_,mass,obs=e
        reconciled(i)
        if kind in (2,35,43):
            poses[actor]=position
        if kind in (2,7) and stage==3:
            programs[actor]=(0,time)
        elif kind in (BEHAVIOR,8) and actor in programs:
            program, entered = programs.pop(actor)
            totals[f"program_{program}_ms"]+=time-entered
            if kind==BEHAVIOR:
                programs[actor]=(payload,time)
        if kind==6:
            totals[f"action_rejected_{e[8]}"] += 1
        elif kind==27:
            totals["excavation_wakes"] += 1
        if kind in (3,28):
            check(resource not in available,"source identity reused")
            available[resource]=mass
            food_positions[resource]=position
            if check_sources:
                expected_position = (.002 if case["treatment"]=="wallwater" else 0.,-.004,0.)
                check(time==0 and ((position==expected_position and mass==(0,0,1200,0) and
                      case["treatment"] in {"water","wallwater"}) or
                      (any(stock) and abs(position[0])==.03 and position[1:]==(0.,0.) and mass==stock)),
                      "explicit source differs from frozen assay")
        elif kind==36:
            release[resource]=mass
            if check_sources:
                check(resource in available and available[resource]==stock and
                      mass==tuple(120*m for m in daily_release),"incorrect finite release inventory")
        elif kind==37:
            change(release,resource,mass,-1)
            change(available,resource,mass)
            if check_sources:
                expected = daily_release if time<=120*DAY else ZERO
                check(mass==expected and time%DAY==0 and 0<time<=terminal,
                      "release differs from the frozen source clock or ration")
        elif kind in (COLLECTED,WATER):
            check(resource in available,"undocumented source debit")
            change(available,resource,mass,-1)
            if kind==COLLECTED:
                if check_sources:
                    check(abs(position[0])>=.025 and math.dist(position,food_positions[resource])<=.002+1e-14,
                          "food was collected without physical source contact")
                change(cargo,actor,mass)
                totals["collection"] += 1
            else:
                check(mass[2] and sum(mass)==mass[2],"invalid pure water dose")
                totals["water_sipped_ug"] += mass[2]
                totals["water_sips"] += 1
        elif kind in (DELIVERED,19):
            change(cargo,actor,mass,-1)
        elif kind==55:
            totals["cue_observations"]+=1
        elif kind==56:
            totals["cue_activations"]+=1
        elif kind==DECISION:
            totals["trail_seen"]+=bool(aux&1)
            totals["trail_weighted"]+=bool(aux&2)
            totals["trail_followed"]+=bool(aux&4)
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
                span=close(actor,time,source)
                totals[f"paid_program_{programs.get(actor,(0,0))[0]}_ms"] += span
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
    if check_sources:
        check(len(available)==expected_sources,"expected source missing or duplicated")
    for actor in tuple(opened):
        close(actor,terminal)
        totals["paid_right_censored"] += 1
    for program,entered in programs.values():
        totals[f"program_{program}_ms"]+=terminal-entered
    for actor in larvae:
        care_rows[actor].update(terminal_ms=terminal,censored=1)
    return (dict(totals) | dict(contacted=len(offered), feeding_selected=len(chosen), feeding_started=len(started),
           maternal_protein_receivers=len(fed), assimilated_larvae=len(absorbed), unfed_contacted=len(offered-fed)),
           [dict(ant=k,**v) for k,v in care_rows.items()])


OBSERVATION_KIND = 42


def cohort_endpoints(stages, horizon, paths, cohorts, care_rows):
    """A living-count match can be made by animals born in a later cohort."""
    daily = dict(stage_occupancy(stages,horizon))
    first = next((ids[1] for ids in daily.values() if ids[1]),frozenset())
    people = {r["ant"]:r for r in paths}
    summary = dict(first_census_larvae=len(first), first_cohort_pupated=0, first_cohort_eclosed=0,
                   first_cohort_energy_deaths=0, first_cohort_water_deaths=0, first_cohort_censored=0,
                   first_cohort_no_ration=0, first_cohort_no_protein_uptake=0)
    early_times = defaultdict(list)
    for identity in sorted(first):
        p, care = people[identity], care_rows[identity]
        summary["first_cohort_pupated"] += p["pupa_ms"] is not None
        summary["first_cohort_eclosed"] += p["adult_ms"] is not None
        summary["first_cohort_energy_deaths"] += care.get("death_cause")==1
        summary["first_cohort_water_deaths"] += care.get("death_cause")==2
        summary["first_cohort_censored"] += bool(care.get("censored"))
        summary["first_cohort_no_ration"] += not p["ration_protein_ug"]
        summary["first_cohort_no_protein_uptake"] += not p["larval_protein_uptake_ug"]
    for identity,p in people.items():
        if p["adult_ms"] is not None:
            category = "first_cohort" if identity in first else "later_cohort"
            for key,a,b in (("egg","birth_ms","larva_ms"),("larva","larva_ms","pupa_ms"),
                            ("pupa","pupa_ms","adult_ms"),("whole","birth_ms","adult_ms")):
                early_times[f"{category}_{key}_median_days"].append((p[b]-p[a])/DAY)
    for census in cohorts:
        for stage,number in (("pupa",2),("worker",3)):
            at = census[f"first_{stage}_ms"]
            if at is not None:
                same = len(daily[at][number] & first)
                summary[f"{census['rule']}_{stage}_first_cohort"] = same
                summary[f"{census['rule']}_{stage}_other_cohort"] = len(daily[at][number])-same
    return summary | {k:median(v) for k,v in early_times.items()}


def run(panel, directory, output, witnesses_only, selection=None):
    output.mkdir(parents=True)
    worlds, larvae, receivers = [], [], []
    references, midpoints = {}, []
    failures = []
    stage_rows = []
    for row, blobs in read_archives(directory,witnesses_only,panel,selection):
        name, receipt = row["case"], row["receipt"]
        if receipt["status"]!="COMPLETE":
            item=dict(case=name, status=receipt["status"], message=blobs["program.log"].decode(errors="replace"))
            if "last_committed.frame" in blobs:
                frame=blobs["last_committed.frame"]
                check(frame[:15]==b"AWSTATE1AWCKPTM","failure did not retain an ecological authority frame")
                cuts=rows(blobs["timings.csv"])
                count=sum(1 for _ in facts(blobs["facts.bin"],WATER))
                check(count==int(cuts[-1]["committed"]),"failure facts disagree with latest complete cut")
                item.update(last_ms=int(cuts[-1]["time_ms"]),committed=count,
                            state_sha256=sha256(frame).hexdigest(),facts_sha256=sha256(blobs["facts.bin"]).hexdigest())
            failures.append(item)
            continue
        case = json.loads(blobs["case.json"])
        mode = receipt.get("mode",case.get("mode"))
        if mode not in ("observed",):
            if panel=="scout":
                prior=references[name.removesuffix("-durable")+"-observed"]
                check(all(prior["artifacts"][key]==receipt["artifacts"][key] for key in ("initial.chk","final.frame","facts.bin")),
                      "scout recovery changed canonical authority")
            else:
                key = name.removesuffix("-"+mode)
                if key not in references:
                    failures.append(dict(case=name,status="COMPARISON_NOT_AVAILABLE",message="observed arm did not complete"))
                    continue
                prior, cuts, summary, raw = references[key]
                check_identity(prior,receipt,name)
                if mode=="durable-split":
                    with TemporaryDirectory(dir=output) as scratch:
                        midpoints.append(dict(case=name,**verify_midpoint(blobs["midpoint.sqlite"],raw,summary,cuts,Path(scratch),fact_schema=9)))
            continue
        raw=blobs["facts.bin"]
        if panel=="scout":
            references[name]=receipt
            verify_scout_material(raw)
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
        stage_rows.extend(stages)
        activity, care_rows=material_and_activity(raw,cuts,case,rows(blobs["geometry_edits.csv"]),check_sources=True)
        if panel=="joint" and case["treatment"]=="joint" and case["software_seed"]==1 and case["source"]=="balanced" and case["parameters"]["maternal_lipid"]==5500:
            references[name]=(receipt,cuts,summary,raw)
        by_id={r["ant"]: r for r in paths}
        result |= cohort_endpoints(stages,case["horizon_ms"],paths,cohorts,{r["ant"]:r for r in care_rows})
        larvae.extend(dict(case=name,**r,first_ration_event=by_id[r["ant"]]["first_positive_protein_ration_event"])
                      for r in care_rows)
        if panel=="joint":
            snapshots=defaultdict(list)
            for ant in rows(blobs["individuals.csv"]):
                time=int(ant["time_ms"])
                if time in (120*DAY,150*DAY):
                    snapshots[time//DAY].append(ant)
            chain, _, _, _=observe_chain(raw,sample,int(summary["queen"]),paths,snapshots,maximum=WATER)
            if case["treatment"]=="joint":
                _, _, recruitment=scout_chain(raw,None,(0.,-.004,0.))
                result["cue_to_delivery_workers"]=sum("recruited_delivery_ms" in data for data in recruitment.values())
                receivers.extend(dict(case=name,actor=actor,observation_end_ms=case["horizon_ms"],**data)
                                 for actor,data in recruitment.items() if data)
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
    if stage_rows:
        write_csv(output/"stages.csv",stage_rows)
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
