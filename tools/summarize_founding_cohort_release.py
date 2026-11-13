"""Reproduce the protected-scope endpoints without changing their gate."""

import argparse
from collections import defaultdict
from fractions import Fraction
import gzip
import json
from pathlib import Path
from statistics import median

from analyze_s6_4_wp6b import check, rows
from final_core_b06_cohorts import stage_occupancy
from run_founding_cohort_release import COUNTS, roster
from run_integrated_founding import DAY
from run_s6_4_wp6b import ROOT, write_json
from verify_ecological_closure import write_csv


REFERENCE = ROOT / "experiments/s6_4_ecological_mechanism_closure/portable-physics/joint/analysis"
POPULATIONS = ("borisovka", "st_petersburg")
LAYOUTS = ("shaft", "dogleg")
SEEDS = {1, 7, 19, 42, 43, 97}
OUTCOMES = ("first_census_larvae", "first_cohort_eclosed_by_day55", "first_cohort_eclosed",
            "first_cohort_pupated", "first_cohort_water_deaths", "first_cohort_energy_deaths", "first_cohort_censored",
            "first_cohort_no_ration", "first_cohort_no_protein_uptake", "queen_alive_120", "queen_alive_150",
            "adult_water_absorption_ug", "collections", "deliveries", "queen_gifts",
            "late_born_adults", "soil_parcels", "at_least_timing_match", "exact_timing_match", "joint")


def reference_cohort():
    reference = [r for r in rows((REFERENCE / "worlds.csv").read_bytes()) if
                 r["treatment"] == "clock" and r["source"] == "balanced" and r["reserve"] == "5500"]
    check(len(reference) == 24, "changed historical clock-only cohort")
    stages = {r["case"]: [] for r in reference}
    for record in rows(gzip.decompress((REFERENCE / "stages.csv.gz").read_bytes())):
        if record["case"] in stages:
            stages[record["case"]].append(record)
    clock = defaultdict(dict)
    for r in reference:
        case = stages[r["case"]]
        first = next((ids[1] for _, ids in stage_occupancy(case, 150 * DAY) if ids[1]), frozenset())
        all_adults = [s for s in case if s["stage"] == "3" and int(s["ant"]) in first]
        check(len(first) == int(r["first_census_larvae"]) and len(all_adults) == int(r["first_cohort_eclosed"]),
              "historical identity result differs")
        clock[r["population"], r["layout"]][int(r["seed"])] = (
            sum(int(s["enter_ms"]) <= 55 * DAY for s in all_adults), len(first))
    check(all(set(clock[p, l]) == SEEDS for p in POPULATIONS for l in LAYOUTS), "historical cohort seeds differ")
    return clock


def summarize(evidence):
    clock = reference_cohort()
    cells, comparisons, decision = [], [], {}
    for panel in ("extended", "correction"):
        complete = rows((evidence / panel / "analysis/worlds.csv").read_bytes())
        expected = {case["case"]: case for _, case, mode, _ in roster(panel) if mode == "observed"}
        check(len(complete) == len({r["case"] for r in complete}), "duplicate completed world")
        check(set(r["case"] for r in complete) <= expected.keys(), "unknown observation")
        missing = expected.keys() - {r["case"] for r in complete}
        failures = json.loads((evidence / panel / "analysis/failures.json").read_bytes())
        check(missing == {r["case"] for r in failures if r["case"] in expected}, "world failure denominator changed")
        for model in sorted({c["panel"] for c in expected.values()}):
            data = [r for r in complete if r["panel"] == model]
            controls_pass = True
            model_cells = []
            for pop in POPULATIONS:
                for layout in LAYOUTS:
                    for supply, reserve in (("balanced", "5500"), ("balanced", "5250"), ("limited", "5500"),
                                            ("blocked", "5500"), ("absent", "5500"), ("no-protein", "5500")):
                        group = [r for r in data if (r["population"], r["layout"], r["source"], r["reserve"]) ==
                                 (pop, layout, supply, reserve)]
                        check({int(r["seed"]) for r in group} <= SEEDS, "out-of-protocol seed")
                        result = dict(panel=panel, model=model, population=pop, layout=layout, supply=supply,
                                      reserve_ug=int(reserve), completed=len(group), denominator=len(SEEDS))
                        result.update({key: sum(int(r.get(key) or 0) for r in group) for key in OUTCOMES})
                        if supply == "balanced":
                            result["engineering_joint_status"] = "PASS" if len(group) == len(SEEDS) and result["joint"] >= 4 else "FAIL"
                        elif supply in ("blocked", "absent"):
                            controls_pass &= len(group) == len(SEEDS) and not (result["collections"] or result["deliveries"])
                        elif supply == "no-protein":
                            controls_pass &= len(group) == len(SEEDS) and all(
                                not int(r["worker_protein_assimilated_lower_bound_ug"]) for r in group)
                        model_cells.append(result)
            nominal = [r for r in model_cells if r["supply"] == "balanced" and r["reserve_ug"] == 5500]
            by_population = []
            for pop in POPULATIONS:
                subset = [r for r in nominal if r["population"] == pop]
                clock_adults, clock_count = (sum(x) for x in zip(*(c for layout in LAYOUTS for c in clock[pop, layout].values())))
                adults = sum(r["first_cohort_eclosed_by_day55"] for r in subset)
                count = sum(r["first_census_larvae"] for r in subset)
                passed = bool(count and all(r["completed"] == len(SEEDS) and r["first_cohort_eclosed_by_day55"] for r in subset)
                              and Fraction(adults, count) >= Fraction(clock_adults, clock_count))
                by_population.append(dict(panel=panel, model=model, population=pop, day55_first_adults=adults,
                                          first_census_larvae=count, clock_day55_first_adults=clock_adults,
                                          clock_first_census_larvae=clock_count,
                                          day55_early_cohort_status="PASS" if passed else "FAIL"))
            joint = all(r.get("engineering_joint_status", "PASS") == "PASS" for r in model_cells)
            early = all(r["day55_early_cohort_status"] == "PASS" for r in by_population)
            decision[model] = dict(joint="PASS" if joint else "FAIL", first_cohort="PASS" if early else "FAIL",
                                   controls="PASS" if controls_pass else "FAIL",
                                   missing_worlds=sum(expected[name]["panel"] == model for name in missing),
                                   complete_count_matches={rule: sum(int(r[f"{rule}_timing_match"]) for r in data)
                                                           for rule in ("exact", "at_least")},
                                   typical_work_span_days=median(float(r["work_span_days"]) for r in data) if data else None)
            cells.extend(model_cells)
            comparisons.extend(by_population)
        check(len(expected) == COUNTS[panel] - 4, "durable or observation controls counted as worlds")
    return cells, comparisons, decision


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    cells, contrasts, decision = summarize(args.evidence)
    if args.check:
        for name, results in (("protected_cells", cells), ("early_cohort_guard", contrasts)):
            saved = rows((args.output / (name + ".csv")).read_bytes())
            check(len(saved) == len(results) and all(all(row[k] == str(v) for k, v in computed.items())
                  for row, computed in zip(saved, results, strict=True)), f"derived {name} differs")
        check(json.loads((args.output / "protected_decision.json").read_bytes()) == decision, "derived decision differs")
    else:
        args.output.mkdir(parents=True, exist_ok=True)
        write_csv(args.output / "protected_cells.csv", cells)
        write_csv(args.output / "early_cohort_guard.csv", contrasts)
        write_json(args.output / "protected_decision.json", decision)
    print(json.dumps(decision, sort_keys=True))
