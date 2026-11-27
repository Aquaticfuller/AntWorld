"""Verify physical founder intake after deferring unnecessary refills."""

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


CUT = ROOT / "research/single_nest/SEED17_REFILL_DEMAND_CUT.awstate.gz"
CUT_SHA256 = "646f88aa23a788e2c0ae91bf62dd5da7219fdb322c3ef90c240b7e59ce7b3083"
START, DEADLINE = 7_948_800_000, 8_085_593_130
FOUNDER, DONOR = 2, 10


def replay(core, folder, raw, physics):
    world = checkpoint(raw)["world"]
    slot = ("a" if physics == 100 else "e") * 32
    (folder / (slot + ".awstate")).write_bytes(fork_cut(core, folder, raw, physics, reference=100))
    start = checkpoint(core.call(f"LOAD_SNAPSHOT {slot} {world}"))
    require(start["time_ms"] == START and start["physics"] == physics and start["ants"][DONOR]["crop_ug"][0] == 389,
            "Incorrect starting crop or replay time")
    end = core.call(f"ADVANCE {DEADLINE}")
    final = checkpoint(end)
    meals, deaths, moved = [], [], 0
    for f in facts(core, final["cursor"], start["cursor"]):
        kind = KINDS[f.kind]
        if f.actor == DONOR:
            if kind == "NutritionTransferred" and f.payload == FOUNDER:
                meals.append(f)
            elif kind == "Moved":
                moved += 1
        if f.actor == FOUNDER and kind == "AntDied":
            deaths.append([f.id, f.time, f.payload])
    q = final["ants"][FOUNDER]
    sugar, water = (sum(f.mass[i] for f in meals) for i in (0, 2))
    receipt = dict(physics=physics, moves=moved, meals=[witness(f) for f in meals],
                   sugar_ug=sugar, water_ug=water, deaths=deaths, energy_nj=q["energy_nj"],
                   final_sha256=sha256(end).hexdigest())
    require(core.call("CHECK_LEDGERS") == b"", "Refill policy changed resource conservation")
    if physics == 100:
        require(deaths == [[1207078, DEADLINE, 1]] and (moved, sugar, water) == (5930, 32, 7),
                "The recorded repeated-refill control changed")
    else:
        require(not deaths and STAGES[q["stage"]] == "Adult" and (moved, sugar, water) == (49, 375, 78),
                "Deferring refill did not recover the funded intake in the same cut")
        receipt["restored_suffix_sha256"] = verify_continuation(core, slot, world, meals[0].time - 1, DEADLINE,
                                                              end, final["cursor"])
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, default=core_path())
    args = parser.parse_args()
    raw = gzip.decompress(CUT.read_bytes())
    require(sha256(raw).hexdigest() == CUT_SHA256, "Frozen refill demand checkpoint changed")
    (ROOT / "out").mkdir(exist_ok=True)
    with TemporaryDirectory(dir=ROOT / "out", prefix="demand-refill-") as temp, closing(NativeCore(args.core.resolve(), temp)) as core:
        print(json.dumps([replay(core, Path(temp), raw, physics) for physics in (100, 101)], separators=(",", ":")))


if __name__ == "__main__":
    main()
