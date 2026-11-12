"""Summarize WP-2 trials by seed, origin pair, and original biological unit."""

import argparse
from collections import Counter, defaultdict
import csv
import io
import json
from pathlib import Path
import random
from statistics import fmean, median, stdev

from analyze_s6_3_2_performance import quantile
from analyze_s6_4_wp2 import DAY, HOUR
from read_s6_4_rm02_sidecar import PROGRAMS, require
from run_s6_4_wp2 import ROOT, sha256, write
from summarize_s6_4_rm02_r1 import grouped, rows


LITERATURE = ROOT / "experiments/s6_3_3/literature"
B01 = LITERATURE / "Reversibility_of_worker_effect_3_days.csv"
B02 = LITERATURE / "B02_retrieval.csv"
ACTIVITY_METRICS = ("active_program_percent", "Rest_percent", "moves_per_worker_day", "committed_path_m_per_worker_day",
                    "dissipated_nj_per_worker_h", "water_lost_ug_per_worker_day", "worker_energy_deaths",
                    "known_active_percent", "unobserved_activity_percent", "queen_energy_nj", "queen_uptake_carb_ug",
                    "queen_eggs", "confirmed_feed_bouts", "placed")


def summarize(values):
    values = list(values)
    if not values:
        return dict(n=0, mean="", median="", minimum="", maximum="", sd="")
    return dict(n=len(values), mean=fmean(values), median=median(values), minimum=min(values), maximum=max(values),
                sd=stdev(values) if len(values) > 1 else "")


def interval(lhs, rhs=None):
    rng = random.Random(64203)
    draws = [fmean(rng.choices(lhs, k=len(lhs))) -
             (fmean(rng.choices(rhs, k=len(rhs))) if rhs is not None else 0) for _ in range(4096)]
    return quantile(draws, .025), quantile(draws, .975)


def emit(folder, name, records, check):
    first, *remaining = records
    text = io.StringIO(newline="")
    writer = csv.DictWriter(text, list(first), lineterminator="\n")
    writer.writeheader()
    writer.writerow(first)
    writer.writerows(remaining)
    target = folder / name
    encoded = text.getvalue().encode()
    if check:
        require(encoded == target.read_bytes(), f"WP-2 comparison differs: {name}")
    else:
        target.write_bytes(encoded)


def activity(analysis, runs):
    living = grouped(rows(analysis / "individuals.csv"), "case")
    for run in runs:
        mode = run["mode"]
        if mode not in ("activity", "integrated"):
            continue
        ants = living[(run["case"],)]
        workers = [r for r in ants if r["caste"] == "worker" and r["initial"] == "1" and r["entry_stage"] == "adult"]
        require(len(workers) == int(run["workers"]), "initial adult worker cohort differs")
        queen, = [r for r in ants if r["caste"] == "queen"]

        def total(field):
            return sum(float(r[field]) for r in workers)

        adult = total("adult_physiology_ms")
        life = total("alive_ms")
        deaths = [r for r in workers if r["death_cause"] == "energy_depleted"]
        last_uptake_lags = [int(r["death_ms"]) - int(r["last_carb_uptake_ms"]) for r in deaths if r["last_carb_uptake_ms"]]
        yield dict(**{key: run[key] for key in ("case", "mode", "arm", "workers", "seed", "origin")},
                   observed_workers=len(workers), adult_worker_ms=int(adult), worker_alive_ms=int(life),
                   active_program_percent=100 * total("active_program_ms") / adult,
                   **{f"{p}_percent": 100 * total(f"{p}_ms") / adult for p in PROGRAMS},
                   known_active_percent=100 * total("known_active_ms") / life,
                   known_inactive_percent=100 * total("known_inactive_ms") / life,
                   timed_locomotor_percent=100 * total("timed_locomotor_ms") / life,
                   unobserved_activity_percent=100 * total("unobserved_activity_ms") / life,
                   moves_per_worker_day=DAY * sum(total(f"moves_{p}") for p in PROGRAMS) / life,
                   committed_path_m_per_worker_day=DAY * total("movement_m") / life,
                   dissipated_nj_per_worker_h=HOUR * total("dissipated_nj") / life,
                   water_lost_ug_per_worker_day=DAY * total("water_lost_ug") / life,
                   nominal_active_surcharge_nj=int(total("nominal_active_surcharge_nj")),
                   nominal_basal_nj=int(total("nominal_basal_nj")), worker_energy_deaths=len(deaths),
                   worker_deaths_with_crop_carb=sum(int(r["crop_carb_ug"]) > 0 for r in deaths),
                   worker_deaths_without_positive_carb_uptake=len(deaths) - len(last_uptake_lags),
                   median_last_carb_to_death_h=median(last_uptake_lags) / HOUR if last_uptake_lags else "",
                   queen_death=queen["death_cause"], queen_energy_nj=int(queen["energy_nj"]),
                   queen_dissipated_nj=int(queen["dissipated_nj"]), queen_exported_nj=int(queen["exported_nj"]),
                   queen_uptake_carb_ug=int(queen["uptake_carb_ug"]), queen_eggs=int(queen["eggs_laid"]),
                   confirmed_feed_bouts=int(run["confirmed_feed_bouts"]), placed=int(run["placed"]))


def activity_groups(per_case):
    for key, cases in sorted(grouped(per_case, "mode", "arm", "workers", "origin").items()):
        for endpoint in ACTIVITY_METRICS:
            values = [r[endpoint] for r in cases]
            low, high = interval(values)
            yield dict(zip(("mode", "arm", "workers", "origin"), key), endpoint=endpoint, **summarize(values),
                       mean_ci_low=low, mean_ci_high=high)


def paired(per_case):
    index = grouped(per_case, "mode", "arm", "workers", "origin")
    for (mode, arm, workers, origin), left in sorted(index.items()):
        control = ("activity", "ordinary", workers, "balanced") if mode == "activity" else (
                   "integrated", "control", workers, origin)
        if (mode, arm, workers, origin) == control:
            continue
        right = {r["seed"]: r for r in index[control]}
        require(set(right) == {r["seed"] for r in left}, "unpaired WP-2 ecology comparison")
        for endpoint in ACTIVITY_METRICS:
            diff = [r[endpoint] - right[r["seed"]][endpoint] for r in left]
            low, high = interval(diff)
            yield dict(mode=mode, treatment=arm, supply=origin, comparator=control[1], workers=workers,
                       endpoint=endpoint, seeds=len(diff), mean_difference=fmean(diff), ci_low=low, ci_high=high)


def comparison(endpoint, arm, scope, simulated, measured, interpretation):
    low, high = interval(simulated, measured)
    return dict(endpoint=endpoint, arm=arm, scope=scope, n_seeds=len(simulated), n_biological_units=len(measured),
                simulation_mean=fmean(simulated), empirical_mean=fmean(measured), empirical_sd=stdev(measured),
                simulated_minus_measured=fmean(simulated) - fmean(measured), ci_low=low, ci_high=high,
                interpretation=interpretation)


def b01(analysis):
    scans = grouped(rows(analysis / "b01_scans.csv"), "case", "window_hour")
    case_rates = []
    for (_, hour), group in scans.items():
        observed = [int(r["positive"]) for r in group if r["status"] == "OBSERVED"]
        case_rates.append(dict(arm=group[0]["arm"], seed=group[0]["seed"], window_hour=hour, scanned=len(group),
                               observed=len(observed), percent_positive=100 * fmean(observed) if observed else ""))
    empirical = grouped(rows(B01), "Treatment", "Time")
    compare = []
    for arm, hour, treatment, time in (("absent", "96", "Without_workers", "24"), ("added", "96", "With_workers", "24"),
                                       ("removed", "120", "Workers_removed", "48")):
        values = [r["percent_positive"] for r in case_rates if r["arm"] == arm and r["window_hour"] == hour
                  and r["percent_positive"] != ""]
        real = empirical[treatment, time]
        require(len({r["Box_label"] for r in real}) == len(real) == 16 and all(r["Scans"] == "50" for r in real),
                "B01 archived biological units differ")
        real_rates = [100 * int(r["Nursing"]) / int(r["Scans"]) for r in real]
        compare.append(comparison("positive_scans_percent", arm, "B01", values, real_rates, "DEVELOPMENT_OPERATOR_APPROXIMATE"))
    return case_rates, compare


def b02(runs, analysis):
    journeys = grouped(rows(analysis / "custody.csv"), "case")
    tests = []
    for r in runs:
        if r["mode"] != "b02":
            continue
        attempts = journeys.get((r["case"],), [])
        placed = [j for j in attempts if j["status"] == "PLACED"]
        timing = {}
        for k in ("first_search_selection_ms", "first_target_selection_ms", "first_contact_proxy_ms", "first_placement_ms"):
            timing[k.removesuffix("_ms") + "_s"] = (int(r[k]) - 180000) / 1000 if r[k] else ""
        tests.append(dict(**{k: r[k] for k in ("case", "arm", "layout", "origin", "seed", "brood")},
                          placed=int(r["placed"]), pickup_attempts=len(attempts), completed=len(placed),
                          interrupted=sum(j["status"] == "INTERRUPTED" for j in attempts),
                          right_censored=sum(j["status"] == "RIGHT_CENSORED" for j in attempts),
                          next_search_seen=sum(j["next_search_status"] == "SELECTED" for j in placed),
                          completed_carry_time_ms=sum(int(j["loaded_motion_ms"]) for j in placed),
                          completed_carry_m=sum(float(j["brood_path_m"]) for j in placed), **timing))
    real = grouped(({key.strip(): value for key, value in row.items()} for row in rows(B02)), "qw", "queen")
    pairs = grouped([r for r in tests if r["brood"] == "6"], "arm", "layout", "seed")
    compare, contrasts = [], []
    for arm, category in (("queen", "q"), ("trio", "w")):
        for endpoint, source in (("placed", "brood items after 10min"), ("first_contact_proxy_s", "first contact"),
                                 ("first_placement_s", "first retrieving")):
            empirical = []
            for (label, _), pair in real.items():
                if label == category:
                    require({r["same"] for r in pair} == {"0", "1"} and len(pair) == 2, "B02 source pair differs")
                    empirical.append(fmean(float(r[source]) for r in pair))
            require(len(empirical) == (79 if category == "q" else 70), "B02 raw cohort differs")
            by_layout = defaultdict(dict)
            for (label, layout, seed), pair in pairs.items():
                if label != arm:
                    continue
                require({r["origin"] for r in pair} == {"own", "foreign"} and len(pair) == 2, "unpaired simulation origins")
                by_layout[layout][seed] = fmean(600 if r[endpoint] == "" else r[endpoint] for r in pair)
            for layout, seed_values in sorted(by_layout.items()):
                interpretation = "PLACEMENT_COUNT_APPROXIMATE" if endpoint == "placed" else "CAPPED_DISTINCT_TIMING_MARKERS"
                compare.append(comparison(endpoint, arm, layout, list(seed_values.values()), empirical, interpretation))
            for layout in ("far", "split", "wall"):
                line = by_layout["line"]
                require(by_layout[layout].keys() == line.keys(), "unpaired layout seeds")
                differences = [value - line[seed] for seed, value in by_layout[layout].items()]
                low, high = interval(differences)
                contrasts.append(dict(arm=arm, layout=layout, control="line", endpoint=endpoint,
                                      seeds=len(differences), mean_difference=fmean(differences), ci_low=low, ci_high=high))
    return tests, compare, contrasts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("analysis", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    runs = list(rows(args.analysis / "runs.csv"))
    require(len(runs) == 228 and len({r["case"] for r in runs}) == 228, "need all 228 WP-2 cases")
    args.out.mkdir(parents=True, exist_ok=True)
    ecology = list(activity(args.analysis, runs))
    b01_cases, b01_compare = b01(args.analysis)
    b02_cases, b02_compare, b02_paired = b02(runs, args.analysis)
    for name, data in (("ecology_by_case.csv", ecology), ("ecology_groups.csv", list(activity_groups(ecology))),
                       ("ecology_paired.csv", list(paired(ecology))), ("b01_windows.csv", b01_cases),
                       ("b01_comparison.csv", b01_compare), ("b02_by_case.csv", b02_cases),
                       ("b02_comparison.csv", b02_compare), ("b02_layout_paired.csv", b02_paired)):
        emit(args.out, name, data, args.check)
    receipt = dict(bootstrap_seed=64203, draws=4096, cases=dict(Counter(r["mode"] for r in runs)),
                   b01_sha256=sha256(B01), b02_sha256=sha256(B02),
                   classification="DEVELOPMENT_COMPARISON_AND_ENGINEERING_DIAGNOSIS")
    path = args.out / "comparison_receipt.json"
    if args.check:
        require(json.loads(path.read_bytes()) == receipt, "comparison provenance differs")
    else:
        write(path, receipt)
    print("Verified 228 cases, paired seed strata and original B01/B02 units")


if __name__ == "__main__":
    main()
