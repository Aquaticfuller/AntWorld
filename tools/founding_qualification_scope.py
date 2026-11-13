"""Run the frozen 180-day finite-resource pairs and audit the original day-150 authority."""

import argparse
from collections import defaultdict
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

from analyze_integrated_founding import located_facts, verify_sources
from analyze_s6_4_wp6b import BIRTH, COLLECTED, DELIVERED, F_BOUNDARY_UPTAKE, STAGE, UPTAKE, assess, check, rows
from founding_qualification_witnesses import COMMAND, REFERENCE, archive_members, load, table
from run_integrated_founding import DAY, environments
from run_s6_4_wp6b import git, run_one, sha, write_json


def cases():
    for matrix in ("nominal","factorial"):
        for identity, standard in environments(matrix):
            if standard["arm"]!="integrated-balanced" or (matrix=="factorial" and standard["profile_index"]!=10):
                continue
            for days in (120,60):
                yield matrix, identity, standard | dict(case=standard["case"]+f"-dose-{days}",
                    scope_reference=standard["case"],arm=f"scope-balanced-{days}",release_days=days,horizon_ms=180*DAY)


def reference_records():
    desired={case["scope_reference"] for _,_,case in cases()}
    with (REFERENCE/"world_receipts.jsonl").open(encoding="utf-8") as stream:
        records={}
        for line in stream:
            row=load(line)
            name=row["receipt"]["case"]
            if row["batch"] in ("resupply-nominal","resupply-factorial") and name in desired:
                records[name]=row["receipt"]
    check(records.keys()==desired,"missing original standard reference")
    return records


def collect(binary, output):
    output.mkdir(parents=True)
    write_json(output/"run.json",dict(source=git("rev-parse","HEAD"),cpp_tree=git("rev-parse","HEAD:cpp"),
        binary_sha256=sha(binary),arguments=COMMAND,protocol_sha256=sha(Path(__file__).resolve().parents[1]/
        "research/s6_4_founding_qualification/FROZEN_CLOSURE_PROTOCOL.md"),cases=[c["case"] for _,_,c in cases()]))
    receipts=[]
    for matrix, identity, case in cases():
        name=case["case"]
        with TemporaryDirectory(dir=output) as scratch:
            work=Path(scratch).resolve()/name
            receipt=run_one(binary,work,identity,case,"observed",COMMAND)
            archive=output/f"{name}.zip"
            with ZipFile(archive,"x",ZIP_DEFLATED,compresslevel=4) as bundle:
                for item in sorted(work.iterdir()):
                    bundle.write(item,f"{name}/{item.name}")
            receipts.append(dict(matrix=matrix,archive=archive.name,archive_sha256=sha(archive),receipt=receipt))
            print(name,receipt["status"],flush=True)
    write_json(output/"archives.json",receipts)


def verify_case(case, summary, raw, blobs, original):
    days=case["release_days"]
    same_authority=None
    if days==120:
        facts=original["artifacts"]["facts.bin"]
        check(sha256(memoryview(raw)[:facts["bytes"]]).hexdigest()==facts["sha256"],"150-day canonical prefix differs")
        same_authority="FACT_PREFIX_EXACT"
    case=case | dict(early_access_mask=3,carbohydrate_yield_nj_per_ug=8_000_000)
    measure,_,offspring,_=assess(case,summary,raw,blobs["cuts.csv"],blobs["individuals.csv"],7)
    cuts=rows(blobs["cuts.csv"])
    material=verify_sources(raw,case,cuts)
    positive_release=[]
    transfers=defaultdict(lambda: [0]*4)
    daily={}
    age_cuts=(60,120,150,180)
    reserve=(1500*days,750*days,4500*days,0)
    for event,_,_ in located_facts(raw):
        _,time,_,kind,actor,_,_,stage,_,amount,_=event
        if kind==37 and any(amount):
            positive_release.append(time)
            reserve=tuple(q-m for q,m in zip(reserve,amount,strict=True))
        if time>days*DAY:
            if kind in (COLLECTED,DELIVERED):
                key="collected" if kind==COLLECTED else "delivered"
                for i,m in enumerate(amount):
                    transfers[key][i]+=m
            elif kind in (UPTAKE,F_BOUNDARY_UPTAKE) and stage==3:
                key="queen_uptake" if actor==int(summary["queen"]) else "worker_uptake"
                for i,m in enumerate(amount):
                    transfers[key][i]+=m
            elif kind==BIRTH:
                transfers["births"][0]+=1
            elif kind==STAGE and stage==3:
                transfers["eclosed"][0]+=1
    check(positive_release==[i*DAY for i in range(1,days+1)] and not any(reserve),"positive release did not stop at the funded limit")
    people=rows(blobs["individuals.csv"])
    for day in age_cuts:
        at=day*DAY
        visible=[r for r in people if int(r["time_ms"])==at]
        queen=next(r for r in visible if r["id"]==summary["queen"])
        workers=[r for r in visible if r["stage"]=="3" and r["mother"]==summary["queen"]]
        alive=[r for r in visible if r["stage"]!="4"]
        cut=cuts[day]
        check(cut["time_ms"]==str(at),"scope daily census changed")
        if day==150 and days==120:
            check(cut["cursor"]==original["summary"]["events"] and cut["rng"]==original["summary"]["rng"],
                  "150-day event or RNG identity differs")
        daily[day]=dict(case=case["case"],day=day,release_days=days,queen_alive=int(queen["stage"]=="3"),
            living_workers=len(workers),queen_energy_nj=queen["energy_nj"],queen_hydration_ug=queen["hydration_ug"],
            queen_mobile_protein_ug=queen["mobile_protein_ug"],queen_lipid_ug=queen["lipid_ug"],
            **{f"{store}_{nutrient}_ug":cut[f"{store}_{nutrient}"] for store in ("available","nest") for nutrient in "cpwo"},
            **{f"reserve_{nutrient}_ug":max(0,days-day)*daily_dose for nutrient,daily_dose in zip("cpwo",(1500,750,4500,0),strict=True)},
            **{f"queen_crop_{nutrient}_ug":queen[f"crop_{nutrient}"] for nutrient in "cpwo"},
            **{f"living_crop_{nutrient}_ug":sum(int(r[f"crop_{nutrient}"]) for r in alive) for nutrient in "cpwo"})
    return dict(case=case["case"],population=case["population"],seed=case["software_seed"],profile=case.get("profile_index"),
        release_days=days,last_positive_release_ms=positive_release[-1],first_worker_ms=measure["first_worker_ms"],
        queen_death_ms=measure["queen_death_ms"],queen_death_cause=measure["queen_death_cause"],
        queen_alive_180=daily[180]["queen_alive"],workers_alive_180=daily[180]["living_workers"],fact_count=measure["source_facts"],
        births=measure["births"],hatch=measure["hatch"],pupation=measure["pupation"],eclosed=measure["eclosed"],
        post_release_births=transfers["births"][0],post_release_eclosed=transfers["eclosed"][0],
        post_release_born_and_eclosed=sum(p["birth_ms"]>days*DAY and p["adult_ms"] is not None for p in offspring),
        **{f"post_release_{name}_{part}_ug":mass for name in ("collected","delivered","queen_uptake","worker_uptake")
           for part,mass in zip("cpwo",transfers[name],strict=True)},
        day150_reference=same_authority,**material),daily.values()


def analyze(raw, output):
    manifest=load((raw/"archives.json").read_bytes())
    expected=list(cases())
    check(len(expected)==len(manifest)==48,"scope assay denominator changed")
    references=reference_records()
    result, cuts=[],[]
    for (matrix, identity, case), row in zip(expected,manifest,strict=True):
        receipt=row["receipt"]
        check(row["matrix"]==matrix and (receipt["case"],receipt["identity"])==(case["case"],identity),"scope case mismatch")
        original=references[case["scope_reference"]]
        check(receipt["status"]=="COMPLETE","scope execution did not complete")
        file=raw/row["archive"]
        check(sha(file)==row["archive_sha256"],"scope archive bytes changed")
        blobs=archive_members(file,case["case"],receipt)
        check(load(blobs["case.json"])==case,"scope input changed")
        world,daily=verify_case(case,receipt["summary"],blobs["facts.bin"],blobs,original)
        result.append(world | dict(matrix=matrix,archive_sha256=row["archive_sha256"]))
        cuts.extend(daily)
        print(case["case"],world["queen_alive_180"],world["workers_alive_180"],flush=True)
    output.mkdir(parents=True,exist_ok=True)
    for name,data in (("worlds.csv",result),("resource_cuts.csv",cuts)):
        (output/name).write_bytes(table(data))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw",type=Path)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--binary",type=Path)
    group.add_argument("--analyze",type=Path)
    args=parser.parse_args()
    if args.binary:
        collect(args.binary.resolve(strict=True),args.raw)
    else:
        analyze(args.raw,args.analyze)


if __name__=="__main__":
    main()
