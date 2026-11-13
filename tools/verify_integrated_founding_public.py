"""Verify the public index, every world receipt and selected original event streams."""

import argparse
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
import zipfile

from analyze_integrated_founding import check, located_facts
from run_integrated_founding import MODELS, SENSITIVITIES, environments
from run_s6_4_wp6b import input_bytes, sha


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def verify(path):
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
    check(len(index["archive_batches"])==len(records),"batch manifest coverage changed")
    witnesses=0
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
    check(sum(map(len,records.values()))==index["attempts"],"global world denominator changed")
    check(witnesses==16,"published witness coverage changed")
    print(f"{index['attempts']} world receipts, {len(records)} batches and {witnesses} canonical witnesses verified")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive",type=Path)
    verify(parser.parse_args().archive)
