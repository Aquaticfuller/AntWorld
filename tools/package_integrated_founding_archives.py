"""Index full local archive batches and publish deterministic case receipts and witnesses."""

import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path
import zipfile

from analyze_integrated_founding import check
from run_integrated_founding import MODELS, environments
from run_s6_4_wp6b import sha, write_json


REPRESENTATIVE_SEED = 1
REPRESENTATIVE_ARMS = {"integrated-balanced", "integrated-blocked"}


def selection(arm, case):
    if case["software_seed"]!=REPRESENTATIVE_SEED:
        return False
    if arm=="resupply-factorial":
        return case.get("profile_index")==10 and case["arm"] in REPRESENTATIVE_ARMS
    return arm in {"diet-nominal","uptake-nominal","resupply-nominal"} and case["arm"] in REPRESENTATIVE_ARMS


def sources(root):
    for folder in sorted(root.iterdir()):
        if not folder.is_dir() or not (folder/"completed.json").is_file():
            continue
        model, matrix = folder.name.rsplit("-",1)
        if model in MODELS and matrix in {"nominal","factorial","closed"}:
            yield folder


def package(raw, published, audits):
    batches=list(sources(raw))
    audit_paths={}
    if audits:
        for folder in batches:
            audit_paths[folder.name]=next((root/f"analysis-{folder.name}/audit.json" for root in audits
                                          if (root/f"analysis-{folder.name}/audit.json").is_file()),None)
    published.mkdir(parents=True)
    index, all_cases = [], []
    for folder in batches:
        model, matrix = folder.name.rsplit("-",1)
        universe = {case["case"]:case for _,case in environments(matrix)}
        meta, end = (json.loads((folder/name).read_text(encoding="utf-8")) for name in ("run.json","completed.json"))
        seen, witnesses = set(), {}
        manifest = published / folder.name
        manifest.mkdir()
        for name in ("run.json", "completed.json"):
            (manifest/name).write_bytes((folder/name).read_bytes())
        checked_bytes = 0
        for name, digest in sorted(end["archives"].items()):
            archive = folder / name
            check(sha(archive)==digest, f"full local archive checksum changed: {archive}")
            checked_bytes += archive.stat().st_size
            with zipfile.ZipFile(archive) as data:
                for member in sorted(item for item in data.namelist() if item.endswith("/receipt.json")):
                    case_name = member.split("/",1)[0]
                    check(case_name not in seen and case_name in universe,"duplicate or unknown world receipt")
                    seen.add(case_name)
                    receipt = json.loads(data.read(member))
                    check(receipt["case"]==case_name and receipt["status"]==end["statuses"][case_name],"mismatched world receipt")
                    all_cases.append(dict(batch=folder.name, archive=name, receipt=receipt))
                    if selection(folder.name,universe[case_name]):
                        witness = manifest / f"{case_name}.zip"
                        with zipfile.ZipFile(witness,"x",zipfile.ZIP_DEFLATED,compresslevel=6) as subset:
                            for part in sorted(item for item in data.namelist() if item.startswith(case_name+"/")):
                                raw_bytes = data.read(part)
                                artifact=part.split("/",1)[1]
                                if part!=member:
                                    check(receipt["artifacts"][artifact]==dict(bytes=len(raw_bytes),sha256=sha256(raw_bytes).hexdigest()),
                                          "published representative has changed bytes")
                                subset.writestr(part,raw_bytes)
                        witnesses[witness.name] = sha(witness)
        check(seen==set(meta["cases"])==end["statuses"].keys(),"case coverage changed")
        audit_path=audit_paths.get(folder.name)
        if audit_path:
            evidence=json.loads(audit_path.read_text(encoding="utf-8"))
            check(evidence["audited_attempts"]==evidence["input_attempts"]==len(seen),"archive lacks a complete fact audit")
            (manifest/"audit.json").write_bytes(audit_path.read_bytes())
        index.append(dict(batch=folder.name,cases=len(seen),bytes=checked_bytes,files=len(end["archives"]),
                          run_sha256=sha(manifest/"run.json"),complete_sha256=sha(manifest/"completed.json"),
                          audit_sha256=sha(audit_path) if audit_path else None,witnesses=witnesses))
    with (published/"world_receipts.jsonl").open("x",encoding="utf-8",newline="\n") as stream:
        for row in all_cases:
            stream.write(json.dumps(row,sort_keys=True,separators=(",",":"))+"\n")
    write_json(published/"index.json",dict(attempts=len(all_cases),archive_batches=index,world_receipts_sha256=sha(published/"world_receipts.jsonl")))
    with (published/"summary.csv").open("x",encoding="utf-8",newline="") as stream:
        table=csv.DictWriter(stream,("batch","cases","bytes","files","run_sha256","complete_sha256"),extrasaction="ignore",lineterminator="\n")
        table.writeheader()
        table.writerows(index)
    print(f"{len(all_cases)} cases and {sum(row['files'] for row in index)} full local archives verified")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw",type=Path)
    parser.add_argument("published",type=Path)
    parser.add_argument("--audits",type=Path,action="append",default=[])
    args=parser.parse_args()
    package(args.raw,args.published,args.audits)
