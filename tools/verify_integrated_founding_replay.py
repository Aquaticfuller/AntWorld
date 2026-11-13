"""Compare committed authority across observation and persistence modes."""

import argparse
from pathlib import Path
from tempfile import TemporaryDirectory
import zipfile

from analyze_integrated_founding import check
from run_integrated_founding import MODELS, NOMINAL, environments
from run_s6_4_wp6b import git, run_one, sha, write_json


AUTHORITY = ("parameters.txt", "initial.chk", "final.frame", "facts.bin")
SUMMARY = ("world", "seed", "queen", "state_hash", "trace_hash", "rng", "events", "time_ms")


def verify(binary, root, models, keep_midpoints=False):
    root.mkdir(parents=True)
    cases = [(i,c) for i,c in environments("nominal") if c["software_seed"]==1 and
             c["arm"] in ("integrated-balanced", "integrated-blocked")]
    records = []
    for model in models:
        command = (*map(str, NOMINAL),"0","3",*MODELS[model])
        for identity, case in cases:
            observations = {}
            for mode in ("observed", "unobserved", "durable"):
                with TemporaryDirectory(dir=root) as scratch:
                    work = Path(scratch) / "case"
                    record = run_one(binary,work,identity,case,mode,command)
                    check(record["status"]=="COMPLETE", f"failed {model}/{case['case']}/{mode}: {record['status']}")
                    if keep_midpoints and mode=="durable":
                        witness=root/f"{model}-{case['case']}-midpoint.zip"
                        with zipfile.ZipFile(witness,"x",zipfile.ZIP_DEFLATED,compresslevel=4) as bundle:
                            for item in sorted(work.glob("midpoint.sqlite*")):
                                if item.name in ("midpoint.sqlite","midpoint.sqlite-wal"):
                                    bundle.write(item,item.name)
                        record["midpoint_archive"] = dict(name=witness.name,sha256=sha(witness),bytes=witness.stat().st_size)
                    observations[mode] = record
            observed = observations["observed"]
            for mode, record in observations.items():
                check(all(record["artifacts"][key]==observed["artifacts"][key] for key in AUTHORITY) and
                      all(record["summary"][key]==observed["summary"][key] for key in SUMMARY),
                      f"authority differs for {model}/{case['case']}/{mode}")
                if mode=="durable":
                    check("midpoint.sqlite" in record["artifacts"] and float(record["summary"]["midpoint_restore_ms"])>0,
                          "durable case did not commit and restore a midpoint")
                print(model,case["case"],mode,record["summary"]["events"],flush=True)
            records.append(dict(model=model,case=case["case"],command=list(command),runs=observations))
    write_json(root/"receipt.json", dict(source=git("rev-parse","HEAD"),cpp_tree=git("rev-parse","HEAD:cpp"),
                                        binary_sha256=sha(binary),rows=len(records),comparisons=records))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary",type=lambda p: Path(p).resolve(strict=True))
    parser.add_argument("out",type=Path)
    parser.add_argument("--model",choices=MODELS,action="append",required=True)
    parser.add_argument("--keep-midpoints",action="store_true")
    args = parser.parse_args()
    verify(args.binary,args.out,args.model,args.keep_midpoints)
