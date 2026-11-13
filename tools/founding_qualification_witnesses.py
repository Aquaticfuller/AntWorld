"""Publish original case members and independently verify facts and interrupted SQLite continuation."""

import argparse
import csv
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

from analyze_integrated_founding import observe_chain, verify_sources
from analyze_s6_4_wp6b import assess, check, rows
from run_integrated_founding import DAY, MODELS, NOMINAL, environments
from run_s6_4_wp6b import ROOT, git, input_bytes, sha, write_json


BASELINE = "a0dc086f6d1b8f5601d743dbcbc1274d073e252e"
REFERENCE = ROOT / "experiments/s6_4_integrated_founding/raw_index"
EXISTING = {
    ("nominal", "borisovka-micro-nominal-0-1-balanced"),
    ("nominal", "st_petersburg-micro-nominal-0-1-balanced"),
    ("nominal", "borisovka-micro-nominal-0-1-blocked"),
}
SELECTION = EXISTING | {
    ("factorial", "borisovka-10-primary-7-on-balanced"),
    ("factorial", "borisovka-10-primary-43-on-balanced"),
    ("nominal", "borisovka-micro-nominal-0-1-absent"),
    ("nominal", "st_petersburg-micro-nominal-0-1-no-protein"),
    ("nominal", "borisovka-micro-nominal-0-1-limited"),
}
EXPECTED = {
    "borisovka-micro-nominal-0-1-balanced": (1, None),
    "st_petersburg-micro-nominal-0-1-balanced": (1, None),
    "borisovka-10-primary-7-on-balanced": (0, 1),
    "borisovka-10-primary-43-on-balanced": (0, 1),
    "borisovka-micro-nominal-0-1-blocked": (0, 2),
    "borisovka-micro-nominal-0-1-absent": (0, 2),
    "st_petersburg-micro-nominal-0-1-no-protein": (0, None),
    "borisovka-micro-nominal-0-1-limited": (0, 1),
}
INTERRUPTED_CASE = "borisovka-micro-nominal-0-1-balanced"
COMMAND = [*map(str, NOMINAL), "0", "3", *MODELS["resupply"]]
SOURCE_FIELDS = ("event_id", "time_ms", "scheduled_id", "kind", "actor_id", "resource_id", "x_m", "y_m", "z_m",
                 *(f"{label}_{ingredient}_ug" for label in ("event", "reserve", "site", "actor_cargo") for ingredient in "cpwo"))


def load(data):
    return json.loads(data)


def reference_records():
    result = {}
    index = load((REFERENCE/"index.json").read_bytes())
    with (REFERENCE/"world_receipts.jsonl").open(encoding="utf-8") as stream:
        for line in stream:
            row=load(line)
            for matrix in ("nominal", "factorial"):
                key=matrix,row["receipt"]["case"]
                if row["batch"]=="resupply-"+matrix and key in SELECTION:
                    result[key]=row
    check(result.keys()==SELECTION,"reference receipt lacks a frozen external case")
    return result,{row["batch"]:row for row in index["archive_batches"]}


def archive_members(path, case, record):
    prefix=case+"/"
    with ZipFile(path) as archive:
        names={name.removeprefix(prefix) for name in archive.namelist() if name.startswith(prefix)}
        check(names==record["artifacts"].keys()|{"receipt.json"},"changed witness member inventory")
        blobs={name:archive.read(prefix+name) for name in names}
    check(load(blobs["receipt.json"])==record,"changed original case receipt")
    for name, proof in record["artifacts"].items():
        check(proof==dict(bytes=len(blobs[name]),sha256=sha256(blobs[name]).hexdigest()),f"changed {case}/{name}")
    return blobs


def analyze(matrix, case_name, original, blobs):
    identity, case = next((i,c) for i,c in environments(matrix) if c["case"]==case_name)
    check(original["status"]=="COMPLETE" and load(blobs["case.json"])==case and
          blobs["parameters.txt"]==input_bytes(identity,case),"witness input differs from preregistered case")
    case=case | dict(early_access_mask=3,carbohydrate_yield_nj_per_ug=8_000_000)
    summary=original["summary"]
    raw=blobs["facts.bin"]
    measure, stages, paths, _=assess(case,summary,raw,blobs["cuts.csv"],blobs["individuals.csv"],7)
    people=rows(blobs["individuals.csv"])
    snapshots={day:[r for r in people if int(r["time_ms"])==day*DAY] for day in (120,150)}
    source_rows=[]

    def source(event, resource, position, reserve, stock, cargo):
        event_id, time, scheduled, kind, actor, _, _, _, _, mass, _=event
        source_rows.append(dict(event_id=event_id,time_ms=time,scheduled_id=scheduled,kind=kind,actor_id=actor,
            resource_id=resource,x_m=position[0],y_m=position[1],z_m=position[2],
            **{f"{label}_{part}_ug":qty for label,values in (("event",mass),("reserve",reserve),("site",stock),("actor_cargo",cargo))
               for part,qty in zip("cpwo",values,strict=True)}))

    material=verify_sources(raw,case,rows(blobs["cuts.csv"]),source)
    chain, workers, trips, _=observe_chain(raw,case,int(summary["queen"]),paths,snapshots)
    check((chain["complete"],measure["queen_death_cause"])==EXPECTED[case_name],
          "external witness no longer supports its declared endpoint")
    verdict=dict(case=case_name,world=summary["world"],facts=measure["source_facts"],births=measure["births"],
                 hatch=measure["hatch"],pupation=measure["pupation"],eclosed=measure["eclosed"],
                 queen_death_ms=measure["queen_death_ms"],queen_death_cause=measure["queen_death_cause"],
                 stage_exposures=len(stages),workers=len(workers),trips=len(trips),source_transactions=len(source_rows),
                 **{k:v for k,v in chain.items() if k.startswith("g_") or k in ("complete","queen_alive_150","workers_censored")},
                 **material)
    return verdict, source_rows, stages


def table(records, fields=None):
    if fields is None and not records:
        return b""
    text=StringIO(newline="")
    out=csv.DictWriter(text,fields if fields is not None else tuple(records[0]),lineterminator="\n")
    out.writeheader()
    out.writerows(records)
    return text.getvalue().encode()


def witness_path(output, matrix, name):
    return (REFERENCE/f"resupply-{matrix}" if (matrix,name) in EXISTING else output)/f"{name}.zip"


def witnesses(output, local=None):
    selected, index=reference_records()
    records, life_stages=[],[]
    for (matrix,name), row in sorted(selected.items()):
        batch=row["batch"]
        path=witness_path(output,matrix,name)
        original=row["receipt"]
        manifest=REFERENCE/batch/"completed.json"
        check(sha(manifest)==index[batch]["complete_sha256"],"reference manifest changed")
        source_digest=load(manifest.read_bytes())["archives"][row["archive"]]
        if (matrix,name) in EXISTING:
            check(sha(path)==index[batch]["witnesses"][path.name],"published baseline witness changed")
        elif local:
            source=local/batch/row["archive"]
            check(sha(source)==source_digest,"original complete archive changed")
            blobs=archive_members(source,name,original)
            with ZipFile(path,"x",ZIP_DEFLATED,compresslevel=4) as archive:
                for filename, content in sorted(blobs.items()):
                    archive.writestr(name+"/"+filename,content)
        blobs=archive_members(path,name,original)
        verdict, source_rows, stages=analyze(matrix,name,original,blobs)
        record=dict(matrix=matrix,case=name,witness_sha256=sha(path),full_batch_archive=row["archive"],
                    full_batch_archive_sha256=source_digest,**{k:v for k,v in verdict.items() if k!="case"})
        records.append(record)
        life_stages.extend(stages)
        transactions=output/f"{name}-source.csv"
        if local:
            transactions.write_bytes(table(source_rows,SOURCE_FIELDS))
        else:
            check(transactions.read_bytes()==table(source_rows,SOURCE_FIELDS),"reconstructed transactions differ")
    for name,data in (("cases.csv",records),("life_stages.csv",life_stages)):
        summary=output/name
        if local:
            summary.write_bytes(table(data))
        else:
            check(summary.read_bytes()==table(data),f"reconstructed {name} differs")
    print(f"{len(records)} original full witnesses, {sum(r['facts'] for r in records)} canonical facts and ledger checks passed")


def interrupted(binary, output, published=None):
    source=REFERENCE/"resupply-nominal"/f"{INTERRUPTED_CASE}.zip"
    reference=reference_records()[0]["nominal",INTERRUPTED_CASE]["receipt"]
    blobs=archive_members(source,INTERRUPTED_CASE,reference)
    inputs=output/"parameters.txt"
    inputs.write_bytes(blobs["parameters.txt"])
    launch=output/"interrupted"
    launch.mkdir()
    result=subprocess.run([binary,inputs,launch,"interrupt-save",*COMMAND],capture_output=True,check=False)
    check(result.returncode==78 and not result.stdout and not result.stderr,"child failed before the declared interruption")
    original=("midpoint.sqlite","midpoint.sqlite-wal","published.frame","interruption.csv")
    fresh={name:(launch/name).read_bytes() for name in original}
    if published:
        archive=published/"interrupted_day75.zip"
        with ZipFile(archive,"x",ZIP_DEFLATED,compresslevel=4) as z:
            for name, data in fresh.items():
                z.writestr(name,data)
    return verify_recovery(binary,output/"reopened",inputs,reference,fresh)


def verify_recovery(binary, destination, inputs, reference, artifacts):
    destination.mkdir()
    database=destination/"midpoint.sqlite"
    for name in ("midpoint.sqlite","midpoint.sqlite-wal"):
        (destination/name).write_bytes(artifacts[name])
    subprocess.run([binary,inputs,destination,"resume-save",*COMMAND,database],check=True)
    reopened,=rows((destination/"resumed.csv").read_bytes())
    marker,=rows(artifacts["interruption.csv"])
    check(marker["attempted_time_ms"]==str(76*DAY) and reopened["generation"]==marker["published_generation"]=="1" and
          reopened["cursor"]==marker["published_cursor"] and reopened["midpoint_ms"]==str(75*DAY),"published generation drift")
    check((destination/"restored_midpoint.frame").read_bytes()==artifacts["published.frame"],"interrupted frame differs")
    check(all(reopened[key]==reference["summary"][key] for key in ("time_ms","state_hash","trace_hash","rng","events")),
          "resumed world continuation differs")
    for name in ("facts.bin","final.frame"):
        check(sha(destination/name)==reference["artifacts"][name]["sha256"],"resumed canonical bytes differ")
    return dict(result=reopened,marker=marker,case=INTERRUPTED_CASE,exit_code=78,
                artifacts={name:dict(bytes=len(data),sha256=sha256(data).hexdigest()) for name,data in artifacts.items()},
                final={name:sha(destination/name) for name in ("facts.bin","final.frame")})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("witnesses",type=Path)
    parser.add_argument("--local-originals",type=Path)
    parser.add_argument("--binary",type=Path,required=True)
    parser.add_argument("--scratch",type=Path,required=True)
    args=parser.parse_args()
    args.scratch.mkdir(parents=True,exist_ok=True)
    args.witnesses.mkdir(parents=True,exist_ok=True)
    witnesses(args.witnesses,args.local_originals)
    binary=args.binary
    if not binary.is_file():
        binary=binary.parent/"Release"/(binary.stem+".exe")
    binary=binary.resolve(strict=True)
    with TemporaryDirectory(dir=args.scratch) as folder:
        work=Path(folder)
        fresh=interrupted(binary,work,args.witnesses if args.local_originals else None)
        if args.local_originals:
            write_json(args.witnesses/"interruption_receipt.json",dict(fresh,archive_sha256=sha(args.witnesses/"interrupted_day75.zip"),
                       source=git("rev-parse","HEAD"),binary_sha256=sha(binary),reference=BASELINE))
        else:
            committed=load((args.witnesses/"interruption_receipt.json").read_bytes())
            archive=args.witnesses/"interrupted_day75.zip"
            check(sha(archive)==committed["archive_sha256"] and committed["reference"]==BASELINE,"wrong interrupted witness archive")
            with ZipFile(archive) as z:
                members={name:z.read(name) for name in z.namelist()}
            reference=reference_records()[0]["nominal",INTERRUPTED_CASE]["receipt"]
            restored=verify_recovery(binary,work/"published",work/"parameters.txt",reference,members)
            check(all(restored[k]==committed[k] for k in restored) and fresh["result"]==restored["result"],
                  "published interruption or independent crash disagrees")
    print("Interrupted day-76 publication recovered the exact day-75 generation and day-150 authority")


if __name__=="__main__":
    main()
