"""Summarize the actual outcomes by frozen factor level and supplemental arm."""

import argparse
from collections import defaultdict
import csv
from pathlib import Path

from analyze_s6_4_wp6b import csv_out
from wp6a_budget_screen import ORDINARY_FACTORS, POPULATIONS


def totals(group):
    finished = [row for row in group if row["status"] == "COMPLETE"]
    fields = ("births", "hatch", "pupation", "eclosed", "actual_rations", "brood_deaths", "brood_censored")
    return dict(attempted=len(group), completed=len(finished), input_rejected=sum(row["status"]=="INPUT_REJECTED" for row in group),
                no_birth=sum(row["births"]=="0" for row in finished), no_hatch=sum(row["hatch"]=="0" for row in finished),
                first_worker_worlds=sum(row["first_worker_ms"]!="" for row in finished),
                queen_alive_at_horizon=sum(row["queen_death_ms"]=="" for row in finished),
                **{field: sum(int(row[field]) for row in finished) for field in fields})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("analysis", type=Path)
    args = parser.parse_args()
    with (args.analysis/"cases.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    supplemental = defaultdict(list)
    for row in rows:
        if row["group"] not in ("primary", "check"):
            supplemental[row["population"],row["group"],row["arm"],row["workers"]].append(row)
    csv_out(args.analysis/"supplemental_sensitivity.csv", [
        dict(population=population, group=group, arm=arm, workers=workers, **totals(cases))
        for (population,group,arm,workers), cases in sorted(supplemental.items())])
    primary = []
    for population in POPULATIONS:
        for care in ("1", "0"):
            matched = [r for r in rows if r["population"]==population and r["group"]=="primary" and r["care"]==care]
            for bit, (factor, levels) in enumerate(ORDINARY_FACTORS.items()):
                for level, value in enumerate(levels):
                    group = [r for r in matched if ((int(r["profile"]) >> (4-bit)) & 1) == level]
                    assert len(group) == 96
                    primary.append(dict(population=population, care=care, factor=factor, level=value, **totals(group)))
    csv_out(args.analysis/"ordinary_factor_sensitivity.csv", primary)


if __name__ == "__main__":
    main()
