"""Publish the frozen raw witness panel alongside complete local archive receipts."""

import argparse
import gzip
from pathlib import Path
import shutil

from analyze_s6_4_wp6b import check
from run_s6_4_wp6b import sha, write_json
from verify_ecological_closure import fixed_witnesses, frozen_names
from verify_ecological_publication import manifest


def publish(scratch, local, output):
    output.mkdir(parents=True,exist_ok=True)
    sources = (("scout","scout",local/"scout","scout-final"),
               ("care","care",scratch/"care","care-public"),
               ("joint-original","joint",scratch/"joint","joint-original-final"),
               ("joint-expanded","joint",scratch/"joint-expanded","joint-expanded-complete"),
               ("joint-repaired","joint",scratch/"joint-repaired","joint-repaired-complete"))
    for name,panel,raw,analysis in sources:
        destination = output/name
        destination.mkdir()
        attempts = manifest(raw)
        check([r["case"] for r in attempts] == frozen_names(panel), "cannot publish an incomplete roster")
        failures = [r["case"] for r in attempts if r["receipt"]["status"]!="COMPLETE"]
        selected = (fixed_witnesses(panel) if name in {"scout","care","joint-repaired"} else
                    set(failures[:1]) if name=="joint-original" else set())
        check(selected <= {r["case"] for r in attempts},"missing fixed witness")
        shutil.copyfile(raw/"run.json",destination/"run.json")
        shutil.copyfile(raw/"archives.jsonl",destination/"archives.jsonl")
        for row in attempts:
            witness = raw/row["archive"]
            check(sha(witness)==row["sha256"],f"local archive digest changed: {witness.name}")
            if row["case"] in selected:
                shutil.copyfile(witness,destination/witness.name)
        (destination/"analysis").mkdir()
        for artifact in sorted((local/analysis).iterdir()):
            if artifact.suffix not in {".csv",".json"}:
                continue
            target = destination/"analysis"/artifact.name
            if artifact.stem in {"larvae","receivers","stages"}:
                with target.with_suffix(".csv.gz").open("xb") as compressed, artifact.open("rb") as stream:
                    with gzip.GzipFile(fileobj=compressed,mode="wb",filename="",mtime=0) as archive:
                        shutil.copyfileobj(stream,archive)
            else:
                shutil.copyfile(artifact,target)
        check((destination/"analysis/worlds.csv").is_file(),"missing independent outcome calculation")
    shutil.copytree(local/"timing",output/"timing")
    write_json(output/"local_archive_hash_audit.json",{
        name: {"manifest_sha256":sha(output/name/"archives.jsonl"),
               "verified_archives":len(frozen_names(panel))}
        for name,panel,_,_ in sources})


if __name__=="__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scratch",type=Path)
    parser.add_argument("local",type=Path)
    parser.add_argument("output",type=Path)
    args=parser.parse_args()
    publish(args.scratch,args.local,args.output)
