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
from tools.measure_single_nest_lifecycle import measure


class MouthLedger:
    def __init__(self):
        self.stages = {}
        self.eclosed = {}
        self.depot = [0, 0, 0, 0]
        self.flows = {}
        self.pending = {}
        self.uptakes = {}
        self.deaths = []
        self.last_collection = {}
        self.absorbed = Counter()

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
            self.flow(f"cargo-to-crop/{f.actor}/{self.last_collection.get(f.actor,0)}", f)
            if f.resource:
                require(f.resource == self.last_collection.get(f.actor) and not f.mass[1] and not f.mass[3],
                        "Social crop load disagrees with the worker's actual collection")
                self.flow(f"social-load/{f.actor}/{f.resource}", f)
        elif kind == "NutritionTransferred":
            recipient = f.payload
            role = self.stages[recipient]
            if recipient == queen:
                role = "Queen"
            elif role == "Adult":
                role = "Callow" if f.time - self.eclosed[recipient] < 7 * DAY else "OlderWorker"
            self.flow(f"oral/{f.actor}/{recipient}/{role}", f)
            if f.mass[0]:
                self.pending.setdefault(recipient,[f.id, f.time])
        elif kind == "PhysiologyUpdated" and f.mass[0] and f.actor in self.pending:
            gift = self.pending.pop(f.actor)
            row = self.uptakes.setdefault(f.actor, dict(episodes=0,first_pair=[*gift,f.id,f.time,f.mass[0]]))
            row["episodes"] += 1
            self.absorbed[f.actor] += f.mass[0]
        elif kind == "AntDied":
            self.deaths.append([f.actor,self.stages[f.actor],DEATHS[f.payload],f.id,f.time,*self.depot[:3]])

    def check(self, frame):
        colony, = frame["colonies"].values()
        require(tuple(self.depot) == tuple(colony["stock_ug"]), "Depot events disagree with native frame")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, default=core_path())
    parser.add_argument("--model", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--supply", choices=("nearby", "absent"), default="nearby")
    parser.add_argument("--days", type=int, default=730)
    args = parser.parse_args()
    ledger = MouthLedger()
    with closing(NativeCore(args.core.resolve(), ROOT / "out")) as core:
        run = measure(core, args.seed, args.supply, args.model, args.days, "wet-wick", True, ledger)
    run.update(binary_sha256=sha256(args.core.read_bytes()).hexdigest(), flows=ledger.flows,
               recipient_subsequent_uptake=ledger.uptakes, deaths_with_depot=ledger.deaths,
               worker_eclosion_ms=ledger.eclosed, sugar_absorbed_at_following_pulses_ug=ledger.absorbed)
    print(json.dumps(run, separators=(",",":")))


if __name__ == "__main__":
    main()
