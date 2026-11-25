"""Count committed trips, local food cues, crop loads and failed moves before founder death."""
import argparse
from collections import Counter
from contextlib import closing
import gzip
import json
from pathlib import Path

from op0 import DAY
from op0.codec import FORAGING_REASONS, KINDS, checkpoint
from op0.live import NativeCore, ROOT, core_path
from tools.compare_m0_worker_rhythm import facts
from tools.verify_sustained_contact import EVIDENCE


def trace(binary, seed, start, stop):
    with gzip.open(EVIDENCE / "SUSTAINED_CONTACT_TRIALS.jsonl.gz", "rt") as source:
        baseline = next(row for line in source if (row := json.loads(line))["physics"] == 67
                        and row["supply"] == "nearby" and row["seed"] == seed)
    days = []
    with closing(NativeCore(binary, ROOT / "out")) as core:
        core.call(baseline["command"])
        for day in range(1, stop + 1):
            frame = checkpoint(core.call(f"ADVANCE {DAY*day}"), forager_routes=True)
            if day > start:
                counts = Counter()
                for event in facts(core, frame["cursor"], cursor):
                    kind = KINDS[event.kind]
                    if kind == "ForagingDecision":
                        counts[(event.actor,FORAGING_REASONS[event.reason])] += 1
                    elif kind in ("FoodCollected","FoodDelivered","CargoIngested","NutritionTransferred"):
                        counts[(event.actor,kind+"_sugar_ug")] += event.mass[0]
                days.append(dict(day=day, decisions={f"{i}/{k}":n for (i,k),n in counts.items() if n},
                                 workers={i:{"mode":r["mode"],"enabled":r["enabled"],"position_m":frame["ants"][i]["position_m"],
                                             "crop_ug":frame["ants"][i]["crop_ug"]} for i,r in frame["forager_routes"].items()}))
            cursor = frame["cursor"]
            core.call("COMPACT_HISTORY")
    return dict(command=baseline["command"], start_day=start, end_day=stop, days=days)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core",type=Path,default=core_path())
    parser.add_argument("--seed",type=int,default=2)
    parser.add_argument("--start",type=int,default=46)
    parser.add_argument("--stop",type=int,default=82)
    args = parser.parse_args()
    if not 1 <= args.start < args.stop <= 730:
        parser.error("Require 1 <= start < stop <= 730")
    print(json.dumps(trace(args.core.resolve(),args.seed,args.start,args.stop),separators=(",",":")))
