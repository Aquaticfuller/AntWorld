"""Inspect a worker's actual actions between identified adult emergence and death cuts."""

from argparse import ArgumentParser
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path

from op0 import DAY
from op0.codec import ACTS, KINDS, OUTCOMES, checkpoint, require
from op0.live import NativeCore, ROOT, core_path
from tools.compare_m0_worker_rhythm import facts
from tools.measure_single_nest_lifecycle import CHUNK_DAYS, COMPACT_BYTES


def inspect(core, trace, worker):
    life = trace["lives"][str(worker)]
    start, end = life["emergence"], life["death"]
    initial = core.call(trace["command"])
    require(sha256(initial).hexdigest() == trace["initial_sha256"], "Input world mismatch")
    kinds, actions, meals, gifts = Counter(), Counter(), [], []
    after = start["fact"]
    cuts = sorted({*range(CHUNK_DAYS * DAY, end["time_ms"], CHUNK_DAYS * DAY), start["time_ms"], end["time_ms"]})
    for time in cuts:
        frame = checkpoint(core.call(f"ADVANCE {time}"))
        if time >= start["time_ms"]:
            for event in facts(core, frame["cursor"], after):
                if event.id > end["fact"]:
                    break
                kind = KINDS[event.kind]
                if kind == "NutritionTransferred" and event.payload == worker:
                    gifts.append([event.id, event.time, event.actor, list(event.mass)])
                if event.actor != worker:
                    continue
                kinds[kind] += 1
                if event.observation:
                    actions[ACTS[event.observation[1]]] += 1
                if kind in ("NestIngested", "CargoIngested", "WorkerWaterIngested", "ActionRejected"):
                    meals.append([event.id, event.time, kind, OUTCOMES[event.outcome], list(event.mass)])
            after = frame["cursor"]
        if int(core.call("HISTORY_STORAGE").split()[2]) >= COMPACT_BYTES:
            core.call("COMPACT_HISTORY")
    require(frame["time_ms"] == end["time_ms"] and kinds["AntDied"] == 1, "Incomplete adult life interval")
    require(core.call("CHECK_LEDGERS") == b"", "Native ledger failure")
    return dict(run=trace["run"], seed=trace["seed"], worker=worker, command=trace["command"],
                initial_sha256=trace["initial_sha256"], emergence=start, death=end,
                depot_position_m=next(iter(frame["colonies"].values()))["position_m"],
                event_counts=kinds, action_observations=actions, intake_and_rejections=meals,
                received_transfers=gifts)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, default=core_path())
    parser.add_argument("--traces", type=Path, default=ROOT / "research/single_nest/PROTECTED_ADULT_BUDGETS.jsonl")
    parser.add_argument("--run", default="callow")
    parser.add_argument("--seed", type=int, default=3)
    parser.add_argument("--worker", type=int, required=True)
    args = parser.parse_args()
    trace, = (row for line in args.traces.read_text(encoding="utf-8-sig").splitlines()
              if (row := json.loads(line))["run"] == args.run and row["seed"] == args.seed)
    with closing(NativeCore(args.core.resolve(), ROOT / "out")) as core:
        print(json.dumps(inspect(core, trace, args.worker), separators=(",", ":")))


if __name__ == "__main__":
    main()
