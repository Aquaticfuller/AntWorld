"""Recalculate the published founding qualification diagnostic and cohort summaries."""

import argparse
from collections import defaultdict
import csv
import gzip
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from analyze_founding_qualification_b06 import summarize
from analyze_founding_qualification_performance import by_cell, collect, key
from analyze_s6_4_wp6b import check
from compare_founding_qualification_runs import compare
from founding_qualification_scope import cases
from founding_qualification_witnesses import table
from profile_founding_qualification import CELLS
from reconcile_s6_4_rm02_performance import verify_manifest
from run_integrated_founding import DAY, environments
from run_s6_4_wp6b import ROOT, input_bytes, sha
from verify_s6_4_wp6b_r2_performance import compare_outputs, run


def read(path, compressed=False):
    opener=gzip.open if compressed else open
    with opener(path,"rt",encoding="utf-8",newline="") as stream:
        return list(csv.DictReader(stream))


def cohorts(output):
    reference=ROOT/"experiments/s6_4_integrated_founding/analysis"
    worlds=read(output/"census_diagnosis.csv")
    observed={r["case"]:r for r in worlds}
    check(len(worlds)==len(observed)==1236,"changed cohort denominator")
    for matrix in ("closed","nominal","factorial"):
        baseline=read(reference/f"resupply-{matrix}"/"censuses.csv")
        expected={case["case"] for _,case in environments(matrix)}
        check({r["case"] for r in worlds if r["matrix"]==matrix}==expected,"changed cohort identity")
        for row in baseline:
            witness=observed[row["case"]]
            key="exact" if row["rule"]=="exact" else "at_least"
            check(witness["k"]==row["k"] and int(witness[f"{key}_complete"])==bool(row["total_d"]) and
                  int(witness[f"pupa_{key}_seen"])==bool(row["larva_d"]) and
                  all(witness[f"{key}_{endpoint}"]==row[endpoint] for endpoint in ("egg_d","larva_d","pupa_d","total_d")),
                  "original B06 match changed")
    for row in read(reference/"resupply-closed"/"timing_comparison.csv"):
        check(row["status"]=="INSUFFICIENT" and row["complete_worlds"]=="0","original B06 verdict changed")
    rows=read(output/"stage_exposures.csv.gz",compressed=True)
    integer_keys=("stage","elapsed_ms","nominal_ms","excess_elapsed_ms","waiting_cuts","protein_short_cuts",
                  "energy_short_cuts","water_short_cuts","multiple_short_cuts","fully_funded_cut")
    for row in rows:
        for key in integer_keys:
            row[key]=int(row[key]) if row[key] else None
        check(row["case"] in observed and row["excess_elapsed_ms"]==max(0,row["elapsed_ms"]-row["nominal_ms"]),
              "invalid known-age exposure")
    check((output/"stage_summary.csv").read_bytes()==table(list(summarize(rows))),"stage summary changed")


def scope(output):
    run_record=json.loads((output/"run.json").read_bytes())
    manifest=json.loads((output/"archives.json").read_bytes())
    worlds=read(output/"worlds.csv")
    cuts=read(output/"resource_cuts.csv")
    expected={c["case"]:(matrix,identity,c) for matrix,identity,c in cases()}
    check(len(expected)==len(manifest)==len(worlds)==48 and len(cuts)==192,"scope denominator changed")
    check(run_record["cases"]==list(expected) and run_record["protocol_sha256"]==
          sha(ROOT/"research/s6_4_founding_qualification/FROZEN_CLOSURE_PROTOCOL.md"),"scope input freeze changed")
    daily=defaultdict(list)
    for cut in cuts:
        daily[cut["case"]].append(cut)
    for world,row in zip(worlds,manifest,strict=True):
        receipt=row["receipt"]
        name=world["case"]
        matrix,identity,case=expected.pop(name)
        days=case["release_days"]
        check(receipt["case"]==name and receipt["identity"]==identity and receipt["status"]=="COMPLETE" and receipt["exit_code"]==0 and
              receipt["artifacts"]["parameters.txt"]["sha256"]==sha256(input_bytes(identity,case)).hexdigest() and
              int(receipt["summary"]["time_ms"])==180*DAY and
              row["archive_sha256"]==world["archive_sha256"] and int(receipt["summary"]["events"])==int(world["fact_count"]) and
              world["matrix"]==matrix and int(world["release_days"])==days and int(world["last_positive_release_ms"])==days*DAY and
              world["day150_reference"]==("FACT_PREFIX_EXACT" if days==120 else "") and
              [int(cut["day"]) for cut in daily[name]]==[60,120,150,180] and
              all(int(cut["release_days"])==days for cut in daily[name]),
              "invalid post-release case receipt")
        last=daily[name][-1]
        check(last["queen_alive"]==world["queen_alive_180"] and last["living_workers"]==world["workers_alive_180"] and
              all(int(last[f"reserve_{part}_ug"])==0 for part in "cpwo"),"inconsistent final scope census")


def legacy(output):
    baseline=ROOT/"experiments/s6_4_integrated_founding/replay"
    for model in ("v1","r1"):
        reference=baseline/f"legacy-{model}-completed.json"
        earlier=json.loads(reference.read_bytes())["statuses"]
        current=json.loads((output/f"{model}.json").read_bytes())
        check(current["reference_sha256"]==sha(reference) and current["attempts"]==len(earlier)==1092 and
              current["statuses"].keys()==earlier.keys(),"legacy replay membership changed")
        for case,row in current["statuses"].items():
            check(row["exact"] and row["signature"]==earlier[case]["signature"] and
                  row["status"]==earlier[case]["status"],"legacy replay does not match its historical authority")


def native(output):
    for kind in ("contacts","births","protected"):
        verify_manifest(output/kind)
        if kind=="protected":
            report=output/"protected-analysis.json"
            status=json.loads(report.read_bytes())["status"]
            code=run("s6_4_wp6b_r2_protected_observer","--analyze",output/kind,report,"--check")
            check(code==int(status!="PASS"),"protected observer report differs")
        else:
            check(run("analyze_s6_3_3_1_performance","--raw",output/kind,"--out",output/f"{kind}-analysis","--check")==0,
                  f"{kind} performance report differs")


def codec(path, baseline):
    receipt=json.loads(path.read_bytes())
    old=by_cell(collect(baseline))
    seen=set()
    for row in receipt["records"]:
        cell=(row["case"],row["model"])
        mode=row["mode"]
        check((cell,mode) not in seen and cell in CELLS and mode in ("observed","durable"),"wrong codec replay cell")
        seen.add((cell,mode))
        summary=row["summary"]
        identity=summary | {label:row[label] for label in ("parameters_sha256","initial_sha256","frame_sha256","facts_sha256")}
        identity["model_version"]=str({"v1":1,"r1":2,"both":3}[row["model"]])
        check({key(old_row) for old_row in old[cell]}=={key(identity)} and
              {old_row["state_hash"] for old_row in old[cell]}=={summary["state_hash"]} and
              (mode!="durable" or float(summary["midpoint_restore_ms"])>0),"wrong codec replay authority")
    check(len(seen)==18,"incomplete codec replay receipt")


def verify(root):
    cohorts(root/"b06")
    scope(root/"scope")
    legacy(root/"replay-legacy")
    performance=root/"performance"
    native(performance)
    experiments=ROOT/"experiments"
    historical=(experiments/"s6_4_integrated_founding/performance/application-inherited",
                experiments/"s6_4_wp6b_r2/performance/append-application",
                experiments/"s6_4_wp6b_r1/performance/application-observer")
    codec(performance/"codec-exact.json",historical[0])
    with TemporaryDirectory() as scratch:
        calculated=Path(scratch)/"diagnostic-analysis"
        check(run("analyze_founding_qualification_performance",performance/"diagnostic",*historical,calculated)==0,
              "cannot reproduce diagnostic")
        compare_outputs(performance/calculated.name,calculated)
    for scope_name in ("inherited","integrated"):
        name=f"application-{scope_name}"
        baseline=experiments/"s6_4_integrated_founding/performance"/name
        rows=list(compare(baseline,performance/name))
        check((performance/f"{name}-paired-codec.csv").read_bytes()==table(rows),"codec comparison changed")
    print("1236 B06 case pairs, 48 scope receipts, 2184 legacy replays and controlled timings verified")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence",type=Path)
    verify(parser.parse_args().evidence.resolve())
