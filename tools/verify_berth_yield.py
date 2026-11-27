"""Check a paid, ordered surface handoff at the seed-2 entrance."""

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


CUT = ROOT / "research/single_nest/SEED2_BERTH_BLOCKAGE_CUT.awstate.gz"
CUT_SHA256 = "87eb90ca4336ee363acccc5636996f1bae265659c413fa6ee2a9c7ddd1ac446e"
START = 7_020_331_092
DEADLINE = 7_041_931_093
FOUNDER, EMPTY, LOADED = 2, 8, 9


def replay(core, folder, raw, physics):
    world = checkpoint(raw)["world"]
    slot = ("a" if physics == 95 else "e") * 32
    (folder / (slot + ".awstate")).write_bytes(fork_cut(core, folder, raw, physics, reference=95))
    initial = checkpoint(core.call(f"LOAD_SNAPSHOT {slot} {world}"), forager_routes=True)
    require(initial["time_ms"] == START and initial["physics"] == physics, "Wrong surface blockage cut")
    empty, loaded = (initial["ants"][i] for i in (EMPTY, LOADED))
    require(not any(empty["carried_ug"]) and loaded["carried_ug"] == (0, 282, 0, 0) and
            initial["forager_routes"][EMPTY]["path"] == initial["forager_routes"][LOADED]["path"],
            "Different loads or connector cell in the paired cut")
    frame = core.call(f"ADVANCE {DEADLINE}")
    final = checkpoint(frame)
    empty_moves, loaded_moves, deliveries, meals, uptake, deaths = [], [], [], [], [], []
    rests = {EMPTY: 0, LOADED: 0}
    for fact in facts(core, final["cursor"], initial["cursor"]):
        kind = KINDS[fact.kind]
        if fact.actor in rests:
            if kind == "Rested":
                rests[fact.actor] += 1
            elif kind == "Moved":
                (empty_moves if fact.actor == EMPTY else loaded_moves).append(fact)
            elif kind == "FoodDelivered":
                deliveries.append(fact)
            elif kind == "NutritionTransferred" and fact.payload == FOUNDER:
                meals.append(fact)
        if fact.actor == FOUNDER:
            if kind == "AntDied":
                deaths.append(fact)
            elif kind in ("PhysiologyUpdated", "FoundingBoundaryUptake") and fact.mass[0]:
                uptake.append(fact)
    result = dict(physics=physics, rests=rests, deaths=[[*witness(f), f.payload] for f in deaths],
                  deliveries=[witness(f) for f in deliveries], paid_meals=[witness(f) for f in meals],
                  sugar_absorption=[witness(f) for f in uptake], final_sha256=sha256(frame).hexdigest())
    require(core.call("CHECK_LEDGERS") == b"", "Berth replay violates conservation")
    if physics == 95:
        require(rests == {EMPTY: 720, LOADED: 720} and not (empty_moves or loaded_moves or deliveries or meals or uptake),
                "The control no longer reproduces the reciprocal block")
        require([(f.id, f.time, f.payload) for f in deaths] == [(658_358, DEADLINE, 1)],
                "The control death changed")
        return result

    require(empty_moves and loaded_moves and deliveries and meals and uptake,
            "A real passage, delivery, mouth transfer and founder absorption are required")
    yield_move, ingress, delivery = empty_moves[0], loaded_moves[0], deliveries[0]
    require(yield_move.time < ingress.time < delivery.time and ingress.position == empty["position_m"] and
            delivery.actor == LOADED and delivery.mass == loaded["carried_ug"],
            "The side-step did not let the original carrier enter and deliver its owned load")
    require(any(f.time > delivery.time and f.mass[0] for f in meals) and not deaths and
            STAGES[final["ants"][FOUNDER]["stage"]] == "Adult", "The founder did not eat and survive")
    during_yield = yield_move.time - max(1, (yield_move.aux >> 32) // 2)
    result.update(first_yield=witness(yield_move), first_ingress=witness(ingress),
                  restored_suffix_sha256=verify_continuation(core, slot, world, during_yield, DEADLINE, frame,
                                                              final["cursor"]))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, default=core_path())
    args = parser.parse_args()
    raw = gzip.decompress(CUT.read_bytes())
    require(sha256(raw).hexdigest() == CUT_SHA256, "The frozen berth checkpoint changed")
    (ROOT / "out").mkdir(exist_ok=True)
    with TemporaryDirectory(dir=ROOT / "out", prefix="berth-yield-") as temp, closing(NativeCore(args.core.resolve(), temp)) as core:
        print(json.dumps([replay(core, Path(temp), raw, physics) for physics in (95, 96)], separators=(",", ":")))


if __name__ == "__main__":
    main()
