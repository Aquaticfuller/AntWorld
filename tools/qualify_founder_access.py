"""Stream paired single-nest outcomes, full canonical digests and spatial access evidence."""

from argparse import ArgumentParser
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from op0 import DAY
from op0.codec import KINDS, U32, checkpoint, decode_fact
from op0.live import NativeCore, core_path


CUTS = (0, 4, 5, 12, 30, 60, 90, 120, 150)
CASES = ((1, "finite"), (2, "finite"), (3, "finite"), (2, "absent"))
COMMAND = {39: "NEW_ANATOMICAL_NEST", 40: "NEW_ORAL_NEST"}


def run_case(core, physics, seed, supply, cuts=CUTS):
    world = 9200 + seed + 10 * (supply == "absent")
    request = f"{COMMAND[physics]} {world} {seed} 250 80 plugged 1955 reachable {supply}"
    initial = core.call(request)
    cursor = 0
    trace = sha256()
    counts = Counter()
    first = {}
    totals = {}
    series = []
    chain = []
    workers = set()
    worker_outcomes = Counter()
    for day in cuts:
        raw = initial if not day else core.call(f"ADVANCE {day * DAY}")
        frame = checkpoint(raw)
        while cursor < frame["cursor"]:
            page = core.call(f"FACTS_AFTER {cursor} 512")
            if not page:
                raise ValueError("Missing committed history")
            trace.update(page)
            pos = 0
            while pos < len(page):
                size = U32.unpack_from(page, pos)[0]
                pos += U32.size
                _, fact = decode_fact(page[pos:pos + size])
                pos += size
                cursor += 1
                if fact.id != cursor or cursor > frame["cursor"]:
                    raise ValueError("Noncontiguous event page")
                kind = KINDS[fact.kind]
                if kind == "StageChanged" and fact.stage == 3:
                    key = "eclosion"
                    workers.add(fact.actor)
                elif kind == "AntDied" and fact.actor == 2:
                    key = "queen_death"
                elif kind == "AntDied" and fact.actor in workers:
                    worker_outcomes[fact.packet()["death_cause"]] += 1
                    key = "worker_death"
                elif kind == "FoundressNestMeal":
                    key = "queen_meal"
                elif kind in ("PhysiologyUpdated", "FoundingBoundaryUptake") and fact.actor == 2 and fact.mass[0]:
                    key = "queen_carb_uptake"
                elif kind in ("PhysiologyUpdated", "FoundingBoundaryUptake") and fact.actor in workers and any(fact.mass):
                    key = "worker_uptake"
                elif kind in ("SoilExcavated", "SoilDropped", "FoodCollected", "FoodDelivered", "FoundingRation",
                              "BroodMoved", "FoundingDietaryEggFunded", "FoundressWaterIngested", "CargoIngested",
                              "NestIngested", "NutritionTransferred"):
                    key = kind
                elif kind == "BiologicalObservation" and fact.actor == 2 and fact.packet()["action"]["act"] == "Approach the depot":
                    key = "approach_" + fact.packet()["action"]["phase"]
                else:
                    continue
                counts[key] += 1
                if key not in first:
                    first[key] = fact.packet()
                sequence = ("FoodDelivered", "queen_meal", "queen_carb_uptake")
                if len(chain) < len(sequence) and key == sequence[len(chain)] and fact.mass[0] and (
                        not chain or fact.time > chain[-1]["time_ms"]):
                    chain.append(fact.packet())
                if key in ("queen_meal", "queen_carb_uptake", "FoodDelivered", "FoundingRation", "CargoIngested",
                           "worker_uptake", "NestIngested", "NutritionTransferred"):
                    total = totals.setdefault(key, [0, 0, 0, 0])
                    for i, mass in enumerate(fact.mass):
                        total[i] += mass
        if core.call("CHECK_LEDGERS"):
            raise ValueError("Unexpected ledger response")
        queen = frame["ants"][2]
        series.append(dict(day=day, cursor=cursor, state_sha256=sha256(raw).hexdigest(), events_sha256=trace.hexdigest(),
                           workers=sum(a["caste"] == 0 and a["stage"] == 3 for a in frame["ants"].values()),
                           queen_alive=queen["stage"] == 3, energy_nj=queen["energy_nj"], water_ug=queen["hydration_ug"],
                           queen_pos_m=queen["position_m"], crop_ug=queen["crop_ug"], oxidized_ug=queen["oxidized_carbs_ug"],
                           stock_ug=frame["stored"]))
    return dict(request=request, seed=seed, supply=supply, physics=physics, cuts=series, first=first, counts=dict(counts),
                totals_ug=totals, worker_death_causes=dict(worker_outcomes), ledger_cuts=len(series),
                carbohydrate_chain=chain, ordered_access=len(chain)==3,
                native_memory_bytes=list(map(int, core.call("MEMORY").split())))


def compare_receipts(left_path, right_path):
    def load(path):
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        if [(row["seed"], row["supply"]) for row in rows] != list(CASES):
            raise ValueError(f"Incomplete or reordered world matrix in {path}")
        return rows

    matched = 0
    errors = []
    for left, right in zip(load(left_path), load(right_path)):
        if left["request"] != right["request"]:
            raise ValueError("World inputs differ between receipts")
        for row in (left, right):
            if tuple(cut["day"] for cut in row["cuts"]) != CUTS or row["ledger_cuts"] != len(CUTS):
                raise ValueError("Missing observation or ledger cut")
        for a, b in zip(left["cuts"], right["cuts"]):
            if a == b:
                matched += 1
            else:
                fields = ", ".join(key for key in a if a[key] != b.get(key))
                errors.append(f"{left['seed']} {left['supply']} day {a['day']}: {fields}")
        for key in ("counts", "totals_ug", "first", "carbohydrate_chain", "ordered_access", "worker_death_causes"):
            if left[key] != right[key]:
                errors.append(f"{left['seed']} {left['supply']}: {key}")
    print(f"{matched}/{len(CASES) * len(CUTS)} matching frame, canonical history and ledger cuts")
    if errors:
        raise SystemExit("\n".join(errors))


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, default=core_path())
    parser.add_argument("--physics", type=int, choices=COMMAND)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--compare", type=Path, nargs=2, metavar=("WINDOWS", "LINUX"))
    parser.add_argument("--scratch", type=Path, default=Path("out"))
    args = parser.parse_args()
    if args.compare:
        compare_receipts(*args.compare)
        return
    if args.physics is None or args.output is None:
        parser.error("simulation requires --physics and --output")
    binary = args.core.resolve()
    args.scratch.mkdir(exist_ok=True, parents=True)
    args.output.parent.mkdir(exist_ok=True, parents=True)
    with TemporaryDirectory(dir=args.scratch) as directory, args.output.open("w", encoding="utf-8", newline="\n") as out:
        for seed, supply in CASES:
            with closing(NativeCore(binary, Path(directory))) as core:
                case = run_case(core, args.physics, seed, supply)
            case["binary_sha256"] = sha256(binary.read_bytes()).hexdigest()
            print(json.dumps(case, sort_keys=True, separators=(",", ":")), file=out, flush=True)
            print(seed, supply, case["counts"], case["cuts"][-1]["workers"], flush=True)


if __name__ == "__main__":
    main()
