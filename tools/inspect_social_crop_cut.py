"""Read the native mouths and food stocks for one world and time from a paired receipt."""

from argparse import ArgumentParser
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
from math import dist
from pathlib import Path

from op0 import DAY
from op0.codec import ACTS, CASTES, KINDS, OUTCOMES, PHASES, PROGRAMS, checkpoint, require
from op0.live import NativeCore, ROOT, core_path, live_bodies
from tools.compare_m0_worker_rhythm import facts
from tools.measure_social_crop import observed_adults
from tools.measure_single_nest_lifecycle import CHUNK_DAYS, COMPACT_BYTES
from tools.verify_protected_habitat import rows


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--physics", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--day", type=int, required=True)
    parser.add_argument("--supply", default="nearby", choices=("nearby", "absent"))
    parser.add_argument("--core", type=Path, default=core_path())
    parser.add_argument("--receipt", type=Path, help="Use a single streamed receipt instead of the published panel")
    parser.add_argument("--until-queen-death", action="store_true", help="Follow actual attempts after the selected cut")
    parser.add_argument("--counts-only", action="store_true", help="Skip the additional replay of individual approach poses")
    parser.add_argument("--follow-worker", type=int, help="Add a focal worker's real actions and daily commitments")
    args = parser.parse_args()
    if not 0 <= args.day <= 730:
        parser.error("Day must be between 0 and 730")
    panel = [json.loads(args.receipt.read_text(encoding="utf-8-sig"))] if args.receipt else rows("SOCIAL_CROP_TRIALS.jsonl")
    receipt, = [r for r in panel
                if (r["physics"], r["seed"], r["supply"]) == (args.physics, args.seed, args.supply)]
    with closing(NativeCore(args.core.resolve(), ROOT / "out")) as core:
        raw = core.call(receipt["command"])
        require(sha256(raw).hexdigest() == receipt["initial_sha256"], "World inputs differ from the trial")
        for cut in range(CHUNK_DAYS, args.day, CHUNK_DAYS):
            core.call(f"ADVANCE_STEP {cut * DAY}")
            if int(core.call("HISTORY_STORAGE").split()[2]) >= COMPACT_BYTES:
                core.call("COMPACT_HISTORY")
        if args.day:
            raw = core.call(f"ADVANCE {args.day * DAY}")
        frame = checkpoint(raw)
        colony, = frame["colonies"].values()
        cut = dict(command=receipt["command"], day=args.day, cursor=frame["cursor"], sha256=sha256(raw).hexdigest(),
                   adults=observed_adults(core, frame), depot_ug=colony["stock_ug"],
                   external_sources=frame["sources"])
        require(core.call("CHECK_LEDGERS") == b"", "Native resource ledger failed")
        if args.day == 730:
            require(cut["sha256"] == receipt["final_sha256"], "Terminal state differs from the trial")
        if args.until_queen_death:
            queen, = [i for i, ant in frame["ants"].items() if CASTES[ant["caste"]] == "Queen"]
            end = receipt["queen_death"]["time_ms"]
            require(frame["time_ms"] < end, "Start the window before the recorded death")
            cursor = frame["cursor"]
            queen_position = frame["ants"][queen]["position_m"]
            attempts, starts = [], {}
            acts, queen_acts, failures, last_doses = Counter(), Counter(), Counter(), {}
            samples, other_meals = [], {}
            focal_cuts, focal_facts, focal_actions, focal_rejections = [], Counter(), Counter(), Counter()
            for time in [*range(frame["time_ms"] + DAY, end, DAY), end]:
                raw = core.call(f"ADVANCE {time}")
                frame = checkpoint(raw)
                focal = frame["ants"].get(args.follow_worker)
                if focal is not None:
                    focal_cuts.append({"time_ms": time, "program": PROGRAMS[focal["program"]],
                                       "position_revision": focal["position_revision"], "energy_nj": focal["energy_nj"],
                                       "body_water_ug": focal["hydration_ug"], "crop_ug": focal["crop_ug"],
                                       "cargo_ug": focal["carried_ug"], "active_work": focal["active_work"],
                                       "carrying_soil": str(args.follow_worker) in frame["soil_carriers"]})
                if args.counts_only and queen in frame["ants"] and time < end:
                    bodies = observed_adults(core, frame)
                    founder = bodies[queen]
                    samples.append({"time_ms": time, "queen_mouth_m": founder["mouth_m"],
                                    "worker_mouths": {i: [round(dist(body["mouth_m"], founder["mouth_m"]) * 1000, 4),
                                                          body["crop_ug"][0]] for i, body in bodies.items()
                                                      if int(i) != queen}})
                for f in facts(core, frame["cursor"], cursor):
                    if f.actor == args.follow_worker:
                        focal_facts[KINDS[f.kind]] += 1
                        if KINDS[f.kind] == "ActionRejected":
                            focal_rejections[f"{f.payload}/{OUTCOMES[f.outcome]}"] += 1
                    if f.observation:
                        phase, action, target, bout, *_ = f.observation
                        key = "/".join((PHASES[phase], ACTS[action]))
                        if f.actor == queen:
                            queen_acts[key] += 1
                        if f.actor == args.follow_worker:
                            focal_actions[key] += 1
                        if target == queen:
                            acts[f"{f.actor}/{key}"] += 1
                            if ACTS[action] == "Approach a nestmate":
                                if PHASES[phase] == "Started":
                                    starts[bout] = (f.time, queen_position)
                                elif PHASES[phase] == "Completed" and bout in starts:
                                    began, previous = starts.pop(bout)
                                    attempts.append(dict(event=f.id, donor=f.actor, time_ms=f.time, duration_ms=f.time - began,
                                                         queen_displacement_m=dist(previous, queen_position)))
                    if KINDS[f.kind] == "Moved" and f.actor == queen:
                        queen_position = f.position
                    if KINDS[f.kind] == "ActionRejected" and f.payload == queen:
                        failures[f"{f.actor}/{OUTCOMES[f.outcome]}"] += 1
                    if KINDS[f.kind] == "NutritionTransferred" and f.payload == queen:
                        last_doses[f.actor] = [f.id, f.time, f.mass]
                    elif args.counts_only and KINDS[f.kind] == "NutritionTransferred":
                        key = f"{f.actor}/{f.payload}"
                        entry = other_meals.setdefault(key, {"events": 0, "mass_ug": [0, 0, 0, 0]})
                        entry["events"] += 1
                        for i, amount in enumerate(f.mass):
                            entry["mass_ug"][i] += amount
                cursor = frame["cursor"]
                if int(core.call("HISTORY_STORAGE").split()[2]) >= COMPACT_BYTES:
                    core.call("COMPACT_HISTORY")
            cut.update(queen_actions=queen_acts, actions_targeting_queen=acts, rejected_actions_with_queen_payload=failures,
                       last_doses=last_doses, death_time_ms=end, death_sha256=sha256(raw).hexdigest(),
                       adults_at_death=observed_adults(core, frame))
            if args.counts_only:
                cut.update(daily_worker_gap_mm_and_crop_sugar_ug=samples, other_transfers=other_meals)
            if args.follow_worker is not None:
                require(focal_cuts, "No focal worker observed in the death window")
                cut.update(focal_worker=args.follow_worker, focal_daily=focal_cuts,
                           focal_fact_counts=focal_facts, focal_actions=focal_actions,
                           focal_rejections_by_payload=focal_rejections)
            require(core.call("CHECK_LEDGERS") == b"", "Invalid death-cut resource ledger")
            if attempts and not args.counts_only:
                core.call(receipt["command"])
                previous_cut = 0
                for attempt in attempts:
                    for when in range(previous_cut + CHUNK_DAYS * DAY, attempt["time_ms"], CHUNK_DAYS * DAY):
                        core.call(f"ADVANCE_STEP {when}")
                        if int(core.call("HISTORY_STORAGE").split()[2]) >= COMPACT_BYTES:
                            core.call("COMPACT_HISTORY")
                    previous_cut = attempt["time_ms"]
                    native = checkpoint(core.call(f"ADVANCE {previous_cut}"))
                    bodies = live_bodies(core.call("BODY_STATES"), native)
                    donor = bodies[str(attempt["donor"])]
                    receiver = bodies[str(queen)]
                    a, b = donor["mouth_m"], receiver["mouth_m"]
                    direction = [v - u for u, v in zip(a, b)]
                    attempt.update(cursor=native["cursor"], mouth_gap_m=dist(a, b),
                                   donor_forward_m=sum(u * v for u, v in zip(direction, donor["forward"])),
                                   receiver_forward_m=-sum(u * v for u, v in zip(direction, receiver["forward"])),
                                   donor_crop_ug=native["ants"][attempt["donor"]]["crop_ug"])
                cut["completed_approach_cuts"] = attempts
    print(json.dumps(cut, separators=(",", ":")))


if __name__ == "__main__":
    main()
