"""Verify a local detour and funded meal from the frozen seed-2 snapshot."""

import argparse
from contextlib import closing
import gzip
from hashlib import sha256
import json
from math import dist
from pathlib import Path
from tempfile import TemporaryDirectory

from op0.codec import ACTS, KINDS, PHASES, STAGES, checkpoint, require
from op0.live import NativeCore, ROOT, core_path, live_bodies
from tools.audit_founding_activity import same_cut
from tools.compare_m0_worker_rhythm import facts
from tools.verify_supply_continuity import ENERGY_CUTS, EVIDENCE, fork_cut, verify_continuation


CUT = ROOT / "research/single_nest/SEED2_FINAL_SUGAR_CUT.awstate.gz"
CUT_SHA256 = "47612f6a350efb1ef31e0c8c411455494e4dccd0b4c5964be3ffda40aa4c3c5f"
START = 6_717_934_579
DEATH = 6_950_144_690
FOUNDER, DONOR = 2, 8


def gap_mm(core, frame):
    poses = live_bodies(core.call("BODY_STATES"), frame)
    return 1000 * dist(poses[str(FOUNDER)]["mouth_m"], poses[str(DONOR)]["mouth_m"])


def replay(core, folder, original, physics):
    path = folder / ("a" * 32 + ".awstate")
    path.write_bytes(fork_cut(core, folder, original, physics, reference=90))
    world = checkpoint(original)["world"]
    command = f"LOAD_SNAPSHOT {path.stem} {world}"
    initial = core.call(command)
    start = checkpoint(initial)
    require(start["physics"] == physics and start["time_ms"] == START, "Wrong replay boundary")
    probes = {int(row[0]): row[1:] for row in map(str.split, core.call("ORAL_ROUTE").decode().splitlines())}
    initial_gap = gap_mm(core, start)
    require(core.call("FRAME") == initial, "Route probe changed authoritative state")
    final = core.call(f"ADVANCE {DEATH}")
    frame = checkpoint(final)
    moves, turns, bouts, receipts, absorption = [], [], [], [], []
    for event in facts(core, frame["cursor"], start["cursor"]):
        kind = KINDS[event.kind]
        if kind == "Moved" and event.actor == DONOR:
            moves.append([event.id, event.time, event.position, event.aux >> 32, event.aux & 0xffff])
        if kind == "Moved" and event.actor in (FOUNDER, DONOR) and event.aux & 0xffff:
            turns.append([event.id, event.time, event.actor, event.aux & 0xffff])
        if event.actor == DONOR and event.observation and event.observation[2] == FOUNDER:
            phase, act, _, bout, began, *_ = event.observation
            if ACTS[act] == "Approach a nestmate":
                bouts.append([event.id, event.time, PHASES[phase], bout, began, event.position])
        if kind == "NutritionTransferred" and event.payload == FOUNDER and event.mass[0]:
            receipts.append([event.id, event.time, event.actor, event.mass, event.source])
        if event.actor == FOUNDER and kind in ("PhysiologyUpdated", "FoundingBoundaryUptake") and event.mass[0]:
            absorption.append([event.id, event.time, event.mass[0]])
    alive = STAGES[frame["ants"][FOUNDER]["stage"]] == "Adult"
    result = dict(physics=physics, probe=probes[DONOR], moves=moves, turns=turns, approaches=bouts,
                  initial_gap_mm=initial_gap,
                  receipts=receipts, sugar_uptake=absorption, founder_alive=alive,
                  facts=frame["cursor"] - start["cursor"], final_sha256=sha256(final).hexdigest())
    if physics == 90:
        probe = probes[DONOR]
        require(probe[:2] == ["1", "0"] and int(probe[4]) > 0 and probe[6] == "0" and probe[11] == "1",
                "The control no longer has a visible offer and an unscheduled approach")
        require(not moves and not receipts and not alive, "Terminal control changed")
    else:
        delivered = [receipt for receipt in receipts if receipt[2] == DONOR]
        require(delivered and alive, "Donor 8 did not feed the founder before the terminal cutoff")
        before_meal = [move for move in moves if move[1] < delivered[0][1]]
        require(before_meal and any(turn[1] < delivered[0][1] for turn in turns),
                "Payment lacks a measured donor approach and a turn by either participant")
        require(any(b[2] == "Completed" and b[1] < delivered[0][1] for b in bouts),
                "No completed donor approach to the founder")
        require(any(at > delivered[0][1] for _, at, _ in absorption), "No subsequent sugar uptake")
        first_move = before_meal[0]
        mid_step = first_move[1] - first_move[3] // 2
        result["restored_suffix_sha256"] = verify_continuation(core, path.stem, world, mid_step,
                                                               DEATH, final, frame["cursor"])
        core.call(command)
        result["first_step_gap_mm"] = gap_mm(core, checkpoint(core.call(f"ADVANCE {first_move[1]}")))
        core.call(f"ADVANCE {delivered[0][1]-1}")
        contact = next(row.split() for row in core.call("ORAL_ACCESS").decode().splitlines()
                       if row.split()[0] == str(DONOR))
        require(contact[2] == "1", "The actual mouths were separated just before handling ended")
        result["first_paid_contact"] = contact
    require(core.call("CHECK_LEDGERS") == b"", "Replay changed the resource ledger")
    path.unlink()
    return result


def verify_secondary_controls(core, folder):
    rows = {}
    for seed in (3, 17):
        expected, world, end = ENERGY_CUTS[seed]
        path = EVIDENCE / f"SEED{seed}_ENERGY_SUPPLY_CUT.awstate.gz"
        require(sha256(gzip.decompress(path.read_bytes())).hexdigest() == expected, "Secondary control changed")
        rows[seed] = same_cut(core, folder, path, world, 78, 93, end)
    require(sum(receipt[3][0] for receipt in rows[3]["founder_receipts"]) == 213 and rows[3]["actors"][2]["death"] is None,
            "The fallback lost the previous seed-3 feeding route")
    inaccessible = next(row.split() for row in rows[17]["start_oral"] if row.split()[0] == "11")
    require(inaccessible[1] == "0" and int(inaccessible[5]) and
            all(receipt[2] != 11 for receipt in rows[17]["founder_receipts"]),
            "An occluded offer reached the queen across the blocked approach")
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, default=core_path())
    parser.add_argument("--physics", type=int, choices=(92, 93), default=93)
    args = parser.parse_args()
    original = gzip.decompress(CUT.read_bytes())
    require(sha256(original).hexdigest() == CUT_SHA256, "The frozen seed-2 snapshot changed")
    scratch = ROOT / "out"
    scratch.mkdir(exist_ok=True)
    with TemporaryDirectory(dir=scratch, prefix="oral-approach-") as temp, closing(NativeCore(args.core.resolve(), temp)) as core:
        records = [replay(core, Path(temp), original, physics) for physics in (90, args.physics)]
        if args.physics == 93:
            records[-1]["secondary_controls"] = verify_secondary_controls(core, Path(temp))
        print(json.dumps(records, separators=(",", ":")))


if __name__ == "__main__":
    main()
