"""Check an equal-crop founder meal against the original gradient rule."""

import argparse
from contextlib import closing
import gzip
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from op0.codec import KINDS, checkpoint, require
from op0.live import NativeCore, ROOT, core_path
from tools.compare_m0_worker_rhythm import facts
from tools.verify_supply_continuity import fork_cut, verify_continuation
from tools.verify_wick_clearance import witness


CUT = ROOT / "research/single_nest/SEED2_EQUAL_CROP_CUT.awstate.gz"
CUT_SHA256 = "81251084153e526da1a23029c2c5ce987ef58e3faa1840e7064e669029acaae2"
START, DEADLINE = 7_257_600_000, 7_511_440_938
FOUNDER, DONOR = 2, 8


def replay(core, folder, raw, physics):
    world = checkpoint(raw)["world"]
    slot = ("a" if physics == 96 else "e") * 32
    (folder / (slot + ".awstate")).write_bytes(fork_cut(core, folder, raw, physics, reference=96))
    command = f"LOAD_SNAPSHOT {slot} {world}"
    initial = core.call(command)
    start = checkpoint(initial)
    require(start["physics"] == physics and start["time_ms"] == START and
            all(start["ants"][i]["crop_ug"][0] == 26 for i in (FOUNDER, DONOR)), "Wrong equal-crop state")
    probe = next(row.split() for row in core.call("ORAL_WATER").decode().splitlines() if row.startswith(f"{DONOR} "))
    require(probe[1:3] == ["1", "1"] and probe[6] == "26" and
            probe[5] == ("0" if physics == 96 else "26"), "Different payable sugar or mouth contact")
    require(core.call("FRAME") == initial, "Read-only offer changed the cut")
    end = core.call(f"ADVANCE {DEADLINE}")
    finish = checkpoint(end)
    stream = list(facts(core, finish["cursor"], start["cursor"]))
    meals = [f for f in stream if KINDS[f.kind] == "NutritionTransferred" and f.payload == FOUNDER and f.mass[0]]
    uptake = [f for f in stream if KINDS[f.kind] in ("PhysiologyUpdated", "FoundingBoundaryUptake") and
              f.actor == FOUNDER and f.mass[0]]
    deaths = [f for f in stream if KINDS[f.kind] == "AntDied" and f.actor == FOUNDER]
    result = dict(physics=physics, probe=probe, founder_meals=[witness(f) for f in meals],
                  sugar_absorption=[witness(f) for f in uptake], final_sha256=sha256(end).hexdigest(),
                  deaths=[[*witness(f), f.payload] for f in deaths])
    require(core.call("CHECK_LEDGERS") == b"", "Sugar replay violates conservation")
    if physics == 96:
        require([(f.id, f.time, f.payload) for f in deaths] == [(315_026, DEADLINE, 1)],
                "The original energy death changed")
    else:
        require(meals and meals[0].actor == DONOR and meals[0].mass[0] == 26 and not deaths,
                "Equal crop suppressed the paid sugar or the founder died before the cutoff")
        first = meals[0]
        require(any(f.time > first.time for f in uptake), "No subsequent founder sugar absorption")
        if physics == 98:
            relay = next((f for f in meals if f.actor == 9), None)
            require(relay is not None and relay.time > first.time and relay.mass[0] > 0,
                    "The original worker still prevents a second donor from paying")
        result["restored_suffix_sha256"] = verify_continuation(core, slot, world, first.time-1, DEADLINE, end,
                                                              finish["cursor"])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, default=core_path())
    parser.add_argument("--physics", type=int, choices=(97, 98), default=98)
    args = parser.parse_args()
    raw = gzip.decompress(CUT.read_bytes())
    require(sha256(raw).hexdigest() == CUT_SHA256, "The frozen equal-crop checkpoint changed")
    (ROOT / "out").mkdir(exist_ok=True)
    with TemporaryDirectory(dir=ROOT / "out", prefix="founder-sugar-") as temp, closing(NativeCore(args.core.resolve(), temp)) as core:
        old, new = [replay(core, Path(temp), raw, p) for p in (96, args.physics)]
        require(new["founder_meals"][0][1] < old["founder_meals"][0][1], "Equal crop still delays intake")
        print(json.dumps([old, new], separators=(",", ":")))


if __name__ == "__main__":
    main()
