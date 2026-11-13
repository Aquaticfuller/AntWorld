"""Reconcile B06 census observations with known-age stage and nutritional exposure."""

import argparse
from collections import Counter, defaultdict
import csv
import gzip
from io import TextIOWrapper
from itertools import groupby
from pathlib import Path
from statistics import median
from zipfile import ZipFile

from analyze_s6_4_wp6b import census, check
from founding_qualification_witnesses import load, table
from run_integrated_founding import DAY, environments
from run_s6_4_wp6b import sha


def read(path):
    with path.open(encoding="utf-8",newline="") as stream:
        return list(csv.DictReader(stream))


def cohorts(world, paths, p):
    first_worker=int(world["first_worker_ms"] or 0)
    c,w=(int(world.get(k) or 0) for k in ("first_queen_carb_ms","first_queen_water_ms"))
    provisioned=max(c,w) if c and w else 0
    first_lay=int(world["first_egg_ms"] or 0)
    for ant, child in paths.items():
        birth=int(child["birth_ms"])
        phase=("opening" if birth<p["first_lay_delay_ms"]+p["opening_bout_width_ms"] else
               "pre_worker" if not first_worker or birth<=first_worker else
               "post_queen_cw" if provisioned and birth>provisioned else "worker_present_pre_queen_cw")
        check(birth>=first_lay,"offspring born before first egg")
        yield ant,phase


def simultaneously(stage_rows):
    changes=defaultdict(Counter)
    for stage in stage_rows:
        current=int(stage["stage"])
        changes[int(stage["enter_event"])][current]+=1
        if stage["end_event"]:
            changes[int(stage["end_event"])][current]-=1
    living, peak=Counter(),Counter()
    for _, delta in sorted(changes.items()):
        living.update(delta)
        check(min(living.values())>=0,"negative simultaneous stage count")
        for stage in delta:
            peak[stage]=max(peak[stage],living[stage])
    return peak


def diagnose(case, world, data, stages, paths, earlier):
    p=case["parameters"]
    waits, daily=defaultdict(Counter),[]
    q=int(next(iter(paths.values()))["mother"]) if paths else None
    stages_by_larva={int(r["ant"]):r for r in stages if r["stage"]=="1"}
    required_energy=p["pupa_basal"]*p["pupa_ms"]
    required_water=p["pupa_water_loss"]*p["pupa_ms"]
    counts=csv.DictReader(data)
    for key, group in groupby(counts,key=lambda r:r["time_ms"]):
        now=int(key)
        visible=Counter()
        for r in group:
            if not q or int(r["mother"])!=q:
                continue
            stage=int(r["stage"])
            visible[stage]+=1
            if stage!=1:
                continue
            ant=int(r["id"])
            if now<int(stages_by_larva[ant]["enter_ms"])+p["larva_ms"]:
                continue
            energy=int(r["energy_nj"])+int(r["lipid_ug"])*p["lipid_yield"]
            short_protein=int(r["tissue_protein_ug"])<p["larval_tissue_target"]
            short_energy=energy<=(required_energy+int(r["energy_carry"]))//DAY
            short_water=int(r["hydration_ug"])<=(required_water+int(r["water_carry"]))//DAY
            waits[ant]["waiting_cuts"]+=1
            waits[ant]["protein_short_cuts"]+=short_protein
            waits[ant]["energy_short_cuts"]+=short_energy
            waits[ant]["water_short_cuts"]+=short_water
            waits[ant]["multiple_short_cuts"]+=sum((short_protein,short_energy,short_water))>=2
            waits[ant]["fully_funded_cut"]+=not (short_protein or short_energy or short_water)
        daily.append((now,visible))
    check([x[0] for x in daily]==list(range(0,case["horizon_ms"]+1,DAY)),"missing daily census")
    rechecked={rule:census(daily,rule=="exact") for rule in ("at_least","exact")}
    for rule, result in rechecked.items():
        check(all(earlier[rule][key]==("" if value is None else str(value)) for key,value in result.items()),"frozen census changed")
    peak=simultaneously(stages)
    k=rechecked["exact"]["k"]
    found={stage:max(n[stage] for _,n in daily) for stage in (0,1,2,3)}
    metadata={key:world[key] for key in ("case","population","matrix","arm","profile","care","group","seed")}
    line=metadata | dict(k=k,first_egg_ms=world["first_egg_ms"],first_worker_ms=world["first_worker_ms"],
        queen_death_ms=world["queen_death_ms"],exact_complete=int(rechecked["exact"]["total_d"] is not None),
        at_least_complete=int(rechecked["at_least"]["total_d"] is not None),
        pupa_exact_seen=int(rechecked["exact"]["pupa_d"] is not None),pupa_at_least_seen=int(rechecked["at_least"]["pupa_d"] is not None),
        eggs_first_census=world["first_eggs_census"],larvae_with_wait_cut=len(waits),
        **{f"peak_stage_{stage}_{source}":data[stage] for source,data in (("daily",found),("event",peak)) for stage in (0,1,2,3)})
    for rule,result in rechecked.items():
        line.update({f"{rule}_{endpoint}":result[endpoint] for endpoint in ("egg_d","larva_d","pupa_d","total_d")})
    grouped=dict(cohorts(world,paths,p))
    exposures=[]
    for row in stages:
        stage=int(row["stage"])
        if stage==3:
            continue
        ant=int(row["ant"])
        clock=p[("egg_ms","larva_ms","pupa_ms")[stage]]
        elapsed=int(row["age_in_stage_ms"])
        wait=waits.get(ant,{}) if stage==1 else {}
        child=paths[ant]
        exposures.append(metadata | dict(ant=ant,phase=grouped[ant],stage=stage,enter_ms=row["enter_ms"],end_ms=row["end_ms"],
            end_event=row["end_event"],outcome=row["outcome"],elapsed_ms=elapsed,nominal_ms=clock,
            excess_elapsed_ms=max(0,elapsed-clock),
            **{key:wait.get(key,0) if stage==1 else None for key in ("waiting_cuts","protein_short_cuts","energy_short_cuts",
                 "water_short_cuts","multiple_short_cuts","fully_funded_cut")},
            **{key:child[key] if stage==1 else None for key in ("first_ration_delay_ms","ration_count","ration_protein_ug",
                 "larval_protein_uptake_ug","terminal_tissue_protein_ug")}))
    return line,exposures


def summarize(exposures):
    bins=defaultdict(list)
    for row in exposures:
        if row["matrix"]=="closed" and (row["group"]!="primary" or row["care"]!="1"):
            continue
        keys=(row["matrix"],row["population"],row["arm"],row["stage"])
        for phase in ("all",row["phase"]):
            bins[(*keys,phase)].append(row)
    for (matrix,pop,arm,stage,phase), data in sorted(bins.items()):
        by_outcome=Counter(r["outcome"] for r in data)
        transitioned=sorted(r["elapsed_ms"]/DAY for r in data if r["outcome"]=="TRANSITION")
        witnessed=[r for r in data if r["waiting_cuts"]]
        yield dict(matrix=matrix,population=pop,arm=arm,stage=stage,phase=phase,
            worlds=len({r["case"] for r in data}),entrants=len(data),transitioned=len(transitioned),
            died_energy=by_outcome["DEATH_1"],died_water=by_outcome["DEATH_2"],censored=by_outcome["RIGHT_CENSORED"],
            deaths_before_clock=sum(r["outcome"].startswith("DEATH_") and r["elapsed_ms"]<r["nominal_ms"] for r in data),
            deaths_at_or_after_clock=sum(r["outcome"].startswith("DEATH_") and r["elapsed_ms"]>=r["nominal_ms"] for r in data),
            transitions_later_than_clock=sum(r["outcome"]=="TRANSITION" and r["excess_elapsed_ms"]>0 for r in data),
            minimum_days=transitioned[0] if transitioned else None,median_days=median(transitioned) if transitioned else None,
            maximum_days=transitioned[-1] if transitioned else None,
            individuals_with_wait_cut=len(witnessed),
            **{key:sum(r[key]>0 for r in witnessed) for key in ("protein_short_cuts","energy_short_cuts","water_short_cuts",
               "multiple_short_cuts","fully_funded_cut")})


def analyze(raw, tables, output):
    output.mkdir(parents=True)
    world_rows, all_exposures=[],[]
    for matrix in ("closed","nominal","factorial"):
        batch=f"resupply-{matrix}"
        folder=raw/batch
        table_dir=tables/batch
        worlds={r["case"]:r for r in read(table_dir/"worlds.csv")}
        inputs={case["case"]:case for _,case in environments(matrix)}
        check(worlds.keys()==inputs.keys(),"world population differs")
        stages=defaultdict(list)
        for row in read(table_dir/"stages.csv"):
            stages[row["case"]].append(row)
        paths=defaultdict(dict)
        for row in read(table_dir/"offspring.csv"):
            paths[row["case"]][int(row["ant"])]=row
        censuses=defaultdict(dict)
        for row in read(table_dir/"censuses.csv"):
            censuses[row["case"]][row["rule"]]=row
        completed=load((folder/"completed.json").read_bytes())
        seen=set()
        for filename,digest in sorted(completed["archives"].items()):
            file=folder/filename
            check(sha(file)==digest,"original B06 cohort archive changed")
            with ZipFile(file) as bundle:
                for member in sorted(name for name in bundle.namelist() if name.endswith("/individuals.csv")):
                    case=member.split("/",1)[0]
                    check(case not in seen,"duplicate B06 cohort case")
                    seen.add(case)
                    with bundle.open(member) as binary, TextIOWrapper(binary,encoding="utf-8",newline="") as stream:
                        world,people=diagnose(inputs[case],worlds[case],stream,stages[case],paths[case],censuses[case])
                    world_rows.append(world)
                    all_exposures.extend(people)
        check(seen==inputs.keys(),"incomplete B06 cohort evidence")
        print(f"{batch}: {len(seen)} unchanged census pairs verified",flush=True)
    for name,data in (("census_diagnosis.csv",world_rows),("stage_summary.csv",list(summarize(all_exposures)))):
        (output/name).write_bytes(table(data))
    with (output/"stage_exposures.csv.gz").open("xb") as stream, gzip.GzipFile(fileobj=stream,mode="wb",mtime=0) as compressed:
        compressed.write(table(all_exposures))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for arg in ("raw","tables","output"):
        parser.add_argument(arg,type=Path)
    args=parser.parse_args()
    analyze(args.raw,args.tables,args.output)
