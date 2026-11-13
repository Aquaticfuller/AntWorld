"""Package fixed complete witnesses and independently rebuilt outcomes."""

import argparse
import json
from pathlib import Path
import shutil

from analyze_s6_4_wp6b import check
from run_founding_cohort_release import COUNTS, manifest, roster
from run_s6_4_wp6b import sha, write_json


def witnesses(panel):
    for _,case,mode,_ in roster(panel):
        if case["software_seed"]!=1:
            continue
        pop, layout = case["population"],case["layout"]
        if (pop,layout) not in {("borisovka","shaft"),("st_petersburg","dogleg")}:
            continue
        nominal=case["parameters"]["maternal_lipid"]==5500
        if panel=="primary" and case["activity_charge"] and case["recruitment"]:
            yield case["case"]
        elif panel=="hatch" and pop=="borisovka":
            yield case["case"]
        elif panel=="extended" and nominal and case["source"]=="balanced" and mode=="observed":
            yield case["case"]
        elif panel=="correction" and nominal and (
            case["source"]=="balanced" or (pop=="borisovka" and case["source"] in {"blocked","absent","no-protein"}) or
            (pop=="st_petersburg" and case["source"]=="limited")):
            yield case["case"]


def publish(source, output):
    output.mkdir(parents=True)
    receipt={}
    for panel,count in COUNTS.items():
        dest=output/panel
        dest.mkdir()
        index=manifest(source/panel)
        expected=[c["case"] for _,c,_,_ in roster(panel)]
        check(len(index)==count and [r["case"] for r in index]==expected,"cannot publish an incomplete roster")
        chosen=set(witnesses(panel))
        for row in index:
            native=source/panel/row["archive"]
            check(sha(native)==row["sha256"],"archive changed before publication")
            if row["case"] in chosen:
                shutil.copyfile(native,dest/native.name)
        for name in ("run.json","archives.jsonl"):
            shutil.copyfile(source/panel/name,dest/name)
        analysis=source/f"final-analysis-{panel}"
        if not analysis.is_dir():
            analysis=source/f"verified-{panel}"
        reduced=dest/"analysis"
        reduced.mkdir()
        for path in analysis.iterdir():
            if path.is_file(): shutil.copyfile(path,reduced/path.name)
        event_samples=reduced/"events"
        event_samples.mkdir()
        for case in sorted(chosen):
            path=analysis/"events"/(case+".csv.gz")
            if path.exists():
                shutil.copyfile(path,event_samples/path.name)
        receipt[panel]=dict(verified_archives=len(index),public_witnesses=len(chosen),
                            manifest_sha256=sha(dest/"archives.jsonl"),failures=json.loads((analysis/"failures.json").read_bytes()))
    write_json(output/"publication.json",receipt)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source",type=Path)
    parser.add_argument("output",type=Path)
    args=parser.parse_args()
    publish(args.source,args.output)
