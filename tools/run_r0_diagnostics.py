"""Stream actual long-horizon M0 facts into daily and individual R0 diagnostics."""

from argparse import ArgumentParser
from collections import Counter
from contextlib import closing
import csv
import gzip
from hashlib import sha256
from itertools import combinations, product
import json
from math import dist
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

from op0 import DAY
from op0.codec import ACTS, DEATHS, KINDS, PROGRAMS, STAGES, U32, checkpoint, decode_fact
from op0.live import NativeCore, ROOT, core_path


HORIZONS = (365, 450, 730)
SUPPLIES = ("continued", "limited", "water-restricted", "seasonal")
SEEDS = (1, 7)
EXTERNAL_GAIN = {"FoodSeeded", "FoodPlaced", "ResourceReleased"}
EXTERNAL_LOSS = {"FoodCollected", "FoundressWaterIngested"}
DEPOT_GAIN = {"FoodDelivered", "ProteinRecycled"}
DEPOT_LOSS = {"NestIngested", "FoundressNestMeal"}
BALANCES = ("queen_energy_nj", "queen_body_water_ug", "queen_crop_carbs_ug", "queen_crop_protein_ug",
            "queen_crop_water_ug", "queen_lipid_ug", "queen_mobile_protein_ug", "unreleased_carbs_ug",
            "unreleased_protein_ug", "unreleased_water_ug", "resident_history_bytes", "compressed_history_bytes")
FLOWS = ("eggs_laid", "hatched", "pupated", "workers_eclosed", "egg_deaths", "larval_deaths", "pupal_deaths",
         "worker_deaths", "queen_deaths", "food_collections", "food_deliveries", "exterior_food_deliveries",
         "transfers", "brood_actions", "brood_arrangements", "excavations", "soil_drops",
         "worker_moves", "known_worker_move_ms", "untimed_worker_moves", "first_exits", "rest_relocations")


def journal(core, cursor, tip, digest):
    while cursor < tip:
        data = core.call(f"FACTS_AFTER {cursor}")
        if not data:
            raise ValueError("Missing canonical journal page")
        digest.update(data)
        offset = 0
        while offset < len(data):
            size = U32.unpack_from(data, offset)[0]
            offset += U32.size
            _, fact = decode_fact(data[offset:offset + size])
            if fact.id != cursor + 1:
                raise ValueError("Nonconsecutive canonical event ID")
            yield fact
            offset += size
            cursor = fact.id
    if cursor != tip:
        raise ValueError("Fact cursor crossed the final cut")


def mass_columns(label, mass):
    return {f"{label}_{component}_ug": amount
            for component, amount in zip(("carbs", "protein", "water", "other"), mass, strict=True)}


class Traffic:
    def __init__(self, queen, surface):
        self.queen, self.surface = queen, surface
        self.stage, self.position, self.workers = {}, {}, {}
        self.external, self.depot, self.released = [0]*4, [0]*4, [0]*4
        self.day, self.total = Counter(), Counter()
        self.external_carriers, self.departed, self.moving_today = set(), set(), set()
        self.death_rows = []

    def commit(self, event):
        if event.outcome > 1:
            return
        actor, at, kind = event.actor, event.time, KINDS[event.kind]
        for stock, gain, loss in ((self.external, EXTERNAL_GAIN, EXTERNAL_LOSS), (self.depot, DEPOT_GAIN, DEPOT_LOSS),
                                  (self.released, {"ResourceReleased"}, set())):
            if kind in gain or kind in loss:
                sign = 1 if kind in gain else -1
                for index, amount in enumerate(event.mass):
                    stock[index] += sign*amount
        if kind in ("AntSeeded", "AntBorn", "StageChanged"):
            self.stage[actor], self.position[actor] = event.stage, event.position
        if kind == "AntBorn":
            self.day["eggs_laid"] += 1
        elif kind == "StageChanged":
            if event.stage in (1, 2, 3):
                self.day[("hatched", "pupated", "workers_eclosed")[event.stage-1]] += 1
            if event.stage == 3:
                self.workers[actor] = dict(born_ms=at, died_ms=None, program=0, program_ms=Counter(),
                                           program_since=at, active=None, stop=None, paid_ms=0,
                                           last_move=at, longest_no_move_ms=0, move_ms=0, distance_m=0.,
                                           speed_min=None, speed_max=None, moves=0, unknown_move_ms_count=0)
        if kind == "AntDied":
            stage = self.stage.get(actor)
            self.stage[actor] = 4
            label = "queen" if actor == self.queen else ("egg", "larval", "pupal", "worker")[stage]
            self.day[label + "_deaths"] += 1
            self.death_rows.append(dict(ant=actor, role=label, stage=STAGES[stage], event_id=event.id,
                                        time_ms=at, cause=DEATHS[event.payload], **mass_columns("external", self.external),
                                        **mass_columns("depot", self.depot)))
        if kind in ("Moved", "BroodMoved"):
            previous = self.position[actor]
            self.position[actor] = event.position
        else:
            previous = None
        w = self.workers.get(actor)
        if kind in ("FoodCollected", "FoodDelivered", "NutritionTransferred", "SoilExcavated", "SoilDropped"):
            self.day[{"FoodCollected": "food_collections", "FoodDelivered": "food_deliveries",
                      "NutritionTransferred": "transfers", "SoilExcavated": "excavations", "SoilDropped": "soil_drops"}[kind]] += 1
        if kind == "FoodCollected" and event.position[1] >= self.surface:
            self.external_carriers.add(actor)
        if kind == "FoodDelivered":
            if actor in self.external_carriers and event.position[1] < self.surface:
                self.day["exterior_food_deliveries"] += 1
            self.external_carriers.discard(actor)
        if kind == "BiologicalObservation" and event.observation[0] == 3:
            act = ACTS[event.observation[1]]
            self.day["rest_relocations"] += act == "Move to a resting site"
            self.day["brood_actions"] += act in {"Inspect brood", "Clean brood", "Arrange brood", "Feed brood",
                                                 "Pick up brood", "Transport brood", "Place brood"}
            self.day["brood_arrangements"] += act == "Arrange brood"
        if not w:
            return
        if kind == "BehaviorChanged":
            w["program_ms"][w["program"]] += at - w["program_since"]
            w["program"], w["program_since"] = event.payload, at
        elif kind == "ActivityChanged":
            if event.payload:
                w["active"] = event.source, at
            elif w["active"] and event.source == w["active"][0]:
                elapsed = at - w["active"][1]
                w["paid_ms"] += elapsed
                w["stop"] = event.source, at, elapsed
                w["active"] = None
        elif kind == "AntDied":
            w["died_ms"] = at
        elif kind == "Moved" and previous != event.position:
            length = dist(previous, event.position)
            w["distance_m"] += length
            w["moves"] += 1
            self.day["distance_m"] += length
            self.day["worker_moves"] += 1
            w["longest_no_move_ms"] = max(w["longest_no_move_ms"], at - w["last_move"])
            w["last_move"] = at
            self.moving_today.add(actor)
            if w["stop"] and w["stop"][:2] == (event.source, at) and w["stop"][2]:
                elapsed = w["stop"][2]
                w["move_ms"] += elapsed
                speed = length*1000/elapsed
                w["speed_min"] = min(w["speed_min"] or speed, speed)
                w["speed_max"] = max(w["speed_max"] or speed, speed)
                self.day["known_worker_move_ms"] += elapsed
            else:
                w["unknown_move_ms_count"] += 1
                self.day["untimed_worker_moves"] += 1
            if previous[1] < self.surface <= event.position[1] and actor not in self.departed:
                self.departed.add(actor)
                self.day["first_exits"] += 1

    def cut(self, core, frame):
        self.total.update(self.day)
        ants = frame["ants"]
        living = Counter(STAGES[a["stage"]] for a in ants.values() if a["caste"] == 0)
        adults = [a for a in ants.values() if a["stage"] == 3 and a["caste"] == 0]
        queen = ants[self.queen]
        width = 2 * frame["geometry"]["body_half_q"] * frame["geometry"]["quantum_m"]
        pairs = [(a["position_m"], b["position_m"]) for a, b in combinations(adults, 2)]
        extra = dict(zip(BALANCES, map(int, core.call(f"R0_BALANCES {self.queen}").split()), strict=True))
        if self.external != list(frame["available"]) or self.depot != list(frame["stored"]):
            raise ValueError("Event-derived food inventory disagrees with checkpoint")
        row = dict(day=frame["time_ms"]//DAY, facts=frame["cursor"], living_workers=living["Adult"],
                   eggs=living["Egg"], larvae=living["Larva"], pupae=living["Pupa"], queen_alive=queen["stage"] == 3,
                   **extra, **mass_columns("external", self.external), **mass_columns("depot", self.depot),
                   **mass_columns("released", self.released), excavation_mm3=frame["soil"][4]*(frame["geometry"]["quantum_m"]*1000)**3,
                   filled_mm3=frame["soil"][5]*(frame["geometry"]["quantum_m"]*1000)**3,
                   adult_exact_overlap_pairs=sum(a == b for a, b in pairs),
                   adult_body_overlap_pairs=sum(all(abs(x-y) < width-1e-12 for x, y in zip(a, b)) for a, b in pairs),
                   living_workers_no_move_record=sum(int(a["id"]) not in self.moving_today for a in adults),
                   daily_distance_m=self.day["distance_m"], cumulative_distance_m=self.total["distance_m"],
                   **{"daily_"+k: self.day[k] for k in FLOWS}, **{k: self.total[k] for k in FLOWS})
        self.day.clear()
        self.moving_today.clear()
        return row

    def individual_results(self, horizon_ms):
        for actor, w in self.workers.items():
            cut = w["died_ms"] if w["died_ms"] is not None else horizon_ms
            w["program_ms"][w["program"]] += cut - w["program_since"]
            yield dict(ant=actor, born_ms=w["born_ms"], died_ms=w["died_ms"], elapsed_alive_ms=cut-w["born_ms"],
                       longest_no_move_ms=max(w["longest_no_move_ms"],cut-w["last_move"]),
                       **{p.lower()+"_ms": w["program_ms"][i] for i, p in enumerate(PROGRAMS)},
                       **{key: w[key] for key in ("paid_ms", "move_ms", "unknown_move_ms_count", "distance_m",
                                                 "speed_min", "speed_max", "moves")})


def write_row(output, row):
    if output.tell() == 0:
        csv.DictWriter(output, fieldnames=row).writeheader()
    csv.DictWriter(output, fieldnames=row).writerow(row)


def trial(core, case, outputs, days):
    seed, supply, layout, physics = (case[k] for k in ("seed", "supply", "layout", "physics"))
    raw = core.call(f"NEW_R0_ASSAY {320000 + seed} {seed} {physics} {supply} {layout}")
    frame = checkpoint(raw)
    queen = next(a for a, row in frame["ants"].items() if row["caste"] == 1)
    traffic = Traffic(queen, frame["surface"]["origin_m"][1])
    digest, start, cursor = sha256(), perf_counter(), 0
    advance_s = 0.
    horizons = {}
    queen_end = None
    for day in range(days+1):
        if day:
            before = perf_counter()
            raw = core.call(f"ADVANCE {day * DAY}")
            advance_s += perf_counter()-before
            frame = checkpoint(raw)
        for fact in journal(core, cursor, frame["cursor"], digest):
            traffic.commit(fact)
        cursor = frame["cursor"]
        row = traffic.cut(core, frame)
        write_row(outputs[0], case | row)
        if day in HORIZONS or day == days:
            core.call("CHECK_LEDGERS")
            horizons[day] = row | {"facts_sha256": digest.hexdigest(), "frame_sha256": sha256(raw).hexdigest()}
        for death in traffic.death_rows:
            ant = frame["ants"][death["ant"]]
            details = {k: ant[k] for k in ("energy_nj", "hydration_ug", "tissue_protein_ug", "updated_ms")}
            entry = case | death | details | mass_columns("crop", ant["crop_ug"])
            write_row(outputs[1], entry)
            if death["ant"] == queen:
                queen_end = {**entry, "mobile_protein_ug": row["queen_mobile_protein_ug"], "lipid_ug": row["queen_lipid_ug"]}
        traffic.death_rows.clear()
    for result in traffic.individual_results(frame["time_ms"]):
        write_row(outputs[2], case | result)
    return case | dict(horizons=horizons, queen_death=queen_end, advance_s=round(advance_s, 4),
                       total_s=round(perf_counter()-start, 4), final_frame_bytes=len(raw))


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--core", type=Path, default=core_path())
    parser.add_argument("--seeds", type=int, nargs="+", default=SEEDS)
    parser.add_argument("--supplies", choices=(*SUPPLIES, "blocked"), nargs="+", default=SUPPLIES)
    parser.add_argument("--physics", choices=(29, 32), type=int, nargs="+", default=(29, 32))
    parser.add_argument("--days", type=int, choices=(*HORIZONS, 90), default=730)
    parser.add_argument("--layout", choices=("shaft", "dogleg"), default="shaft")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    core = args.core.resolve(strict=True)
    metadata = dict(core_sha256=sha256(core.read_bytes()).hexdigest(), days=args.days, seeds=args.seeds,
                    supplies=args.supplies, physics=args.physics, layout=args.layout,
                    protocol_sha256=sha256((ROOT / "research/r0/PROTOCOL.md").read_bytes()).hexdigest())
    (args.output / "inputs.json").write_text(json.dumps(metadata, indent=2)+"\n", encoding="utf-8")
    with (TemporaryDirectory(dir=args.output) as work,
          gzip.open(args.output / "daily.csv.gz", "wt", encoding="utf-8", newline="") as daily,
          gzip.open(args.output / "deaths.csv.gz", "wt", encoding="utf-8", newline="") as deaths,
          gzip.open(args.output / "individuals.csv.gz", "wt", encoding="utf-8", newline="") as workers,
          (args.output / "runs.jsonl").open("x", encoding="utf-8") as runs):
        failed = False
        for seed, supply, physics in product(args.seeds, args.supplies, args.physics):
            case = dict(seed=seed, supply=supply, layout=args.layout, physics=physics)
            print("Starting",case,flush=True)
            with closing(NativeCore(core, work)) as model:
                try:
                    result = trial(model, case, (daily, deaths, workers), args.days)
                except Exception as error:
                    result = case | {"error": str(error)}
                    failed = True
            runs.write(json.dumps(result)+"\n")
            runs.flush()
            print("Finished", case, result.get("total_s", result.get("error")), flush=True)
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
