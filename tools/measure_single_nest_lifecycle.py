"""Measure founding colony growth from native frames and committed facts."""

from argparse import ArgumentParser
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
from statistics import median

from op0 import DAY
from op0.codec import CASTES, DEATHS, FORAGING_REASONS, KINDS, STAGES, checkpoint, require
from op0.live import ROOT, NativeCore, core_path, founding_balance
from tools.compare_m0_worker_rhythm import facts


DAYS = (7, 14, 30, 49, 55, 60, 90, 112, 150, 163, 180, 226, 286, 365, 730)
WORLD_BASES = {"extended": 9800, "finite": 2**32 + 9800, "absent": 2 * 2**32 + 9800, "nearby": 3 * 2**32 + 9800}
TREATMENTS = ("reference", "feeding", "budget", "sustained", "protected", "anatomical", "local-dig", "callow", "meal-search", "social-crop", "crop-exchange", "chamber-return", "mouth-range", "checked-offer", "local-departure", "meal-rendezvous", "first-meal", "responsive-meal", "work-face", "local-crop-return", "worked-exit", "sustained-contact", "yielding-return", "chamber-handoff", "body-orientation", "local-solicitation", "source-refill", "founder-appetite", "trip-load", "founder-route", "exit-attachment", "confirmed-meal-route", "stationary-body", "feeding-stance", "founder-wick", "repeat-collection", "work-face-detour", "familiar-site-detour", "nursery-arrival", "local-stimulus", "stimulus-meal-priority", "stimulus-refill-intent", "stimulus-mouth-visibility", "stimulus-final-leg", "bounded-meal-route", "local-needs", "joint-meal-route", "continuous-meal", "mouth-detour", "mouth-detour-fallback")
EGG, LARVA, PUPA, ADULT, DEAD = range(len(STAGES))
WORKER, QUEEN = CASTES.index("Worker"), CASTES.index("Queen")
NO_LEGAL_STEP = FORAGING_REASONS.index("No legal step")
CHUNK_DAYS = 14
COMPACT_BYTES = 96 * 1024 * 1024


def census(frame):
    living = Counter((ant["stage"], ant["caste"]) for ant in frame["ants"].values())
    return dict(day=frame["time_ms"] // DAY, eggs=living[EGG, WORKER], larvae=living[LARVA, WORKER],
                pupae=living[PUPA, WORKER], workers=living[ADULT, WORKER], queen_alive=bool(living[ADULT, QUEEN]))


def history(stream, through, queen, individual_records=False):
    stages, eclosions, first, worker_deaths = {}, {}, {}, {}
    transitions, deaths, larval_unused_crop = Counter(), Counter(), Counter()
    delivery = [0, 0, 0]
    nutrition = dict(queen_nest=[0, 0, 0], queen_worker=[0, 0, 0],
                     queen_larva=[0, 0, 0], worker_larva=[0, 0, 0], larval_uptake=[0, 0, 0])
    first_brood = set()
    later_depot_feeders = {}
    first_death_ms = None
    first_fed = set()
    first_brood_deaths = Counter()
    lives = {}
    soil_drops = Counter()
    last_carb_delivery = None
    alive = peak = 0
    peak_ms = last_worker_death_ms = None
    queen_death = None
    for fact, frame in stream:
        kind = KINDS[fact.kind]
        if (kind == "NestIngested" and fact.mass[0] and fact.actor in eclosions and
                fact.actor not in first_brood and fact.actor not in later_depot_feeders):
            later_depot_feeders[fact.actor] = [fact.id, fact.time, fact.mass[0]]
        if fact.actor in lives and stages.get(fact.actor) == ADULT and kind in (
                "Moved", "Rested", "WorkerWaterIngested", "FoodCollected", "FoodDelivered",
                "SoilExcavated", "SoilDropped", "NestIngested", "CargoIngested", "NutritionTransferred"):
            work = lives[fact.actor].setdefault("adult_actions", {})
            item = work.setdefault(kind, dict(count=0, first_fact=fact.id, last_fact=fact.id))
            item["count"] += 1
            item["last_fact"] = fact.id
        if kind in ("AntSeeded", "AntBorn", "StageChanged"):
            stages[fact.actor] = fact.stage
        if kind == "AntBorn":
            transitions["eggs_laid"] += 1
            if first_death_ms is not None and fact.time > first_death_ms:
                transitions["eggs_laid_after_first_juvenile_loss"] += 1
            if fact.time > 365 * DAY:
                transitions["eggs_after_year_one"] += 1
            first.setdefault("egg_ms", fact.time)
            if fact.time < first["egg_ms"] + DAY:
                first_brood.add(fact.actor)
                if individual_records:
                    lives[fact.actor] = dict(born_ms=fact.time, birth_fact=fact.id, feeds=[], stages=[])
        elif kind == "ReproductionAttempt" and fact.aux == 1:
            transitions["brood_budget_deferrals"] += 1
        elif kind == "StageChanged":
            if fact.actor in lives:
                lives[fact.actor]["stages"].append([fact.id, fact.time, STAGES[fact.stage]])
            if fact.stage == LARVA:
                transitions["hatched"] += 1
            elif fact.stage == PUPA:
                transitions["pupated"] += 1
            elif fact.stage == ADULT and frame["ants"][fact.actor]["caste"] == WORKER:
                eclosions[fact.actor] = fact.time
                if fact.aux:
                    transitions["eclosions_with_alternate_heading"] += 1
                if fact.time > 365 * DAY:
                    transitions["eclosions_after_year_one"] += 1
                first.setdefault("worker_ms", fact.time)
                alive += 1
                if alive > peak:
                    peak, peak_ms = alive, fact.time
        elif kind == "AntDied":
            stage = stages.pop(fact.actor)
            cause = DEATHS[fact.payload]
            if fact.actor in lives:
                lives[fact.actor]["death"] = [fact.id, fact.time, STAGES[stage], cause]
            if fact.actor == queen:
                queen_death = dict(time_ms=fact.time, event_id=str(fact.id), cause=cause)
            else:
                deaths[f"{STAGES[stage]}: {cause}"] += 1
                if stage < ADULT:
                    if first_death_ms is None:
                        first_death_ms = fact.time
                    if fact.actor in first_brood:
                        first_brood_deaths[f"{STAGES[stage]}: {cause}"] += 1
                if stage == LARVA:
                    crop = frame["ants"][fact.actor]["crop_ug"]
                    if crop[0] and cause == "Energy depleted":
                        larval_unused_crop["energy_death_with_carbohydrate"] += 1
                    if crop[2] and cause == "Dehydration":
                        larval_unused_crop["dehydration_with_water"] += 1
                if fact.actor in eclosions:
                    worker_deaths[fact.actor] = fact.time
                    alive -= 1
                    last_worker_death_ms = fact.time
        elif kind == "SoilDropped":
            surface_y = frame["surface"]["origin_m"][1]
            soil_drops["surface" if fact.position[1] >= surface_y else "underground"] += 1
        elif kind == "FoodDelivered":
            for index, mass in enumerate(fact.mass[:3]):
                delivery[index] += mass
            if fact.mass[0]:
                first.setdefault("carbohydrate_delivery_ms", fact.time)
                last_carb_delivery = fact.time
            if fact.mass[2]:
                first.setdefault("water_delivery_ms", fact.time)
            if fact.time > 365 * DAY:
                transitions["deliveries_after_year_one"] += 1
        elif kind == "WorkerWaterIngested":
            transitions["worker_wick_drinks"] += 1
            transitions["worker_wick_water_ug"] += fact.mass[2]
        elif kind == "ForagingStarted" and fact.aux == 1:
            transitions["connector_restarts"] += 1
        elif kind == "Moved" and fact.stage == ADULT and fact.actor != queen:
            transitions["adult_worker_moves"] += 1
        elif kind == "CargoIngested":
            transitions["worker_cargo_carbs_ug"] += fact.mass[0]
        elif kind == "ForagingDecision" and fact.reason == NO_LEGAL_STEP:
            transitions["foraging_decisions_without_legal_step"] += 1
        route = None
        if kind == "FoundressNestMeal":
            route = "queen_nest"
        elif kind == "FoundingRation":
            route = "queen_larva"
        elif kind == "NutritionTransferred":
            if fact.payload == queen:
                route = "queen_worker"
            elif stages.get(fact.payload) == LARVA:
                route = "worker_larva"
        elif kind == "PhysiologyUpdated" and fact.stage == LARVA:
            route = "larval_uptake"
        positive = any(fact.mass) or (kind == "FoundingRation" and fact.aux > 0)
        if route in ("queen_larva", "worker_larva") and fact.payload in first_brood and positive:
            first_fed.add(fact.payload)
            if fact.payload in lives:
                lives[fact.payload]["feeds"].append([fact.id, fact.time, fact.actor, *fact.mass[:3],
                                                     fact.aux if kind == "FoundingRation" else 0])
        if route:
            for index, mass in enumerate(fact.mass[:3]):
                nutrition[route][index] += mass
    transitions["eclosed_workers"] = len(eclosions)
    first_workers = first_brood & eclosions.keys()
    survival = {}
    for age in (7, 30, 90):
        counts = Counter()
        for worker in first_workers:
            target = eclosions[worker] + age * DAY
            death = worker_deaths.get(worker)
            status = "dead" if death is not None and death <= target else "alive" if target <= through else "censored"
            counts[status] += 1
        survival[age] = {status: counts[status] for status in ("alive", "dead", "censored")}
    return dict(transitions=transitions, offspring_deaths=deaths, first=first, peak_workers=peak, first_peak_ms=peak_ms,
                last_worker_death_ms=last_worker_death_ms, workers_still_alive=alive,
                median_worker_life_ms_among_deaths=median(when-eclosions[worker] for worker,when in worker_deaths.items()) if worker_deaths else None,
                first_brood_eggs=len(first_brood), first_brood_eclosed=len(first_workers), first_brood_worker_survival=survival,
                first_brood_fed=len(first_fed), first_brood_juvenile_deaths=first_brood_deaths, soil_drops=soil_drops,
                delivered_cpw_ug=delivery, nutrition_cpw_ug=nutrition, queen_death=queen_death,
                last_carbohydrate_delivery_ms=last_carb_delivery,
                larval_unused_crop=larval_unused_crop, later_worker_first_depot_carbs=later_depot_feeders,
                **({"first_brood_lives": lives} if individual_records else {}))


def measure(core, seed, supply, treatment, days, wick="small-wick", individual_records=False, observer=None):
    case_id = WORLD_BASES[supply] + seed + TREATMENTS.index(treatment) * (2**34)
    if wick == "wet-wick":
        case_id += 2**39
    elif wick == "nursery-wick":
        require(treatment == "protected", "Nursery wick requires the protected founding environment")
        case_id += 2**40
    settings = f"{case_id} {seed} 250 80 plugged 1955 reachable {supply} sheltered mineral"
    command = (f"NEW_VARIABLE_NEST {settings}" if treatment == "reference"
               else f"NEW_PROVISIONED_NEST {settings} {treatment}")
    if treatment == "anatomical":
        require(supply != "extended" and wick == "small-wick", "Unsupported anatomical reference conditions")
        command = f"NEW_ANATOMICAL_NEST {case_id} {seed} 250 80 plugged 1955 reachable {supply}"
    if wick != "small-wick":
        command += f" {wick}"
    initial = raw = core.call(command)
    frame = checkpoint(initial)
    queen, = (identifier for identifier, ant in frame["ants"].items() if ant["caste"] == QUEEN)
    states = []
    history_peak = compactions = 0
    # Old executables lack the compact command. Use their original census
    # cuts and retain their original limits for reproduction.
    checkpoints = {d for d in DAYS if d <= days} | {days}
    if days >= 73:
        checkpoints.add(73)
    review = checkpoints | set(range(CHUNK_DAYS, days, CHUNK_DAYS)) if core.sustained_nest else checkpoints

    def read():
        nonlocal raw, frame, history_peak, compactions
        after = 0
        for day in sorted(review):
            raw = core.call(f"ADVANCE {day * DAY}")
            frame = checkpoint(raw)
            if day in checkpoints:
                states.append(census(frame))
            for fact in facts(core, frame["cursor"], after):
                if observer is not None:
                    observer.event(fact, queen)
                yield fact, frame
            if observer is not None:
                observer.check(frame)
            after = frame["cursor"]
            _, _, encoded, _ = map(int, core.call("HISTORY_STORAGE").split())
            history_peak = max(history_peak, encoded)
            if core.sustained_nest and encoded >= COMPACT_BYTES:
                core.call("COMPACT_HISTORY")
                require(core.call("FRAME") == raw, "History compaction changed the checkpoint frame")
                compactions += 1

    result = history(read(), days * DAY, queen, individual_records)
    require(result["workers_still_alive"] == census(frame)["workers"],
            "Worker eclosions and deaths disagree with the final frame")
    require(core.call("CHECK_LEDGERS") == b"", "Native ledger verification failed")
    _, peak_rss, _ = map(int, core.call("MEMORY").split())
    if death := result["queen_death"]:
        core.call(command)
        if compactions:
            for cut in range(CHUNK_DAYS * DAY, death["time_ms"], CHUNK_DAYS * DAY):
                core.call(f"ADVANCE_STEP {cut}")
                if int(core.call("HISTORY_STORAGE").split()[2]) >= COMPACT_BYTES:
                    core.call("COMPACT_HISTORY")
        death_frame = checkpoint(core.call(f"ADVANCE {death['time_ms']}"))
        require(death_frame["ants"][queen]["stage"] == DEAD, "Queen death cut did not reproduce")
        surface_y = death_frame["surface"]["origin_m"][1]
        death.update(balance=founding_balance(core, death_frame, queen),
                     oxidized_carbs_ug=death_frame["ants"][queen]["oxidized_carbs_ug"],
                     nest_carbs_ug=sum(row["stock_ug"][0] for row in death_frame["colonies"].values()),
                     carried_carbs_ug=sum(a["carried_ug"][0] for a in death_frame["ants"].values()),
                     surface_carbs_ug=sum(row["stock_ug"][0] for row in death_frame["sources"].values()
                                          if row["position_m"][1] >= surface_y))
    return dict(command=command, world_id=frame["world"], physics=frame["physics"], seed=seed, supply=supply, treatment=treatment,
                wick=wick,
                initial_sha256=sha256(initial).hexdigest(), final_sha256=sha256(raw).hexdigest(), census=states,
                committed_facts=frame["cursor"], peak_encoded_history_bytes=history_peak, history_compactions=compactions,
                native_process_peak_rss_bytes=peak_rss, **result)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, default=core_path())
    parser.add_argument("--seed", type=int, action="append", help="Repeat to select multiple seeds. Default is 1, 2, 3.")
    parser.add_argument("--supply", choices=WORLD_BASES, default="extended")
    parser.add_argument("--treatment", choices=TREATMENTS, default="reference")
    parser.add_argument("--days", type=int, default=730)
    parser.add_argument("--wick", choices=("small-wick", "wet-wick", "nursery-wick"), default="small-wick")
    parser.add_argument("--individuals", action="store_true", help="Include first-brood stage, feed and death witnesses.")
    args = parser.parse_args()
    seeds = args.seed or (1, 2, 3)
    if any(not 1 <= seed <= 2147483647 for seed in seeds):
        parser.error("Seeds must be positive, at most 2147483647")
    if not 1 <= args.days <= 730:
        parser.error("The run length must be between 1 and 730 days")
    if args.wick == "wet-wick" and args.treatment == "reference":
        parser.error("The wet wick requires a provisioned nest treatment.")
    scratch = ROOT / "out"
    scratch.mkdir(exist_ok=True)
    with closing(NativeCore(args.core.resolve(), scratch)) as core:
        require(core.variable_nest, "Build the variable-nest live executable first")
        require(args.treatment == "reference" or core.provisioned_nest, "Build the provisioned-nest live executable first")
        require(args.treatment != "local-dig" or core.local_dig, "Build the local excavation executable first")
        require(args.treatment != "meal-search" or core.meal_search, "Build the worker search executable first")
        require((args.treatment != "callow" and args.wick != "nursery-wick") or core.callow_hydration,
                "Rebuild the live Core for the worker hydration trial")
        require(args.treatment != "protected" or core.protected_nest, "Build the protected founding executable first")
        require(args.treatment != "sustained" and args.wick == "small-wick" or core.sustained_nest,
                "Build the sustained-supply live executable first")
        for seed in seeds:
            print(json.dumps(measure(core, seed, args.supply, args.treatment, args.days, args.wick, args.individuals)), flush=True)


if __name__ == "__main__":
    main()
