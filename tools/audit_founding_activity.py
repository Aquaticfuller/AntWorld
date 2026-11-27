"""Measure actual adult work and silence in matched founding replays."""

import argparse
from collections import Counter, defaultdict
from contextlib import closing
import gzip
from hashlib import sha256
import json
from math import dist
from pathlib import Path
from struct import Struct
from tempfile import TemporaryDirectory

from op0 import DAY
from op0.archive import digest, sqlite_inputs
from op0.codec import (ACTS, CASTES, DEATHS, KINDS, OUTCOMES, PHASES, PROGRAMS, STAGES, Reader,
                       checkpoint, checkpoint_header, decode_fact, require)
from op0.live import ROOT, NativeCore, core_path, founding_balance, live_motion
from tools.compare_m0_worker_rhythm import facts
from tools.measure_first_meal import founding_command
from tools.verify_supply_continuity import (ENERGY_CUTS, EVIDENCE, MODELS, STOP, WATER_CUT, WORLD, WORK_CUT, WORK_WORLD,
                                            fork_cut, history_digest, verify_continuation)


ADULT = STAGES.index("Adult")
DEAD = STAGES.index("Dead")
HANDLING = {"Inspect brood", "Arrange brood", "Clean brood", "Feed brood", "Pick up brood", "Place brood",
            "Close worker contact", "Entrance antennal contact", "Collect food", "Ingest food", "Transfer nutrition",
            "Deliver food", "Excavate", "Handle soil"}
PAYMENTS = {"FoodCollected", "FoodDelivered", "CargoIngested", "NestIngested", "NutritionTransferred",
            "WorkerWaterIngested", "FoundressWaterIngested", "FoundressNestMeal"}
PHYSICAL = {"BroodMoved", "SoilExcavated", "SoilDropped", "SoilPickedUp"}
MINUTE = 60_000
SCHEDULED_EVENT = Struct("<QQIIQQBQBQQ3dQQQB")


def interval_summary(intervals, start, end):
    """Merge overlapping evidence and measure covered activity and its gaps."""
    active, gap = 0, 0
    cursor = start
    for first, last in sorted(intervals):
        if last < start or first > end:
            continue
        first, last = max(start, first), min(end, last)
        gap = max(gap, first - cursor)
        active += max(0, last - max(cursor, first))
        cursor = max(cursor, last)
    return active, max(gap, end - cursor)


def agent(ant, time):
    return dict(start=time, position=ant["position_m"], endpoints=[], distance=0., counts=Counter(),
                reviews=[], movement=[], handling=[], paid=[], points=[], funded=[], uptake=[],
                program=[(time, ant["program"])], work=time if int(ant.get("active_work") or 0) else None, death=None)


def measure(core, start, end_ms):
    start_ms = start["time_ms"]
    adults = {i: agent(a, start_ms) for i, a in start["ants"].items() if a["stage"] == ADULT}
    before = {i: founding_balance(core, start, i) for i in adults}
    access = core.call("MEAL_ACCESS").decode("ascii").splitlines()
    pairs = core.call("ORAL_ACCESS").decode("ascii").splitlines()
    raw = core.call(f"ADVANCE {end_ms}")
    end = checkpoint(raw)
    founder, = [i for i, a in end["ants"].items() if CASTES[a["caste"]] == "Queen"]
    received = []
    for fact in facts(core, end["cursor"], start["cursor"]):
        kind = KINDS[fact.kind]
        if kind == "StageChanged" and fact.stage == ADULT:
            body = dict(end["ants"][fact.actor], program=0, position_m=fact.position, active_work="0")
            adults[fact.actor] = agent(body, fact.time)
        if kind == "NutritionTransferred" and fact.payload == founder and sum(fact.mass):
            received.append((fact.id, fact.time, fact.actor, fact.mass))
        adult = adults.get(fact.actor)
        if adult is None:
            continue
        if kind == "AutonomyDecision":
            adult["reviews"].append(fact.time)
        elif kind == "NutritionDecision":
            adult["counts"]["nutrition_reviews"] += 1
        elif kind == "ForagingDecision":
            adult["counts"]["forage_reviews"] += 1
        elif kind == "AntDied":
            adult["death"] = (fact.id, fact.time, DEATHS[fact.payload])
        elif kind == "BehaviorChanged":
            adult["program"].append((fact.time, fact.payload))
        elif kind == "ActivityChanged":
            if fact.payload:
                adult["work"] = fact.time
            elif adult["work"] is not None:
                adult["paid"].append((adult["work"], fact.time))
                adult["work"] = None
        elif kind == "Moved" and adult["position"] != fact.position:
            adult["distance"] += dist(adult["position"], fact.position)
            adult["counts"]["moves"] += 1
            endpoints = adult["endpoints"]
            if len(endpoints) == 2:
                adult["counts"]["reversals"] += fact.position == endpoints.pop(0)
            endpoints.append(fact.position)
            adult["position"] = fact.position
            duration = fact.aux >> 32
            adult["movement"].append((fact.time-duration, fact.time))
        elif kind in PAYMENTS and sum(fact.mass):
            adult["counts"][kind] += 1
            adult["points"].append((fact.time, fact.time))
            adult["funded"].append((fact.id, fact.time, kind, fact.related, fact.mass))
        elif kind in PHYSICAL:
            adult["counts"][kind] += 1
            adult["points"].append((fact.time, fact.time))
        elif kind in ("PhysiologyUpdated", "FoundingBoundaryUptake") and sum(fact.mass):
            adult["uptake"].append((fact.id, fact.time, fact.mass))
        elif fact.observation:
            phase, action, target, _, began, timed, *_ = fact.observation
            name = ACTS[action]
            if PHASES[phase] == "Completed" and name in HANDLING:
                adult["handling"].append((began if timed else fact.time, fact.time))
                adult["counts"][name] += 1
            elif PHASES[phase] == "Interrupted" and name != "Inactive":
                adult["counts"][f"{name}/interrupted/{OUTCOMES[fact.outcome]}"] += 1

    continuations = live_motion(core.call("WORKER_MOTION"), end)
    rows = {}
    for i, adult in adults.items():
        begin = adult["start"]
        finish = adult["death"][1] if adult["death"] else end_ms
        if adult["work"] is not None:
            adult["paid"].append((adult["work"], finish))
        if i in continuations:
            motion = continuations[i]
            adult["movement"].append((motion["begins_ms"], finish))
        move_ms, move_gap = interval_summary(adult["movement"], begin, finish)
        activity = adult["movement"] + adult["handling"] + adult["points"]
        action_ms, quiet = interval_summary(activity, begin, finish)
        paid_ms, _ = interval_summary(adult["paid"], begin, finish)
        _, work_gap = interval_summary(activity + adult["paid"], begin, finish)
        review_times = [begin, *adult["reviews"], finish]
        programs = Counter()
        for (first, code), (last, _) in zip(adult["program"], [*adult["program"][1:], (finish, 0)]):
            programs[PROGRAMS[code]] += last-first
        rows[i] = dict(caste=CASTES[end["ants"][i]["caste"]], from_ms=begin, through_ms=finish,
                       moves=adult["counts"]["moves"], distance_mm=1000*adult["distance"],
                       active_motion_ms=move_ms, active_documented_ms=action_ms, paid_work_ms=paid_ms,
                       largest_no_motion_ms=move_gap, largest_no_documented_action_ms=quiet,
                       largest_no_documented_action_or_paid_work_ms=work_gap,
                       reviews=len(adult["reviews"]), largest_review_gap_ms=max(b-a for a, b in zip(review_times, review_times[1:])),
                       program_ms=programs, counts=adult["counts"], death=adult["death"],
                       funding=adult["funded"], uptake=adult["uptake"], start_balance=before.get(i),
                       end_balance=founding_balance(core, end, i))
    require(core.call("CHECK_LEDGERS") == b"", "Native resource ledger mismatch")
    return dict(physics=end["physics"], worker_timing=start["flags"]["worker_activity_timing"], seed=end["seed"],
                from_ms=start_ms, through_ms=end_ms, actors=rows, founder_receipts=received,
                start_access=access, start_oral=pairs, first_cursor=start["cursor"], final_cursor=end["cursor"],
                final_sha256=sha256(raw).hexdigest())


def same_cut(core, folder, path, world, reference, version, stop):
    original = gzip.decompress(path.read_bytes())
    cut = fork_cut(core, folder, original, version, reference)
    slot = "a"*32
    saved = folder/(slot+".awstate")
    saved.write_bytes(cut)
    try:
        start = checkpoint(core.call(f"LOAD_SNAPSHOT {slot} {world}"))
        require(start["physics"] == version, "Wrong cutoff physics")
        return dict(case=path.name, input_sha256=sha256(cut).hexdigest(), **measure(core, start, stop))
    finally:
        saved.unlink()


def first_adult(core):
    core.call("FIND_NEXT_MILESTONE worker 0")
    deadline = 95*DAY
    while True:
        hit = core.call(f"ADVANCE_UNTIL {deadline} worker")
        if hit and hit != b"exhausted":
            _, event = decode_fact(hit)
            frame = checkpoint(core.call("FRAME"))
            require(event.time == frame["time_ms"], "The first worker is not at the committed cut")
            return event, frame
        if hit or checkpoint(core.call("FRAME"))["time_ms"] == deadline:
            raise ValueError("No first worker within 95 days")


def found(core, seed, model, minutes, dwell, hours):
    timing = (minutes*MINUTE, dwell*MINUTE) if minutes else None
    command = founding_command(seed, model, "nearby", timing)
    initial = core.call(command)
    event, frame = first_adult(core)
    witness = dict(id=event.id, time_ms=event.time, actor=event.actor, position_m=event.position)
    return dict(case="first adult", supply="nearby", initial_sha256=sha256(initial).hexdigest(), command=command,
                first_adult=witness, **measure(core, frame, event.time+hours*60*MINUTE))


def verify_timing(core):
    model = MODELS[80]
    nominal = core.call(founding_command(1, model, "nearby"))
    require(core.call(founding_command(1, model, "nearby", (15*MINUTE, 60*MINUTE))) == nominal,
            "Explicit nominal timing changed the initial frame")
    try:
        core.call(founding_command(1, model, "nearby", (60*MINUTE, 5*MINUTE)))
    except ValueError:
        require(core.call("FRAME") == nominal, "Rejected timing changed the current world")
    else:
        raise ValueError("Check interval exceeded minimum program time")
    raw = core.call(founding_command(1, model, "nearby", (5*MINUTE, 60*MINUTE)))
    require(checkpoint(raw)["flags"]["worker_activity_timing"] == dict(check_ms=5*MINUTE, minimum_program_ms=60*MINUTE),
            "Explicit timing was not saved")
    event, frame = first_adult(core)
    slot = "c"*32
    core.call(f"SAVE_SNAPSHOT {slot}")
    split = event.time+1  # The newly emerged worker's initial ordinary review.
    stop = event.time+90*MINUTE
    expected = core.call(f"ADVANCE {stop}")
    suffix = verify_continuation(core, slot, frame["world"], split, stop, expected, checkpoint(expected)["cursor"])
    require(core.call("CHECK_LEDGERS") == b"", "Native resource ledger mismatch after restore")
    return dict(initial_sha256=sha256(raw).hexdigest(), timing=checkpoint(raw)["flags"]["worker_activity_timing"],
                split_ms=split, through_ms=stop, final_sha256=sha256(expected).hexdigest(), restored_suffix_sha256=suffix)


def pending_reviews(raw):
    reader = Reader(memoryview(raw)[:-8])
    checkpoint_header(reader)
    reader.take(40)  # Allocator positions, queue sequence and RNG state.
    reviews = {}
    for _ in range(reader.uint()):
        identifier, at, _, _, _, _, _, payload, kind, actor, *_ = reader.unpack(SCHEDULED_EVENT)
        if kind == 15:  # ScheduledEvent::Kind::AutonomyWake
            require(actor not in reviews, "An adult has duplicate review work")
            reviews[actor] = (identifier, at, payload)
    return reviews


def verify_stimulus(core, folder, seed, version):
    if seed == 2:
        path, world, reference, stop = WATER_CUT, WORLD, 73, STOP
    else:
        _, world, stop = ENERGY_CUTS[seed]
        path, reference = EVIDENCE/f"SEED{seed}_ENERGY_SUPPLY_CUT.awstate.gz", 78
    original = gzip.decompress(path.read_bytes())
    slot = "e"*32
    saved = folder/(slot+".awstate")
    saved.write_bytes(fork_cut(core, folder, original, version, reference))
    start = checkpoint(core.call(f"LOAD_SNAPSHOT {slot} {world}"))
    raw = core.call(f"ADVANCE {stop}")
    end = checkpoint(raw)
    physical = defaultdict(list)
    candidates = []
    for event in facts(core, end["cursor"], start["cursor"]):
        kind = KINDS[event.kind]
        if kind in ("Moved", "FoodDelivered", "FoundingBoundaryUptake", "PhysiologyUpdated"):
            physical[event.time].append((event.id, kind, event.actor, event.mass))
        elif kind == "AutonomyDecision":
            relevant = [fact for fact in physical[event.time-1]
                        if fact[2] == event.actor or (fact[1] == "FoodDelivered" and event.actor == 2)]
            if relevant:
                candidates.append((event.time-1, event.actor, event.source, event.id, relevant))
    core.call(f"LOAD_SNAPSHOT {slot} {world}")
    for when, actor, scheduled, decision, precursors in candidates:
        at_event = core.call(f"ADVANCE {when}")
        if pending_reviews(at_event).get(actor) != (scheduled, when+1, 4):
            continue
        continuation = verify_continuation(core, slot, world, when, stop, raw, end["cursor"])
        require(core.call("CHECK_LEDGERS") == b"", "Native resource ledger mismatch after the local wake")
        saved.unlink()
        saved.write_bytes(fork_cut(core, folder, original, 80, reference))
        core.call(f"LOAD_SNAPSHOT {slot} {world}")
        control = pending_reviews(core.call(f"ADVANCE {when}")).get(actor)
        require(control is not None and control[1] > when+1, "The matched control has no later pending review")
        return dict(seed=seed, physics=version, action_ms=when, actor=actor, trigger_facts=precursors,
                    review_id=decision, review_scheduled_id=scheduled, review_ms=when+1,
                    control_review=control, saved_wait_ms=control[1]-when-1,
                    final_sha256=sha256(raw).hexdigest(), restored_suffix_sha256=continuation)
    raise ValueError("No saved local stimulus followed by an actual review in the selected cut")


def verify_final_leg(core, folder):
    original = gzip.decompress(WATER_CUT.read_bytes())
    slot = "c"*32
    saved = folder/(slot+".awstate")
    saved.write_bytes(fork_cut(core, folder, original, 84))
    start = checkpoint(core.call(f"LOAD_SNAPSHOT {slot} {WORLD}"))
    when = 5_019_637_108
    cut = checkpoint(core.call(f"ADVANCE {when}"))
    chosen, = [event for event in facts(core, cut["cursor"], start["cursor"])
               if event.id == 264476 and event.time == when and event.actor == 8 and event.related == 2
               and event.observation and PHASES[event.observation[0]] == "Selected"
               and ACTS[event.observation[1]] == "Approach a nestmate"]
    saved.unlink()
    core.call(f"SAVE_SNAPSHOT {slot}")
    control = saved.read_bytes()
    cases = []
    for version in (84, 86):
        saved.write_bytes(fork_cut(core, folder, control, version, reference=84))
        core.call(f"LOAD_SNAPSHOT {slot} {WORLD}")
        first = checkpoint(core.call(f"ADVANCE {when+1}"))
        stop = when+2000
        raw = core.call(f"ADVANCE {stop}")
        final = checkpoint(raw)
        events = list(facts(core, final["cursor"], cut["cursor"]))
        approach = [(e.id, e.time, PHASES[e.observation[0]], OUTCOMES[e.outcome]) for e in events
                    if e.actor == 8 and e.observation and e.observation[3] == chosen.observation[3]]
        if version == 84:
            require([e[2:] for e in approach] == [("Interrupted", "Out of reach")], "Reference rejection changed")
        else:
            require([e[2:] for e in approach] == [("Started", "Success"), ("Completed", "Success")] and
                    final["ants"][8]["position_m"] != cut["ants"][8]["position_m"], "Final allowed approach leg did not complete")
        continuation = (verify_continuation(core, slot, WORLD, first["time_ms"], stop, raw, final["cursor"])
                        if version == 86 else None)
        require(core.call("CHECK_LEDGERS") == b"", "Final leg changed the resource ledgers")
        cases.append(dict(physics=version, approach=approach, position_m=final["ants"][8]["position_m"],
                          restored_suffix_sha256=continuation, final_sha256=sha256(raw).hexdigest()))
    return dict(seed=2, selected_event=chosen.id, bout=chosen.observation[3], at_ms=when,
                input_sha256=sha256(control).hexdigest(), cases=cases)


def verify_archive(core, folder, version):
    core.call(founding_command(1, MODELS[version], "nearby"))
    birth, _ = first_adult(core)
    cut_ms = birth.time+6*60*MINUTE
    raw = core.call(f"ADVANCE {cut_ms}")
    frame = checkpoint(raw)
    expected = history_digest(core, 0, frame["cursor"])
    slot = "f"*32
    core.call(f"SAVE {slot}")
    path = folder/(slot+".sqlite")
    for first, tip, _, records, _ in sqlite_inputs(path):
        require(first["world"] == frame["world"] and tip["cursor"] == frame["cursor"] and
                tip["physics"] == version and digest(records) == expected, "Independent archive read disagrees with canonical history")
    stop = cut_ms+30*MINUTE
    continued = core.call(f"ADVANCE {stop}")
    cursor = checkpoint(continued)["cursor"]
    require(cursor > frame["cursor"], "The archive continuation did not exercise any work")
    continued_history = history_digest(core, frame["cursor"], cursor)
    require(core.call(f"LOAD {slot} {frame['world']}") == raw, "Full checkpoint changed on load")
    require(core.call(f"ADVANCE {stop}") == continued and
            history_digest(core, frame["cursor"], cursor) == continued_history,
            "Published archive changed the continuation")
    require(core.call("CHECK_LEDGERS") == b"", "Native resource ledger mismatch after archive restore")
    return dict(physics=version, archive_bytes=path.stat().st_size, cursor=frame["cursor"], history_sha256=expected,
                continuation_facts=cursor-frame["cursor"],
                frame_sha256=sha256(raw).hexdigest(), continued_sha256=sha256(continued).hexdigest(),
                restored_suffix_sha256=continued_history)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, default=core_path())
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--seed", type=int, help="Start from birth rather than use the archived cuts")
    mode.add_argument("--verify-timing", action="store_true", help="Verify opt-in timing and exact continuation")
    mode.add_argument("--stimulus", action="store_true", help="Compare local event wakeups to physics 80")
    mode.add_argument("--verify-stimulus", type=int, choices=(2, 3), help="Verify one saved local stimulus and continuation")
    mode.add_argument("--verify-archive", action="store_true", help="Check full SQLite history and bytewise continuation")
    mode.add_argument("--verify-final-leg", action="store_true", help="Recheck the selected adult approach at its last allowed leg")
    parser.add_argument("--stimulus-version", type=int, choices=(82, 83, 84, 85, 86, 87, 88, 89, 90, 92, 93, 94, 95), default=90)
    parser.add_argument("--model", choices=("protected", *MODELS.values()), default=MODELS[80])
    parser.add_argument("--minutes", type=int, choices=(5, 15))
    parser.add_argument("--dwell-minutes", type=int, choices=(15, 60), default=60)
    parser.add_argument("--hours", type=int, choices=(6, 24, 48), default=24)
    args = parser.parse_args()
    scratch = ROOT/"out"
    scratch.mkdir(exist_ok=True)
    with TemporaryDirectory(dir=scratch, prefix="founding-activity-") as temp, closing(NativeCore(args.core.resolve(), temp)) as core:
        if args.verify_timing:
            print(json.dumps(verify_timing(core), separators=(",", ":")))
            return
        if args.verify_stimulus:
            print(json.dumps(verify_stimulus(core, Path(temp), args.verify_stimulus, args.stimulus_version), separators=(",", ":")))
            return
        if args.verify_archive:
            print(json.dumps(verify_archive(core, Path(temp), args.stimulus_version), separators=(",", ":")))
            return
        if args.verify_final_leg:
            print(json.dumps(verify_final_leg(core, Path(temp)), separators=(",", ":")))
            return
        if args.seed is not None:
            print(json.dumps(found(core, args.seed, args.model, args.minutes, args.dwell_minutes, args.hours),
                             separators=(",", ":")))
            return
        folder = Path(temp)
        cases = [(WATER_CUT, WORLD, 73, (73, 80), STOP)]
        for seed, (_, world, stop) in ENERGY_CUTS.items():
            versions = (78, 80, 81) if seed == 17 else (78, 80)
            cases.append((EVIDENCE/f"SEED{seed}_ENERGY_SUPPLY_CUT.awstate.gz", world, 78, versions, stop))
        cases.append((WORK_CUT, WORK_WORLD, 78, (78, 79, 80), 4_723_650_953+DAY))
        for path, world, reference, versions, stop in cases:
            if args.stimulus:
                versions = (80, args.stimulus_version)
            for version in versions:
                print(json.dumps(same_cut(core, folder, path, world, reference, version, stop), separators=(",", ":")), flush=True)


if __name__ == "__main__":
    main()
