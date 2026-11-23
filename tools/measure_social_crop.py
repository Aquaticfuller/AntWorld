"""Stream native food transactions and follow the lives of their recipients."""

import argparse
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path

from op0 import DAY
from op0.codec import DEATHS, KINDS, STAGES, require
from op0.live import NativeCore, ROOT, core_path
from op0.live import live_bodies
from tools.measure_single_nest_lifecycle import measure


class MouthLedger:
    def __init__(self, core=None):
        self.core = core
        self.cuts = []
        self.stages = {}
        self.eclosed = {}
        self.depot = [0, 0, 0, 0]
        self.flows = {}
        self.pending = {}
        self.uptakes = {}
        self.deaths = []
        self.last_collection = {}
        self.absorbed = Counter()
        self.direct_load = Counter()
        self.background = {}
        self.first_mouth = {}
        self.known_live_crops = {}
        self.other_crops_at_death = {}

    def withdraw_sugar(self, actor, amount):
        # Each upper bound refers to sugar still in this worker. Without a
        # tracer, any physically possible mixing order must be allowed.
        marked = self.direct_load[actor]
        background = self.background.get(actor)
        minimum = max(0, amount - background) if background is not None else 0
        maximum = min(amount, marked)
        require(minimum <= maximum, "Sugar debit exceeds the observed worker crop")
        self.direct_load[actor] -= minimum
        if background is not None:
            self.background[actor] -= amount - maximum
        return minimum, maximum

    def credit_background(self, actor, amount):
        if actor in self.background:
            self.background[actor] += amount

    def flow(self, key, f):
        row = self.flows.setdefault(key, dict(events=0, mass_ug=[0]*4, first=[f.id,f.time]))
        row["events"] += 1
        row["last"] = [f.id, f.time]
        for i, amount in enumerate(f.mass):
            row["mass_ug"][i] += amount

    def event(self, f, queen):
        kind = KINDS[f.kind]
        if kind in ("AntSeeded", "AntBorn", "StageChanged"):
            self.stages[f.actor] = STAGES[f.stage]
            if kind == "StageChanged" and self.stages[f.actor] == "Adult":
                self.eclosed[f.actor] = f.time
        if kind in ("FoodDelivered", "ProteinRecycled", "NestIngested", "FoundressNestMeal"):
            delta = 1 if kind in ("FoodDelivered", "ProteinRecycled") else -1
            for i, mass in enumerate(f.mass):
                self.depot[i] += delta * mass
            require(min(self.depot) >= 0, "Negative reconstructed nest stock")
        if kind == "FoodCollected":
            self.last_collection[f.actor] = f.resource
            self.flow(f"collection/{f.actor}/{f.resource}", f)
        elif kind == "CargoIngested":
            if f.actor in self.known_live_crops:
                self.known_live_crops[f.actor] += f.mass[0]
            self.flow(f"cargo-to-crop/{f.actor}/{self.last_collection.get(f.actor,0)}", f)
            if f.resource:
                require(f.resource == self.last_collection.get(f.actor) and not f.mass[1] and not f.mass[3],
                        "Social crop load disagrees with the worker's actual collection")
                self.flow(f"social-load/{f.actor}/{f.resource}", f)
                self.direct_load[f.actor] += f.mass[0]
            else:
                self.credit_background(f.actor, f.mass[0])
        elif kind == "NestIngested":
            self.credit_background(f.actor, f.mass[0])
            if f.actor in self.known_live_crops:
                self.known_live_crops[f.actor] += f.mass[0]
        elif kind == "NutritionTransferred":
            recipient = f.payload
            role = self.stages[recipient]
            if recipient == queen:
                role = "Queen"
            elif role == "Adult":
                role = "Callow" if f.time - self.eclosed[recipient] < 7 * DAY else "OlderWorker"
            self.flow(f"oral/{f.actor}/{recipient}/{role}", f)
            if f.actor in self.eclosed and f.mass[0]:
                lo, hi = self.withdraw_sugar(f.actor, f.mass[0])
                bounds = self.first_mouth.setdefault(f"{f.actor}/{recipient}/{role}", [0, 0])
                bounds[0] += lo
                bounds[1] += hi
            self.credit_background(recipient, f.mass[0])
            if recipient in self.known_live_crops:
                self.known_live_crops[recipient] += f.mass[0]
            if f.actor in self.known_live_crops:
                self.known_live_crops[f.actor] -= f.mass[0]
            if f.mass[0]:
                self.pending.setdefault(recipient,[f.id, f.time])
        elif kind in ("PhysiologyUpdated", "FoundingBoundaryUptake") and f.mass[0]:
            if f.actor in self.known_live_crops:
                self.known_live_crops[f.actor] -= f.mass[0]
            if f.actor in self.eclosed:
                self.withdraw_sugar(f.actor, f.mass[0])
            if f.actor in self.pending:
                gift = self.pending.pop(f.actor)
                row = self.uptakes.setdefault(f.actor, dict(episodes=0,first_pair=[*gift,f.id,f.time,f.mass[0]]))
                row["episodes"] += 1
                self.absorbed[f.actor] += f.mass[0]
        elif kind == "AntDied":
            self.known_live_crops.pop(f.actor, None)
            self.other_crops_at_death[f.id] = {ant: sugar for ant, sugar in self.known_live_crops.items() if sugar}
            self.deaths.append([f.actor,self.stages[f.actor],DEATHS[f.payload],f.id,f.time,*self.depot[:3]])

    def check(self, frame):
        colony, = frame["colonies"].values()
        require(tuple(self.depot) == tuple(colony["stock_ug"]), "Depot events disagree with native frame")
        if self.core and frame["time_ms"] in (49*DAY, 60*DAY, 73*DAY, 90*DAY, 150*DAY, 365*DAY, 730*DAY):
            bodies = live_bodies(self.core.call("BODY_STATES"), frame)
            adults = {ant: dict(center_m=a["position_m"], mouth_m=bodies[str(ant)]["mouth_m"],
                                crop_ug=a["crop_ug"]) for ant, a in frame["ants"].items()
                      if STAGES[a["stage"]] == "Adult"}
            self.cuts.append(dict(time_ms=frame["time_ms"], cursor=frame["cursor"], adults=adults,
                                  depot_ug=list(self.depot)))
        for ant in self.eclosed:
            sugar = frame["ants"][ant]["crop_ug"][0]
            if ant in self.known_live_crops:
                require(self.known_live_crops[ant] == sugar, "Tracked worker crop disagrees with native frame")
            if STAGES[frame["ants"][ant]["stage"]] == "Adult":
                self.known_live_crops[ant] = sugar
            known = self.background.get(ant)
            if known is not None:
                require(sugar <= known + self.direct_load[ant], "Untraced sugar entered an adult worker")
            self.background[ant] = min(sugar, known) if known is not None else sugar
            self.direct_load[ant] = min(sugar, self.direct_load[ant])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, default=core_path())
    parser.add_argument("--model", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--supply", choices=("nearby", "absent"), default="nearby")
    parser.add_argument("--days", type=int, default=730)
    args = parser.parse_args()
    with closing(NativeCore(args.core.resolve(), ROOT / "out")) as core:
        ledger = MouthLedger(core)
        run = measure(core, args.seed, args.supply, args.model, args.days, "wet-wick", True, ledger)
    run.update(binary_sha256=sha256(args.core.read_bytes()).hexdigest(), flows=ledger.flows,
               recipient_subsequent_uptake=ledger.uptakes, deaths_with_depot=ledger.deaths,
               worker_eclosion_ms=ledger.eclosed, sugar_absorbed_at_following_pulses_ug=ledger.absorbed)
    run["first_mouth_direct_source_sugar_bounds_ug"] = ledger.first_mouth
    run["other_worker_crop_sugar_at_death_ug"] = ledger.other_crops_at_death
    run["adult_mouth_cuts"] = ledger.cuts
    print(json.dumps(run, separators=(",",":")))


if __name__ == "__main__":
    main()
