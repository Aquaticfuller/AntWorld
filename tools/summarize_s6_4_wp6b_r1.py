"""Compare paid feeding, competition and founding endpoints in paired simulated worlds."""

import argparse
from collections import Counter, defaultdict
import csv
import gzip
import json
from pathlib import Path
from random import Random
from statistics import mean, median

from analyze_s6_4_wp6b import csv_out, interval
from run_s6_4_wp6b import write_json
from wp6a_budget_screen import DAY_MS, POPULATIONS


def read(path):
    with (gzip.open(path, "rt", encoding="utf-8", newline="") if path.suffix == ".gz" else
          path.open(encoding="utf-8", newline="")) as stream:
        return list(csv.DictReader(stream))


def describe_paths(root, wanted):
    cases = {r["case"]: r for r in read(root/"cases.csv") if r["case"] in wanted}
    larvae, meals = defaultdict(list), defaultdict(list)
    for kind, values in (("larvae", larvae), ("meals", meals)):
        for row in read(root/f"{kind}.csv.gz"):
            if row["case"] in cases:
                values[row["case"]].append(row)
    return cases, larvae, meals


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("v1", "r1", "candidate", "out"):
        parser.add_argument("--"+name, type=Path, required=True)
    args = parser.parse_args()
    primary = [r for r in read(args.r1/"cases.csv") if r["group"] in ("primary", "check")]
    wider = [r for r in read(args.r1/"cases.csv") if r["group"] == "wider" and
             r["arm"] in ("opening_lay_spacing-low", "lay_interval-high")]
    named = {r["case"] for r in primary+wider}
    first = describe_paths(args.v1, named)
    second = describe_paths(args.r1, named)
    official = {r["case"]: r for r in read(args.candidate/"cases.csv")}
    rng = Random(640601)
    groups, paired, difference = [], [], []
    distribution_keys = [f"doses_{n}" for n in range(7)]
    count_keys = ("births", "hatch", "visible_opportunities", "feed_selected", "feed_started", "feed_completed",
                  "feed_interrupted", "meals_seen_again", "meals_selected_again", "tissue_met", "pupa", "eclosed",
                  "larval_death_cause_1", "larval_death_cause_2", "larval_right_censored", *distribution_keys)

    def number(row, key):
        return int(row.get(key) or 0)

    def median_field(rows, key):
        values = [float(r[key]) for r in rows if r.get(key)]
        return median(values) if values else None

    for pop in POPULATIONS:
        for group in ("primary", "check"):
            for care in ("0", "1"):
                selection = [r["case"] for r in primary if (r["population"],r["group"],r["care"]) == (pop,group,care)]
                for label, (cases, larvae, meals) in (("v1", first), ("r1", second)):
                    rows = [cases[name] for name in selection]
                    recipients = [row for name in selection for row in larvae[name]]
                    doses = [row for name in selection for row in meals[name]]
                    row = dict(population=pop, group=group, care=care, model=label, worlds=len(rows),
                               worlds_with_worker=sum(number(r,"eclosed")>0 for r in rows),
                               worlds_queen_dead=sum(bool(r["queen_death_ms"]) for r in rows),
                               median_queen_death_day=(median_field(rows,"queen_death_ms") or 0)/DAY_MS or None,
                               median_terminal_maternal_p_ug=median_field(rows,"queen_terminal_p_ug"),
                               median_protein_gini=median_field(rows,"protein_gini_including_zeros"),
                               doses_lipid_ug=sum(number(d,"lipid_ug") for d in doses),
                               doses_protein_ug=sum(number(d,"protein_ug") for d in doses),
                               doses_water_ug=sum(number(d,"water_ug") for d in doses),
                               first_worker_median_day=median([min(int(l["adult_ms"]) for l in larvae[name] if l["adult_ms"])/DAY_MS
                                   for name in selection if number(cases[name],"eclosed")]) if any(number(r,"eclosed") for r in rows) else None,
                               **{key:sum(number(r,key) for r in rows) for key in count_keys})
                    assert sum(row[key] for key in distribution_keys) == len(recipients) == row["hatch"]
                    if label == "r1":
                        for key in ("repeat_selected", "repeat_expired", "repeat_unavailable", "repeated_positive_protein", "repeated_interrupted"):
                            row[key] = sum(number(official[name],key) for name in selection)
                    groups.append(row)
                grid = defaultdict(list)
                for name in selection:
                    before, after = first[0][name], second[0][name]
                    changes = {f"delta_{key}":number(after,key)-number(before,key) for key in count_keys}
                    changes["delta_worker_world"] = int(number(after,"eclosed")>0)-int(number(before,"eclosed")>0)
                    row = dict(case=name, population=pop, group=group, care=care, seed=after["seed"],
                               profile=official[name]["profile"], **changes)
                    paired.append(row)
                    grid[row["profile"]].append(changes)
                profiles = list(grid.values())
                for key in ("delta_worker_world", "delta_feed_completed", "delta_doses_0", "delta_tissue_met", "delta_pupa"):
                    draws = [mean(row[key] for p in rng.choices(profiles,k=len(profiles)) for row in rng.choices(p,k=len(p)))
                             for _ in range(4096)]
                    low, high = interval(draws)
                    difference.append(dict(population=pop, group=group, care=care, endpoint=key,
                                           estimate=mean(r[key] for p in profiles for r in p), ci95_lo=low, ci95_hi=high,
                                           n_profiles=len(profiles), worlds=len(selection)))
    matched_wider = []
    for r in wider:
        name = r["case"]
        for label, (cases, larvae, _) in (("v1", first),("r1", second)):
            row = cases[name]
            offspring = larvae[name]
            first_adult = min((l for l in offspring if l["adult_ms"]), key=lambda l: int(l["adult_ms"]), default=None)
            matched_wider.append(dict(case=name, population=r["population"], seed=r["seed"], model=label, arm=r["arm"],
                **{k:number(row,k) for k in ("births","hatch","wakes_with_contact","feed_completed","pupa","eclosed")},
                first_adult=first_adult["ant"] if first_adult else None,
                first_adult_ms=first_adult["adult_ms"] if first_adult else None,
                first_adult_meals=first_adult["effective_protein_meals"] if first_adult else None,
                first_adult_contact_wakes=first_adult["contact_wakes"] if first_adult else None))
    options = defaultdict(Counter)
    for row in official.values():
        if row["group"] == "r1-sensitivity" or (row["group"] == "micro" and row["arm"] == "nominal"):
            options[row["population"],row["sensitivity"] or "nominal"].update(
                worlds=1, workers=int(number(row,"eclosed")>0), larvae=number(row,"hatch"),
                pupae=number(row,"pupation"), rations=number(row,"actual_rations"), repeats=number(row,"repeated_positive_protein"))
    args.out.mkdir(parents=True)
    for name, rows in (("populations.csv",groups),("paired_worlds.csv",paired),("paired_bootstrap.csv",difference),
                       ("wider_success_controls.csv",matched_wider),
                       ("option_sensitivity.csv",[dict(population=p, option=o, **c) for (p,o),c in sorted(options.items())])):
        csv_out(args.out/name,rows)
    print(json.dumps([r for r in groups if r["group"] == "primary" and r["care"] == "1"], indent=2))


if __name__ == "__main__":
    main()
