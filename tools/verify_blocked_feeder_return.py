"""Replay seed 17 with sugar stranded on the surface for the final six hours."""

import argparse
from collections import Counter
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


CUT = ROOT / "research/single_nest/SEED17_STRANDED_CROP_CUT.awstate.gz"
CUT_SHA256 = "2a86242b8c96985eaf95254d6c0a31095bd3b671c96189a2453af49792dd799c"
START, DEADLINE = 7_276_277_684, 7_297_877_685
FOUNDER, DONORS = 2, (10, 14)


def replay(core, folder, raw, physics):
    world = checkpoint(raw)["world"]
    slot = ("a" if physics == 99 else "e") * 32
    (folder / (slot + ".awstate")).write_bytes(fork_cut(core, folder, raw, physics, reference=99))
    start = checkpoint(core.call(f"LOAD_SNAPSHOT {slot} {world}"), forager_routes=True)
    require(start["time_ms"] == START and start["physics"] == physics and
            [(start["ants"][i]["crop_ug"][0], start["ants"][i]["carried_ug"],
              start["forager_routes"][i]["current_trip_liquid"]) for i in DONORS] ==
            [(441, (0, 0, 0, 0), False), (725, (0, 0, 0, 0), False)],
            "Wrong trapped donor inventory")
    end = core.call(f"ADVANCE {DEADLINE}")
    final = checkpoint(end)
    moves, meals, deaths, uptake = [], [], [], []
    blocked = Counter()
    for f in facts(core, final["cursor"], start["cursor"]):
        kind = KINDS[f.kind]
        if f.actor in DONORS:
            if kind == "Moved":
                moves.append(f)
            elif kind == "NutritionTransferred" and f.payload == FOUNDER and f.mass[0]:
                meals.append(f)
            elif kind == "ForagingDecision" and f.reason == 7:
                blocked[f.actor] += 1
        if f.actor == FOUNDER:
            if kind == "AntDied":
                deaths.append([f.id, f.time, f.payload])
            elif kind in ("PhysiologyUpdated", "FoundingBoundaryUptake") and f.mass[0]:
                uptake.append(f)
    receipt = dict(physics=physics, founder_start_energy_nj=start["ants"][FOUNDER]["energy_nj"],
                   founder_end_energy_nj=final["ants"][FOUNDER]["energy_nj"], blocked=blocked,
                   moves=[witness(f) for f in moves], meals=[witness(f) for f in meals],
                   sugar_absorption=[witness(f) for f in uptake], deaths=deaths,
                   final_sha256=sha256(end).hexdigest())
    require(core.call("CHECK_LEDGERS") == b"", "Cargo recirculation violates the resource ledger")
    if physics == 99:
        require(deaths == [[954466, DEADLINE, 1]] and not moves and not meals and
                blocked == {10: 720, 14: 720}, "Stranded crop control changed")
        return receipt

    require(not deaths and STAGES[final["ants"][FOUNDER]["stage"]] == "Adult" and meals and uptake,
            "No funded founder meal after surface traffic clearance")
    for meal in meals:
        require(any(f.actor == meal.actor and f.id < meal.id and f.position[1] < 0 for f in moves),
                "A donor paid without completing a physical underground move")
    step = moves[0]
    resume = step.time - max(1, (step.aux >> 32) // 2)
    receipt["restored_suffix_sha256"] = verify_continuation(core, slot, world, resume, DEADLINE, end, final["cursor"])
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, default=core_path())
    args = parser.parse_args()
    raw = gzip.decompress(CUT.read_bytes())
    require(sha256(raw).hexdigest() == CUT_SHA256, "Frozen stranded crop checkpoint changed")
    (ROOT / "out").mkdir(exist_ok=True)
    with TemporaryDirectory(dir=ROOT / "out", prefix="blocked-feeder-") as temp, closing(NativeCore(args.core.resolve(), temp)) as core:
        print(json.dumps([replay(core, Path(temp), raw, physics) for physics in (99, 100)], separators=(",", ":")))


if __name__ == "__main__":
    main()
