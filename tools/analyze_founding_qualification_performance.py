"""Verify frozen diagnostic samples and measure repeatability of the unchanged historical gates."""

import argparse
from collections import defaultdict
from itertools import product
import json
from math import isfinite
from pathlib import Path
from random import Random
from statistics import median

from analyze_s6_3_3_1_performance import read, telemetry
from analyze_s6_4_wp6b import check
from founding_qualification_witnesses import table
from profile_founding_qualification import CELLS, PROTOCOL, diagnostic_schedule
from profile_s6_4_wp6b import percentile
from reconcile_s6_4_rm02_performance import verify_manifest
from run_s6_4_wp6b import sha, write_json
from run_s6_4_wp6b_r2_performance import APPEND_LAYOUT, MAPPING


SIGNATURE = ("world","seed","model_version","parameters_sha256","initial_sha256","frame_sha256","facts_sha256","events","rng")
METRICS = ("total_ms", "process_ms")
PHASES = ("thread_cpu_ms","setup_ms","initial_encode_ms","advance_ms","observation_state_ms","observation_csv_ms","cut_ms",
          "midpoint_encode_ms","sqlite_open_ms","save_ms","restore_ms","restore_encode_ms","sqlite_close_ms","output_close_ms",
          "checkpoint_ms","final_frame_ms","fact_export_ms","capture_frame_ms","seal_blocks_ms","derive_indexes_ms",
          "write_indexes_ms","commit_ms","verify_blocks_ms","restore_frame_ms","check_indexes_ms","vfs_read_ms","vfs_write_ms",
          "vfs_sync_ms","common_sync_ms","optional_sync_ms",*METRICS,"outer_residual_ms","wall_minus_thread_cpu_ms")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def collect(archive):
    return [r for folder in sorted(archive.glob("session*")) if (folder/"samples.csv").is_file()
            for r in read(folder/"samples.csv")]


def by_cell(samples):
    groups=defaultdict(list)
    for row in samples:
        groups[row["case"],row["model"]].append(row)
    return groups


def key(row):
    return tuple(row[field] for field in SIGNATURE)


def check_inputs(archive, original):
    freeze, batch, start=(load(archive/name) for name in ("freeze.json","batch_result.json","batch_start.json"))
    check(freeze["protocol_sha256"]==sha(PROTOCOL) and freeze["mapping_sha256"]==sha(MAPPING) and
          freeze["sources"][APPEND_LAYOUT.name]==sha(APPEND_LAYOUT),"diagnostic freeze changed")
    check(start["freeze_sha256"]==sha(archive/"freeze.json") and start["started_utc_ns"]==batch["started_utc_ns"],"changed batch receipt")
    expected=by_cell(collect(original))
    admitted=[]
    for name,digest in freeze["schedules"].items():
        folder=archive/name
        schedule=read(folder/"schedule.csv")
        check(sha(folder/"schedule.csv")==digest and schedule==[{k:str(v) for k,v in row.items()}
              for row in diagnostic_schedule(int(name[-1]))],"changed diagnostic schedule")
        attempts=[load(path) for path in sorted(folder.glob("admission*_receipt.json"))]
        check(len(attempts)<=3 and all(not a["admitted"] for a in attempts[:-1]),"invalid admission sequence")
        for i, attempt in enumerate(attempts,1):
            counters=attempt["checks"]
            qualified=all(counters[k] for k in ("native_intervals_valid","power_valid","sensors_valid")) and all(
                counters[k+"_complete"] and counters[k+"_p50"]<=10 and counters[k+"_p95"]<=20
                for k in ("system_busy_pct","processor_busy_pct"))
            check(qualified==attempt["admitted"] and len(read(folder/f"admission{i}.csv"))==60,"invalid admission evaluation")
            if i>1:
                check(attempt["started_utc_ns"]-attempts[i-2]["ended_utc_ns"]>=300_000_000_000,"admission retry was early")
        if not (folder/"receipt.json").is_file():
            continue
        receipt=load(folder/"receipt.json")
        observed=read(folder/"samples.csv")
        cuts=read(folder/"cuts.csv")
        check(attempts[-1]["admitted"] and receipt["admission_attempt"]==attempts[-1]["attempt"] and
              receipt["binary_sha256"]==freeze["binary_sha256"] and receipt["rows"]==len(observed),"inconsistent timed receipt")
        qualified=telemetry(folder,receipt)[1]
        check(qualified==receipt["telemetry_qualified"],"timed telemetry mismatch")
        if qualified and len(observed)==len(schedule):
            admitted.append(name)
        for row, plan in zip(observed,schedule):
            cell=row["case"],row["model"]
            check(all(row[k]==v for k,v in plan.items()) and cell in CELLS and
                  {key(r) for r in expected[cell]}=={key(row)},"diagnostic changed authoritative work")
            check(all(isfinite(float(row[k])) and float(row[k])>=0 for k in PHASES[:-2]),"invalid diagnostic phase value")
            check(all(int(row[f"{k}_calls"])>0 for k in ("capture_frame","seal_blocks","verify_blocks","restore_frame","vfs_sync")),
                  "expected storage phase was not observed")
        check(len(cuts)==91*len(observed),"changed daily cut count")
    observed=collect(archive)
    check(batch["completed"]==admitted,"collection status differs from qualified data")
    return observed,dict(status="COMPLETE" if len(observed)==216 and len(admitted)==3 else
        "NOT_RUN" if not observed else "INCONCLUSIVE",rows=len(observed),planned=216,qualified_sessions=len(admitted),
        collection=batch["outcome"],source=freeze["source"],binary_sha256=freeze["binary_sha256"])


def phase_tables(samples):
    phases,tails=[],[]
    for (case,model), group in sorted(by_cell(samples).items()):
        for row in group:
            row["outer_residual_ms"]=float(row["process_ms"])-float(row["total_ms"])
            row["wall_minus_thread_cpu_ms"]=float(row["total_ms"])-float(row["thread_cpu_ms"])
        for treatment in ("on","off","off-a","off-b"):
            selected=[r for r in group if r["treatment"]==treatment]
            if not selected:
                continue
            for phase in PHASES:
                values=[float(row[phase]) for row in selected]
                phases.append(dict(case=case,model=model,treatment=treatment,n=len(values),phase=phase,p50=median(values),
                    p95=percentile(values,.95),p99=percentile(values,.99),maximum=max(values)))
            for metric in METRICS:
                peak=max(selected,key=lambda r:float(r[metric]))
                tails.append(dict(case=case,model=model,treatment=treatment,metric=metric,session=peak["session"],sample=peak["sample"],
                    **{phase:peak[phase] for phase in PHASES}))
    return phases,tails


def diagnostics(archives):
    rng=Random(640604)
    result=[]
    for name,archive in archives:
        for (case,model), group in sorted(by_cell(collect(archive)).items()):
            sessions=sorted({r["session"] for r in group})
            for metric in METRICS:
                parts={s:{arm:[float(r[metric]) for r in group if r["session"]==s and r["treatment"]==arm]
                      for arm in ("on","off","off-a","off-b")} for s in sessions}
                check(len(parts)==3 and all(len(x)==2 for p in parts.values() for x in p.values()),"incomplete historical pairs")
                on,off=([n for p in parts.values() for n in p[arm]] for arm in ("on","off"))
                aa,bb=([n for p in parts.values() for n in p[arm]] for arm in ("off-a","off-b"))
                flips=[]
                for flags in product((False,True),repeat=3):
                    a,b=( [n for s,flip in zip(sessions,flags) for n in parts[s]["off-a" if (flip==side) else "off-b"]]
                          for side in (False,True) )
                    flips.append(median(a)/median(b))
                ab=[median(p["on"])/median(p["off"]) for p in parts.values()]
                loo=[median([n for s,p in parts.items() if s!=omit for n in p["on"]])/
                     median([n for s,p in parts.items() if s!=omit for n in p["off"]]) for omit in sessions]
                bootstrap=sorted(median(rng.choices(ab,k=3)) for _ in range(4096))
                result.append(dict(archive=name,case=case,model=model,metric=metric,samples=len(on),
                    p50=median(on)/median(off),p95=percentile(on,.95)/percentile(off,.95),aa=median(aa)/median(bb),
                    aa_swaps_outside=sum(not .9<=x<=1.1 for x in flips),aa_swaps=len(flips),aa_swap_min=min(flips),aa_swap_max=max(flips),
                    session_ratio_min=min(ab),session_ratio_max=max(ab),leave_session_min=min(loo),leave_session_max=max(loo),
                    paired_ratio=median(ab),paired_ci_lo=percentile(bootstrap,.025),paired_ci_hi=percentile(bootstrap,.975),
                    largest_order_statistic_weight=0.75,probability_top5_observed=1-.95**len(on)))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("diagnostic",type=Path)
    parser.add_argument("historical",type=Path,nargs="+")
    parser.add_argument("output",type=Path)
    args=parser.parse_args()
    verify_manifest(args.diagnostic)
    samples,decision=check_inputs(args.diagnostic,args.historical[0])
    args.output.mkdir(parents=True)
    phases,tails=phase_tables(samples)
    records=diagnostics((path.name,path) for path in args.historical)
    for name,data in (("phases.csv",phases),("phase_tails.csv",tails),("repeatability.csv",records)):
        (args.output/name).write_bytes(table(data))
    write_json(args.output/"diagnostic_status.json",decision)
    print(decision)


if __name__=="__main__":
    main()
