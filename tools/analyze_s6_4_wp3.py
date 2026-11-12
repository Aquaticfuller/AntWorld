"""Rebuild WP-3 individual, trip, group and paired diagnostic tables."""

import argparse
from collections import Counter, defaultdict
import csv
from dataclasses import dataclass, field
from itertools import product
import math
from pathlib import Path
import random
from statistics import mean, median
from tempfile import TemporaryDirectory

from s6_4_wp3_cases import AGES, SEEDS, SIGNALS
from verify_s6_4_wp3 import extracted, require, rows, select, verify_live, verify_prepared


@dataclass
class Trip:
    number: int
    opened_ms: int
    opened_event: int
    moves: int = 0
    path_m: float = 0
    loaded_moves: int = 0
    loaded_path_m: float = 0
    collect_event: int | None = None
    collect_ms: int | None = None
    resource: int | None = None
    acquired_ug: int = 0
    delivered_ug: int = 0


@dataclass
class Individual:
    role: str
    position: tuple | None = None
    first: dict = field(default_factory=dict)
    counts: Counter = field(default_factory=Counter)
    outcome: Counter = field(default_factory=Counter)
    mass: dict = field(default_factory=lambda: {key: [0] * 4 for key in ("collected", "delivered")})
    trip: Trip | None = None
    trip_count: int = 0
    cargo_ug: int = 0
    distance_m: float = 0
    marked_units: float = 0
    resources: set = field(default_factory=set)
    completed_delivery: bool = False

    def seen(self, endpoint, fact):
        self.first.setdefault(endpoint, (fact.time, fact.event))
        self.counts[endpoint] += 1


ENDPOINTS = ("forager_start", "policy_forage", "search", "departure", "recorded_cue", "local_food_choice",
             "feeder_arrival", "pickup_choice", "positive_collection", "loaded_nest_arrival", "positive_delivery", "death")
COMPONENTS = ("carbs", "protein", "water", "other")


def write(path, data):
    require(bool(data), f"no output rows for {path.name}")
    keys = list(dict.fromkeys(key for row in data for key in row))
    with path.open("x", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, keys, lineterminator="\n")
        writer.writeheader()
        writer.writerows(data)


def opened(individual, fact):
    individual.trip_count += 1
    individual.trip = Trip(individual.trip_count, fact.time, fact.event)


def terminal(case, actor, individual, status, time, event, trips):
    trip = individual.trip
    if trip is None:
        return
    trips.append(dict(case=case.key, actor=actor, role=individual.role, trip=trip.number,
                      opened_ms=trip.opened_ms, opened_event=trip.opened_event, terminal_ms=time,
                      terminal_event=event, terminal_status=status, moves=trip.moves, path_m=trip.path_m,
                      loaded_moves=trip.loaded_moves, loaded_path_m=trip.loaded_path_m,
                      collection_ms=trip.collect_ms, collection_event=trip.collect_event,
                      resource=trip.resource, acquired_ug=trip.acquired_ug, delivered_ug=trip.delivered_ug))
    individual.trip = None


def observe(case, actor, individual, fact, nest, feeders, trips, stock_removal):
    counts = individual.counts
    counts[fact.kind] += 1
    if fact.kind == "ForagingStarted":
        individual.seen("forager_start", fact)
    elif fact.kind == "BehaviorChanged" and fact.payload == 3 and fact.source:
        individual.seen("policy_forage", fact)
    elif fact.kind == "ForagingDecision":
        if fact.reason in (1, 2, 3, 4):
            individual.seen("search", fact)
        if fact.resource:
            individual.seen("recorded_cue", fact)
        if fact.reason == 2:
            individual.seen("local_food_choice", fact)
        if fact.mode == 3:
            individual.seen("pickup_choice", fact)
        counts["marked_choices"] += fact.reason == 3
        counts["memory_choices"] += fact.reason == 4
        counts["forgot_memory"] += fact.forgot_memory
        if stock_removal is not None and fact.event > stock_removal:
            counts["search_after_depletion"] += fact.reason == 1
            counts["forgot_after_depletion"] += fact.forgot_memory
    elif fact.kind == "Moved":
        origin = individual.position
        individual.position = fact.position
        require(origin is not None, "movement has no previous committed position")
        displacement = math.dist(origin, fact.position)
        if displacement and origin == nest and not individual.cargo_ug:
            individual.seen("departure", fact)
            if individual.trip is None:
                opened(individual, fact)
        if displacement and fact.position in feeders:
            individual.seen("feeder_arrival", fact)
            counts["feeder_arrivals_after_removal"] += stock_removal is not None and fact.event > stock_removal
        if displacement and fact.position == nest and individual.cargo_ug:
            individual.seen("loaded_nest_arrival", fact)
        individual.distance_m += displacement
        individual.marked_units += fact.deposited_units
        counts["marked_moves"] += fact.mode == 1
        counts["memory_moves"] += fact.mode == 2
        counts["deposit_moves"] += fact.deposited_units > 0
        if individual.trip is not None:
            individual.trip.path_m += displacement
            individual.trip.moves += 1
            if individual.cargo_ug:
                individual.trip.loaded_moves += 1
                individual.trip.loaded_path_m += displacement
        if fact.position == nest and not individual.cargo_ug:
            terminal(case, actor, individual, "RETURNED_EMPTY", fact.time, fact.event, trips)
    elif fact.kind == "FoodCollected":
        mass = sum(fact.mass)
        require(mass > 0, "collection has no positive debit")
        individual.seen("positive_collection", fact)
        if individual.completed_delivery:
            counts["collections_after_delivery"] += 1
            counts["repeat_same_resource"] += fact.resource in individual.resources
        individual.resources.add(fact.resource)
        counts["partial_collection"] += fact.outcome == "Partial"
        individual.cargo_ug += mass
        individual.mass["collected"] = [a + b for a, b in zip(individual.mass["collected"], fact.mass)]
        if individual.trip is None:
            opened(individual, fact)
        trip = individual.trip
        if trip.collect_event is None:
            trip.collect_event, trip.collect_ms, trip.resource = fact.event, fact.time, fact.resource
        trip.acquired_ug += mass
    elif fact.kind == "FoodDelivered":
        mass = sum(fact.mass)
        require(individual.trip is not None and mass == individual.cargo_ug > 0 and fact.position == nest,
                "delivery and reconstructed cargo disagree")
        individual.seen("positive_delivery", fact)
        individual.cargo_ug = 0
        individual.trip.delivered_ug = mass
        individual.mass["delivered"] = [a + b for a, b in zip(individual.mass["delivered"], fact.mass)]
        individual.completed_delivery = True
        terminal(case, actor, individual, "DELIVERED", fact.time, fact.event, trips)
    elif fact.kind == "CargoIngested":
        require(0 < sum(fact.mass) <= individual.cargo_ug, "invalid reconstructed cargo debit")
        individual.cargo_ug -= sum(fact.mass)
    elif fact.kind == "ActionRejected":
        require(sum(fact.mass) == 0, "rejected action transferred mass")
        individual.outcome[fact.outcome] += 1
        counts["collection_rejected"] += bool(fact.resource and fact.mode == 3)
    elif fact.kind == "AutonomyDecision":
        counts["policy_candidates_examined"] += fact.auxiliary
    elif fact.kind == "AntDied":
        individual.seen("death", fact)
        counts["death_reason_code"] = fact.payload
        terminal(case, actor, individual, "DEATH", fact.time, fact.event, trips)


def status(individual, endpoint):
    if endpoint in individual.first:
        return "RECONSTRUCTED" if endpoint in ("departure", "feeder_arrival", "loaded_nest_arrival") else "COMMITTED_FACT"
    if "death" in individual.first:
        return "COMPETING_DEATH"
    return "RIGHT_CENSORED"


def individual_rows(case, config, summary, facts, dest):
    release, end = int(summary["release_ms"]), int(summary["horizon_ms"])
    cuts = rows(dest / "actors.csv")
    origins = {fact.actor: fact.position for fact in facts if fact.kind == "AntSeeded"}
    nest = next(fact.position for fact in facts if fact.kind == "ColonySeeded")
    feeders = {fact.position for fact in facts if fact.kind == "FoodSeeded"}
    observed = {int(r["actor"]): Individual(r["role"], origins[int(r["actor"])])
                for r in cuts if int(r["cut"]) == 1}
    start = {int(r["actor"]): r for r in cuts if int(r["sim_ms"]) == release}
    views = defaultdict(list)
    for item in rows(dest / "local_steps.csv"):
        views[int(item["actor"])].append(item)
    possible = [int(i["scheduled_id"]) for i in rows(dest / "inputs.csv") if i["input"] == "fixture_stock_removal_request"]
    depletions = [f for f in facts if f.source in possible and f.kind == "FoodCollected"]
    removal = depletions[0].event if depletions else None
    trips = []
    for fact in facts:
        if fact.actor in observed:
            observe(case, fact.actor, observed[fact.actor], fact, nest, feeders, trips, removal)
    individual_data = []
    for actor, individual in observed.items():
        terminal(case, actor, individual, "RIGHT_CENSORED", end, None, trips)
        profile = start[actor]
        actor_steps = views[actor]
        exposed = [r for r in actor_steps if int(r["sim_ms"]) >= release and float(r["effective_trail_units"]) > 0]
        release_units = [float(r["effective_trail_units"]) for r in actor_steps if int(r["sim_ms"]) == release]
        data = dict(case=case.key, world_id=config["world_id"], actor=actor, role=individual.role,
                    release_ms=release, horizon_ms=end, trajectory_m=individual.distance_m,
                    committed_moves=individual.counts["Moved"], marked_choices=individual.counts["marked_choices"],
                    marked_moves=individual.counts["marked_moves"], deposited_units=individual.marked_units,
                    deposit_moves=individual.counts["deposit_moves"], memory_choices=individual.counts["memory_choices"],
                    memory_moves=individual.counts["memory_moves"], forgot_memory=individual.counts["forgot_memory"],
                    searches_after_removal=individual.counts["search_after_depletion"],
                    forgot_after_removal=individual.counts["forgot_after_depletion"],
                    feeder_arrivals_after_removal=individual.counts["feeder_arrivals_after_removal"],
                    release_neighbors=profile["neighbors"], release_private_cells=profile["memory_cells"] or 0,
                    release_max_trail_units=max(release_units) if release_units else
                    (0 if profile["sensing_status"] == "CUT_SNAPSHOT" else None),
                    first_available_trail_cut_ms=min((int(r["sim_ms"]) for r in exposed), default=None),
                    sampled_exposure_cuts=len({r["cut"] for r in exposed}), sensory_response="UNOBSERVED",
                    cue_to_activation_cause="UNOBSERVED", actual_contact="UNOBSERVED",
                    policy_decisions=individual.counts["AutonomyDecision"],
                    policy_candidates_examined=individual.counts["policy_candidates_examined"],
                    collections_after_delivery=individual.counts["collections_after_delivery"],
                    repeat_same_resource=individual.counts["repeat_same_resource"],
                    partial_collection=individual.counts["partial_collection"],
                    collection_rejected=individual.counts["collection_rejected"],
                    cargo_ug_at_end=individual.cargo_ug, rejection_count=sum(individual.outcome.values()),
                    rejected_outcomes="|".join(f"{key}={value}" for key, value in sorted(individual.outcome.items())),
                    death_reason_code=individual.counts["death_reason_code"] if "death" in individual.first else None)
        for key in ENDPOINTS:
            at, event = individual.first.get(key, (None, None))
            data[key + "_ms"], data[key + "_event"], data[key + "_status"] = at, event, status(individual, key)
            data[key + "_count"] = individual.counts[key]
        for key, components in individual.mass.items():
            for name, mass in zip(COMPONENTS, components):
                data[f"{key}_{name}_ug"] = mass
            data[f"{key}_ug"] = sum(components)
        first_delivery = next((t for t in trips if t["actor"] == actor and t["terminal_status"] == "DELIVERED"), None)
        data["first_matched_loaded_return_ms"] = (first_delivery["terminal_ms"] - first_delivery["collection_ms"]
                                                   if first_delivery else None)
        individual_data.append(data)
    field_rows = rows(dest / "field.csv")
    launch_field = [float(r["effective_trail_units"]) for r in field_rows if int(r["sim_ms"]) == release]
    receipt = dict(case=case.key, family=case.family, layout=case.layout, signal=case.signal,
                   age=case.age, memory=case.memory, seed=case.seed, **summary,
                   release_marked_cells=len(launch_field), release_trail_units=sum(launch_field),
                   scout_delivered=int(any(f["role"] == "scout" and f["positive_delivery_count"] for f in individual_data)),
                   depletion_fact=removal, depletion_ug=sum(sum(f.mass) for f in depletions))
    return individual_data, trips, receipt


def rate(values):
    return mean(values) if values else None


def group_metrics(cohort, release):
    require(bool(cohort), "empty cohort")
    any_event = lambda item, name: item[name + "_status"] in ("COMMITTED_FACT", "RECONSTRUCTED")
    discovery = [i for i in cohort if any_event(i, "local_food_choice")]
    arrived = [i for i in cohort if any_event(i, "feeder_arrival")]
    collected = [i for i in cohort if any_event(i, "positive_collection")]
    delivered = [i for i in cohort if any_event(i, "positive_delivery")]
    return dict(subjects=len(cohort), cue=len(discovery), arrival=len(arrived), collection=len(collected), delivery=len(delivered),
                departed=sum(any_event(i, "departure") for i in cohort),
                autonomous_start=sum(any_event(i, "policy_forage") for i in cohort),
                collected_ug=sum(i["collected_ug"] for i in cohort), delivered_ug=sum(i["delivered_ug"] for i in cohort),
                path_m=mean(i["trajectory_m"] for i in cohort), marked_moves=sum(i["marked_moves"] for i in cohort),
                memory_choices=sum(i["memory_choices"] for i in cohort),
                collection_partial=sum(i["partial_collection"] for i in cohort),
                failed_actions=sum(i["rejection_count"] for i in cohort),
                delivery_censored=sum(i["positive_delivery_status"] == "RIGHT_CENSORED" for i in cohort),
                delivery_competing_death=sum(i["positive_delivery_status"] == "COMPETING_DEATH" for i in cohort),
                exposure=sum(i["sampled_exposure_cuts"] > 0 for i in cohort),
                cue_rate=len(discovery) / len(cohort), arrival_rate=len(arrived) / len(cohort),
                collection_rate=len(collected) / len(cohort),
                delivery_rate=len(delivered) / len(cohort),
                departure_rate=mean(any_event(i, "departure") for i in cohort),
                delivered_of_collectors=rate([any_event(i, "positive_delivery") for i in collected]),
                collected_of_arrivals=rate([any_event(i, "positive_collection") for i in arrived]),
                repeat_of_deliverers=rate([i["repeat_same_resource"] > 0 for i in delivered]),
                collection_ms=median(i["positive_collection_ms"] - release for i in collected) if collected else None,
                cue_ms=median(i["local_food_choice_ms"] - release for i in discovery) if discovery else None,
                delivery_ms=median(i["positive_delivery_ms"] - release for i in delivered) if delivered else None,
                pickup_to_delivery_ms=median(i["first_matched_loaded_return_ms"] for i in delivered)
                if delivered else None)


def comparison(groups):
    index = {(r["family"], r["layout"], r["signal"], r["memory"], r["age"], r["role"], r["seed"]): r for r in groups}
    result = []
    metrics = ("departure_rate", "cue_rate", "arrival_rate", "collection_rate", "delivery_rate", "collected_of_arrivals", "delivered_of_collectors",
               "repeat_of_deliverers", "collection_ms", "delivery_ms", "path_m", "marked_moves")

    def compare(name, arms, measures=metrics):
        for metric in measures:
            deltas = []
            for seed in SEEDS:
                values = [(index.get((*key, seed), {}).get(metric), sign) for key, sign in arms]
                if all(value is not None for value, _ in values):
                    deltas.append((seed, sum(sign * value for value, sign in values)))
            values = [value for _, value in deltas]
            lower = upper = None
            if len(values) >= 2:
                rng = random.Random(64207)
                boot = sorted(mean(rng.choices(values, k=len(values))) for _ in range(4096))
                lower, upper = boot[102], boot[3993]
            result.append(dict(contrast=name, metric=metric, paired_seeds=len(values), planned_seeds=len(SEEDS),
                               mean_delta=rate(values), lower_95=lower, upper_95=upper,
                               seed_deltas="|".join(f"{seed}:{value:.12g}" for seed, value in deltas)))

    for layout in ("near", "far"):
        def factorial(signal, memory):
            return ("factorial", layout, signal, memory, "fresh", "forager")
        for memory in (0, 1):
            compare(f"factorial/{layout}/memory{memory}/present-minus-blind",
                    [(factorial("present", memory), 1), (factorial("blind", memory), -1)])
        for signal in SIGNALS:
            compare(f"factorial/{layout}/{signal}/memory-on-minus-off",
                    [(factorial(signal, 1), 1), (factorial(signal, 0), -1)])
        compare(f"factorial/{layout}/trail-by-memory",
                [(factorial("present", 1), 1), (factorial("blind", 1), -1),
                 (factorial("present", 0), -1), (factorial("blind", 0), 1)])
    for role, age in product(("host_started", "policy_enrolled", "passive"), AGES):
        arm = lambda signal: ("scout", "near", signal, 0, age, role)
        compare(f"scout/{role}/{age}/present-minus-blind", [(arm("present"), 1), (arm("blind"), -1)])
        compare(f"scout/{role}/{age}/blind-minus-absent", [(arm("blind"), 1), (arm("absent"), -1)])
    for role, age in product(("host_started", "policy_enrolled"), ("aged", "expired")):
        arm = lambda a: ("scout", "near", "present", 0, a, role)
        compare(f"scout/{role}/fresh-minus-{age}", [(arm("fresh"), 1), (arm(age), -1)])
    for layout in ("wall", "gap", "deplete", "empty"):
        arm = lambda geometry: ("disruption", geometry, "absent", 1, "fresh", "forager")
        compare(f"disruption/{layout}-minus-open", [(arm(layout), 1), (arm("open"), -1)])
    for layout, control in (("dense8", "sparse8"), ("dense32", "dense8")):
        for role in ("host_started", "policy_enrolled", "passive"):
            arm = lambda geometry: ("density", geometry, "present", 0, "fresh", role)
            compare(f"density/{role}/{layout}-minus-{control}", [(arm(layout), 1), (arm(control), -1)])
    for age in AGES:
        arm = lambda signal: ("prepared", "straight", signal, 0, age, "detached")
        compare(f"prepared/{age}/present-minus-blind", [(arm("present"), 1), (arm("blind"), -1)],
                ("on_line_steps", "first_consecutive", "marked_choices"))
    return result


def rebuild(archive, out):
    groups, worlds, people, trips, prepared = [], [], [], [], []
    detached = {}
    for case in select(archive, []):
        keys = dict(case=case.key, family=case.family, layout=case.layout, signal=case.signal,
                    memory=case.memory, age=case.age, seed=case.seed)
        with extracted(archive, case) as data:
            if case.family == "prepared":
                track = verify_prepared(case, data)
                detached[(case.signal, case.age, case.seed)] = [(r["to_x"], r["to_z"]) for r in track]
                on_line = [r["marked_line"] == "1" for r in track]
                result = dict(keys, role="detached", on_line_steps=sum(on_line),
                              first_consecutive=on_line.index(False) if not all(on_line) else len(on_line),
                              marked_choices=sum(int(r["chosen_mode"]) == 1 for r in track))
                prepared.append(result)
                groups.append(result)
            else:
                config, summary, facts = verify_live(case, data)
                individuals, trip_rows, world = individual_rows(case, config, summary, facts, data)
                people.extend(individuals)
                trips.extend(trip_rows)
                worlds.append(world)
                for role in sorted({i["role"] for i in individuals}):
                    cohort = [i for i in individuals if i["role"] == role]
                    groups.append(dict(keys, role=role, **group_metrics(cohort, 0 if role == "scout" else
                                                                      int(summary["release_ms"]))))
    if prepared:
        for age, seed in product(AGES, SEEDS):
            a, b = (detached.get((signal, age, seed)) for signal in ("absent", "blind"))
            require(a is None or b is None or a == b, "blind prepared trajectory changed relative to blank")
    out.mkdir(parents=True)
    for name, data in (("case_results", worlds), ("individuals", people), ("trips", trips), ("group_metrics", groups),
                       ("paired_contrasts", comparison(groups)), ("prepared", prepared)):
        if data:
            write(out / (name + ".csv"), data)
    print(f"{len(worlds)} worlds, {len(people)} individuals, {len(trips)} episodes, {len(prepared)} detached paths")


def compare_archives(expected, actual):
    names = {path.name for path in actual.iterdir()}
    require(names == {path.name for path in expected.iterdir()}, "analysis artifact set differs")
    for name in sorted(names):
        wanted, rebuilt = rows(expected / name), rows(actual / name)
        require(len(wanted) == len(rebuilt), f"analysis row count differs: {name}")
        for left, right in zip(wanted, rebuilt):
            require(left.keys() == right.keys(), f"analysis columns differ: {name}")
            for key, value in left.items():
                if value == right[key]:
                    continue
                # Only decimal floats may differ by platform rounding. IDs, counts,
                # statuses and pipe-delimited identities remain exact.
                if any(c in value for c in ".eE") and any(c in right[key] for c in ".eE"):
                    try:
                        if math.isclose(float(value), float(right[key]), rel_tol=1e-12, abs_tol=1e-14):
                            continue
                    except ValueError:
                        pass
                raise ValueError(f"analysis cell differs: {name} / {key}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        with TemporaryDirectory(prefix="wp3-analysis-") as scratch:
            target = Path(scratch) / "comparison"
            rebuild(args.archive, target)
            compare_archives(args.out, target)
    else:
        rebuild(args.archive, args.out)


if __name__ == "__main__":
    main()
