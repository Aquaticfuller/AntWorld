"""Recompute frozen timing gates and measure a candidate protocol with known controls."""

import argparse
from collections import defaultdict
from itertools import combinations, product
from math import sqrt
from pathlib import Path
import platform
from statistics import NormalDist, median

from analyze_founding_qualification_performance import by_cell, collect, diagnostics, key, load, phase_tables
from analyze_s6_3_3_1_performance import read
from analyze_s6_4_wp6b import check
from founding_qualification_witnesses import table
from profile_s6_4_wp6b import percentile
from run_s6_4_wp6b import ROOT, sha, write_json


EXP = ROOT / "experiments"
INPUTS = {
    "r1": EXP / "s6_4_wp6b_r1/performance/application-observer",
    "r2": EXP / "s6_4_wp6b_r2/performance/append-application",
    "integrated_inherited": EXP / "s6_4_integrated_founding/performance/application-inherited",
    "closure_inherited": EXP / "s6_4_founding_qualification/performance/application-inherited",
    "integrated_v7": EXP / "s6_4_integrated_founding/performance/application-integrated",
    "closure_v7": EXP / "s6_4_founding_qualification/performance/application-integrated",
}
COUNTS = (480, 720, 720, 720, 96, 96)
PHASE_INPUT = EXP / "s6_4_founding_qualification/performance/diagnostic"
TIMES = ("total_ms", "process_ms")
RATIO_LIMITS = (1.10, 1.20)
AA_LIMITS = (.90, 1.10)
HARD_MAX_MS = 20
SEED, TRIALS, DRAWS = 640941, 240, 399


def wilson(count, n, z=1.959963984540054):
    p = count / n
    d = 1 + z*z/n
    mean = (p + z*z/(2*n))/d
    margin = z*sqrt(p*(1-p)/n + z*z/(4*n*n))/d
    return max(0., mean-margin), min(1., mean+margin)


def old_gate(rows, captures, recorded):
    arms = {a: [r for r in rows if r["treatment"] == a] for a in ("on", "off", "off-a", "off-b")}
    check(len(rows) == 24 and all(len(v) == 6 for v in arms.values()) and len({key(r) for r in rows}) == 1,
          "changed timing denominator or authority")
    cuts = [float(row["cut_ms"]) for row in captures if row["treatment"] == "on"]
    horizon = int(rows[0]["time_ms"]) // 86_400_000
    check(len(cuts) == 6*(horizon+1), "changed foreground sample count")
    increment = max(median([int(r["peak_rss_bytes"]) for r in arms["on"] if r["session"] == s]) -
                    median([int(r["peak_rss_bytes"]) for r in arms["off"] if r["session"] == s]) for s in ("1", "2", "3"))
    result = dict(cut_p95_ms=percentile(cuts,.95), cut_max_ms=max(cuts), rss_increment_mib=increment / 1048576)
    valid = result["cut_p95_ms"] <= 5 and result["cut_max_ms"] <= HARD_MAX_MS and result["rss_increment_mib"] <= 16
    for metric in TIMES:
        a,b,c,d = ([float(r[metric]) for r in g] for g in arms.values())
        p50, p95, aa = median(a)/median(b), percentile(a,.95)/percentile(b,.95), median(c)/median(d)
        result.update({metric+"_p50_ratio": p50, metric+"_p95_ratio": p95, metric+"_off_off": aa})
        valid &= p50 <= RATIO_LIMITS[0] and p95 <= RATIO_LIMITS[1] and AA_LIMITS[0] <= aa <= AA_LIMITS[1]
    check(all(abs(v-float(recorded[k])) < 1e-10 for k, v in result.items()) and recorded["status"] == ("PASS" if valid else "FAIL"),
          "historical estimator does not reproduce the accepted record")
    return result | dict(status=recorded["status"], observed_cuts=len(cuts))


def phase_comparison(samples):
    metrics = ("total_ms", "process_ms", "cut_ms", "advance_ms", "observation_state_ms", "observation_csv_ms",
               "midpoint_encode_ms", "save_ms", "restore_ms", "restore_frame_ms", "check_indexes_ms", "vfs_sync_ms",
               "optional_sync_ms", "fact_export_ms", "outer_residual_ms", "wall_minus_thread_cpu_ms", "thread_cpu_ms",
               "peak_rss_bytes")
    result = []
    for (case, model), group in sorted(by_cell(samples).items()):
        blocks = defaultdict(list)
        for row in group:
            blocks[row["session"], row["block"]].append(row)
        for (session, block), pair in sorted(blocks.items()):
            pair = sorted(pair, key=lambda row: int(row["slot"]))
            check(len(pair) == 4 and len({key(r) for r in pair}) == 1, "invalid phase block or changed work")
            for left, right in ((pair[0], pair[1]), (pair[2], pair[3])):
                check(left["treatment"] != right["treatment"], "phase order lacks two distinct treatments")
                comparator = "AB" if {left["treatment"], right["treatment"]} == {"on", "off"} else "AA"
                first, second = sorted((left, right), key=lambda r: r["treatment"] in ("on", "off-a"))
                result.append(dict(case=case,model=model,session=session,block=block,left=left["sample"],right=right["sample"],
                                   comparator=comparator, events=left["events"],
                                   **{metric: float(second[metric])-float(first[metric]) for metric in metrics}))
    return result


def historical(output):
    verdicts, cells, violations, checks = {}, [], [], []
    for (name, path), count in zip(INPUTS.items(), COUNTS, strict=True):
        samples = collect(path)
        check(len(samples) == count, f"changed historical collection size: {name}")
        source = path.with_name(path.name + "-analysis")
        prior = {(r["case"], r["model"]): r for r in read(source / "cells.csv")}
        captures = defaultdict(list)
        capture_count = 0
        for run in sorted(path.glob("session*")):
            if not (run / "samples.csv").is_file():
                continue
            decision = load(run / "receipt.json")
            check(decision["telemetry_qualified"], "attempted to reclassify an unadmitted timing collection")
            for row in read(run / "cuts.csv"):
                captures[row["case"], row["model"]].append(row)
                capture_count += 1
                if row["treatment"] == "on" and float(row["cut_ms"]) > HARD_MAX_MS:
                    violations.append(dict(collection=name, **row))
            checks.extend(dict(file=f.relative_to(ROOT).as_posix(), sha256=sha(f)) for f in (run/"samples.csv",run/"cuts.csv",run/"receipt.json"))
        verdicts[name] = {}
        for k, group in sorted(by_cell(samples).items()):
            result = old_gate(group, captures[k], prior[k])
            cells.append(dict(collection=name, case=k[0], model=k[1], **result))
            verdicts[name][k] = result["status"]
        check(set(verdicts[name]) == set(prior) and capture_count > 0, "missing historical cell or foreground evidence")
    agreement = []
    for left,right in combinations(verdicts,2):
        a,b=verdicts[left],verdicts[right]
        shared=a.keys() & b.keys()
        af={k for k in shared if a[k]=="FAIL"}
        bf={k for k in shared if b[k]=="FAIL"}
        agreement.append(dict(first=left,second=right,common=len(shared),first_fail=len(af),second_fail=len(bf),
                              both_fail=len(af&bf),either_fail=len(af|bf),same=sum(a[k]==b[k] for k in shared)))
    phase_samples = collect(PHASE_INPUT)
    check(len(phase_samples) == 216, "missing phase observations")
    phase_tables(phase_samples)  # Calculate the original residual definitions before pairing.
    records = phase_comparison(phase_samples)
    signatures = {k:{key(r) for r in group} for k,group in by_cell(collect(INPUTS["integrated_inherited"])).items()}
    check(all({key(r)} == signatures[r["case"],r["model"]] for r in phase_samples), "phase diagnostics changed canonical work")
    checks.extend(dict(file=f.relative_to(ROOT).as_posix(),sha256=sha(f)) for f in sorted(PHASE_INPUT.glob("session*/samples.csv")))
    tables = {"original_cells":cells,"agreement":agreement,"foreground_violations":violations,"phase_pairs":records,
              "session_diagnostics":diagnostics(list(INPUTS.items())),"inputs":checks}
    for name, entries in tables.items():
        (output/f"{name}.csv").write_bytes(table(entries))
    return {name:dict(cells=len(values),passed=list(values.values()).count("PASS")) for name,values in verdicts.items()}


def simulate(output, falsifiers=False):
    import numpy as np

    def decisions(times, test_windows):
        estimates = np.quantile(times.reshape(4,-1,2), [.5,.95], axis=1)
        a_b = estimates[:,0,:] / estimates[:,1,:]
        a_a = estimates[0,2,:] / estimates[0,3,:]
        if test_windows == 3:
            pass_ = np.all(a_b <= np.asarray(RATIO_LIMITS)[:, None]) and np.all((AA_LIMITS[0] <= a_a) & (a_a <= AA_LIMITS[1]))
            return pass_, (np.nan, np.nan), None
        # The same admitted-window draws apply to both surfaces and all four arms.
        indexes = bootstrap.integers(test_windows,size=(DRAWS,test_windows))
        draw = times[:,indexes].reshape(4,DRAWS,-1,2)
        with np.errstate(invalid="raise"):
            positions = np.array([.5,.95])*(draw.shape[2]-1)
            lower = positions.astype(int)
            rank = np.sort(np.concatenate((lower,lower+1)))
            quantiles = np.partition(draw, rank, axis=2)
            boot = np.stack([quantiles[:,:,i,:]+(j-i)*(quantiles[:,:,i+1,:]-quantiles[:,:,i,:])
                             for i,j in zip(lower,positions,strict=True)])
            ab = boot[:,0]/boot[:,1]
            aa = boot[0,2]/boot[0,3]
            limits = np.quantile(ab,.95,axis=1)
            aa_band = np.quantile(aa,[.05,.95],axis=0)
            pass_ = np.all(limits <= np.asarray(RATIO_LIMITS)[:, None]) and np.all(aa_band[0]>=AA_LIMITS[0]) and np.all(aa_band[1]<=AA_LIMITS[1])
            tail_interval = np.quantile(ab[1],[.025,.975],axis=0)
            return pass_, tuple(np.log(tail_interval[1]/tail_interval[0])/2), tail_interval

    seed = 640943 if falsifiers else SEED
    root = np.random.SeedSequence(seed)
    data, bootstrap = (np.random.Generator(np.random.PCG64(s)) for s in root.spawn(2))
    regimes = {"quiet": (.03,.02,.03), "clustered": (.10,.05,.07)}
    if falsifiers:
        scenarios = [("valid",1.05,0,0.,1.),("tail_boundary",1.05,1.20,0.,1.),("tail_above",1.05,1.24,0.,1.),
                     ("aa_above",1.05,0,0.,1.13),("maximum",1.05,0,30.4863,1.)]
        designs = (3,96)
    else:
        scenarios = [(str(r),r,0,0.,1.) for r in (1.,1.05,1.10,1.14,1.25)] + [("tail-only",1.05,-1,0.,1.),("maximum",1.05,0,30.4863,1.)]
        designs = (3,32,64,96)
    all_rows, aggregate = [], []
    normal = NormalDist()
    for (regime, (s,p,e)), (case, multiplier, tail, hard, drift), n in product(regimes.items(), scenarios, designs):
        m = 2 if n == 3 else 4
        sd = np.sqrt(s*s + p*p + (np.array([e,1.5*e]))**2)
        shift_basis = sd*(normal.inv_cdf(.95)-normal.inv_cdf(.90))
        slope = 2 if tail == -1 else np.log(tail/multiplier)/shift_basis[1] if tail else 0
        shift = slope*shift_basis
        exact_tail = multiplier * np.exp(shift)
        selected = []
        for i in range(TRIALS):
            session = data.normal(0,s,size=(n,1,1))
            paired = data.normal(0,p,size=(2,n,m,2))
            residual = data.normal(0,[e,1.5*e],size=(4,n,m,2))
            log_times = session + paired[[0,0,1,1]] + residual
            log_times[0] += np.log(multiplier) + (slope*np.maximum(log_times[0]-sd*normal.inv_cdf(.90),0) if tail else 0)
            if drift != 1:
                log_times[2] += np.log(drift)
            passes,width,band = decisions(np.exp(log_times),n)
            row = dict(regime=regime,scenario=case,windows=n,pairs_per_arm=m,trial=i,known_median=multiplier,
                       known_app_p95=exact_tail[0],known_process_p95=exact_tail[1],
                       decision="FAIL_HARD" if hard>HARD_MAX_MS else "PASS" if passes else "FAIL_POINT" if n==3 else "INCONCLUSIVE",
                       max_cut_ms=hard,app_tail_log_halfwidth=width[0] if n>3 else "",process_tail_log_halfwidth=width[1] if n>3 else "",
                       app_tail_covered=int(band[0,0]<=exact_tail[0]<=band[1,0]) if n>3 else "",
                       process_tail_covered=int(band[0,1]<=exact_tail[1]<=band[1,1]) if n>3 else "")
            if falsifiers:
                row["known_aa_ratio"] = drift
            selected.append(row)
        passes = sum(row["decision"]=="PASS" for row in selected)
        prob=passes/TRIALS
        lo,hi=wilson(passes,TRIALS)
        aggregate.append(dict(regime=regime,scenario=case,windows=n,trials=TRIALS,pass_count=passes,pass_probability=prob,
            pass_lo=lo,pass_hi=hi,independent_34_pass=prob**34,any_dependence_lower=max(0,34*prob-33),any_dependence_upper=prob,
            app_median_tail_halfwidth=median(row["app_tail_log_halfwidth"] for row in selected) if n>3 else "",
            process_median_tail_halfwidth=median(row["process_tail_log_halfwidth"] for row in selected) if n>3 else "",
            app_tail_coverage=sum(row["app_tail_covered"] for row in selected)/TRIALS if n>3 else "",
            process_tail_coverage=sum(row["process_tail_covered"] for row in selected)/TRIALS if n>3 else ""))
        all_rows.extend(selected)
    for name, values in (("synthetic_trials",all_rows),("synthetic_summary",aggregate)):
        (output/f"{name}.csv").write_bytes(table(values))
    return dict(numpy=np.__version__, windows=list(designs), seed=seed, trials_per_scenario=TRIALS, draws=DRAWS)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--historical-only", action="store_true")
    parser.add_argument("--falsifiers", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    states = historical(args.output) if not args.falsifiers else None
    synthetic = None if args.historical_only else simulate(args.output,args.falsifiers)
    write_json(args.output/"receipt.json",dict(original=states,synthetic=synthetic,python=platform.python_version(),
                                              platform=platform.platform(),script_sha256=sha(Path(__file__))))
    print(states)
