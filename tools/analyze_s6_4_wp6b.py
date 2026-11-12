"""Reconcile F1 material and lineage from raw facts and fixed daily cuts."""

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
from itertools import groupby
import json
from pathlib import Path
from random import Random
from statistics import median
import struct
import zipfile

from run_s6_4_wp6b import frozen_cases, input_bytes, sha
from wp6a_budget_screen import DAY_MS, ORDINARY_FACTORS, POPULATIONS


ANT_SEEDED, MOVED, STAGE, DIED, RESTED = 2, 4, 7, 8, 13
COLLECTED, DELIVERED, UPTAKE, CARGO, NEST, GIFT = 5, 12, 16, 19, 20, 21
AUTONOMY, LAY, BIRTH, RECYCLED, OBSERVATION = 31, 34, 35, 38, 42
F_CONFIG, F_SEED, F_EGG, F_CONVERT, F_RATION = range(44, 49)
F_MOBILIZE, F_CUE = 49, 50
OBS_SELECTED, OBS_STARTED, OBS_COMPLETED, OBS_INTERRUPTED = 1, 2, 3, 4
FEED = 7
MASS = struct.Struct("<QQQQ")
IDENTITY = struct.Struct("<QQQQQ")
PAYLOAD = struct.Struct("<QQBQ")
BOUT = struct.Struct("<BBQQQBddd")
RANGES = {"borisovka": [(15, 18), (7, 14), (13, 16), (39, 47)],
          "st_petersburg": [(14, 19), (8.5, 12.5), (12, 16), (37, 44)]}


def check(condition, message):
    if not condition:
        raise ValueError(message)


def rows(data):
    return list(csv.DictReader(data.decode().splitlines()))


def facts(data, max_kind=F_RATION):
    cursor, sequence, prior_time = 0, 1, 0
    world = None
    while cursor < len(data):
        size = int.from_bytes(data[cursor:cursor+4], "little")
        cursor += 4
        check(size in (159, 210) and cursor+size <= len(data), "invalid canonical length")
        event_id, high, low, time, source = IDENTITY.unpack_from(data, cursor)
        world = world or (high, low)
        payload, value, kind, actor = PAYLOAD.unpack_from(data, cursor+49)
        check(event_id == sequence and world == (high, low) and time >= prior_time and kind <= max_kind and
              (size == 210) == (kind == OBSERVATION), "canonical order or kind changed")
        yield (event_id, time, source, kind, actor, payload, value, data[cursor+146], data[cursor+147],
               MASS.unpack_from(data, cursor+114), BOUT.unpack_from(data, cursor+159) if size == 210 else None)
        cursor += size
        sequence += 1
        prior_time = time


def compare_cut(cut, people, stocks, flows, initial_energy, profile):
    check(all(cut[f"introduced_{k}"] == cut[f"accounted_{k}"] for k in "cpwo"), "cut material imbalance")
    check(int(cut["energy_input_nj"]) == int(cut["body_energy_nj"]) + int(cut["dissipated_nj"]), "cut body energy imbalance")
    check(int(cut["initial_q3"]) == sum(int(cut[k]) for k in ("remaining_q3", "carried_q3", "deposited_q3")), "cut soil imbalance")
    totals = [0, 0, 0]
    for row in people:
        ant = int(row["id"])
        check(row["time_ms"] == cut["time_ms"] and row["cursor"] == cut["cursor"], "individual outside its cut")
        lipid, spent, mobile = stocks.get(ant, (0, 0, 0))
        if row["enrolled"] == "1":
            observed = tuple(int(row[k]) for k in ("lipid_ug", "spent_lipid_ug", "mobile_protein_ug"))
            check(observed == (lipid, spent, mobile), "identity's reconstructed lipid or mobile protein differs")
        else:
            check(ant not in stocks, "F1 stock outside explicit enrollment")
        for i, value in enumerate((lipid, spent, mobile)):
            check(value >= 0, "negative reserve")
            totals[i] += value
        expected = (int(row["crop_c"]) + int(row["oxidized_carb_ug"]),
                    int(row["crop_p"]) + int(row["tissue_protein_ug"]) + mobile,
                    int(row["crop_w"]) + int(row["hydration_ug"]) + int(row["lost_water_ug"]), int(row["crop_o"]))
        check(tuple(flows[ant]) == expected, "identity's material flows differ from its compartments")
        energy = initial_energy.get(ant, 0) + spent * profile["lipid_yield"] + 1_000_000 * int(row["oxidized_carb_ug"])
        check(energy == int(row["energy_nj"]) + int(row["dissipated_nj"]), "identity's realized energy differs from funded input")
    check(tuple(totals) == tuple(int(cut[k]) for k in ("owned_lipid_ug", "spent_lipid_ug", "mobile_protein_ug")), "reserve sum differs")
    check(totals[0] + totals[1] == profile["maternal_lipid"], "world lipid did not close")


def census(sets, exact):
    first_egg = next((t for t, c in sets if c[0]), None)
    first_larva, k = next(((t, c[1]) for t, c in sets if c[1]), (None, 0))
    wanted = (lambda n: n == k) if exact else (lambda n: n >= k)
    first_pupa, pupae = next(((t, c[2]) for t, c in sets if k and t > first_larva and wanted(c[2])), (None, 0))
    first_worker, workers = next(((t, c[3]) for t, c in sets if first_pupa is not None and t > first_pupa and wanted(c[3])), (None, 0))
    durations = [None if a is None or b is None else (b-a) / DAY_MS for a, b in
                 ((first_egg, first_larva), (first_larva, first_pupa), (first_pupa, first_worker), (first_egg, first_worker))]
    return dict(zip(("egg_d", "larva_d", "pupa_d", "total_d"), durations, strict=True), k=k,
                first_egg_ms=first_egg, first_larva_ms=first_larva, first_pupa_ms=first_pupa,
                first_worker_ms=first_worker, pupa_overshoot=max(0, pupae-k), worker_overshoot=max(0, workers-k))


def assess(case, summary, raw, cut_data, individual_data, profile_version=1):
    profile, queen = case["parameters"], int(summary["queen"])
    cut_rows = rows(cut_data)
    daily = [(int(time), list(group)) for time, group in groupby(rows(individual_data), lambda r: r["time_ms"])]
    check([t for t, _ in daily] == list(range(0, case["horizon_ms"]+1, DAY_MS)) == [int(c["time_ms"]) for c in cut_rows],
          "daily census denominator changed")
    baseline = {int(row["id"]): row for row in daily[0][1]}
    initial_energy = {ant: int(row["energy_nj"]) for ant, row in baseline.items() if row["enrolled"] == "0"}
    flows = defaultdict(lambda: [0, 0, 0, 0])
    for ant, row in baseline.items():
        if ant != queen:
            flows[ant] = [int(row["crop_c"]), int(row["crop_p"]) + int(row["tissue_protein_ug"]),
                          int(row["crop_w"]) + int(row["hydration_ug"]), int(row["crop_o"])]
    stocks, stages, child, counts = {}, {}, {}, Counter()
    firsts = {}
    current_cut = 0
    prior_ration = None
    last = 0
    scan_matches, scan_feeding, larval_wakes = set(), set(), set()
    care_begin = 55 * DAY_MS
    scan_starts = [care_begin + offset * 60_000 for offset in range(5, 55)]

    def transfer(sender, recipient, amount):
        for i, value in enumerate(amount):
            if sender is not None:
                flows[sender][i] -= value
            if recipient is not None:
                flows[recipient][i] += value

    for event, time, source, kind, actor, payload, value, stage, outcome, mass, obs in facts(raw, F_CUE if profile_version == 3 else F_RATION):
        while current_cut < len(cut_rows) and int(cut_rows[current_cut]["cursor"]) < event:
            compare_cut(cut_rows[current_cut], daily[current_cut][1], stocks, flows, initial_energy, profile)
            current_cut += 1
        last = event
        counts[f"fact_{kind}"] += 1
        if prior_ration is not None:
            check(kind == OBSERVATION and obs[:3] == (OBS_COMPLETED, FEED, prior_ration[2]) and
                  (actor, source, mass) == (queen, prior_ration[0], prior_ration[1]), "ration without completed act")
            prior_ration = None
        if kind in (ANT_SEEDED, BIRTH, STAGE, DIED):
            stages[actor] = stage
        if kind == F_CONFIG:
            check(actor == 0 and value == profile_version, "bad F1 profile declaration")
        elif kind == F_SEED:
            check(actor == queen and payload == profile["maternal_lipid"] and mass == (0, profile["maternal_protein"], profile["maternal_water"], 0),
                  "unfunded or mismatched foundress seed")
            stocks[actor] = [payload, 0, mass[1]]
            transfer(None, actor, mass)
        elif kind == BIRTH:
            check(payload == queen and value == 0 and mass == (0, profile["egg_protein"], profile["egg_water"], 0), "unexpected source of egg material")
            child[actor] = dict(birth=time, egg=event, stages=[(0, time, event)], death=None, rations=[], uptake=[], adult_decisions=0,
                                adult_actions=0)
            transfer(queen, actor, mass)
        elif kind == F_EGG:
            check(actor == queen and payload in child and value == profile["egg_lipid"] and not any(mass), "egg lipid packet differs")
            stocks[actor][0] -= value
            stocks[actor][2] -= profile["egg_protein"]
            stocks[payload] = [value, 0, 0]
        elif kind in (F_CONVERT, F_MOBILIZE):
            check(actor in stocks and payload > 0 and value == payload * profile["lipid_yield"], "lipid conversion is unbacked")
            if kind == F_MOBILIZE:
                check(case["early_access_mask"] & 1 and actor in child and stages[actor] == 1, "invalid R2 mobilization stage or mode")
            stocks[actor][0] -= payload
            stocks[actor][1] += payload
        elif kind == F_RATION:
            check(actor == queen and payload in child and stages[payload] == 1 and 0 <= value <= profile["ration_lipid_limit"] and
                  mass[1] <= profile["ration_protein_limit"] and mass[2] <= profile["ration_water_limit"] and (value or any(mass)), "invalid actual ration")
            stocks[actor][0] -= value
            stocks[actor][2] -= mass[1]
            stocks[payload][0] += value
            transfer(queen, payload, mass)
            child[payload]["rations"].append((time, event, value, mass[1], mass[2]))
            prior_ration = (source, mass, payload)
            counts["ration_lipid"] += value
            counts["ration_protein"] += mass[1]
            counts["ration_water"] += mass[2]
        elif kind == GIFT:
            transfer(actor, payload, mass)
            label = "queen" if payload == queen else "larva" if stages[payload] == 1 else "adult_worker"
            counts[f"worker_to_{label}"] += 1
            for nutrient, amount in zip("cpwo", mass, strict=True):
                counts[f"worker_to_{label}_{nutrient}"] += amount
        elif kind in (CARGO, NEST):
            transfer(None, actor, mass)
        elif kind == RECYCLED:
            transfer(actor, None, mass)
        elif kind == UPTAKE:
            if actor in child and stages[actor] == 1 and any(mass):
                child[actor]["uptake"].append((time, event, *mass))
            if actor == queen:
                counts["queen_absorbed_c"] += mass[0]
                counts["queen_absorbed_w"] += mass[2]
        elif kind == STAGE and actor in child:
            check(stage == child[actor]["stages"][-1][0]+1, "identity skipped a stage")
            child[actor]["stages"].append((stage, time, event))
            firsts.setdefault(stage, time)
        elif kind == DIED:
            if actor in child:
                child[actor]["death"] = (time, payload, event)
            if actor == queen:
                firsts["queen_death"], firsts["queen_cause"] = time, payload
        elif kind == AUTONOMY and actor in child:
            child[actor]["adult_decisions"] += 1
        elif kind == OBSERVATION and actor == queen:
            phase, act, target, _, began, known, *_ = obs
            if phase == 0 and target in child and stages[target] == 1:
                counts["queen_larva_opportunities"] += 1
                larval_wakes.add(source)
            if phase == OBS_SELECTED and target in child and stages[target] == 1:
                counts["queen_larva_selections"] += 1
            if known and phase in (OBS_COMPLETED, OBS_INTERRUPTED) and act != 0:
                counts["queen_observed_act_ms"] += time-began
            if act == FEED:
                counts[f"queen_feed_phase_{phase}"] += 1
            if known and phase in (OBS_COMPLETED, OBS_INTERRUPTED) and act in (3, 4, 5, FEED) and began < scan_starts[-1] + 10_000 and time > scan_starts[0]:
                matches = scan_feeding if act == FEED else scan_matches
                matches.update(i for i, start in enumerate(scan_starts) if began < start + 10_000 and time > start)
        if kind in (COLLECTED, DELIVERED):
            counts[f"food_mass_{kind}"] += sum(mass)
        if kind in (MOVED, COLLECTED, DELIVERED, RESTED, GIFT, NEST, CARGO, RECYCLED) and actor in child and stages[actor] == 3:
            child[actor]["adult_actions"] += 1

    while current_cut < len(cut_rows):
        check(int(cut_rows[current_cut]["cursor"]) == last, "snapshot has unrecorded terminal facts")
        compare_cut(cut_rows[current_cut], daily[current_cut][1], stocks, flows, initial_energy, profile)
        current_cut += 1
    check(last == int(summary["events"]) and counts["fact_44"] == counts["fact_45"] == 1 and
          counts["fact_46"] == len(child), "incomplete committed record")

    final = {int(row["id"]): row for row in daily[-1][1]}
    timeline = []
    paths = []
    for ant, record in child.items():
        chain = record["stages"]
        pupation = next((event for stage, _, event in chain if stage == 2), None)
        meal = next((event for _, event, _, p, _ in record["rations"] if p), None)
        uptake = next((event for _, event, _, p, _, _ in record["uptake"] if p and meal and event > meal), None)
        if pupation and case["externally_seeded_workers"] == 0 and not case.get("arm") == "contact-blocked":
            check(meal and uptake and meal < uptake < pupation, "unfunded non-worker pupation")
        for index, (stage, time, origin) in enumerate(chain):
            if index + 1 < len(chain):
                _, end, terminal = chain[index+1]
                outcome = "TRANSITION"
            elif record["death"]:
                end, cause, terminal = record["death"]
                outcome = f"DEATH_{cause}"
            else:
                end, terminal, outcome = case["horizon_ms"], None, "RIGHT_CENSORED"
            timeline.append(dict(case=case["case"], ant=ant, mother=queen, stage=stage, enter_ms=time, enter_event=origin,
                                 end_ms=end, end_event=terminal, age_in_stage_ms=end-time, outcome=outcome))
        larva_ms = next((t for s,t,_ in chain if s==1), None)
        larva_end = next((t for s,t,_ in chain if s==2), record["death"][0] if record["death"] else case["horizon_ms"])
        paths.append(dict(case=case["case"], ant=ant, mother=queen, birth_ms=record["birth"], larva_ms=larva_ms,
                          pupa_ms=next((t for s,t,_ in chain if s==2), None), adult_ms=next((t for s,t,_ in chain if s==3), None),
                          ration_count=len(record["rations"]), first_positive_protein_ration_event=meal, first_following_protein_uptake_event=uptake,
                          reached_larval_clock_cap=int(larva_ms is not None and larva_end-larva_ms>=profile["larva_ms"]),
                          first_ration_delay_ms=record["rations"][0][0]-larva_ms if record["rations"] else None,
                          ration_protein_ug=sum(row[3] for row in record["rations"]), larval_protein_uptake_ug=sum(row[3] for row in record["uptake"]),
                          last_stage=int(final[ant]["stage"]), terminal_lipid_ug=final[ant]["lipid_ug"], terminal_energy_nj=final[ant]["energy_nj"],
                          terminal_water_ug=final[ant]["hydration_ug"], terminal_tissue_protein_ug=final[ant]["tissue_protein_ug"],
                          autonomy_decisions=record["adult_decisions"], committed_adult_actions=record["adult_actions"]))

    daily_counts = [(t, Counter(int(p["stage"]) for p in people if int(p["mother"]) == queen)) for t, people in daily]
    matched = [dict(case=case["case"], rule=rule, **census(daily_counts, rule=="exact")) for rule in ("at_least", "exact")]
    first_lay = next(iter(child.values()))["birth"] if child else None
    first_eggs = next((c[0] for _, c in daily_counts if c[0]), 0)
    queen_cut = final[queen]
    last_cut = cut_rows[-1]
    result = dict(births=len(child), attempts=counts[f"fact_{LAY}"], hatch=sum(p["larva_ms"] is not None for p in paths),
                  pupation=sum(p["pupa_ms"] is not None for p in paths), eclosed=sum(p["adult_ms"] is not None for p in paths),
                  first_egg_ms=first_lay, first_larva_ms=firsts.get(1), first_pupa_ms=firsts.get(2), first_worker_ms=firsts.get(3),
                  first_eggs_census=first_eggs, eggs_first_24h=sum(p["birth_ms"] < first_lay+DAY_MS for p in paths) if child else 0,
                  queen_death_ms=firsts.get("queen_death"), queen_death_cause=firsts.get("queen_cause"),
                  queen_lipid_left=queen_cut["lipid_ug"], queen_protein_left=queen_cut["mobile_protein_ug"],
                  queen_energy_left=queen_cut["energy_nj"], queen_water_left=queen_cut["hydration_ug"],
                  no_care_pupations=int(not case["care_enabled"] and any(p["pupa_ms"] is not None for p in paths)),
                  remaining_food_c=last_cut["available_c"], remaining_nest_c=last_cut["nest_c"], last_living=last_cut["living"],
                  brood_deaths=sum(p["last_stage"] == 4 for p in paths), brood_censored=sum(p["last_stage"] != 4 for p in paths),
                  b01_like_handling_scans=len(scan_matches), b01_like_feeding_scans=len(scan_feeding), b01_like_scan_n=50,
                  day55_foundress_alive=int(next(p["stage"] for p in daily[55][1] if int(p["id"])==queen)!= "4"),
                  eclosed_workers_with_decisions=sum(p["autonomy_decisions"] > 0 for p in paths),
                  eclosed_workers_with_actions=sum(p["committed_adult_actions"] > 0 for p in paths),
                  day49_eggs=daily_counts[49][1][0], day49_larvae=daily_counts[49][1][1], day49_pupae=daily_counts[49][1][2],
                  day49_new_workers=daily_counts[49][1][3], queen_wakes_with_larva=len(larval_wakes),
                  **{k: counts[k] for k in ("ration_lipid", "ration_protein", "ration_water", "queen_absorbed_c", "queen_absorbed_w",
                       "queen_larva_opportunities", "queen_larva_selections", "queen_observed_act_ms",
                       *(f"queen_feed_phase_{i}" for i in range(1, 5)), f"food_mass_{COLLECTED}", f"food_mass_{DELIVERED}",
                       *(f"worker_to_{role}{suffix}" for role in ("queen", "larva", "adult_worker") for suffix in ("", "_c", "_p", "_w", "_o")))},
                  actual_rations=counts["fact_48"], source_facts=last)
    return result, timeline, paths, matched


def csv_out(path, records):
    if not records:
        return
    fields = dict.fromkeys(key for row in records for key in row)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(fields), lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)


def verify_run(root, output):
    expected = {case["case"]: (i, case) for i, case in frozen_cases()}
    run = json.loads((root / "completed.json").read_text())
    check(set(run["statuses"]) == set(expected) and run["attempts"] == len(expected), "formal case coverage changed")
    results, timeline, paths, censuses, costs = [], [], [], [], []
    seen = set()
    for filename, digest in run["archives"].items():
        archive = root / filename
        check(sha(archive) == digest, f"archive digest changed: {filename}")
        with zipfile.ZipFile(archive) as reader:
            for receipt in (name for name in reader.namelist() if name.endswith("/receipt.json")):
                prefix = receipt.removesuffix("receipt.json")
                record = json.loads(reader.read(receipt))
                name = record["case"]
                identity, case = expected[name]
                check(name not in seen and identity == record["identity"] and record["status"] == run["statuses"][name], "wrong or duplicate case receipt")
                seen.add(name)
                data = {}
                for item, info in record["artifacts"].items():
                    content = reader.read(prefix+item)
                    check(len(content) == info["bytes"] and hashlib.sha256(content).hexdigest() == info["sha256"], f"bad artifact: {name}/{item}")
                    if item in ("case.json", "parameters.txt", "facts.bin", "cuts.csv", "individuals.csv"):
                        data[item] = content
                check(json.loads(data["case.json"]) == case and data["parameters.txt"] == input_bytes(identity, case), "case parameters differ")
                row = dict(case=name, group=case["group"], population=case["population"], care=int(case["care_enabled"]),
                           arm=case.get("arm", "ordinary"), workers=case["externally_seeded_workers"], seed=case["software_seed"],
                           profile=case.get("profile_index"), status=record["status"])
                if record["status"] == "COMPLETE":
                    try:
                        metrics, lives, workers, counts = assess(case, record["summary"], data["facts.bin"], data["cuts.csv"], data["individuals.csv"])
                    except ValueError as err:
                        raise ValueError(f"{name}: {err}") from err
                    timeline.extend(lives)
                    paths.extend(workers)
                    censuses.extend(counts)
                    costs.append(dict(case=name, process_wall_ms=record["elapsed_ms"], **record["summary"]))
                    row.update(metrics)
                results.append(row)
    check(seen == set(expected), "raw case coverage differs from receipt")
    output.mkdir(parents=True)
    for filename, values in (("cases.csv", results), ("stage_exposure.csv", timeline), ("offspring.csv", paths),
                             ("daily_count_timing.csv", censuses), ("assay_costs.csv", costs)):
        csv_out(output / filename, values)
    evaluate(output, results, timeline, censuses)


def interval(values):
    values = sorted(values)
    return [values[int((len(values)-1)*p)] for p in (.025, .975)] if values else [None, None]


def evaluate(output, results, timeline, censuses):
    by_case = {r["case"]: r for r in results}
    population_rows, point_rows, factor_rows, timing_rows = [], [], [], []
    rng = Random(640601)
    for pop in POPULATIONS:
        ordinary = [r for r in results if r["group"] in ("primary", "check") and r["population"] == pop]
        for group in ("primary", "check"):
            grid = defaultdict(dict)
            for r in ordinary:
                if r["group"] == group:
                    grid[r["profile"]].setdefault(r["seed"], {})[r["care"]] = r
            passes = set()
            profiles = []
            for index, paired in sorted(grid.items()):
                on = sum(p[1].get("eclosed", 0) > 0 for p in paired.values())
                off = sum(p[0].get("eclosed", 0) > 0 for p in paired.values())
                if on >= 4:
                    passes.add(index)
                profiles.append([int(p[1].get("eclosed", 0)>0) - int(p[0].get("eclosed", 0)>0) for p in paired.values()])
                point_rows.append(dict(population=pop, group=group, profile=index, seeds=len(paired), worker_on=on, worker_off=off, passes=int(on>=4)))
            intervals = []
            for _ in range(4096):
                diff = [x for p in rng.choices(profiles, k=len(profiles)) for x in rng.choices(p, k=len(p))]
                intervals.append(sum(diff)/len(diff))
            population_rows.append(dict(population=pop, group=group, passing_profiles=len(passes), profiles=len(grid),
                                        required=24 if group=="primary" else 6, successful_on=sum(r.get("eclosed",0)>0 for r in ordinary if r["group"]==group and r["care"]),
                                        trials_on=sum(1 for r in ordinary if r["group"]==group and r["care"]), paired_ci95=interval(intervals)))
            if group == "primary":
                for bit, (factor, bounds) in enumerate(ORDINARY_FACTORS.items()):
                    for level, value in enumerate(bounds):
                        good = sum((index >> (4-bit)) & 1 == level for index in passes)
                        factor_rows.append(dict(population=pop, factor=factor, level=value, passing=good, profiles=16, required=10))
        for rule in ("at_least", "exact"):
            contributing = [c for c in censuses if c["rule"]==rule and by_case[c["case"]]["population"] == pop and
                            by_case[c["case"]]["group"]=="primary" and by_case[c["case"]]["care"]]
            complete = sum(c["total_d"] is not None for c in contributing)
            for endpoint, limits in zip(("egg_d", "larva_d", "pupa_d", "total_d"), RANGES[pop], strict=True):
                groups = defaultdict(list)
                for c in contributing:
                    if c[endpoint] is not None:
                        groups[by_case[c["case"]]["profile"]].append(c[endpoint])
                values = [x for p in groups.values() for x in p]
                boot = []
                if values:
                    pools = list(groups.values())
                    for _ in range(4096):
                        boot.append(median(x for p in rng.choices(pools,k=len(pools)) for x in rng.choices(p,k=len(p))))
                ci = interval(boot)
                status = "INSUFFICIENT" if complete < 12 or not values else "PASS" if limits[0]-1 <= ci[0] <= ci[1] <= limits[1]+1 else "FAIL"
                timing_rows.append(dict(population=pop, rule=rule, endpoint=endpoint, contributing=len(values), complete_worlds=complete,
                                        worlds=len(contributing), median=median(values) if values else None, lo95=ci[0], hi95=ci[1],
                                        published_min=limits[0], published_max=limits[1], status=status))
    csv_out(output/"robustness_profiles.csv", point_rows)
    csv_out(output/"robustness_factors.csv", factor_rows)
    csv_out(output/"timing_comparison.csv", timing_rows)
    curves = []
    series = defaultdict(Counter)
    for row in timeline:
        r = by_case[row["case"]]
        if r["group"] == "primary":
            series[r["population"], r["care"], row["stage"]][row["age_in_stage_ms"], row["outcome"]] += 1
    for (pop, care, stage), events in sorted(series.items()):
        at_risk, alive, transitions, deaths = sum(events.values()), 1.0, 0.0, 0.0
        for time, values in groupby(sorted(events.items()), lambda x: x[0][0]):
            group = dict((outcome, count) for (_, outcome), count in values)
            t, d = group.get("TRANSITION", 0), sum(n for k,n in group.items() if k.startswith("DEATH"))
            c = group.get("RIGHT_CENSORED", 0)
            transitions += alive*t/at_risk
            deaths += alive*d/at_risk
            alive *= 1 - (t+d)/at_risk
            curves.append(dict(population=pop, care=care, stage=stage, stage_age_ms=time, at_risk=at_risk, transitioned=t,
                               died=d, censored=c, cumulative_transition=transitions, cumulative_death=deaths, survival=alive))
            at_risk -= t+d+c
    csv_out(output/"competing_events.csv", curves)
    decision = dict(statuses=dict(Counter(r["status"] for r in results)), coverage=len(results), population=population_rows,
                    any_no_care_pupations=any(r.get("no_care_pupations",0) for r in results),
                    profiles_gate=all(r["passing_profiles"]>=r["required"] for r in population_rows) and all(r["passing"]>=r["required"] for r in factor_rows),
                    timing_gate=all(r["status"]=="PASS" for r in timing_rows if r["rule"]=="at_least"))
    (output/"decision.json").write_text(json.dumps(decision,indent=2)+"\n",encoding="utf-8",newline="\n")
    print(json.dumps(decision,indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw",type=Path)
    parser.add_argument("analysis",type=Path)
    args = parser.parse_args()
    verify_run(args.raw,args.analysis)
