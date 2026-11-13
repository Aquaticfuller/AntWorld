"""Summarize all observed timing phases and preserve every application tail."""

import argparse
from collections import defaultdict
import csv
from pathlib import Path
from statistics import median

from analyze_s6_3_3_1_performance import read
from profile_s6_4_wp6b import percentile


PHASES = ("setup_ms","advance_ms","cut_ms","checkpoint_ms","midpoint_save_ms","midpoint_restore_ms",
          "common_sync_ms","optional_sync_ms","post_cut_ms","total_ms","process_ms","peak_rss_bytes",
          "midpoint_sqlite_bytes","frame_bytes","facts_bytes","events")


def emit(path, records):
    if records:
        with path.open("x",encoding="utf-8",newline="") as stream:
            output=csv.DictWriter(stream,list(dict.fromkeys(field for row in records for field in row)),lineterminator="\n")
            output.writeheader()
            output.writerows(records)


def summarize(archive, output):
    groups=defaultdict(list)
    for session in sorted(archive.glob("session*")):
        source=session/"samples.csv"
        if source.is_file():
            for row in read(source):
                groups[row["case"],row["model"],row["treatment"]].append(row)
    phases, tails = [], []
    for (case,model,treatment),group in sorted(groups.items()):
        common=dict(case=case,model=model,treatment=treatment,n=len(group))
        for phase in PHASES:
            values=[float(row[phase]) for row in group]
            phases.append(common | dict(phase=phase,p50=median(values),p95=percentile(values,.95),
                                       p99=percentile(values,.99),maximum=max(values)))
        for measure in ("process_ms","total_ms"):
            biggest=max(group,key=lambda row:float(row[measure]))
            tails.append(common | dict(ranked_by=measure,session=biggest["session"],sample=biggest["sample"],
                process_outside_measured_application_ms=float(biggest["process_ms"])-float(biggest["total_ms"]),
                **{key:biggest[key] for key in PHASES}))
    output.mkdir(parents=True)
    emit(output/"phase_percentiles.csv",phases)
    emit(output/"cell_tails.csv",tails)
    print(f"{sum(map(len,groups.values()))} original process samples; {len(tails)} indexed tails")


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive",type=Path)
    parser.add_argument("output",type=Path)
    args=parser.parse_args()
    summarize(args.archive,args.output)
