"""Summarize the qualified RM-02 baseline without changing the frozen analysis."""

import argparse
from collections import Counter, defaultdict
from contextlib import ExitStack
import csv
import gzip
import io
import json
from pathlib import Path
import statistics
from tempfile import TemporaryDirectory

from analyze_s6_3_2_performance import quantile
from analyze_s6_4_rm02 import DAY, copy_verified, get_json, mass, state_record
from read_s6_4_rm02_sidecar import COMPONENTS, decode_fact, open_sidecar, require
from run_s6_4_rm02 import frozen_cases


FLOW_KINDS = ("FoodCollected", "FoodDelivered", "CargoIngested", "NestIngested", "ProteinRecycled")
ROLES = ("worker", "queen", "larva")


def rows(path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8", newline="") as stream:
        yield from csv.DictReader(stream)


def grouped(records, *fields):
    result = defaultdict(list)
    for row in records:
        result[tuple(row[field] for field in fields)].append(row)
    return result


def sum_columns(records, fields):
    return {field: sum(int(row[field]) for row in records) for field in fields}


def ecology_summary(horizons):
    totals = ("queen_alive", "eggs", "hatches", "eclosed", "larval_deaths", "nutrition_decisions",
              "nutrition_examined", "nutrition_zero_examined", "partial_gifts", "nurse_switches",
              "foraging_switches", "worker_to_worker_gifts", "worker_to_queen_gifts", "worker_to_larva_gifts")
    means = ("queen_days_alive", "queen_energy_nj", "queen_crop_carb_ug",
             "queen_uptake_carb_ug", "queen_uptake_water_ug", "queen_uptake_protein_ug",
             "worker_to_queen_carb_ug", "worker_to_queen_water_ug", "worker_to_queen_protein_ug",
             "worker_to_larva_protein_ug")
    return [
        dict(day=int(t) // DAY, arm=arm, workers=int(size), cases=len(group),
             totals=sum_columns(group, totals),
             means={field: statistics.mean(float(r[field]) for r in group) for field in means},
             death_or_censor=dict(Counter(r["death_cause"] for r in group)))
        for (t, arm, size), group in sorted(grouped(horizons, "sim_ms", "arm", "workers").items())
    ]


def death_stock_rows(analysis):
    deaths = list(rows(analysis / "queen_death_stocks.csv"))
    by_case = {row["case"]: row for row in deaths}
    keys = {(r["case"], r[phase + "_cut_ms"]) for r in deaths for phase in ("prior", "next")}
    focal = defaultdict(Counter)
    for row in rows(analysis / "body_cuts.csv.gz"):
        key = (row["case"], row["sim_ms"])
        if key in keys and row["caste"] == "worker" and row["stage"] != "dead":
            focal[key]["living_focal_workers"] += 1
            for component in COMPONENTS:
                focal[key][f"living_focal_worker_crop_{component}_ug"] += int(row[f"crop_{component}_ug"])
    for row in deaths:
        for phase in ("prior", "next"):
            stock = focal[row["case"], row[phase + "_cut_ms"]]
            row[phase + "_living_focal_workers"] = stock["living_focal_workers"]
            for component in COMPONENTS:
                field = f"living_focal_worker_crop_{component}_ug"
                row[phase + "_" + field] = stock[field]
        for label in ("last_positive_gift", "last_positive_carb_pulse"):
            for suffix in ("event_id", "ms", "lag_ms"):
                row[f"{label}_{suffix}"] = ""
    for name, label in (("gifts", "last_positive_gift"), ("uptake", "last_positive_carb_pulse")):
        for row in rows(analysis / (name + ".csv.gz")):
            death = by_case.get(row["case"])
            if death is None or int(row["event_id"]) >= int(death["death_event_id"]):
                continue
            queen_record = row["route"] == "worker_to_queen" if name == "gifts" else (
                row["role"] == "queen" and int(row["uptake_carb_ug"]) > 0)
            if queen_record:
                death[f"{label}_event_id"] = row["event_id"]
                death[f"{label}_ms"] = row["sim_ms"]
                death[f"{label}_lag_ms"] = int(death["death_ms"]) - int(row["sim_ms"])
    return deaths


def gift_followup_summary(analysis):
    result = []
    for (arm, size, component), group in sorted(grouped(rows(analysis / "queen_gift_followup.csv"),
                                                       "arm", "workers", "component").items()):
        counts = Counter(row["status"] for row in group)
        observed = [int(row["elapsed_ms"]) for row in group if row["status"] == "NEXT_POSITIVE_PULSE"]
        result.append(dict(arm=arm, workers=int(size), component=component, statuses=dict(counts),
                           observed_lag_ms=dict(minimum=min(observed), p50=statistics.median(observed),
                                                p95=quantile(observed, .95), maximum=max(observed)) if observed else {}))
    return result


def coverage_summary(analysis, runs):
    window = grouped(rows(analysis / "opportunity_coverage.csv.gz"), "case")
    worker_programs = defaultdict(Counter)
    for row in rows(analysis / "body_cuts.csv.gz"):
        if (row["case"],) in window and row["caste"] == "worker":
            worker_programs[row["workers"]][row["program"]] += 1
    summary = []
    work = ("cuts", "examined", "scoped_facts", "lost", "crop_checks", "pending_status_1", "neighbor_status_1",
            "NutritionDecision", "NutritionDecision_candidates_examined", "NutritionDecision_zero_examined",
            "typed_opportunities", "typed_gift_choices", "typed_inactive_choices", "NutritionTransferred",
            "positive_pulses", "zero_pulses", "request_POSITIVE", "request_ZERO_COMMITTED_REJECTION",
            "request_RIGHT_CENSORED", "request_UNOBSERVED", "ActionRejected")
    for (mode, size), group in sorted(grouped(runs, "mode", "workers").items()):
        if mode == "ecology":
            continue
        cuts = [cut for row in group for cut in window.get((row["case"],), ())]
        stats = sum_columns(group, work)
        summary.append(dict(mode=mode, workers=int(size), cases=len(group), totals=stats,
                            event_range=[min(int(r["events"]) for r in group), max(int(r["events"]) for r in group)],
                            cut_payload_bytes=sum(int(r["raw_bytes"]) for r in group),
                            stored_payload_bytes=sum(int(r["stored_bytes"]) for r in group),
                            geometry_cuts_with_workers=sum(int(r["geometric_workers"]) > 0 for r in cuts),
                            geometry_worker_cut_occurrences=sum(int(r["geometric_workers"]) for r in cuts),
                            geometry_cuts_with_larvae=sum(int(r["geometric_larvae"]) > 0 for r in cuts),
                            window_worker_program_cuts=dict(worker_programs[size]) if mode == "window" else {},
                            pending_request_cut_occurrences=sum(int(r["pending_trophallaxis"]) for r in cuts)))
    return summary


def queen_budget(case, cut, initial, state, absorbed_carb, absorbed_water, egg_water):
    values = dict(sim_ms=cut["time"], as_of_event=cut["cursor"],
                  initial_body_energy_nj=initial["energy_nj"], absorbed_carb_ug=absorbed_carb,
                  carb_yield_nj_per_ug=state["yield_nj_per_ug"],
                  energy_dissipated_nj=state["dissipated_nj"] - initial["dissipated_nj"],
                  energy_exported_to_eggs_nj=state["exported_nj"] - initial["exported_nj"],
                  body_energy_nj=state["energy_nj"], initial_body_water_ug=initial["body_water_ug"],
                  absorbed_water_ug=absorbed_water, water_exported_to_eggs_ug=egg_water,
                  water_lost_ug=state["water_lost_ug"] - initial["water_lost_ug"],
                  body_water_ug=state["body_water_ug"])
    energy = (values["initial_body_energy_nj"] + absorbed_carb * values["carb_yield_nj_per_ug"]
              - values["energy_dissipated_nj"] - values["energy_exported_to_eggs_nj"])
    water = values["initial_body_water_ug"] + absorbed_water - egg_water - values["water_lost_ug"]
    require(energy == values["body_energy_nj"] and water == values["body_water_ug"],
            f"queen body budget differs at {case['case']} cut {cut['time']}")
    return case | values


def flow_totals(raw, horizons, sidecar, budgets):
    indexed = {(r["case"], int(r["sim_ms"])): int(r["queen"]) for r in horizons}
    for case in frozen_cases():
        if case["mode"] != "ecology":
            continue
        name = case["case"]
        folder = raw / "raw" / name
        receipt = get_json(folder / "receipt.json")
        copy_verified(folder, receipt, sidecar)
        queens = {queen for (leaf, _), queen in indexed.items() if leaf == name}
        queen, = queens
        counts = Counter()
        flows = defaultdict(lambda: [0, 0, 0, 0])
        opening = None
        absorbed_carb = absorbed_water = egg_water = 0
        with open_sidecar(sidecar) as (manifest, cuts):
            for cut in cuts:
                for tag, data in cut["payload"]:
                    if tag != 1:
                        continue
                    fact = decode_fact(data, manifest["world"])
                    if fact.kind == "PhysiologyUpdated" and fact.actor == queen:
                        absorbed_carb += fact.mass[0]
                        absorbed_water += fact.mass[2]
                    if fact.kind == "AntBorn" and fact.payload == queen:
                        egg_water += fact.mass[2]
                    if fact.kind in FLOW_KINDS:
                        role = "queen" if fact.actor == queen else "larva" if fact.stage == 1 else "worker"
                        key = fact.kind, role
                        counts[key] += 1
                        for index, amount in enumerate(fact.mass):
                            flows[key][index] += amount
                states = dict(state_record(data) for tag, data in cut["payload"] if tag == 2)
                current = states[queen]
                if opening is None:
                    require(cut["time"] == 0 and absorbed_carb == absorbed_water == egg_water == 0,
                            f"missing initial queen budget: {name}")
                    opening = current
                budget = queen_budget(case, cut, opening, current, absorbed_carb, absorbed_water, egg_water)
                if (name, cut["time"]) in indexed:
                    budgets.append(budget)
                    for kind in FLOW_KINDS:
                        for role in ROLES:
                            yield case | dict(sim_ms=cut["time"], event_kind=kind, actor_role=role,
                                              committed_events=counts[kind, role], **mass("committed", flows[kind, role]))


def write_or_check(folder, name, content, check):
    path = folder / name
    if check:
        require(path.read_bytes() == content.encode(), f"R1 diagnosis differs: {path}")
    else:
        path.write_bytes(content.encode())


def export_csv(folder, name, records, check):
    first = next(records, None)
    require(first is not None, f"missing records: {name}")
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, list(first), lineterminator="\n")
    writer.writeheader()
    writer.writerow(first)
    writer.writerows(records)
    write_or_check(folder, name, stream.getvalue(), check)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw", type=Path)
    parser.add_argument("analysis", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    runs = list(rows(args.analysis / "runs.csv"))
    require(len(runs) == 72 and all(r["status"] == "PASS" and r["lost"] == "0" for r in runs),
            "the R1 summary requires all 72 frozen cases and complete observations")
    horizons = list(rows(args.analysis / "horizons.csv"))
    require(len(horizons) == 60, "expected 48 day-90 and 12 depot day-180 records")
    deaths = death_stock_rows(args.analysis)
    export_csv(args.out, "queen_death_focal_worker_stocks.csv", iter(deaths), args.check)
    budgets = []
    with TemporaryDirectory() as temporary:
        export_csv(args.out, "committed_ingestion_and_supply.csv",
                   flow_totals(args.raw, horizons, Path(temporary) / "trace.sqlite", budgets), args.check)
    require(len(budgets) == len(horizons), "missing queen budget endpoint")
    export_csv(args.out, "queen_body_budgets.csv", iter(budgets), args.check)
    totals = ("events", "cuts", "examined", "scoped_facts", "lost", "crop_checks", "NutritionTransferred",
              "positive_pulses", "zero_pulses", "ActionRejected", "raw_bytes", "stored_bytes")
    result = dict(accepted_cases=len(runs), total=sum_columns(runs, totals),
                  by_mode={mode: sum_columns(group, totals)
                           for (mode,), group in sorted(grouped(runs, "mode").items())},
                  ecology=ecology_summary(horizons), coverage=coverage_summary(args.analysis, runs),
                  queen_gift_followup=gift_followup_summary(args.analysis))
    write_or_check(args.out, "baseline_summary.json", json.dumps(result, indent=2) + "\n", args.check)
    print(f"{len(runs)} qualified runs; {result['total']['events']} examined events; {len(deaths)} queen death stock windows")


if __name__ == "__main__":
    main()
