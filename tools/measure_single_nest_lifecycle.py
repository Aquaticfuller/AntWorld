"""Measure Physics 45 colony growth from native frames and committed facts."""

from argparse import ArgumentParser
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
from statistics import median
from tempfile import TemporaryDirectory

from op0 import DAY
from op0.codec import CASTES, DEATHS, KINDS, STAGES, checkpoint, require
from op0.live import ROOT, NativeCore, core_path, founding_balance
from tools.compare_m0_worker_rhythm import facts


DAYS = (7, 14, 30, 49, 60, 150, 180, 365, 730)
WORLD_BASES = {"extended": 9800, "finite": 2**32 + 9800, "absent": 2 * 2**32 + 9800}
EGG, LARVA, PUPA, ADULT, DEAD = range(len(STAGES))
WORKER, QUEEN = CASTES.index("Worker"), CASTES.index("Queen")


def census(frame):
    living = Counter((ant["stage"], ant["caste"]) for ant in frame["ants"].values())
    return dict(day=frame["time_ms"] // DAY, eggs=living[EGG, WORKER], larvae=living[LARVA, WORKER],
                pupae=living[PUPA, WORKER], workers=living[ADULT, WORKER], queen_alive=bool(living[ADULT, QUEEN]))


def history(core, frame, queen):
    stages, eclosions, first = {}, {}, {}
    transitions, deaths = Counter(), Counter()
    delivery = [0, 0, 0]
    worker_lives = []
    alive = peak = 0
    peak_ms = last_worker_death_ms = None
    queen_death = None
    for fact in facts(core, frame["cursor"]):
        kind = KINDS[fact.kind]
        if kind in ("AntSeeded", "AntBorn", "StageChanged"):
            stages[fact.actor] = fact.stage
        if kind == "AntBorn":
            transitions["eggs_laid"] += 1
            first.setdefault("egg_ms", fact.time)
        elif kind == "StageChanged":
            if fact.stage == LARVA:
                transitions["hatched"] += 1
            elif fact.stage == PUPA:
                transitions["pupated"] += 1
            elif fact.stage == ADULT and frame["ants"][fact.actor]["caste"] == WORKER:
                eclosions[fact.actor] = fact.time
                first.setdefault("worker_ms", fact.time)
                alive += 1
                if alive > peak:
                    peak, peak_ms = alive, fact.time
        elif kind == "AntDied":
            stage = stages.pop(fact.actor)
            cause = DEATHS[fact.payload]
            if fact.actor == queen:
                queen_death = dict(time_ms=fact.time, event_id=str(fact.id), cause=cause)
            else:
                deaths[f"{STAGES[stage]}: {cause}"] += 1
                if fact.actor in eclosions:
                    worker_lives.append(fact.time - eclosions[fact.actor])
                    alive -= 1
                    last_worker_death_ms = fact.time
        elif kind == "FoodDelivered":
            for index, mass in enumerate(fact.mass[:3]):
                delivery[index] += mass
            if fact.mass[0]:
                first.setdefault("carbohydrate_delivery_ms", fact.time)
            if fact.mass[2]:
                first.setdefault("water_delivery_ms", fact.time)
    require(alive == census(frame)["workers"], "Worker eclosions and deaths disagree with the final frame")
    transitions["eclosed_workers"] = len(eclosions)
    return dict(transitions=transitions, offspring_deaths=deaths, first=first, peak_workers=peak, first_peak_ms=peak_ms,
                last_worker_death_ms=last_worker_death_ms, workers_still_alive=alive,
                median_worker_life_ms_among_deaths=median(worker_lives) if worker_lives else None,
                delivered_cpw_ug=delivery, queen_death=queen_death)


def measure(core, seed, supply):
    case_id = WORLD_BASES[supply] + seed
    command = f"NEW_VARIABLE_NEST {case_id} {seed} 250 80 plugged 1955 reachable {supply} sheltered mineral"
    initial = core.call(command)
    states = []
    for day in DAYS:
        raw = core.call(f"ADVANCE {day * DAY}")
        frame = checkpoint(raw)
        states.append(census(frame))
    require(core.call("CHECK_LEDGERS") == b"", "Native ledger verification failed")
    queen, = (identifier for identifier, ant in frame["ants"].items() if ant["caste"] == QUEEN)
    result = history(core, frame, queen)
    if death := result["queen_death"]:
        core.call(command)
        death_frame = checkpoint(core.call(f"ADVANCE {death['time_ms']}"))
        require(death_frame["ants"][queen]["stage"] == DEAD, "Queen death cut did not reproduce")
        surface_y = death_frame["surface"]["origin_m"][1]
        death.update(balance=founding_balance(core, death_frame, queen),
                     oxidized_carbs_ug=death_frame["ants"][queen]["oxidized_carbs_ug"],
                     nest_carbs_ug=sum(row["stock_ug"][0] for row in death_frame["colonies"].values()),
                     surface_carbs_ug=sum(row["stock_ug"][0] for row in death_frame["sources"].values()
                                          if row["position_m"][1] >= surface_y))
    return dict(command=command, world_id=frame["world"], physics=frame["physics"], seed=seed, supply=supply,
                initial_sha256=sha256(initial).hexdigest(), final_sha256=sha256(raw).hexdigest(), census=states,
                committed_facts=frame["cursor"], **result)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, default=core_path())
    parser.add_argument("--seed", type=int, action="append", help="Repeat to select multiple seeds. Default is 1, 2, 3.")
    parser.add_argument("--supply", choices=WORLD_BASES, default="extended")
    args = parser.parse_args()
    seeds = args.seed or (1, 2, 3)
    if any(not 1 <= seed <= 2147483647 for seed in seeds):
        parser.error("Seeds must be positive, at most 2147483647")
    scratch = ROOT / "out"
    scratch.mkdir(exist_ok=True)
    with TemporaryDirectory(dir=scratch, prefix="single-nest-lifecycle-") as work:
        with closing(NativeCore(args.core.resolve(), work)) as core:
            require(core.variable_nest, "Build the variable-nest live executable first")
            for seed in seeds:
                print(json.dumps(measure(core, seed, args.supply)), flush=True)


if __name__ == "__main__":
    main()
