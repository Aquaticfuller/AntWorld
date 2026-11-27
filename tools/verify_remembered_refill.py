"""Check a real feeder round trip from beyond immediate berth perception."""

import argparse
from contextlib import closing
import gzip
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from op0.codec import KINDS, STAGES, checkpoint, require
from op0.live import NativeCore, ROOT, core_path
from tools.compare_m0_worker_rhythm import facts
from tools.verify_supply_continuity import fork_cut, verify_continuation
from tools.verify_wick_clearance import witness


CUT = ROOT / "research/single_nest/SEED2_REFILL_MEMORY_CUT.awstate.gz"
CUT_SHA256 = "86a828a6dfe650f48aaa3029598a44f5f9a34542f55a41de5b7dc56a3c23602e"
START, DEADLINE = 7_344_000_000, 7_530_050_154
FOUNDER, WORKERS, FEEDER = 2, (8, 9), 4


def replay(core, folder, raw, physics):
    world = checkpoint(raw)["world"]
    slot = ("a" if physics == 98 else "e") * 32
    (folder / (slot + ".awstate")).write_bytes(fork_cut(core, folder, raw, physics, reference=98))
    initial = core.call(f"LOAD_SNAPSHOT {slot} {world}")
    start = checkpoint(initial, forager_routes=True)
    require(start["time_ms"] == START and start["physics"] == physics and
            all(not start["ants"][i]["crop_ug"][0] and start["forager_routes"][i]["last_source"] == FEEDER
                for i in WORKERS), "Wrong refill observation cut")
    probes = [row.split() for row in core.call("REFILL_ACCESS").decode().splitlines()]
    require({int(row[0]) for row in probes} == set(WORKERS) and
            all(row[5:7] == ["0", "1"] and len(row) == 10 for row in probes),
            "Missing experienced, out-of-range bearer with a physically clear local leg")
    require(core.call("FRAME") == initial, "Refill observation alters the state")
    end = core.call(f"ADVANCE {DEADLINE}")
    final = checkpoint(end)
    visits, collections, crop, meals, uptake, deaths, moves = [], [], [], [], [], [], []
    for f in facts(core, final["cursor"], start["cursor"]):
        kind = KINDS[f.kind]
        if f.actor in WORKERS:
            if kind == "ForagingStarted":
                visits.append(f)
            elif kind == "FoodCollected" and f.resource == FEEDER and f.mass[0]:
                collections.append(f)
            elif kind == "CargoIngested" and f.mass[0]:
                crop.append(f)
            elif kind == "NutritionTransferred" and f.payload == FOUNDER and f.mass[0]:
                meals.append(f)
            elif kind == "Moved":
                moves.append(f)
        if f.actor == FOUNDER:
            if kind in ("PhysiologyUpdated", "FoundingBoundaryUptake") and f.mass[0]:
                uptake.append(f)
            elif kind == "AntDied":
                deaths.append(f)
    result = dict(physics=physics, probes=probes, visits=[witness(f) for f in visits],
                  collections=[[*witness(f), f.resource] for f in collections], crop=[witness(f) for f in crop],
                  founder_meals=[witness(f) for f in meals], sugar_absorption=[witness(f) for f in uptake],
                  deaths=[[*witness(f), f.payload] for f in deaths], final_sha256=sha256(end).hexdigest())
    require(core.call("CHECK_LEDGERS") == b"", "Refill violates resource conservation")
    if physics == 98:
        require(not (visits or collections or crop or meals) and
                [(f.id, f.time, f.payload) for f in deaths] == [(297_353, DEADLINE, 1)],
                "The empty collector control changed")
        return result

    require(not deaths and STAGES[final["ants"][FOUNDER]["stage"]] == "Adult", "The founder did not survive refill")
    require(visits and collections and crop and meals and uptake, "Missing paid source-to-mouth chain")
    for actor in WORKERS:
        previous = start["cursor"]
        for phase in (visits, collections, crop, meals):
            fact = next((f for f in phase if f.actor == actor and f.id > previous), None)
            require(fact is not None, "The experienced worker did not resupply and feed the founder")
            previous = fact.id
    step = next(f for f in moves if f.time < visits[0].time)
    result["first_return_step"] = witness(step)
    during_step = step.time - max(1, (step.aux >> 32) // 2)
    result["restored_suffix_sha256"] = verify_continuation(core, slot, world, during_step, DEADLINE,
                                                          end, final["cursor"])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, default=core_path())
    args = parser.parse_args()
    raw = gzip.decompress(CUT.read_bytes())
    require(sha256(raw).hexdigest() == CUT_SHA256, "The frozen refill checkpoint changed")
    (ROOT / "out").mkdir(exist_ok=True)
    with TemporaryDirectory(dir=ROOT / "out", prefix="remembered-refill-") as temp, closing(NativeCore(args.core.resolve(), temp)) as core:
        print(json.dumps([replay(core, Path(temp), raw, physics) for physics in (98, 99)], separators=(",", ":")))


if __name__ == "__main__":
    main()
