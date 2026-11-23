"""Repeat one measured worker-to-founder transaction from a bounded continuation."""

import argparse
from contextlib import closing
from hashlib import sha256
import json
from math import dist
from pathlib import Path
from tempfile import TemporaryDirectory

from op0 import DAY
from op0.codec import KINDS, checkpoint, require
from op0.live import NativeCore, ROOT, core_path, live_bodies
from tools.compare_m0_worker_rhythm import facts


def verify(binary, trial):
    choices = [flow["first"] for key, flow in trial["mouths"].items()
               if key.endswith("/Queen") and flow["mass_ug"][0]]
    sequence = trial.get("step_then_meal", {}).get("queen_to_worker")
    event_id, time = sequence["meal"][:2] if sequence else min(choices)
    with TemporaryDirectory(dir=ROOT / "out") as temp, closing(NativeCore(binary, temp)) as core:
        initial = core.call(trial["command"])
        require(sha256(initial).hexdigest() == trial["initial_sha256"], "Different world")
        for t in range(4*DAY, time-1, 4*DAY):
            core.call(f"ADVANCE {t}")
            if int(core.call("HISTORY_STORAGE").split()[2]) >= 32*1024**2:
                core.call("COMPACT_HISTORY")
        before_raw = core.call(f"ADVANCE {time-1}")
        before = checkpoint(before_raw)
        bodies = live_bodies(core.call("BODY_STATES"), before)
        access = core.call("MEAL_ACCESS")
        require(core.call("FRAME")==before_raw, "Observation changed the authoritative state")
        slot = "1"*32
        core.call(f"SAVE_SNAPSHOT {slot}")
        size = (Path(temp) / (slot+".awstate")).stat().st_size
        after_raw = core.call(f"ADVANCE {time}")
        after = checkpoint(after_raw)
        batch = list(facts(core, after["cursor"], before["cursor"]))
        meal, = [f for f in batch if f.id==event_id and KINDS[f.kind]=="NutritionTransferred"]
        require(meal.mass[0]>0, "No positive sugar at the registered meal")
        donor, receiver = meal.actor, meal.payload
        debit = [x-y for x,y in zip(before["ants"][donor]["crop_ug"],after["ants"][donor]["crop_ug"])]
        credit = [y-x for x,y in zip(before["ants"][receiver]["crop_ug"],after["ants"][receiver]["crop_ug"])]
        require(debit==credit==list(meal.mass), "The actual crop changes do not match the meal")
        gap = dist(bodies[str(donor)]["mouth_m"], bodies[str(receiver)]["mouth_m"])
        require(gap<=0.000650001, "Mouths outside contact")
        projected = core.call(f'MEAL_EVENTS {before["cursor"]} {after["cursor"]-before["cursor"]}')
        require(core.call(f'LOAD_SNAPSHOT {slot} {before["world"]}')==before_raw, "Snapshot changed before contact")
        require(core.call("MEAL_ACCESS")==access and core.call(f"ADVANCE {time}")==after_raw and
                core.call(f'MEAL_EVENTS {before["cursor"]} {after["cursor"]-before["cursor"]}')==projected,
                "Continuation diverged at the oral transaction")
        require(core.call("CHECK_LEDGERS")==b"", "Ledger disagreement")
        return dict(seed=trial["seed"],physics=trial["physics"],event=event_id,time_ms=time,
                    donor=donor,receiver=receiver,mouth_gap_mm=1000*gap,debit_ug=debit,credit_ug=credit,
                    before_sha256=sha256(before_raw).hexdigest(),after_sha256=sha256(after_raw).hexdigest(),
                    snapshot_bytes=size)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt",type=Path)
    parser.add_argument("--core",type=Path,default=core_path())
    args = parser.parse_args()
    print(json.dumps(verify(args.core.resolve(), json.loads(args.receipt.read_text(encoding="utf-8-sig")))))
