"""Replay the accepted 2,184 v1 and R1 worlds without duplicating their original archives."""

import argparse
from pathlib import Path
from tempfile import TemporaryDirectory

from analyze_s6_4_wp6b import check
from founding_qualification_witnesses import load
from run_s6_4_wp6b import ROOT, git, run_one, sha, write_json
from run_s6_4_wp6b_r1 import EXACT, enumerate_cases


def replay(binary, output, scratch):
    reference=ROOT/"experiments/s6_4_integrated_founding/replay"
    scratch.mkdir(parents=True,exist_ok=True)
    output.mkdir(parents=True)
    for model in ("v1","r1"):
        path=reference/f"legacy-{model}-completed.json"
        prior=load(path.read_bytes())["statuses"]
        check(len(prior)==1092 and all(r["exact"] for r in prior.values()),"accepted legacy work differs")
        receipts={}
        for identity,case in enumerate_cases(model):
            name=case["case"]
            if name not in prior:
                continue
            with TemporaryDirectory(dir=scratch) as location:
                flags=tuple(map(str,case.get("care_memory",())))
                row=run_one(binary,Path(location).resolve()/"case",identity,case,"observed",flags)
                actual={key:row["artifacts"].get(key) for key in EXACT}
                previous=prior[name]
                receipts[name]=dict(status=row["status"],exit_code=row["exit_code"],elapsed_ms=row["elapsed_ms"],
                    exact=actual==previous["signature"] and row["status"]==previous["status"],signature=actual)
        write_json(output/f"{model}.json",dict(source=git("rev-parse","HEAD"),binary_sha256=sha(binary),
            reference_sha256=sha(path),statuses=receipts,attempts=len(receipts)))
        check(receipts.keys()==prior.keys() and all(r["exact"] for r in receipts.values()),"legacy authority mismatch")
        print(f"{model}: {len(receipts)} canonical, state and census identities",flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("binary","output","scratch"):
        parser.add_argument(name,type=Path)
    args=parser.parse_args()
    replay(args.binary.resolve(strict=True),args.output,args.scratch)
