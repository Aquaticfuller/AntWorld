"""Replay the nursery stall and compare nutrition timing and finite food supply."""

from argparse import ArgumentParser
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
from math import dist
from pathlib import Path
from tempfile import TemporaryDirectory

from op0.archive import file_hash, json_bytes
from op0.codec import KINDS, OUTCOMES, PROGRAMS, checkpoint
from op0.live import NativeCore, core_path
from tools.run_r0_diagnostics import journal


TREATMENTS = {"traffic": 1, "provisioned": 2, "cadence": 3, "no_food": 4}
SEEDS = (17, 29, 41)
CUTS_S = (60, 120, 300, 600, 1200, 1800, 2700, 3600)


def run(binary, directory, seed, treatment):
    command = f"NEW_NURSERY 91 {seed} {TREATMENTS[treatment]}"
    with closing(NativeCore(binary, directory)) as core:
        initial = core.call(command)
        frame = checkpoint(initial)
        workers = {id_ for id_, a in frame["ants"].items() if (a["stage"], a["caste"]) == (3, 0)}
        positions = {id_: frame["ants"][id_]["position_m"] for id_ in workers}
        digest, windows, begin_s = sha256(), [], 0
        cursor = frame["cursor"]
        for end_s in CUTS_S:
            final = core.call(f"ADVANCE {end_s * 1000}")
            frame = checkpoint(final)
            events, acts, moving = Counter(), Counter(), set()
            transfers, delivered = [0] * 4, [0] * 4
            travel_mm = 0
            for event in journal(core, cursor, frame["cursor"], digest):
                if event.actor not in workers:
                    continue
                kind = KINDS[event.kind]
                events[kind] += 1
                if kind == "Moved":
                    travel_mm += 1000 * dist(positions[event.actor], event.position)
                    positions[event.actor] = event.position
                    moving.add(str(event.actor))
                if kind in ("NutritionTransferred", "FoodDelivered") and OUTCOMES[event.outcome] in ("Success", "Partial"):
                    mass = transfers if kind == "NutritionTransferred" else delivered
                    for i, amount in enumerate(event.mass):
                        mass[i] += amount
                if event.observation and event.observation[0] == 3:
                    acts[event.packet()["action"]["act"]] += 1
            windows.append(dict(begin_s=begin_s, end_s=end_s, moving=sorted(moving, key=int),
                                travel_mm=round(travel_mm, 5), events=dict(events), acts=dict(acts),
                                transferred_ug=transfers, delivered_ug=delivered,
                                programs=dict(Counter(PROGRAMS[frame["ants"][i]["program"]] for i in workers))))
            begin_s, cursor = end_s, frame["cursor"]
        core.call("CHECK_LEDGERS")
    return dict(treatment=treatment, seed=seed, command=command, physics=frame["physics"], windows=windows,
                event_cursor=cursor, continuation_sha256=digest.hexdigest(),
                initial_sha256=sha256(initial).hexdigest(), final_sha256=sha256(final).hexdigest())


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--core", type=Path, default=core_path())
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    binary = args.core.resolve(strict=True)
    with TemporaryDirectory(dir=args.output.parent) as directory:
        cases = [run(binary, directory, seed, treatment) for seed in SEEDS for treatment in TREATMENTS]
    args.output.write_bytes(json_bytes(dict(binary_sha256=file_hash(binary), cases=cases)))
    for case in cases:
        print(json.dumps(dict(treatment=case["treatment"], seed=case["seed"],
                              moves=[w["events"].get("Moved", 0) for w in case["windows"]],
                              exchanges=[w["events"].get("NutritionTransferred", 0) for w in case["windows"]],
                              deliveries=[w["events"].get("FoodDelivered", 0) for w in case["windows"]])))


if __name__ == "__main__":
    main()
