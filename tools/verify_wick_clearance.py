"""Verify paid water and sugar from the seed-2 dehydration checkpoint."""

import argparse
from contextlib import closing
import gzip
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from op0.codec import ACTS, KINDS, PHASES, STAGES, checkpoint, require
from op0.live import NativeCore, ROOT, core_path
from tools.compare_m0_worker_rhythm import facts
from tools.verify_supply_continuity import fork_cut, verify_continuation


CUT = ROOT / "research/single_nest/SEED2_WICK_BLOCKAGE_CUT.awstate.gz"
CUT_SHA256 = "d77a6d0c1dcdcc857e30d888d7b40200955b9e2693a2d36d9d52a55deef797bb"
START = 5_443_200_000
DEADLINE = 5_610_240_000
FOUNDER, WATER_CARRIER, WICK = 2, 9, 3


def witness(event):
    return [event.id, event.time, event.actor, event.source, list(event.mass), event.position]


def replay(core, scratch, original, physics):
    world = checkpoint(original)["world"]
    slot = ("a" if physics == 93 else "e") * 32
    path = scratch / (slot + ".awstate")
    path.write_bytes(fork_cut(core, scratch, original, physics, reference=93))
    command = f"LOAD_SNAPSHOT {slot} {world}"
    raw = core.call(command)
    start = checkpoint(raw)
    require(start["time_ms"] == START and start["physics"] == physics, "Wrong replay cut")
    wick = next(row.split() for row in core.call("WICK_ACCESS").decode().splitlines()
                if row.startswith(f"{FOUNDER} "))
    donor = next(row.split() for row in core.call("ORAL_WATER").decode().splitlines()
                 if row.startswith(f"{WATER_CARRIER} "))
    require(wick[9:11] == ["1", "0"] and len(wick) == 15, "Founder unexpectedly has a clear wick route")
    require(donor[1:3] == ["1", "0"] and donor[7] == "0" and int(donor[-2]) > 0 and int(donor[-1]) > 0,
            "The blocked carrier and the founder no longer show a payable water request")
    require(core.call("FRAME") == raw, "Probing changed the replay cut")
    final = core.call(f"ADVANCE {DEADLINE}")
    end = checkpoint(final)
    history = list(facts(core, end["cursor"], start["cursor"]))
    deaths = [f for f in history if f.actor == FOUNDER and KINDS[f.kind] == "AntDied"]
    moves = [f for f in history if f.actor == FOUNDER and KINDS[f.kind] == "Moved"]
    drinks = [f for f in history if f.actor == FOUNDER and KINDS[f.kind] == "FoundressWaterIngested"]
    gifts = [f for f in history if KINDS[f.kind] == "NutritionTransferred" and f.payload == FOUNDER and any(f.mass)]
    uptake = [f for f in history if f.actor == FOUNDER and KINDS[f.kind] in ("PhysiologyUpdated", "FoundingBoundaryUptake")
              and (f.mass[0] or f.mass[2])]
    clearance = [f for f in history if f.actor in (8, 9) and f.observation and
                 PHASES[f.observation[0]] == "Completed" and ACTS[f.observation[1]] == "Move to a resting site"]
    result = dict(physics=physics, start_frame_sha256=sha256(raw).hexdigest(), wick_probe=wick, donor_probe=donor,
                  founder_moved=[witness(f) for f in moves], founder_water_from_wick=[witness(f) for f in drinks],
                  oral_receipts=[witness(f) for f in gifts], uptake=[witness(f) for f in uptake],
                  clearance=[witness(f) for f in clearance], founder_deaths=[[*witness(f), f.payload] for f in deaths],
                  wick_stock_ug=[start["sources"][WICK]["stock_ug"][2], end["sources"][WICK]["stock_ug"][2]],
                  final_sha256=sha256(final).hexdigest())
    require(core.call("CHECK_LEDGERS") == b"", "Wick replay violates conservation")
    if physics == 93:
        require([(f.id, f.time, f.payload) for f in deaths] == [(121_565, DEADLINE, 2)] and
                not (moves or drinks or gifts or uptake), "The dehydration control changed")
        return result

    require(not deaths and STAGES[end["ants"][FOUNDER]["stage"]] == "Adult", "Founder still dies")
    require(bool(drinks) and all(f.resource == WICK and f.mass[2] > 0 for f in drinks),
            "Missing funded intake from the original wick")
    first = drinks[0]
    require(result["wick_stock_ug"][0] - result["wick_stock_ug"][1] >= sum(f.mass[2] for f in drinks) and
            any(f.id < first.id and f.source == first.source and f.position == first.position for f in moves),
            "The founder drank without a committed arrival or source debit")
    yield_end = next((f for f in clearance if f.time < moves[0].time), None)
    require(yield_end is not None, "No worker repositioning before the founder's approach")
    yield_move = next(f for f in history if f.actor == yield_end.actor and f.source == yield_end.source and
                      KINDS[f.kind] == "Moved")
    meal = next((f for f in gifts if f.actor == WATER_CARRIER and f.mass[0] and f.mass[2]), None)
    require(meal is not None and any(f.time > meal.time and f.mass[2] > 0 for f in uptake) and
            any(f.time > meal.time and f.mass[0] > 0 for f in uptake), "Missing paid mixed meal and later uptake")
    mid_step = yield_move.time - max(1, (yield_move.aux >> 32) // 2)
    result["restored_suffix_sha256"] = verify_continuation(core, slot, world, mid_step, DEADLINE, final, end["cursor"])
    core.call(command)
    core.call(f"ADVANCE {meal.time-1}")
    paid_contact = next(row.split() for row in core.call("ORAL_ACCESS").decode().splitlines()
                        if row.startswith(f"{WATER_CARRIER} "))
    require(paid_contact[2] == "1", "The actual mouths were separated immediately before the mixed meal")
    result["first_paid_contact"] = paid_contact
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, default=core_path())
    parser.add_argument("--physics", type=int, choices=(95, 96), default=95)
    args = parser.parse_args()
    raw = gzip.decompress(CUT.read_bytes())
    require(sha256(raw).hexdigest() == CUT_SHA256, "The frozen wick checkpoint changed")
    scratch = ROOT / "out"
    scratch.mkdir(exist_ok=True)
    with TemporaryDirectory(dir=scratch, prefix="wick-clearance-") as temp, closing(NativeCore(args.core.resolve(), temp)) as core:
        print(json.dumps([replay(core, Path(temp), raw, physics) for physics in (93, args.physics)], separators=(",", ":")))


if __name__ == "__main__":
    main()
