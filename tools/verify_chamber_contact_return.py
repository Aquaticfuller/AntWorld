"""Replay a fed carrier blocked at the actual floor of the founding chamber."""

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


CUT = ROOT / "research/single_nest/SEED29_CROP_RETURN_CUT.awstate.gz"
CUT_SHA256 = "521b658b4b9eea9b8f9a6066b9f58d683534c42cab1e332bb2e3c510f60c1d00"
DEADLINE = 6_581_141_432
FOUNDER, DONOR = 2, 8


def replay(core, folder, raw, physics):
    world = checkpoint(raw)["world"]
    slot = ("a" if physics == 101 else "e") * 32
    (folder / (slot + ".awstate")).write_bytes(fork_cut(core, folder, raw, physics, reference=101))
    start = checkpoint(core.call(f"LOAD_SNAPSHOT {slot} {world}"), forager_routes=True)
    require(start["time_ms"] == DEADLINE - 21_600_000 and start["physics"] == physics and
            start["ants"][DONOR]["crop_ug"][0] == 284 and start["forager_routes"][DONOR]["current_trip_liquid"],
            "Incorrect chamber return start")
    end = core.call(f"ADVANCE {DEADLINE}")
    final = checkpoint(end)
    meals, moves, deaths, rests = [], [], [], 0
    for f in facts(core, final["cursor"], start["cursor"]):
        kind = KINDS[f.kind]
        if f.actor == DONOR:
            if kind == "NutritionTransferred" and f.payload == FOUNDER:
                meals.append(f)
            elif kind == "Moved":
                moves.append(f)
            elif kind == "Rested":
                rests += 1
        if f.actor == FOUNDER and kind == "AntDied":
            deaths.append([f.id, f.time, f.payload])
    sugar, water = (sum(f.mass[i] for f in meals) for i in (0, 2))
    q = final["ants"][FOUNDER]
    result = dict(physics=physics, rests=rests, moves=[witness(f) for f in moves], meals=[witness(f) for f in meals],
                  sugar_ug=sugar, water_ug=water, deaths=deaths, founder_energy_nj=q["energy_nj"],
                  final_sha256=sha256(end).hexdigest())
    require(core.call("CHECK_LEDGERS") == b"", "Early contact berth violates conservation")
    if physics == 101:
        require(deaths == [[537798, DEADLINE, 1]] and rests == 720 and not (moves or meals),
                "The blocked chamber control changed")
    else:
        require(not deaths and STAGES[q["stage"]] == "Adult" and rests < 720 and (sugar, water) == (284, 86) and
                moves and meals and moves[0].time < meals[0].time,
                "No physical approach and paid meal after returning to the local berth")
        result["restored_suffix_sha256"] = verify_continuation(core, slot, world, meals[0].time - 1, DEADLINE,
                                                             end, final["cursor"])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, default=core_path())
    args = parser.parse_args()
    raw = gzip.decompress(CUT.read_bytes())
    require(sha256(raw).hexdigest() == CUT_SHA256, "Frozen chamber return checkpoint changed")
    (ROOT / "out").mkdir(exist_ok=True)
    with TemporaryDirectory(dir=ROOT / "out", prefix="chamber-contact-") as temp, closing(NativeCore(args.core.resolve(), temp)) as core:
        print(json.dumps([replay(core, Path(temp), raw, v) for v in (101, 102)], separators=(",", ":")))


if __name__ == "__main__":
    main()
