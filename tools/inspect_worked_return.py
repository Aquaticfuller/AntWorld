"""Trace the final six hours of actual worker traffic before a recorded founder death."""

import argparse
from collections import Counter, deque
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path

from op0 import DAY
from op0.codec import ACTS, CASTES, KINDS, OUTCOMES, PHASES, PROGRAMS, STAGES, checkpoint, require
from op0.live import NativeCore, ROOT, core_path
from tools.compare_m0_worker_rhythm import facts


def inspect(core, trial):
    raw = core.call(trial["command"])
    require(sha256(raw).hexdigest() == trial["initial_sha256"], "World identity mismatch")
    stop = trial["queen_death"][1] - 1
    start = stop - DAY // 4
    for t in range(4 * DAY, start, 4 * DAY):
        core.call(f"ADVANCE {t}")
        core.call("COMPACT_HISTORY")

    def cut(frame):
        return {actor: dict(program=PROGRAMS[ant["program"]], position_m=ant["position_m"],
                            crop_ug=ant["crop_ug"], cargo_ug=ant["carried_ug"], route=route)
                for actor, route in frame["forager_routes"].items()
                if STAGES[(ant := frame["ants"][actor])["stage"]] == "Adult"}

    before = checkpoint(core.call(f"ADVANCE {start}"), forager_routes=True)
    raw = core.call(f"ADVANCE {stop}")
    after = checkpoint(raw, forager_routes=True)
    counts = Counter()
    last = {}
    founder, = (actor for actor, ant in before["ants"].items() if CASTES[ant["caste"]] == "Queen")
    approaches = deque(maxlen=24)
    payments = []
    for f in facts(core, after["cursor"], before["cursor"]):
        if f.observation:
            phase, act, target = f.observation[:3]
            if ACTS[act] == "Approach a nestmate" and founder in (f.actor, target):
                approaches.append([f.id, f.time, f.actor, target, PHASES[phase], OUTCOMES[f.outcome], list(f.position)])
        if KINDS[f.kind] == "NutritionTransferred" and f.payload == founder and f.mass[0]:
            payments.append([f.id, f.time, f.actor, list(f.mass)])
        if f.actor not in after["forager_routes"]:
            continue
        kind = KINDS[f.kind]
        if kind in ("ForagingDecision", "Moved", "FoodCollected", "CargoIngested", "FoodDelivered", "ActionRejected"):
            label = f"{f.actor}/{kind}/{f.mode}/{f.reason}/{f.outcome}"
            counts[label] += 1
            last[label] = [f.id, f.time, list(f.position)]
    require(raw == core.call("FRAME"), "Read changed the world")
    end = checkpoint(core.call(f'ADVANCE {stop + 1}'))
    require(any(KINDS[f.kind] == "AntDied" and f.id == trial["queen_death"][0]
                for f in facts(core, end["cursor"], after["cursor"])), "Different terminal event")
    return dict(seed=trial["seed"], interval_ms=[start, stop], before=cut(before), after=cut(after),
                event_counts=counts, last_event=last, last_founder_approaches=list(approaches),
                founder_sugar_payments=payments, predeath_sha256=sha256(raw).hexdigest())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--core", type=Path, default=core_path())
    args = parser.parse_args()
    with closing(NativeCore(args.core.resolve(), ROOT / "out")) as core:
        print(json.dumps(inspect(core, json.loads(args.receipt.read_text(encoding="utf-8-sig")))))
