"""Recalculate the published founding qualification diagnostic and cohort summaries."""

import argparse
from collections import defaultdict
import csv
import gzip
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from analyze_founding_qualification_b06 import summarize
from analyze_s6_4_wp6b import check
from compare_founding_qualification_runs import compare
from founding_qualification_scope import cases
from founding_qualification_witnesses import table
from run_integrated_founding import DAY, environments
from run_s6_4_wp6b import ROOT
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
    manifest=json.loads((output/"archives.json").read_bytes())
    worlds=read(output/"worlds.csv")
    cuts=read(output/"resource_cuts.csv")
    expected={c["case"]:(matrix,identity,c) for matrix,identity,c in cases()}
    check(len(expected)==len(manifest)==len(worlds)==48 and len(cuts)==192,"scope denominator changed")
    daily=defaultdict(list)
    for cut in cuts:
        daily[cut["case"]].append(int(cut["day"]))
    for world,row in zip(worlds,manifest,strict=True):
        receipt=row["receipt"]
        name=world["case"]
        matrix,identity,case=expected.pop(name)
        days=case["release_days"]
        check(receipt["case"]==name and receipt["identity"]==identity and receipt["status"]=="COMPLETE" and
              row["archive_sha256"]==world["archive_sha256"] and int(receipt["summary"]["events"])==int(world["fact_count"]) and
              world["matrix"]==matrix and int(world["release_days"])==days and int(world["last_positive_release_ms"])==days*DAY and
              world["day150_reference"]==("FACT_PREFIX_EXACT" if days==120 else "") and daily[name]==[60,120,150,180],
              "invalid post-release case receipt")


def verify(root):
    cohorts(root/"b06")
    scope(root/"scope")
    performance=root/"performance"
    experiments=ROOT/"experiments"
    historical=(experiments/"s6_4_integrated_founding/performance/application-inherited",
                experiments/"s6_4_wp6b_r2/performance/append-application",
                experiments/"s6_4_wp6b_r1/performance/application-observer")
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
    print("1236 B06 case pairs, all exposure summaries, 48 scope receipts and diagnostic timings verified")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence",type=Path)
    verify(parser.parse_args().evidence.resolve())
