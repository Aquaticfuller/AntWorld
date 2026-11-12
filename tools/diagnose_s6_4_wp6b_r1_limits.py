"""Locate the inherited hatch, colony count and adult survival limits from audited paths."""

import argparse
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median

from analyze_s6_4_wp6b import csv_out
from run_s6_4_wp6b import frozen_cases
from summarize_s6_4_wp6b_r1 import read
from wp6a_budget_screen import DAY_MS, POPULATIONS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    base = args.experiment
    analysis = base/"analysis"
    cases = {r["case"]: r for r in read(analysis/"cases.csv") if r["group"] == "primary" and r["care"] == "1"}
    profiles = {c["case"]: c["parameters"] for _, c in frozen_cases() if c["case"] in cases}
    stages = [r for r in read(analysis/"stage_exposure.csv") if r["case"] in cases]
    offspring = {(r["case"],r["ant"]): r for r in read(analysis/"offspring.csv") if r["case"] in cases}
    counts = {r["case"]: r for r in read(analysis/"daily_count_timing.csv") if r["case"] in cases and r["rule"] == "at_least"}
    larval_paths = [r for r in read(base/"candidate_paths/larvae.csv.gz") if r["case"] in cases]
    days = defaultdict(Counter)
    for r in stages:
        if r["stage"] not in ("2","3"):
            continue
        first, end = ((int(r[key])+DAY_MS-1)//DAY_MS for key in ("enter_ms","end_ms"))
        for day in range(first, end+int(r["outcome"] == "RIGHT_CENSORED")):
            days[r["case"],r["stage"]][day] += 1
    count_rows, edge_rows, arm_rows, workers = [], [], [], []
    for name, census in counts.items():
        k = int(census["k"])
        pupa, adult = (max(days[name,stage].values(),default=0) for stage in ("2","3"))
        count_rows.append(dict(case=name,population=cases[name]["population"],first_larval_count=k,
                               peak_daily_pupae=pupa,peak_daily_workers=adult,cumulative_eclosions=cases[name]["eclosed"],
                               matched_full_count=bool(census["total_d"])))
    for pop in POPULATIONS:
        cohort = [r for r in stages if r["stage"] == "3" and cases[r["case"]]["population"] == pop]
        durations = [int(r["age_in_stage_ms"]) for r in cohort]
        workers.append(dict(population=pop,adults=len(cohort),energy_deaths=sum(r["outcome"]=="DEATH_1" for r in cohort),
                            dehydration=sum(r["outcome"]=="DEATH_2" for r in cohort),
                            censored=sum(r["outcome"]=="RIGHT_CENSORED" for r in cohort),
                            min_alive_ms=min(durations),median_alive_ms=median(durations),max_alive_ms=max(durations)))
        selected = {name for name,p in profiles.items() if cases[name]["population"] == pop and
                    p["egg_lipid"] == 11 and p["egg_basal"] == 22_000_000}
        p = profiles[sorted(selected)[0]]
        energy = p["egg_lipid"]*p["lipid_yield"] - p["egg_basal"]*p["egg_ms"]//DAY_MS
        larvae = [r for r in larval_paths if r["case"] in selected]
        six_hours = 6*3_600_000
        arm_rows.append(dict(population=pop,worlds=len(selected),worlds_with_worker=sum(int(cases[n]["eclosed"])>0 for n in selected),
                             egg_energy_remaining_nj=energy,larval_maintenance_window_h=24*energy/p["larva_basal"],
                             larvae=len(larvae),paid_recipients=sum(bool(r["first_meal_ms"]) for r in larvae),
                             energy_deaths_before_6h=sum(r["death_cause"]=="1" and int(r["end_ms"])-int(r["hatch_ms"])<six_hours for r in larvae),
                             energy_deaths_before_24h=sum(r["death_cause"]=="1" and int(r["end_ms"])-int(r["hatch_ms"])<4*six_hours for r in larvae)))
        for r in larvae:
            if not r["first_meal_ms"] or r["first_uptake_ms"] or r["death_cause"] != "1":
                continue
            birth, meal = int(r["birth_ms"]), int(r["first_meal_ms"])
            period = profiles[r["case"]]["refill_period"]
            next_pulse = birth+((meal-birth)//period+1)*period
            end = offspring[r["case"],r["ant"]]
            edge_rows.append(dict(case=r["case"],ant=r["ant"],hatch_ms=r["hatch_ms"],meal_event=r["first_meal_event"],meal_ms=meal,
                next_nominal_pulse_ms=next_pulse,death_ms=r["end_ms"],unconverted_lipid_ug=end["terminal_lipid_ug"],
                terminal_energy_nj=end["terminal_energy_nj"],terminal_water_ug=end["terminal_water_ug"],
                received_protein_ug=r["maternal_protein_ug"],actual_positive_uptake="ABSENT"))
    args.output.mkdir(parents=True)
    for name, data in (("cohort_counts.csv",count_rows), ("hatch_budget_arms.csv",arm_rows),
                       ("unconverted_before_death.csv",edge_rows), ("adult_survival.csv",workers)):
        csv_out(args.output/name,data)


if __name__ == "__main__":
    main()
