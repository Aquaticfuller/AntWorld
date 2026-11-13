"""Verify funded first-cohort trajectories and matched contrasts from native archives."""

import argparse
from collections import Counter, defaultdict
import gzip
from hashlib import sha256
from itertools import combinations
import json
from math import isclose
from pathlib import Path
from random import Random
from statistics import mean
from struct import unpack_from
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from analyze_integrated_founding import observe_chain
from analyze_s6_4_wp6b import assess, check, facts, rows, RANGES
from final_core_b06_cohorts import stage_occupancy
from run_founding_cohort_release import COUNTS, manifest, roster
from run_integrated_founding import DAY
from run_ecological_closure import SCOUT_ARMS, scout
from run_s6_4_wp6b import ROOT, input_bytes, run_one, sha, write_json
from verify_ecological_closure import WATER, cohort_endpoints, material_and_activity, write_csv
from verify_final_core_integration import check_identity, verify_midpoint


STATE_COLUMNS = ("time_ms", "cursor", "stage", "program", "hydration_ug", "crop_w", "energy_nj", "lipid_ug",
                 "spent_lipid_ug", "mobile_protein_ug", "crop_p", "tissue_protein_ug", "dissipated_nj",
                 "lost_water_ug", "next_absorption_ms")
PHASES = ("opportunity", "selected", "started", "completed", "interrupted")
FACTS = {7:"stage", 8:"death", 16:"absorption", 35:"birth", 47:"lipid_conversion", 48:"maternal_ration",
         49:"lipid_mobilization", 50:"hatch_cue", 51:"foundress_nest_meal", 53:"boundary_uptake",
         57:"paid_activity", 58:"water_ingested"}
PAID_CARE = 57


def follow_first(raw, stage_rows, people, queen, horizon, case):
    daily = dict(stage_occupancy(stage_rows,horizon))
    census_time, first = next(((t,ids[1]) for t,ids in daily.items() if ids[1]),(None,frozenset()))
    hatches={int(s["ant"]):s["enter_ms"] for s in stage_rows if s["stage"]==1 and int(s["ant"]) in first}
    track = {identity:dict(case=case,ant=identity,first_census_ms=census_time) for identity in sorted(first)}
    slices = defaultdict(dict)
    for row in people:
        actor = int(row["id"])
        if actor in first or actor==queen:
            slices[actor][int(row["time_ms"])] = {key:row[key] for key in STATE_COLUMNS}
    event_rows, last_ration = [], set()
    maternal = Counter()
    paid_work=None
    for event,time,source,kind,actor,payload,value,stage,outcome,mass,obs in facts(raw,WATER):
        recipient = obs[2] if kind==42 else payload if kind in (48,50) else actor
        name = FACTS.get(kind)
        if kind==42 and actor==queen:
            phase,act,_,bout,began,known,*_ = obs
            name = PHASES[phase] if not phase else f"{PHASES[phase]}_{'feed' if act==7 else 'other'}"
            if phase in (3,4) and known and act:
                maternal["observed_timed_care_ms"]+=time-began
        elif kind==21:
            recipient=payload
            name="worker_exchange"
        elif kind==34 and actor==queen:
            name="reproduction_attempt"
        if not name or (recipient not in first and actor!=queen and recipient!=queen):
            continue
        if name=="absorption" and not any(mass):
            continue
        if recipient in track:
            row=track[recipient]
            if kind in (7,8,35):
                label = "death" if kind==8 else "birth" if kind==35 else ("egg", "hatch", "pupa", "adult")[stage]
                row[label+"_ms"]=time
                row[label+"_event"]=event
                if kind==8:
                    row["death_cause"]=payload
            elif kind in (42,48,50) and actor==queen and time>=hatches[recipient]:
                row.setdefault("first_"+name+"_ms",time)
                row.setdefault("first_"+name+"_event",event)
                row[name+"_count"]=row.get(name+"_count",0)+1
            if kind==48:
                last_ration.add(recipient)
                for key,amount in (("maternal_water_ug",mass[2]),("maternal_protein_ug",mass[1]),("maternal_lipid_ug",value)):
                    row[key]=row.get(key,0)+amount
            if kind==16 and stage==1:
                for key,amount in (("protein",mass[1]),("water",mass[2])):
                    if amount:
                        row.setdefault(f"first_{key}_uptake_ms",time)
                        row.setdefault(f"first_{key}_uptake_event",event)
                        row[f"larval_{key}_uptake_ug"]=row.get(f"larval_{key}_uptake_ug",0)+amount
            if kind in (47,49) and stage==1:
                row["larval_lipid_converted_ug"]=row.get("larval_lipid_converted_ug",0)+payload
        if actor==queen or recipient==queen:
            maternal[name+"_count"]+=1
            if kind==58: maternal["local_water_ug"]+=mass[2]
            if kind in (16,53): maternal["assimilated_water_ug"]+=mass[2]
            if kind==48: maternal["total_ration_water_ug"]+=mass[2]
            if kind==PAID_CARE:
                if payload:
                    check(paid_work is None,"overlapping maternal work")
                    paid_work=(source,time)
                else:
                    check(paid_work is not None and paid_work[0]==source,"unmatched maternal work")
                    maternal["paid_maternal_work_ms"]+=time-paid_work[1]
                    paid_work=None
            if kind==8 and paid_work is not None:
                maternal["paid_maternal_work_ms"]+=time-paid_work[1]
                paid_work=None
        if recipient in first or (actor==queen and kind in (7,8,34,47,48,51,53,57,58)) or recipient==queen:
            entry = dict(case=case,event=event,time_ms=time,source=source,kind=name,actor=actor,recipient=recipient,
                         stage=stage,outcome=outcome,payload=payload,value=value,carbs_ug=mass[0],protein_ug=mass[1],water_ug=mass[2])
            if kind==42: entry.update(bout=obs[3],began_ms=obs[4],duration_known=obs[5])
            # A day-boundary event precedes the cut at that timestamp. Use
            # only a strictly earlier cut for preceding state evidence.
            preceding=(time-1)//DAY*DAY
            for key, identity in (("queen",queen),("larva",recipient)):
                if preceding in slices.get(identity,{}) and (key=="queen" or identity in first):
                    entry.update({f"{key}_prior_{field}":slices[identity][preceding][field] for field in STATE_COLUMNS})
            event_rows.append(entry)
    if paid_work is not None:
        maternal["paid_maternal_work_ms"]+=horizon-paid_work[1]
    for identity, row in track.items():
        row["larval_outcome"]=("PUPATED" if "pupa_ms" in row else f"DEATH_{row['death_cause']}" if "death_cause" in row else "RIGHT_CENSORED")
        row["adult_outcome"]=("ECLOSED" if "adult_ms" in row else f"DEATH_{row['death_cause']}" if "death_cause" in row else "RIGHT_CENSORED")
        row["no_paid_ration"]=int(identity not in last_ration)
        row["paid_protein_not_absorbed"]=int(bool(row.get("maternal_protein_ug")) and not row.get("larval_protein_uptake_ug"))
        row["paid_water_not_absorbed"]=int(bool(row.get("maternal_water_ug")) and not row.get("larval_water_uptake_ug"))
    prefate = sum(s["stage"]==1 and s["outcome"].startswith("DEATH") and census_time is not None and s["end_ms"]<=census_time
                  for s in stage_rows)
    return list(track.values()),event_rows,dict(maternal) | {"deaths_before_first_census":prefate}


def paired_effects(panel, worlds):
    keys = (("first_meal", "activity_charge", "recruitment", "water_access") if panel=="primary"
            else ("hatch_cue", "repeat_feeding"))
    outcomes = ("first_rate", "energy_rate", "water_rate", "no_ration_rate", "maternal_ration_water", "local_water_ug")
    groups=defaultdict(list)
    for r in worlds:
        groups[r["population"],r["layout"],r["seed"]].append(r)
    expanded, results = [], []
    for count in (1,2):
        for terms in combinations(keys,count):
            for endpoint in outcomes:
                for block, data in groups.items():
                    values=defaultdict(list)
                    for r in data:
                        v=tuple(int(r[k]=="reachable") if k=="water_access" else r[k] for k in terms)
                        values[v].append(r.get(endpoint,0))
                    if len(data)!=2**len(keys) or any(v is None for x in values.values() for v in x):
                        estimate=None
                    elif count==1:
                        estimate=mean(values[(1,)])-mean(values[(0,)])
                    else:
                        estimate=mean(values[1,1])-mean(values[0,1])-mean(values[1,0])+mean(values[0,0])
                    expanded.append(dict(population=block[0],layout=block[1],seed=block[2],contrast="*".join(terms),
                                         endpoint=endpoint,estimate=estimate))
    generator=Random(62426)
    grouped=defaultdict(list)
    for row in expanded:
        grouped[row["population"],row["contrast"],row["endpoint"]].append(row)
    for (population, contrast, endpoint), data in grouped.items():
        seeds=defaultdict(list)
        for r in data:
            if r["estimate"] is not None:
                seeds[r["seed"]].append(r["estimate"])
        cluster=[mean(v) for v in seeds.values() if len(v)==2]
        distributions=sorted(mean(generator.choices(cluster,k=len(cluster))) for _ in range(5000)) if len(cluster)==6 else []
        results.append(dict(population=population,contrast=contrast,endpoint=endpoint,seed_clusters=len(cluster),
                            estimate=mean(cluster) if distributions else None,
                            lo=distributions[124] if distributions else None,hi=distributions[4874] if distributions else None))
    return expanded,results


def native_binary(binary):
    if not binary.is_file():
        binary = binary.parent / "Release" / (binary.stem + ".exe")
    return binary.resolve(strict=True)


def replay_correction(binary, selected, comparisons, output):
    binary = native_binary(binary)
    replayed = []
    for identity, case, mode, args in selected:
        if mode != "durable-split":
            continue
        with TemporaryDirectory(dir=output) as scratch:
            rerun = run_one(binary, Path(scratch) / "rerun", identity, case, "durable", args)
            check(rerun["status"] == "COMPLETE", "native protected-profile replay failed")
            original = comparisons[case["observed_case"]]
            check_identity(original, rerun, case["case"])
            for name in ("cuts.csv", "individuals.csv", "geometry_edits.csv", "space_cuts.csv"):
                check(original["artifacts"][name] == rerun["artifacts"][name], f"native replay changed {name}")
            replayed.append({"case": case["case"], "events": rerun["summary"]["events"],
                             "facts_sha256": rerun["artifacts"]["facts.bin"]["sha256"]})
    check(len(replayed) == 2, "changed native protected-profile replay roster")
    write_json(output / "fresh_replay.json", {"binary_sha256": sha(binary), "cases": replayed})


def replay_scout_controls(binary, output):
    binary = native_binary(binary)
    reference = ROOT / "experiments/s6_4_ecological_mechanism_closure/portable-physics/scout"
    roster = {r["case"]: r["receipt"] for r in manifest(reference)}
    results = []
    with TemporaryDirectory(dir=output) as scratch:
        for arm in SCOUT_ARMS:
            for seed in range(1, 13):
                name = f"{arm}-{seed}-observed"
                current = scout(binary, Path(scratch) / name, arm, seed, "observed", portable=True)
                prior = roster[name]
                check(current["status"] == prior["status"] == "COMPLETE", f"scout replay failed: {name}")
                for key in ("initial.chk", "final.frame", "facts.bin", "identities.csv"):
                    check(current["artifacts"][key] == prior["artifacts"][key], f"{name}: scout authority changed: {key}")
                results.append({"case": name, "facts_sha256": current["artifacts"]["facts.bin"]["sha256"]})
    write_json(output / "fresh_scout_controls.json", {"binary_sha256": sha(binary), "cases": results})


def verify(panel, directory, output, public=False, packed_summary=None, binary=None):
    output.mkdir(parents=True)
    selected=list(roster(panel))
    expected={case["case"]:(identity,case,mode) for identity,case,mode,_ in selected}
    archived=manifest(directory)
    check(list(expected)==[r["case"] for r in archived] and len(archived)==COUNTS[panel],"frozen denominator differs")
    if public:
        from publish_founding_cohort_release import witnesses
        check({p.stem for p in directory.glob("*.zip")}==set(witnesses(panel)),"public witness roster changed")
        indexed = json.loads((directory.parent / "publication.json").read_bytes())[panel]
        check(indexed["verified_archives"] == len(archived) and indexed["public_witnesses"] == len(set(witnesses(panel)))
              and indexed["manifest_sha256"] == sha(directory / "archives.jsonl")
              and indexed["canonical_facts"] == sum(int((r["receipt"]["summary"] or {}).get("events", 0)) for r in archived),
              "public archive identity receipt changed")
    worlds,trajectories,failures,midpoints=[],[],[],[]
    event_output=output/"events"
    event_output.mkdir()
    comparisons={r["case"]:r["receipt"] for r in archived}
    for row in archived:
        path=directory/row["archive"]
        if public and not path.is_file(): continue
        identity,case,mode=expected[row["case"]]
        receipt=row["receipt"]
        check(sha(path)==row["sha256"],"archive SHA differs")
        with ZipFile(path) as source:
            check(set(source.namelist())=={"receipt.json",*receipt["artifacts"]} and
                  len(source.namelist())==len(receipt["artifacts"])+1,"wrong archive members")
            check(json.loads(source.read("receipt.json"))==receipt,"wrong archived run receipt")
            raw={key:source.read(key) for key in receipt["artifacts"]}
        check(all(sha256(data).hexdigest()==receipt["artifacts"][key]["sha256"] and len(data)==receipt["artifacts"][key]["bytes"]
                  for key,data in raw.items()),"archive member changed")
        check(raw["parameters.txt"]==input_bytes(identity,case) and json.loads(raw["case.json"])==case,"frozen input differs")
        if receipt["status"]!="COMPLETE":
            failures.append(dict(case=case["case"],status=receipt["status"],diagnostic=raw["program.log"].decode(errors="replace")))
            continue
        check(raw["initial.chk"][:7]==b"AWCKPTM" and unpack_from("<II",raw["initial.chk"],8)==(22,25 if case["hatch_cue"] else 26),
              "wrong biological contract")
        if mode!="observed":
            reference=comparisons[case["observed_case"]]
            check_identity(reference,receipt,case["case"])
            if mode=="durable-split":
                with ZipFile(directory/(case["observed_case"]+".zip")) as original, TemporaryDirectory(dir=output) as scratch:
                    midpoints.append(dict(case=case["case"],**verify_midpoint(raw["midpoint.sqlite"],raw["facts.bin"],receipt["summary"],
                                               rows(original.read("cuts.csv")),Path(scratch),fact_schema=9)))
            continue
        sample=case | dict(arm="integrated-"+case["source"],early_access_mask=3,carbohydrate_yield_nj_per_ug=8_000_000)
        summary=receipt["summary"]
        queen=int(summary["queen"])
        data,stages,paths,cohorts=assess(sample,summary,raw["facts.bin"],raw["cuts.csv"],raw["individuals.csv"],7,ecological=True)
        people,cuts=rows(raw["individuals.csv"]),rows(raw["cuts.csv"])
        activity,care=material_and_activity(raw["facts.bin"],cuts,case,rows(raw["geometry_edits.csv"]),check_sources=True)
        data |= activity | cohort_endpoints(stages,case["horizon_ms"],paths,cohorts,{r["ant"]:r for r in care})
        track,selected_events,maternal=follow_first(raw["facts.bin"],stages,people,queen,case["horizon_ms"],case["case"])
        check(sum("adult_ms" in r for r in track)==data["first_cohort_eclosed"] and
              all(r.get("first_opportunity_ms",r["hatch_ms"])>=r["hatch_ms"] for r in track),"first cohort lineage disagreement")
        check(case["hatch_cue"] or not maternal.get("hatch_cue_count"),"disabled hatch cue emitted a fact")
        data["first_cohort_eclosed_by_day55"]=sum(r.get("adult_ms",56*DAY)<=55*DAY for r in track)
        for rule in cohorts:
            name=rule["rule"]
            data |= {f"{name}_{key}":rule[key] for key in ("k","egg_d","larva_d","pupa_d","total_d")}
            data[f"{name}_timing_match"]=int(all(rule[k] is not None and a<=rule[k]<=b for k,(a,b) in
                zip(("egg_d","larva_d","pupa_d","total_d"),RANGES[case["population"]],strict=True)))
        if panel in ("extended","correction"):
            snapshots=defaultdict(list)
            for row in people:
                t=int(row["time_ms"])//DAY
                if t in (120,150): snapshots[t].append(row)
            chain,*_=observe_chain(raw["facts.bin"],sample,queen,paths,snapshots,maximum=WATER)
            chain = {"collections": 0, "deliveries": 0, "queen_gifts": 0} | chain
            data |= chain | {"joint":int(chain["complete"] and activity.get("soil_parcels",0)>0)}
            check(case["source"] not in ("absent","blocked") or not (chain["collections"] or chain["deliveries"]),"offsite stock crosses a control")
            check(case["source"]!="no-protein" or not chain["worker_protein_assimilated_lower_bound_ug"],"protein-free control acquired protein")
        denominator=data["first_census_larvae"]
        for label,key in (("first","first_cohort_eclosed"),("energy","first_cohort_energy_deaths"),("water","first_cohort_water_deaths"),
                          ("no_ration","first_cohort_no_ration")):
            data[f"{label}_rate"]=data[key]/denominator if denominator else None
        maternal["paid_maternal_energy_nj"]=maternal.get("paid_maternal_work_ms",0)*case["parameters"]["queen_active"]
        worlds.append(dict(case=case["case"],reference_case=case["reference_case"],panel=case["panel"],population=case["population"],
                           layout=case["layout"],seed=case["software_seed"],reserve=case["parameters"]["maternal_lipid"],source=case["source"],
                           **{k:case[k] for k in ("first_meal","activity_charge","recruitment","water_access","hatch_cue","repeat_feeding")},
                           **data,**(maternal | {"maternal_ration_water":maternal.get("total_ration_water_ug",0)})))
        trajectories.extend(track)
        if selected_events:
            csv_file=event_output/(case["case"]+".csv")
            write_csv(csv_file,selected_events)
            with csv_file.open("rb") as data, csv_file.with_suffix(".csv.gz").open("xb") as target:
                with gzip.GzipFile(fileobj=target,filename="",mode="wb",mtime=0) as archive:
                    archive.write(data.read())
            csv_file.unlink()
    if packed_summary:
        def keyed(table,keys):
            return {tuple(r[key] for key in keys):r for r in rows((packed_summary/(table+".csv")).read_bytes())}
        def matches(prior,value):
            if isinstance(value,float):
                return bool(prior) and isclose(float(prior),value,rel_tol=1e-13,abs_tol=1e-13)
            return prior==("" if value is None else str(value))
        for table,computed,keys in (("worlds",worlds,("case",)),("first_cohort",trajectories,("case","ant"))):
            saved=keyed(table,keys)
            for r in computed:
                prior=saved[tuple(str(r[key]) for key in keys)]
                check(all(matches(prior[key],value) for key,value in r.items()),
                      f"public {table} differs from reconstructed original events")
        prior_events = packed_summary / "events"
        check({p.name for p in event_output.iterdir()} == {p.name for p in prior_events.iterdir()},
              "public event witness missing")
        for file in event_output.iterdir():
            check(gzip.decompress(file.read_bytes()) == gzip.decompress((prior_events / file.name).read_bytes()),
                  "public event chain changed")
    for name, data in (("worlds",worlds),("first_cohort",trajectories)):
        if data: write_csv(output/(name+".csv"),data)
    write_json(output/"failures.json",failures)
    write_json(output/"midpoints.json",midpoints)
    if not public and panel in ("primary","hatch"):
        blocks,effects=paired_effects(panel,worlds)
        write_csv(output/"paired_blocks.csv",blocks)
        write_csv(output/"paired_effects.csv",effects)
    if binary:
        check(panel == "correction", "native replay is defined for the protected-profile panel")
        replay_correction(binary, selected, comparisons, output)
    print(f"{panel}: {len(worlds)} observed, {len(failures)} failures, {len(midpoints)} exact durable prefixes")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("panel",choices=tuple(COUNTS))
    parser.add_argument("input",type=Path)
    parser.add_argument("output",type=Path)
    parser.add_argument("--public",action="store_true")
    parser.add_argument("--packed-summary",type=Path)
    parser.add_argument("--binary",type=Path)
    parser.add_argument("--scout-binary",type=Path)
    args=parser.parse_args()
    verify(args.panel,args.input,args.output,args.public,args.packed_summary,args.binary)
    if args.scout_binary:
        replay_scout_controls(args.scout_binary,args.output)
