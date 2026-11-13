"""Replay the nine frozen cells against the old authoritative application signatures."""

import argparse
from pathlib import Path
from tempfile import TemporaryDirectory

from analyze_founding_qualification_performance import SIGNATURE, by_cell, collect, key
from analyze_s6_4_wp6b import check
from profile_founding_qualification import CELLS
from profile_s6_4_wp6b_r1 import workload
from run_s6_4_wp6b import git, run_one, sha, write_json
from run_s6_4_wp6b_r1 import NOMINAL


ARGUMENTS={"v1": ("0","0","0"), "r1": (*map(str,NOMINAL),"0"), "both": (*map(str,NOMINAL),"0","3")}


def verify(binary, history, output, scratch):
    scratch.mkdir(parents=True,exist_ok=True)
    old=by_cell(collect(history))
    cases=workload()
    records=[]
    for name,model in sorted(CELLS):
        references={key(row) for row in old[name,model]}
        check(len(references)==1,"historic cell changed its authoritative work")
        reference,=references
        identity,case=cases[name]
        for mode in ("observed","durable"):
            with TemporaryDirectory(dir=scratch) as folder:
                receipt=run_one(binary,Path(folder).resolve()/"case",identity,case,mode,ARGUMENTS[model])
                check(receipt["status"]=="COMPLETE",f"codec replay did not complete: {name}/{model}/{mode}")
                summary,artifacts=receipt["summary"],receipt["artifacts"]
                digest={f"{label}_sha256":artifacts[file]["sha256"] for label,file in
                        (("parameters","parameters.txt"),("initial","initial.chk"),("frame","final.frame"),("facts","facts.bin"))}
                actual=summary | digest | dict(model_version=str({"v1":1,"r1":2,"both":3}[model]))
                check(tuple(actual[field] for field in SIGNATURE)==reference,f"codec replay changed authority: {name}/{model}/{mode}")
                check(len({r["state_hash"] for r in old[name,model]}|{summary["state_hash"]})==1,"codec changed full state hash")
                if mode=="durable":
                    check(float(summary["midpoint_restore_ms"])>0 and "midpoint.sqlite" in artifacts,"midpoint recovery did not run")
                records.append(dict(case=name,model=model,mode=mode,summary=summary,**digest))
                print(name,model,mode,summary["events"],flush=True)
    write_json(output,dict(source=git("rev-parse","HEAD"),binary_sha256=sha(binary),records=records))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("binary","history","output","scratch"):
        parser.add_argument(name,type=Path)
    args=parser.parse_args()
    verify(args.binary.resolve(strict=True),args.history,args.output,args.scratch)
