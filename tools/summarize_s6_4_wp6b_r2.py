"""Report paired R2 first meals, development and finite-water follow-up."""

import argparse
from collections import Counter, defaultdict
import csv
import gzip
from pathlib import Path
from random import Random
from statistics import median

from analyze_s6_4_wp6b import DAY_MS, csv_out, interval
from run_s6_4_wp6b import sha, write_json
from run_s6_4_wp6b_r2 import ROOT, declared_cases


def read(path):
    reader = gzip.open if path.suffix == ".gz" else open
    with reader(path, "rt", encoding="utf-8", newline="") as stream:
        yield from csv.DictReader(stream)


def number(row, key):
    return int(row.get(key) or 0)


def gini(values):
    total = sum(values)
    if not total:
        return None
    n = len(values)
    return sum((2 * i - n - 1) * x for i, x in enumerate(sorted(values), 1)) / (n * total)


def summarize_individuals(folder, cases, *, old_meals=None):
    people, counters, adults = defaultdict(list), defaultdict(Counter), []
    for individual in read(folder / "individuals.csv.gz"):
        name = individual["case"]
        if name not in cases:
            continue
        c = counters[name]
        people[name].append(number(individual, "maternal_p_ug"))
        c["births"] += 1
        c["pupations"] += bool(individual["pupation_ms"])
        if individual["hatch_ms"]:
            c["hatches"] += 1
            c["exposed_hatches"] += bool(individual["first_local_contact_ms"])
            c["maternal_first_meals"] += bool(individual["meal_ms"])
            c["early_maternal_first_meals"] += bool(individual["meal_ms"]) and (
                number(individual, "meal_ms") - number(individual, "hatch_ms") <= 6 * 3_600_000)
            meals = old_meals.get((name, individual["ant"]), 0) if old_meals is not None else number(individual, "effective_protein_meals")
            c[f"positive_protein_meals_{min(meals, 5)}"] += 1
            c["cued_hatches"] += bool(individual.get("local_hatch_cue_ms"))
            c["mobilizing_larvae"] += bool(individual.get("emergency_conversion_ms"))
            c["mobilizations"] += number(individual, "emergency_conversions")
            c["actual_larval_uptake_after_meal"] += bool(individual["uptake_after_meal_ms"])
            c["tissue_requirement_met"] += bool(individual["tissue_met_ms"])
            c["larval_energy_deaths"] += not individual["pupation_ms"] and individual["death_cause"] == "1"
            c["larval_water_deaths"] += not individual["pupation_ms"] and individual["death_cause"] == "2"
            c["larval_right_censored"] += not individual["pupation_ms"] and individual["outcome"] == "RIGHT_CENSORED"
        if not individual["eclosion_ms"]:
            continue
        c["adults"] += 1
        c["adult_energy_deaths"] += individual["death_cause"] == "1"
        c["adult_water_deaths"] += individual["death_cause"] == "2"
        c["adult_right_censored"] += individual["outcome"] == "RIGHT_CENSORED"
        age = number(individual, "terminal_ms") - number(individual, "eclosion_ms")
        moved = number(individual, "moves") > 0
        drank = number(individual, "adult_water_absorbed_ug") > 0
        c["adults_with_water_uptake"] += drank
        c["adult_water_absorbed_ug"] += number(individual, "adult_water_absorbed_ug")
        for key in ("collected_water_ug", "delivered_water_ug", "gift_water_out_ug", "completed_care_acts"):
            c[f"adult_{key}"] += number(individual, key)
        for days in (1, 7):
            c[f"adults_at_least_{days}d"] += age >= days * DAY_MS
            c[f"adults_censored_before_{days}d"] += age < days * DAY_MS and individual["outcome"] == "RIGHT_CENSORED"
            c[f"adults_at_least_{days}d_and_moved"] += age >= days * DAY_MS and moved
        adults.append(individual | {"adult_age_at_exit_ms": age, "actual_move": int(moved), "positive_water_uptake": int(drank)})
    return counters, {name: gini(values) for name, values in people.items()}, adults


def water_pairs(rows, output):
    arms = ("water-reachable", "water-blocked", "water-absent")
    blocks = defaultdict(dict)
    for row in rows:
        if row["group"] == "water":
            blocks[row["model"], row["population"], row["seed"]][row["arm"]] = row
    pairs = []
    for (model, pop, seed), values in sorted(blocks.items()):
        assert set(values) == set(arms)
        for arm in arms[1:]:
            a, b = values[arm], values[arms[0]]
            pairs.append(dict(model=model, population=pop, seed=seed, control=arm,
                              **{f"delta_{key}": number(b, key) - number(a, key) for key in
                                 ("adults", "adults_with_water_uptake", "adult_water_absorbed_ug", "adults_at_least_1d",
                                  "adults_at_least_7d", "adults_at_least_7d_and_moved", "adult_energy_deaths",
                                  "adult_water_deaths", "adult_right_censored")}))
    csv_out(output / "water_paired_worlds.csv", pairs)
    groups = defaultdict(list)
    for row in pairs:
        groups[row["model"], row["population"], row["control"]].append(row)
    rng = Random(640601)
    summary = []
    for (model, pop, arm), records in sorted(groups.items()):
        assert len(records) == 6
        for key in (k for k in records[0] if k.startswith("delta_")):
            values = [r[key] for r in records]
            lo, hi = interval([sum(rng.choices(values, k=len(values))) / len(values) for _ in range(4096)])
            summary.append(dict(model=model, population=pop, control=arm, endpoint=key, worlds=len(values),
                                mean_delta=sum(values) / len(values), ci95_low=lo, ci95_high=hi))
    csv_out(output / "water_paired_summary.csv", summary)


def cue_summary(histories, by_model, output):
    counts = defaultdict(Counter)
    for model, source in histories.items():
        if model == "r1":
            continue
        for cue in read(source / "cues.csv.gz"):
            case = by_model[model][cue["case"]]
            row = counts[model, case["population"], case["group"], case["arm"], case["care"], case["high_risk"]]
            row["cues"] += 1
            for field in ("wake_event", "opportunity_event", "selected_event", "started_event", "terminal_event", "meal_event"):
                row[field] += bool(cue[field])
            row["confirmed_interruption"] += cue["terminal_phase"] == "4"
            row["completed_without_positive_payment"] += cue["terminal_phase"] == "3" and not cue["meal_event"]
    keys = ("model", "population", "group", "arm", "care", "high_risk")
    csv_out(output / "cue_outcomes.csv", [dict(zip(keys, key, strict=True), **row) for key, row in sorted(counts.items())])


def spacing_controls(models, output):
    scope = ROOT / "experiments/s6_4_wp6b/analysis/cases.csv"
    old = {r["case"]: r for r in read(scope)}
    rows = []
    for _, case in declared_cases("v1"):
        if case.get("arm") not in ("opening_lay_spacing-low", "lay_interval-high"):
            continue
        name = case["case"]
        r = old[name]
        rows.append(dict(case=name, population=case["population"], seed=case["software_seed"], arm=case["arm"],
                         v1_eclosed=r["eclosed"], v1_first_worker_ms=r["first_worker_ms"],
                         **{f"{m}_{key}": data[name].get(key, 0) for m, data in models.items()
                            if m in ("r1","h1","h2","both") for key in
                            ("adults","hatches","maternal_first_meals","pupations","tissue_requirement_met","first_worker_ms")}))
    assert len(rows) == 24 and sum(number(row,"v1_eclosed") > 0 for row in rows) == 5
    csv_out(output / "wider_spacing_controls.csv", rows)


def summarize(root, output):
    histories = {m: root / f"{m}-tracks" for m in ("h1", "h2", "both", "water-r1", "water-both")}
    base = ROOT / "experiments/s6_4_wp6b_r1"
    histories["r1"] = root / "r1_tracks"
    old_meals = {(r["case"], r["ant"]): int(r["effective_protein_meals"]) for r in read(base / "candidate_paths/larvae.csv.gz")}
    results, workers = [], []
    by_model = {}
    for model, source in histories.items():
        declared = {c["case"]: c for _, c in declared_cases(model)}
        counts, concentration, adults = summarize_individuals(source, declared, old_meals=old_meals if model == "r1" else None)
        scope = base / "analysis" if model == "r1" else root / f"{model}-analysis"
        budgets = {r["case"]: r for r in read(scope / "cases.csv")}
        normalized = {}
        for name, c in declared.items():
            b = budgets[name]
            stats = counts[name]
            assert stats["hatches"] == number(b, "hatch") and stats["adults"] == number(b, "eclosed"), name
            assert sum(stats[f"positive_protein_meals_{n}"] for n in range(6)) == stats["hatches"], name
            p = c["parameters"]
            risk = c["group"] == "primary" and c["population"] == "borisovka" and p["egg_lipid"] == 11 and p["egg_basal"] == 22_000_000
            row = dict(model=model, case=name, population=c["population"], seed=c["software_seed"],
                       group=c["group"], profile=c.get("profile_index"), care=int(c["care_enabled"]),
                       arm=c.get("arm", "ordinary"), high_risk=int(risk), status=b["status"],
                       maternal_protein_gini_all_offspring=concentration.get(name), **stats)
            for key in ("queen_death_ms", "queen_death_cause", "queen_lipid_left", "queen_protein_left", "queen_water_left", "source_facts",
                        "actual_rations", "ration_lipid", "ration_protein", "ration_water", "first_worker_ms"):
                row[key] = b.get(key)
            results.append(row)
            normalized[name] = row
        by_model[model] = normalized
        if model.startswith("water-"):
            start = {(r["case"], r["ant"]): r for r in read(source / "points.csv.gz") if r["point"] == "ECLOSION"}
            workers.extend(dict(model=model, arm=declared[r["case"]]["arm"], population=declared[r["case"]]["population"], **r,
                                **{f"at_eclosion_{k}": start[r["case"], r["ant"]][k] for k in
                                   ("body_nj", "owned_lipid_ug", "body_water_ug", "crop_water_ug", "env_water_ug", "nest_water_ug")})
                           for r in adults)
    output.mkdir(parents=True)
    csv_out(output / "cases.csv", results)
    csv_out(output / "water_adults.csv", workers)
    water_pairs(results, output)
    cue_summary(histories, by_model, output)
    spacing_controls(by_model, output)
    group_keys = ("model", "population", "group", "arm", "care", "high_risk")
    fields = sorted({key for row in results for key in row if key not in (*group_keys, "status", "case", "seed", "profile",
                     "maternal_protein_gini_all_offspring", "queen_death_ms", "queen_death_cause", "first_worker_ms")})
    groups = defaultdict(list)
    for row in results:
        groups[tuple(row[k] for k in group_keys)].append(row)
    aggregates = []
    for group, records in sorted(groups.items()):
        ages = [int(r["first_worker_ms"]) / DAY_MS for r in records if r["first_worker_ms"]]
        gini_values = [r["maternal_protein_gini_all_offspring"] for r in records if r["maternal_protein_gini_all_offspring"] is not None]
        aggregates.append(dict(zip(group_keys, group, strict=True), worlds=len(records), worlds_eclosed=len(ages),
                               first_worker_median_day=median(ages) if ages else None,
                               maternal_protein_gini_median=median(gini_values) if gini_values else None,
                               queens_died=sum(bool(r["queen_death_ms"]) for r in records),
                               worlds_with_adult_water_uptake=sum(number(r, "adults_with_water_uptake") > 0 for r in records),
                               **{key: sum(number(r, key) for r in records) for key in fields}))
    csv_out(output / "groups.csv", aggregates)

    rng = Random(640601)
    paired, contrasts = [], []
    for before, after in (("r1", "h1"), ("r1", "h2"), ("r1", "both"), ("h2", "both"), ("h1", "both")):
        for pop in ("borisovka", "st_petersburg"):
            for level in ("all", "high-risk"):
                if pop != "borisovka" and level == "high-risk":
                    continue
                blocks = defaultdict(list)
                for name, a in by_model[before].items():
                    if a["population"] != pop or a["group"] != "primary" or not a["care"] or (level == "high-risk" and not a["high_risk"]):
                        continue
                    b = by_model[after][name]
                    item = dict(before=before, after=after, population=pop, scope=level, profile=a["profile"], seed=a["seed"], case=name,
                                delta_world_eclosed=int(bool(b.get("adults"))) - int(bool(a.get("adults"))))
                    for key in ("hatches", "maternal_first_meals", "early_maternal_first_meals", "pupations", "adults", "tissue_requirement_met"):
                        item["delta_" + key] = number(b, key) - number(a, key)
                    paired.append(item)
                    blocks[a["profile"]].append(item)
                cohorts = list(blocks.values())
                all_rows = [r for cohort in cohorts for r in cohort]
                for endpoint in (key for key in all_rows[0] if key.startswith("delta_")):
                    distribution = []
                    for _ in range(4096):
                        values = [r[endpoint] for cohort in rng.choices(cohorts, k=len(cohorts)) for r in rng.choices(cohort, k=len(cohort))]
                        distribution.append(sum(values) / len(values))
                    lo, hi = interval(distribution)
                    contrasts.append(dict(before=before, after=after, population=pop, scope=level, endpoint=endpoint,
                                          worlds=len(all_rows), profiles=len(cohorts), mean_delta=sum(r[endpoint] for r in all_rows) / len(all_rows),
                                          ci95_low=lo, ci95_high=hi))
    csv_out(output / "paired_worlds.csv", paired)
    csv_out(output / "paired_summary.csv", contrasts)
    write_json(output / "receipt.json", dict(outputs={p.name: sha(p) for p in sorted(output.iterdir())},
               inputs={m: sha(p / "receipt.json") for m, p in histories.items()},
               r1_protein_doses_sha256=sha(base / "candidate_paths/larvae.csv.gz"), seed=640601, bootstrap=4096))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    summarize(args.root, args.output)
