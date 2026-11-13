"""Verify the public index, every world receipt and selected original event streams."""

import argparse
from collections import defaultdict
import csv
from hashlib import sha256
import json
from pathlib import Path
import zipfile

from analyze_integrated_founding import check, located_facts
from run_integrated_founding import MODELS, SENSITIVITIES, environments
from run_s6_4_wp6b import input_bytes, sha


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def verify_audit(folder, receipt, manifest):
    for name in ("audit.json", "worlds.csv", "censuses.csv"):
        check(sha(folder/name)==manifest[f"{Path(name).stem}_sha256"], "published analysis file changed")
    audit, worlds = load(folder/"audit.json"), read_csv(folder/"worlds.csv")
    check(len(worlds)==audit["audited_attempts"]==audit["input_attempts"]==len(receipt) and
          {row["case"] for row in worlds}==receipt.keys(), "published analysis coverage changed")
    facts = 0
    for row in worlds:
        original = receipt[row["case"]]["receipt"]
        check(row["status"]==original["status"] and int(row["exit_code"])==original["exit_code"], "analysis status differs from original receipt")
        if row["status"]=="COMPLETE":
            count = int(row["source_facts"])
            check(count==int(original["summary"]["events"]), "analysis fact count differs from original receipt")
            if row.get("canonical_sha256"):
                check(row["canonical_sha256"]==original["artifacts"]["facts.bin"]["sha256"], "analysis fact identity differs")
            facts += count
    check(facts==audit["checked_facts"] and sum(int(row["complete"]) for row in worlds)==audit["complete_worlds"],
          "published audit totals differ from world tables")
    return facts


def verify(path, analysis=None):
    index = load(path/"index.json")
    file = path/"world_receipts.jsonl"
    check(sha(file)==index["world_receipts_sha256"],"world receipt manifest mismatch")
    records=defaultdict(dict)
    with file.open(encoding="utf-8") as stream:
        for line in stream:
            row=json.loads(line)
            case=row["receipt"]["case"]
            check(case not in records[row["batch"]],"duplicate archived world")
            records[row["batch"]][case]=row
    expected = {
        "nominal":set(MODELS),
        "factorial":{"r2","both","diet","uptake","resupply"},
        "closed":{"diet","uptake","resupply"},
    }
    check(set(records)=={f"{model}-{matrix}" for matrix,models in expected.items() for model in models},"batch scope changed")
    check(len(index["archive_batches"])==len(records) and
          {batch["batch"] for batch in index["archive_batches"]}==records.keys(),"batch manifest coverage changed")
    witnesses, audited_facts = 0, 0
    if analysis:
        entries = read_csv(analysis/"audit_index.csv")
        manifests = {row["batch"]:row for row in entries}
        check({folder.name for folder in analysis.iterdir() if folder.is_dir()}==records.keys(), "published audit inventory changed")
        check(len(entries)==len(manifests) and manifests.keys()==records.keys(), "published audit index changed")
    for batch in index["archive_batches"]:
        folder=path/batch["batch"]
        model,matrix=folder.name.rsplit("-",1)
        check(sha(folder/"run.json")==batch["run_sha256"] and sha(folder/"completed.json")==batch["complete_sha256"],"batch receipt hash changed")
        run,complete=load(folder/"run.json"),load(folder/"completed.json")
        official={case["case"]:(identity,case) for identity,case in environments(matrix)
                  if model not in SENSITIVITIES or case["arm"]=="integrated-balanced"}
        receipt=records[folder.name]
        check(batch["cases"]==len(receipt)==complete["attempts"] and len(complete["archives"])==batch["files"] and
              set(run["cases"])==receipt.keys()==complete["statuses"].keys()==official.keys(),"case inventory changed")
        if batch["audit_sha256"]:
            audit=folder/"audit.json"
            check(sha(audit)==batch["audit_sha256"] and load(audit)["audited_attempts"]==len(receipt),"full fact audit mismatch")
        check(run["arguments"][4:]==list(MODELS[model]),"model identity changed")
        for name,row in receipt.items():
            record=row["receipt"]
            check(row["archive"] in complete["archives"] and record["identity"]==official[name][0] and
                  record["status"]==complete["statuses"][name],"archive membership mismatch")
            if record["status"]=="COMPLETE":
                check(record["exit_code"]==0 and int(record["summary"]["time_ms"])==official[name][1]["horizon_ms"],"partial world marked complete")
        for name,digest in batch["witnesses"].items():
            file=folder/name
            case_name=file.stem
            check(sha(file)==digest and case_name in receipt,"published witness mismatch")
            record=receipt[case_name]["receipt"]
            with zipfile.ZipFile(file) as archive:
                root=case_name+"/"
                for member,expected in record["artifacts"].items():
                    content=archive.read(root+member)
                    check(len(content)==expected["bytes"] and sha256(content).hexdigest()==expected["sha256"],"published fact member changed")
                identity,case=official[case_name]
                check(archive.read(root+"parameters.txt")==input_bytes(identity,case),"physical input changed")
                if record["status"]=="COMPLETE":
                    count=sum(1 for _ in located_facts(archive.read(root+"facts.bin")))
                    check(count==int(record["summary"]["events"]),"canonical fact count differs")
            witnesses+=1
        if analysis:
            manifest = manifests[folder.name]
            check(manifest["completed_sha256"]==batch["complete_sha256"], "analysis uses a different original archive")
            audited_facts += verify_audit(analysis/folder.name,receipt,manifest)
    check(sum(map(len,records.values()))==index["attempts"],"global world denominator changed")
    check(witnesses==16,"published witness coverage changed")
    print(f"{index['attempts']} world receipts, {len(records)} batches and {witnesses} canonical witnesses verified")
    if analysis:
        print(f"{audited_facts} canonical fact counts reconciled across published audits")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive",type=Path)
    parser.add_argument("--analysis",type=Path)
    args=parser.parse_args()
    verify(args.archive,args.analysis)
