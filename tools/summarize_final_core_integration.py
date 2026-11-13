"""Summarize paired ecological worlds without using worker events as replicates."""

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from random import Random
from statistics import mean, median

from analyze_s6_4_wp6b import check
from final_core_integration import POPULATIONS, SEEDS
from final_core_performance_study import wilson
from founding_qualification_witnesses import table
from profile_s6_4_wp6b import percentile


DAY = 86_400_000
PAIR_METRICS = ("observed_departures", "collections", "deliveries", "valid_loaded_trips", "g_actual_trip", "complete",
                "queen_alive_150", "naive_trail_label_then_delivery", "completed_soil_parcels", "worker_path_m")
ARMS = (("compact-marked","compact-blind"), ("shaft-marked","shaft-blind"),
        ("compact-blind","compact-silent"), ("shaft-marked","compact-marked"),
        ("shaft-fast-marked","shaft-marked"), ("shaft-fast-blocked","shaft-blocked"))


def value(row, key):
    return float(row[key] or 0)


def summarize(matrix, shaft, clock, output):
    groups = defaultdict(dict)
    for path in (matrix,shaft,clock):
        with (path/"worlds.csv").open(newline="",encoding="utf-8") as stream:
            for row in csv.DictReader(stream):
                population, seed, arm = row["case"].split("-",2)
                check(int(seed) not in groups[population,arm],"duplicate independent world")
                groups[population,arm][int(seed)] = row
    rows, paired = [], []
    for (population,arm), data in sorted(groups.items()):
        check(set(data) == set(SEEDS),"incomplete seed panel")
        cases = list(data.values())
        n = len(cases)
        result = dict(population=population,arm=arm,worlds=n)
        for endpoint in ("complete", "joint_chain", "g_eclosion", "g_actual_trip", "g_sustained_worker", "g_larval_uptake",
                         "g_queen_uptake", "g_late_eclosion", "queen_alive_150"):
            count = sum(int(row[endpoint]) for row in cases)
            lo,hi=wilson(count,n)
            result.update({endpoint:count,f"{endpoint}_lo":lo,f"{endpoint}_hi":hi})
        result["soil_worlds"] = sum(value(row,"completed_soil_parcels")>0 for row in cases)
        for endpoint in ("events","eclosed","workers_censored","adult_energy_deaths","adult_water_deaths","worker_moves",
                         "worker_committed_rests","worker_care_completed","worker_care_known_ms","deposited_units",
                         "worker_trail_labels","naive_trail_label_then_delivery","observed_departures","departures_after_other_mark",
                         "valid_loaded_trips","completed_soil_parcels","excavated_q3","filled_q3","first_census_eclosed","first_census_k",
                         "delivered_c","delivered_p","delivered_w","worker_protein_assimilated_lower_bound_ug"):
            result[endpoint] = sum(value(row,endpoint) for row in cases)
        exposed = sum(value(row,f"worker_{program}_residence_ms") for row in cases
                      for program in ("paused","rest","nurse","forage","excavate"))
        result["worker_exposure_days"] = exposed / DAY
        for program in ("paused","rest","nurse","forage","excavate"):
            result[f"worker_{program}_residence_share"] = sum(value(row,f"worker_{program}_residence_ms") for row in cases) / exposed if exposed else None
        terminal = [float(row["queen_death_ms"])/DAY for row in cases if row["queen_death_ms"]]
        result["queen_deaths_with_positive_depot_c"] = sum(value(row,"depot_c_at_queen_death_ug")>0 for row in cases)
        result["queen_death_median_days_conditional"] = median(terminal) if terminal else None
        for endpoint in ("exact_larval_census_days","exact_total_census_days","at_least_larval_census_days","at_least_total_census_days",
                         "first_load_to_delivery_ms"):
            values = [float(row[endpoint]) for row in cases if row[endpoint]]
            result[f"{endpoint}_n"] = len(values)
            result[f"{endpoint}_median"] = median(values) if values else None
        rows.append(result)
    rng=Random(640942)
    for population in POPULATIONS:
        for treatment,control in ARMS:
            a,b=groups[population,treatment],groups[population,control]
            for endpoint in (*PAIR_METRICS,"first_load_to_delivery_ms"):
                selected=[seed for seed in SEEDS if endpoint!="first_load_to_delivery_ms" or a[seed][endpoint] and b[seed][endpoint]]
                if not selected:
                    continue
                differences=[value(a[seed],endpoint)-value(b[seed],endpoint) for seed in selected]
                draws=sorted(mean(rng.choices(differences,k=len(differences))) for _ in range(4096))
                paired.append(dict(population=population,treatment=treatment,control=control,endpoint=endpoint,
                    matched_seed_pairs=len(selected),mean_difference=mean(differences),minimum=min(differences),maximum=max(differences),
                    seed_bootstrap_lo=percentile(draws,.025),seed_bootstrap_hi=percentile(draws,.975)))
    output.mkdir(parents=True,exist_ok=True)
    (output/"group_summary.csv").write_bytes(table(rows))
    (output/"paired_world_contrasts.csv").write_bytes(table(paired))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for arg in ("matrix","shaft","clock","output"):
        parser.add_argument(arg,type=Path)
    args=parser.parse_args()
    summarize(args.matrix,args.shaft,args.clock,args.output)
