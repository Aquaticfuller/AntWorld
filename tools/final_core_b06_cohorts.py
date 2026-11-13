"""Reconstruct same-count and same-lineage B06 endpoints from archived stage histories."""

import argparse
from collections import Counter, defaultdict
import csv
import gzip
from pathlib import Path
from statistics import median

from analyze_s6_4_wp6b import RANGES, census, check
from founding_qualification_witnesses import table
from run_integrated_founding import DAY
from run_s6_4_wp6b import ROOT, sha, write_json


EXP = ROOT / "experiments"
CLOSURE = EXP / "s6_4_founding_qualification/b06"
HISTORY = EXP / "s6_4_integrated_founding/analysis"


def read(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def duration(a, b):
    return (b-a)/DAY if a is not None and b is not None else None


def stage_occupancy(stages, horizon):
    changes = defaultdict(list)
    for s in stages:
        ant, stage = int(s["ant"]), int(s["stage"])
        check(0 <= stage <= 3, "unexpected developmental stage")
        changes[int(s["enter_ms"])].append((int(s["enter_event"]), stage, ant, True))
        if s["end_event"]:
            changes[int(s["end_ms"])].append((int(s["end_event"]), stage, ant, False))
        else:
            check(s["outcome"] == "RIGHT_CENSORED" and int(s["end_ms"]) == horizon, "unexplained missing terminal event")
    pending = iter(sorted(changes.items()))
    item = next(pending,None)
    alive = [set() for _ in range(4)]
    for at in range(0,horizon+1,DAY):
        while item is not None and item[0] <= at:
            # The committed event ID gives a total order, including exact cut-boundary transitions.
            for _, stage, ant, enters in sorted(item[1], key=lambda x: (x[0],x[3])):
                if enters:
                    check(all(ant not in ids for ids in alive), "identity entered two stages")
                    alive[stage].add(ant)
                else:
                    alive[stage].remove(ant)
            item = next(pending,None)
        yield at, tuple(frozenset(ids) for ids in alive)
    check(item is None, "stage evidence extends beyond the final observation")


def case_record(meta, stages, nutrition, archived):
    horizon = (90 if meta["matrix"]=="closed" else 150)*DAY
    daily = list(stage_occupancy(stages,horizon))
    counts = [(t, [len(ids) for ids in sets]) for t,sets in daily]
    by_time = dict(daily)
    exact, at_least = (census(counts, rule=="exact") for rule in ("exact","at_least"))
    for rule,computed in (("exact",exact),("at_least",at_least)):
        check(all(archived[rule][key] == ("" if value is None else str(value)) for key,value in computed.items()),
              f"archived {rule} count reader differs in {meta['case']}")
    first_larva = exact["first_larva_ms"]
    first = by_time[first_larva][1] if first_larva is not None else frozenset()
    check(len(first) == exact["k"], "first observed cohort does not reproduce target")
    by_child = defaultdict(dict)
    for row in stages:
        by_child[int(row["ant"])][int(row["stage"])] = row
    first_cut = by_time[first_larva] if first_larva is not None else (frozenset(),)*4
    next_d = [(t,sets) for t,sets in daily if first_larva is not None and t >= first_larva]
    summary = {k:meta[k] for k in ("case","population","matrix","arm","profile","seed")}
    summary.update(k=len(first), first_larval_cut_ms=first_larva,
                   earlier_larval_entries=sum(1 in s and int(s[1]["enter_ms"])<=first_larva and ant not in first
                                              for ant,s in by_child.items()) if first_larva is not None else 0,
                   first_observed_same_lineage_pupal_peak=max((len(sets[2]&first) for _,sets in next_d),default=0),
                   first_observed_same_lineage_adult_peak=max((len(sets[3]&first) for _,sets in next_d),default=0),
                   other_eggs_at_first_larval_cut=len(first_cut[0]))
    people = []
    for ant in sorted(first):
        lineage = by_child[ant]
        larva = lineage[1]
        exposure = nutrition[ant]
        row = dict(case=meta["case"], ant=ant, egg_ms=int(lineage[0]["enter_ms"]), hatch_ms=int(larva["enter_ms"]),
                   larval_clock_ms=exposure["nominal_ms"], larval_exit_ms=int(larva["end_ms"]), larval_exit=larva["outcome"],
                   pupa_ms=int(lineage[2]["enter_ms"]) if 2 in lineage else None,
                   adult_ms=int(lineage[3]["enter_ms"]) if 3 in lineage else None,
                   adult_exit=lineage[3]["outcome"] if 3 in lineage else None,
                   **{k:exposure[k] for k in ("ration_count","ration_protein_ug","larval_protein_uptake_ug","waiting_cuts",
                       "protein_short_cuts","energy_short_cuts","water_short_cuts","first_ration_delay_ms")})
        people.append(row)
    summary.update(first_cohort_pupated=sum(p["pupa_ms"] is not None for p in people),
                   first_cohort_eclosed=sum(p["adult_ms"] is not None for p in people),
                   first_cohort_larval_energy_deaths=sum(p["larval_exit"]=="DEATH_1" for p in people),
                   first_cohort_larval_water_deaths=sum(p["larval_exit"]=="DEATH_2" for p in people),
                   first_cohort_larval_censored=sum(p["larval_exit"]=="RIGHT_CENSORED" for p in people),
                   first_cohort_no_paid_ration=sum(int(p["ration_count"])==0 for p in people),
                   first_cohort_no_protein_uptake=sum(int(p["larval_protein_uptake_ug"])==0 for p in people),
                   first_cohort_eligible_but_wait_cut=sum(int(p["waiting_cuts"])>0 for p in people),
                   first_cohort_worker_deaths=sum(bool(p["adult_exit"] and p["adult_exit"].startswith("DEATH")) for p in people))
    for label, rule in (("exact",exact),("at_least",at_least)):
        for stage, position in (("pupa",2),("worker",3)):
            t = rule[f"first_{stage}_ms"]
            matched = by_time[t][position] if t is not None else None
            summary.update({f"{label}_{stage}_first_ms":t,f"{label}_{stage}_cohort_members":len(matched&first) if matched is not None else None,
                            f"{label}_{stage}_other_members":len(matched-first) if matched is not None else None})
        summary[f"{label}_total_days"] = rule["total_d"]
        ranges = RANGES[meta["population"]]
        endpoints = (rule[k] for k in ("egg_d","larva_d","pupa_d","total_d"))
        summary[f"{label}_within_all_reference_ranges"] = int(all(v is not None and low<=v<=high
                                                               for v,(low,high) in zip(endpoints,ranges,strict=True)))
    return summary, people


def summarize(worlds, people):
    grouped, individuals = defaultdict(list), defaultdict(list)
    key = lambda row: (row["matrix"], row["population"])
    for row in worlds:
        grouped[key(row)].append(row)
    world_groups = {row["case"]:key(row) for row in worlds}
    for row in people:
        individuals[world_groups[row["case"]]].append(row)
    for (matrix,population), cases in sorted(grouped.items()):
        cohort = individuals[matrix,population]
        adult_time = [duration(row["egg_ms"],row["adult_ms"]) for row in cohort if row["adult_ms"] is not None]
        larval_time = [duration(row["hatch_ms"],row["pupa_ms"]) for row in cohort if row["pupa_ms"] is not None]
        yield dict(matrix=matrix,population=population,worlds=len(cases),first_census_larvae=len(cohort),
            any_first_cohort_eclosion=sum(row["first_cohort_eclosed"]>0 for row in cases),
            all_first_cohort_eclosed=sum(row["k"]>0 and row["first_cohort_eclosed"]==row["k"] for row in cases),
            first_cohort_larval_median_days=median(larval_time) if larval_time else None,
            first_cohort_egg_to_worker_median_days=median(adult_time) if adult_time else None,
            **{field:sum(row[field] for row in cases) for field in (
                "first_cohort_pupated","first_cohort_eclosed","first_cohort_larval_energy_deaths","first_cohort_larval_water_deaths",
                "first_cohort_larval_censored","first_cohort_no_paid_ration","first_cohort_no_protein_uptake",
                "first_cohort_eligible_but_wait_cut","first_cohort_worker_deaths","exact_within_all_reference_ranges",
                "at_least_within_all_reference_ranges")},
            **{f"{rule}_census_{stage}_worlds":sum(row[f"{rule}_{stage}_first_ms"] is not None for row in cases)
               for rule in ("exact","at_least") for stage in ("pupa","worker")},
            **{f"{rule}_census_{stage}_other_members":sum(row[f"{rule}_{stage}_other_members"] or 0 for row in cases)
               for rule in ("exact","at_least") for stage in ("pupa","worker")})


def analyze(output):
    metadata = {r["case"]:r for r in read(CLOSURE/"census_diagnosis.csv") if
                (r["matrix"]=="closed" and r["care"]=="1" and r["group"]=="primary") or
                (r["matrix"] in ("nominal","factorial") and r["arm"]=="balanced")}
    exposure_path=CLOSURE/"stage_exposures.csv.gz"
    with gzip.open(exposure_path,"rt",encoding="utf-8",newline="") as stream:
        nutrition=defaultdict(dict)
        for r in csv.DictReader(stream):
            if r["stage"]=="1" and r["case"] in metadata:
                nutrition[r["case"]][int(r["ant"])]=r
    summary, people, files = [],[],[CLOSURE/"census_diagnosis.csv",exposure_path]
    for matrix in ("closed","nominal","factorial"):
        root=HISTORY/f"resupply-{matrix}"
        retained={k:r for k,r in metadata.items() if r["matrix"]==matrix}
        path=root/"stages.csv"
        stages=defaultdict(list)
        for row in read(path):
            if row["case"] in retained:
                stages[row["case"]].append(row)
        files.append(path)
        path=root/"censuses.csv"
        archives=defaultdict(dict)
        for row in read(path):
            if row["case"] in retained:
                archives[row["case"]][row["rule"]]=row
        files.append(path)
        for name,meta in sorted(retained.items()):
            result, individuals=case_record(meta,stages[name],nutrition[name],archives[name])
            summary.append(result)
            people.extend(individuals)
    check(len(summary)==444,"unexpected B06 follow-up cohort count")
    output.mkdir(parents=True,exist_ok=True)
    for name,values in (("cohort_worlds",summary),("first_census_larvae",people),("cohort_summary",list(summarize(summary,people)))):
        (output/f"{name}.csv").write_bytes(table(values))
    write_json(output/"receipt.json",dict(worlds=len(summary),first_census_larvae=len(people),old_readers_preserved=True,
        original_b06_status="INSUFFICIENT",files={path.relative_to(ROOT).as_posix():sha(path) for path in files}))
    print(f"Reproduced both fixed B06 readers for {len(summary)} selected worlds and tracked {len(people)} first-census larvae")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output",type=Path)
    analyze(parser.parse_args().output)
