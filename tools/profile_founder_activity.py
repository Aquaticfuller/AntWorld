"""Attribute a published world's event workload to actual work in 30-day intervals."""

from argparse import ArgumentParser
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from op0 import DAY
from op0.codec import ACTS, FORAGING_REASONS, KINDS, OUTCOMES, PHASES, checkpoint
from op0.live import NativeCore, core_path, live_bodies
from tools.compare_m0_worker_rhythm import facts


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--core", type=Path, default=core_path())
    parser.add_argument("--seed", type=int, default=2)
    parser.add_argument("--supply", choices=("finite", "absent"), default="finite")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scratch", type=Path, default=Path("out"))
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.receipt.read_text(encoding="utf-8").splitlines()]
    row, = [r for r in rows if r["seed"] == args.seed and r["supply"] == args.supply]
    cut = row["cuts"][-1]
    duration = cut["day"] * DAY
    windows = []
    for end in range(30, cut["day"] + 1, 30):
        windows.append(dict(end_day=end, events=Counter(), rejections=Counter(), actions=Counter(),
                            foraging_reasons=Counter(), waiting_workers=Counter()))
    with TemporaryDirectory(dir=args.scratch) as tmp, closing(NativeCore(args.core.resolve(), Path(tmp))) as core:
        core.call(row["request"])
        raw = core.call(f"ADVANCE {duration}")
        if sha256(raw).hexdigest() != cut["state_sha256"]:
            raise ValueError("The final frame differs from the published world")
        seen = 0
        wall_handoffs = {}
        for fact in facts(core, cut["cursor"]):
            window = windows[max(0, fact.time - 1) // (30 * DAY)]
            kind = KINDS[fact.kind]
            window["events"][kind] += 1
            if row["physics"] == 42 and kind == "FoodDelivered" and fact.payload == 1:
                handoffs = wall_handoffs.setdefault(fact.actor, [])
                handoffs.append(dict(delivery=fact.packet(), next_movement=None))
            if kind == "Moved" and fact.actor in wall_handoffs:
                for handoff in reversed(wall_handoffs[fact.actor]):
                    if handoff["next_movement"] is not None:
                        break
                    handoff["next_movement"] = fact.packet()
            if kind == "ActionRejected":
                window["rejections"][OUTCOMES[fact.outcome]] += 1
            if kind == "ForagingDecision":
                window["foraging_reasons"][FORAGING_REASONS[fact.reason]] += 1
                if fact.mode == 6:
                    window["waiting_workers"][fact.actor] += 1
            if fact.observation:
                phase, act = fact.observation[:2]
                window["actions"][f"{ACTS[act]} / {PHASES[phase]}"] += 1
            seen += 1
        frame = checkpoint(raw)
        if seen != frame["cursor"] or core.call("CHECK_LEDGERS"):
            raise ValueError("The workload profile does not cover the complete canonical journal")
        bodies = live_bodies(core.call("BODY_STATES"), frame)
        survivors = {a["id"]: dict(position_m=a["position_m"], body=bodies[a["id"]], cargo_ug=a["carried_ug"],
                                   crop_ug=a["crop_ug"], program=a["program"])
                     for a in frame["ants"].values() if a["stage"] == 3}
    output = dict(request=row["request"], frame_sha256=cut["state_sha256"], cursor=seen, survivors=survivors,
                  depot=frame["colonies"][1], intervals=windows)
    if row["physics"] == 42:
        output["wall_handoffs"] = wall_handoffs
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
