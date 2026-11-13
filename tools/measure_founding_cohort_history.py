"""Measure the same authority with resident and bounded committed histories."""

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from analyze_s6_4_wp6b import check, rows
from founding_qualification_witnesses import COMMAND
from run_ecological_closure import roster
from run_founding_cohort_release import PROTOCOL
from run_s6_4_wp6b import ROOT, git, run_one, sha, write_json
from verify_ecological_closure import write_csv
from verify_ecological_publication import manifest
from verify_final_core_integration import check_identity


ORIGINAL = ROOT / "experiments/s6_4_ecological_mechanism_closure/portable-physics/joint"
FIXED = ("borisovka-1-shaft-joint-balanced-5500", "st_petersburg-1-dogleg-joint-limited-5500")
AUTHORITY = ("initial.chk", "final.frame", "facts.bin", "cuts.csv", "individuals.csv", "geometry_edits.csv", "space_cuts.csv")
MEASURED = ("history_cost.csv", "capture_phases.csv", "timings.csv", "phases.csv", "summary.csv", "profile.csv",
            "case.json", "parameters.txt", "program.log", "receipt.json")


def collect(binary, directory, scratch):
    frozen={row["case"]:row["receipt"] for row in manifest(ORIGINAL)}
    largest=max((r for r in frozen if "-limited-" in r),key=lambda name:int(frozen[name]["summary"]["events"]))
    check(largest==FIXED[1],"historical stress case changed")
    identities={case["case"]:(identity,case) for identity,case,mode in roster("joint") if mode=="observed"}
    directory.mkdir(parents=True)
    scratch.mkdir(parents=True,exist_ok=True)
    write_json(directory/"run.json",dict(source=git("rev-parse","HEAD"),cpp_tree=git("rev-parse","HEAD:cpp"),
               binary_sha256=sha(binary),protocol_sha256=sha(ROOT/PROTOCOL),cases=FIXED,pairs=3,
               scope="fixed work and real durable I/O; diagnostic, not an admitted application qualification"))
    stats=[]
    for name in FIXED:
        identity,case=identities[name]
        case=case | {"arm":case["arm"].replace("ecology-","ecology5-",1)}
        for pair in range(1,4):
            modes=("history-bounded","history-resident") if pair==2 else ("history-resident","history-bounded")
            for mode in modes:
                target=directory/f"{name}-{pair}-{mode}"
                target.mkdir()
                with TemporaryDirectory(dir=scratch) as workdir:
                    work=Path(workdir)/"case"
                    receipt=run_one(binary,work,identity,case,mode,COMMAND)
                    for filename in MEASURED:
                        if (work/filename).exists(): (target/filename).write_bytes((work/filename).read_bytes())
                    record=dict(case=name,pair=pair,mode=mode,status=receipt["status"],wall_ms=receipt["elapsed_ms"])
                    if receipt["status"]=="COMPLETE":
                        check_identity(frozen[name],receipt,name)
                        check(all(receipt["artifacts"][key]==frozen[name]["artifacts"][key] for key in AUTHORITY),
                              "engineering arm changed observation bytes")
                        costs=rows((target/"history_cost.csv").read_bytes())
                        phases=rows((target/"phases.csv").read_bytes())[0]
                        state=receipt["summary"]
                        record |= dict(facts=int(state["events"]),peak_rss_bytes=int(state["peak_rss_bytes"]),
                            state_hash=state["state_hash"],trace_hash=state["trace_hash"],rng=state["rng"],
                            max_hot_bytes=max(int(r["hot_bytes_before"]) for r in costs),
                            final_hot_bytes=int(costs[-1]["hot_bytes_after"]),
                            sqlite_bytes=int(costs[-1]["database_bytes"]),
                            publications=sum(float(r["durable_save_ms"])>0 for r in costs),
                            save_ms=sum(float(r["durable_save_ms"]) for r in costs),
                            validated_restore_ms=sum(float(r["validated_restore_ms"]) for r in costs),
                            checkpoint_ms=float(state["checkpoint_ms"]),advance_ms=float(state["advance_ms"]),
                            observation_ms=float(state["cut_ms"]),decode_block_calls=int(phases["decode_block_calls"]),
                            decode_block_ms=float(phases["decode_block_ms"]),sqlite_sync_ms=float(phases["vfs_sync_ms"]))
                    stats.append(record)
                    write_json(target/"sample.json",record)
                    print(json.dumps(record,sort_keys=True),flush=True)
    write_csv(directory/"samples.csv",stats)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ("binary","output","scratch"):
        parser.add_argument(key,type=Path)
    a=parser.parse_args()
    collect(a.binary.resolve(strict=True),a.output.resolve(),a.scratch.resolve())
