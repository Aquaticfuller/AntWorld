"""Replay an empty crop, its external meal and the first gift to a newly emerged worker."""

from argparse import ArgumentParser
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path

from op0 import DAY
from op0.codec import KINDS, checkpoint, require
from op0.live import NativeCore, ROOT, core_path
from tools.compare_m0_worker_rhythm import facts
from tools.verify_protected_habitat import rows


def trace(core, trial):
    donor, callow = 8, 9
    pickup = trial["flows"]["collection/8/4"]["first"]
    gift = trial["flows"]["oral/8/9/Callow"]["first"]
    uptake = trial["recipient_subsequent_uptake"]["9"]["first_pair"]
    initial = core.call(trial["command"])
    require(sha256(initial).hexdigest() == trial["initial_sha256"], "World identity differs")
    before = checkpoint(core.call(f"ADVANCE {pickup[1] - 1}"))
    body = before["ants"][donor]
    require(not any(body["crop_ug"]) and not any(body["carried_ug"]), "Donor did not start empty")
    raw = core.call(f"ADVANCE {gift[1]}")
    after = checkpoint(raw)
    inventory = [0, 0, 0, 0]
    cargo = [0, 0, 0, 0]
    events = []
    birth = None
    for f in facts(core, after["cursor"], before["cursor"]):
        kind = KINDS[f.kind]
        if f.actor == callow and kind == "StageChanged" and f.stage == 3:
            birth = [f.id, f.time]
        if not any(f.mass) or not (f.actor == donor or (kind == "NutritionTransferred" and f.payload == donor)):
            continue
        if kind == "FoodCollected":
            require(f.resource == 4 and (f.id == pickup[0] or (not f.mass[0] and not f.mass[2])),
                    "Unexpected source of liquids")
            cargo = [a + b for a, b in zip(cargo, f.mass)]
        elif kind == "CargoIngested":
            require(f.resource == 4, "Unmarked crop credit")
            cargo = [a - b for a, b in zip(cargo, f.mass)]
            inventory = [a + b for a, b in zip(inventory, f.mass)]
        elif kind == "FoodDelivered":
            cargo = [a - b for a, b in zip(cargo, f.mass)]
        elif kind == "NutritionTransferred":
            require(f.id == gift[0] and f.actor == donor and f.payload == callow, "Unexpected gift")
            inventory = [a - b for a, b in zip(inventory, f.mass)]
            require(min(inventory) >= 0, "Unfunded dose")
        else:
            require(kind == "BiologicalObservation", f"Unexpected material path: {kind}")
            continue
        require(min(cargo) >= 0, "Unfunded cargo withdrawal")
        recipient = f.payload if kind == "NutritionTransferred" else None
        events.append(dict(id=f.id, time_ms=f.time, kind=kind, actor=f.actor, recipient=recipient,
                           source=f.resource or None, mass_ug=f.mass))
    require(birth and 0 <= gift[1] - birth[1] < 7 * DAY and events[-1]["id"] == gift[0],
            "The recipient or meal cut differs")
    require(inventory == list(after["ants"][donor]["crop_ug"]) and cargo == list(after["ants"][donor]["carried_ug"])
            and uptake[:2] == gift,
            "Donor inventory or subsequent uptake differs")
    later = checkpoint(core.call(f"ADVANCE {uptake[3]}"))
    pulse, = [f for f in facts(core, later["cursor"], after["cursor"]) if f.id == uptake[2]]
    require(pulse.actor == callow and KINDS[pulse.kind] in ("PhysiologyUpdated", "FoundingBoundaryUptake")
            and pulse.mass[0] == uptake[4] > 0 and core.call("CHECK_LEDGERS") == b"", "Missing native uptake")
    return dict(command=trial["command"], initial_sha256=trial["initial_sha256"], meal_frame_sha256=sha256(raw).hexdigest(),
                before_ms=before["time_ms"], before_cursor=before["cursor"], donor=donor, recipient=callow,
                initial_crop_ug=body["crop_ug"], initial_cargo_ug=body["carried_ug"], recipient_emergence=birth,
                transactions=events, donor_crop_after_ug=inventory, recipient_crop_after_ug=after["ants"][callow]["crop_ug"],
                next_positive_uptake=dict(id=pulse.id, time_ms=pulse.time, kind=KINDS[pulse.kind], mass_ug=pulse.mass))


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, default=core_path())
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    panel = [json.loads(args.receipt.read_text(encoding="utf-8-sig"))] if args.receipt else rows("SOCIAL_CROP_TRIALS.jsonl")
    trial, = [r for r in panel if (r["physics"], r["seed"], r["supply"]) == (54, 3, "nearby")]
    with closing(NativeCore(args.core.resolve(), ROOT / "out")) as core:
        print(json.dumps(trace(core, trial), separators=(",", ":")))


if __name__ == "__main__":
    main()
