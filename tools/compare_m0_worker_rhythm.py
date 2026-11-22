"""Run paired MicroWorld worker rhythm fixtures and count committed actions."""

from argparse import ArgumentParser
from collections import Counter, defaultdict
from contextlib import closing
from itertools import groupby
import json
from pathlib import Path
from statistics import quantiles
from tempfile import TemporaryDirectory

from op0 import DAY
from op0.codec import ACTS, CASTES, KINDS, PHASES, U32, checkpoint, decode_fact
from op0.live import ROOT, NativeCore, core_path


MINUTE = 60_000
PROFILES = {"standard": "", "5-minute": " 300000 1800000", "15-minute": " 900000 3600000"}
INGESTED = {"NestIngested", "CargoIngested", "FoundressNestMeal", "FoundressWaterIngested"}
CARE = {"Inspect brood", "Arrange brood", "Clean brood", "Pick up brood", "Place brood"}


def facts(core, end, after=0):
    latest = after
    while latest < end:
        raw = core.call(f"FACTS_AFTER {latest}")
        if not raw:
            raise ValueError("Missing facts at the end of the experiment")
        index = 0
        while index < len(raw):
            size = U32.unpack_from(raw, index)[0]
            index += U32.size
            _, fact = decode_fact(raw[index:index + size])
            if fact.id != latest + 1:
                raise ValueError("Canonical facts went out of order")
            latest = fact.id
            index += size
            yield fact


def describe(core, frame):
    counts = Counter()
    positions = {}
    emergence, death = {}, {}
    minutes, movement = defaultdict(set), defaultdict(set)
    workers = {i for i, a in frame["ants"].items() if CASTES[a["caste"]] == "Worker"}
    for f in facts(core, frame["cursor"]):
        if f.actor not in workers:
            continue
        kind = KINDS[f.kind]
        if f.stage == 3 and kind == "StageChanged":
            emergence[f.actor] = f.time
            positions[f.actor] = f.position
        if f.outcome > 1:
            continue
        if kind == "AntDied":
            death[f.actor] = f.time
        if f.actor not in emergence:
            continue
        category = None
        if kind == "Moved" and positions.get(f.actor) != f.position:
            positions[f.actor] = f.position
            category = "moves"
        elif kind in INGESTED and sum(f.mass):
            category = "intake"
        elif kind == "NutritionTransferred" and sum(f.mass):
            category = "transfers"
        elif kind in ("FoodDelivered", "SoilExcavated"):
            category = "deliveries" if kind == "FoodDelivered" else "excavations"
        elif f.observation and PHASES[f.observation[0]] == "Completed" and ACTS[f.observation[1]] in CARE:
            category = "brood_handling"
        if category is None:
            continue
        counts[category] += 1
        elapsed = f.time - emergence[f.actor]
        if elapsed < DAY:
            minutes[f.actor].add(elapsed // MINUTE)
            if category == "moves":
                movement[f.actor].add(elapsed // MINUTE)

    first = next(iter(emergence), None)
    available = min(DAY, death.get(first, frame["time_ms"]) - emergence[first]) // MINUTE if first else 0
    values = minutes[first]
    gaps = [sum(1 for _ in group) for active, group in groupby(i in values for i in range(available)) if not active]
    return dict(facts=frame["cursor"], worker_actions=dict(counts), first_worker_id=first,
                end_workers=sum(frame["ants"][i]["stage"] == 3 for i in workers), emerged=len(emergence),
                first_worker_survived_7_days=bool(first and death.get(first, frame["time_ms"]) - emergence[first] >= 7 * DAY),
                first_worker_scored_min=available, first_worker_action_min=sum(i < available for i in values),
                first_worker_move_min=sum(i < available for i in movement[first]),
                first_worker_longest_quiet_min=max(gaps, default=None),
                first_worker_quiet_p90_min=quantiles(gaps, n=10, method="inclusive")[-1] if len(gaps) > 1 else None)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, default=core_path())
    parser.add_argument("--seeds", type=int, nargs="+", default=(1, 7, 19))
    parser.add_argument("--profiles", choices=PROFILES, nargs="+", default=tuple(PROFILES))
    args = parser.parse_args()
    directory = ROOT / "out"
    directory.mkdir(exist_ok=True)
    with TemporaryDirectory(dir=directory, prefix="m0-rhythm-") as workdir:
        for seed in args.seeds:
            for name in args.profiles:
                with closing(NativeCore(args.core.resolve(), workdir)) as core:
                    core.call(f"NEW {270000 + seed} {seed}{PROFILES[name]}")
                    for day in range(10, 91, 10):
                        raw = core.call(f"ADVANCE {day * DAY}")
                    core.call("CHECK_LEDGERS")
                    results = describe(core, checkpoint(raw))
                    print(json.dumps({"seed": seed, "profile": name, "horizon_days": 90, **results}), flush=True)


if __name__ == "__main__":
    main()
