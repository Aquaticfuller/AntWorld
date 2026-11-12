"""Compare WP-4 worlds by seed and common follow-up."""

import argparse
from collections import defaultdict
import csv
import io
from itertools import product
import json
from pathlib import Path
from random import Random
from statistics import mean

from analyze_s6_4_wp4 import DAY
from read_s6_4_rm02_sidecar import require
from s6_4_wp4_cases import SEEDS, SUPPLY
from verify_s6_4_wp3 import rows


OUTCOMES = ("births", "hatches", "pupations", "emergences", "queen_survival", "queen_followup_days",
            "received_carbs_ug", "received_protein_ug", "received_water_ug", "absorbed_carbs_ug",
            "absorbed_water_ug", "energy_nj", "hydration_ug", "exported_nj", "dissipated_nj")


def numeric(row, names):
    return {k: int(row[k]) for k in names}


def outcomes(cases, cuts, offspring):
    for case in cases:
        if case["family"] not in ("ecology", "reserve"):
            continue
        key = case["case"]
        horizon = int(case["horizon_ms"])
        for endpoint in sorted({90 * DAY, horizon}):
            cut = cuts[key][endpoint]
            output = dict(case=key, family=case["family"], arm=case["arm"], seed=int(case["seed"]),
                          workers=int(case["workers"]), day=endpoint // DAY, births=int(cut["eggs"]),
                          queen_survival=int(cut["stage"]) != 4,
                          queen_followup_days=min(endpoint, int(case["maternal_stop_ms"])) / DAY)
            for name, stage in (("hatches", "egg"), ("pupations", "larva"), ("emergences", "pupa")):
                output[name] = sum(row["stage"] == stage and row["endpoint"] == "transition"
                                   and int(row["stop_ms"]) <= endpoint for row in offspring[key])
            output.update(numeric(cut, OUTCOMES[6:]))
            yield output


def bootstrap(deltas):
    rng = Random(640405)
    distribution = sorted(mean(rng.choices(deltas, k=len(deltas))) for _ in range(4096))
    return dict(delta_mean=round(mean(deltas), 9), low95=round(distribution[102], 9),
                high95=round(distribution[3993], 9))


def paired(series):
    by_key = {(s["family"], s["arm"], s["workers"], s["day"], s["seed"]): s for s in series}
    designs = []
    for supply, (left, right) in product(SUPPLY, ((0, 8), (8, 32))):
        designs.append((f"workers_{left}_to_{right}_{supply}",
                        ("ecology", supply, left, 90), ("ecology", supply, right, 90)))
    for supply, count in product(("depot", "scarce", "empty"), (0, 8, 32)):
        designs.append((f"{supply}_minus_ordinary_{count}",
                        ("ecology", "ordinary", count, 90), ("ecology", supply, count, 90)))
    for count in (0, 8):
        designs.append((f"half_reserves_minus_original_{count}",
                        ("ecology", "ordinary", count, 90), ("reserve", "ordinary", count, 90)))
    designs.append(("workers_8_to_32_depot_full", ("ecology", "depot", 8, 180), ("ecology", "depot", 32, 180)))
    for label, left, right in designs:
        for name in OUTCOMES:
            before = [by_key[left + (seed,)][name] for seed in SEEDS]
            after = [by_key[right + (seed,)][name] for seed in SEEDS]
            yield dict(contrast=label, day=left[-1], outcome=name, seeds=len(SEEDS),
                       reference_mean=round(mean(before), 9), contrast_mean=round(mean(after), 9),
                       **bootstrap([b - a for a, b in zip(before, after, strict=True)]))


def write(path, data, check):
    if check:
        require(path.read_bytes() == data, f"derived summary differs: {path.name}")
    else:
        path.write_bytes(data)


def output_table(path, records, check):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, list(records[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    write(path, stream.getvalue().encode(), check)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("analysis", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = args.analysis
    cases = rows(root / "case_results.csv")
    require(len(cases) == 104, "paired analysis requires all frozen cases")
    cut_rows, offspring = defaultdict(dict), defaultdict(list)
    for row in rows(root / "maternal_cuts.csv"):
        cut_rows[row["case"]][int(row["sim_ms"])] = row
    for row in rows(root / "offspring_stages.csv"):
        offspring[row["case"]].append(row)
    series = list(outcomes(cases, cut_rows, offspring))
    output_table(root / "common_window_outcomes.csv", series, args.check)
    output_table(root / "paired_contrasts.csv", list(paired(series)), args.check)
    metrics = {row["case"]: row for row in cases}
    grouped = defaultdict(list)
    for item in series:
        grouped[item["family"], item["arm"], item["workers"], item["day"]].append(item)
    summary = [dict(family=family, arm=arm, workers=count, day=day, runs=len(group),
                    queen_alive=sum(w["queen_survival"] for w in group), births=sum(w["births"] for w in group),
                    hatches=sum(w["hatches"] for w in group), pupations=sum(w["pupations"] for w in group),
                    emergences=sum(w["emergences"] for w in group), queen_deaths_with_crop=sum(
                        not w["queen_survival"] and any(int(cut_rows[w["case"]][day * DAY][key])
                                                     for key in ("crop_carbs_ug", "crop_protein_ug", "crop_water_ug"))
                        for w in group))
               for (family, arm, count, day), group in grouped.items()]
    output_table(root / "group_summary.csv", summary, args.check)
    totals = dict(cases=len(metrics), **{field: sum(int(row[field]) for row in cases)
        for field in ("events", "cuts", "budgets_checked", "attempts", "births", "gifts", "brood_moves",
                      "egg_transition", "egg_death", "larva_transition", "larva_death", "pupa_transition",
                      "pupa_death")})
    write(root / "totals.json", (json.dumps(totals, indent=2) + "\n").encode(), args.check)
    print(totals)


if __name__ == "__main__":
    main()
