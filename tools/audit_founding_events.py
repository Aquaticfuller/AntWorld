"""Trace physiology thresholds and local wake ownership in compact founding controls."""

import argparse
from contextlib import closing
import gzip
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from op0 import DAY
from op0.codec import KINDS, Reader, checkpoint, checkpoint_header, decode_fact, require
from op0.live import ROOT, NativeCore, core_path
from tools.audit_founding_activity import SCHEDULED_EVENT, pending_reviews
from tools.compare_m0_worker_rhythm import facts
from tools.measure_first_meal import founding_command
from tools.verify_supply_continuity import ENERGY_CUTS, EVIDENCE, MODELS, fork_cut, verify_continuation


def queue(raw):
    reader = Reader(memoryview(raw)[:-8])
    checkpoint_header(reader)
    reader.take(40)
    for _ in range(reader.uint()):
        identifier, at, _, _, _, _, _, payload, kind, actor, _, _, _, _, _, issued_at, *_ = reader.unpack(SCHEDULED_EVENT)
        yield at, identifier, actor, payload, kind, issued_at


def consume_review(core, before, actor, reason, at):
    """Follow the actual pending handle to its committed decision."""
    owned = pending_reviews(before).get(actor)
    if not owned or owned[1:] != (at+1, reason):
        return None
    start = checkpoint(before)["cursor"]
    stop = checkpoint(core.call(f"ADVANCE {at+1}"))["cursor"]
    decision, = [e for e in facts(core, stop, start) if e.actor == actor and e.source == owned[0]
                 and KINDS[e.kind] == "AutonomyDecision"]
    return dict(actor=actor, reason=reason, wake=owned[0], decision=decision.id, decision_ms=decision.time)


def internal_crossings(core, folder, version):
    command = founding_command(2, MODELS[version], "absent")
    raw = core.call(command)
    raw = core.call(f"ADVANCE {40*DAY}")
    answer = {}
    while checkpoint(raw)["time_ms"] < 93*DAY and len(answer) < 2:
        frame = checkpoint(raw)
        scheduled = [row for row in queue(raw) if row[2] == 2 and row[4] == 8]
        if not scheduled:
            break
        at, pending, actor, inputs, *_ = scheduled[0]
        reason = 6 if inputs & 2 else 5 if inputs & 1 else 0
        if not reason or reason in answer:
            raw = core.call(f"ADVANCE {at}")
            continue
        slot = "1"*32
        path = folder/(slot+".awstate")
        core.call(f"SAVE_SNAPSHOT {slot}")
        before = core.call(f"ADVANCE {at}")
        receipt = consume_review(core, before, actor, reason, at)
        if receipt:
            end = core.call("FRAME")
            require(core.call(f"LOAD_SNAPSHOT {slot} {frame['world']}") == raw, "Need forecast changed during restoration")
            require(core.call(f"ADVANCE {at+1}") == end, "Need event changed during restoration")
            answer[reason] = dict(physiology_event=pending, inputs=inputs, threshold_ms=at, **receipt)
        path.unlink()
        raw = core.call("FRAME")
    require(core.call("CHECK_LEDGERS") == b"", "Need forecast changed the resource ledger")
    return dict(command=command, crossings=answer)


def hatch_signal(core, version):
    command = founding_command(1, MODELS[version], "nearby")
    core.call(command)
    cursor = 0
    through = 49*DAY
    for _ in range(24):
        core.call(f"FIND_NEXT_MILESTONE hatch {cursor}")
        reply = core.call(f"ADVANCE_UNTIL {through} hatch")
        if not reply:
            continue
        if reply == b"exhausted":
            break
        _, hatch = decode_fact(reply)
        raw = core.call("FRAME")
        receipt = consume_review(core, raw, 2, 7, hatch.time)
        if receipt:
            return dict(hatch=hatch.id, larva=hatch.actor, threshold_ms=hatch.time, **receipt)
        cursor = hatch.id
    return None


def observed_contact(core, folder, version):
    path = EVIDENCE/"SEED3_ENERGY_SUPPLY_CUT.awstate.gz"
    expected, world, stop = ENERGY_CUTS[3]
    source = gzip.decompress(path.read_bytes())
    require(sha256(source).hexdigest() == expected, "Wrong cut for the contact witness")
    slot = "2"*32
    (folder/(slot+".awstate")).write_bytes(fork_cut(core, folder, source, version, reference=78))
    start = checkpoint(core.call(f"LOAD_SNAPSHOT {slot} {world}"))
    final = core.call(f"ADVANCE {stop}")
    through = checkpoint(final)["cursor"]
    movements, candidates, meals = {}, [], []
    for event in facts(core, through, start["cursor"]):
        kind = KINDS[event.kind]
        if kind == "Moved":
            movements[event.time] = event
        elif kind == "AutonomyDecision" and event.time-1 in movements:
            candidates.append((event, movements[event.time-1]))
        elif kind == "NutritionTransferred" and event.payload == 2 and sum(event.mass):
            meals.append([event.id, event.time, event.actor, event.mass])
    core.call(f"LOAD_SNAPSHOT {slot} {world}")
    for decision, movement in candidates:
        cut = core.call(f"ADVANCE {movement.time}")
        if pending_reviews(cut).get(decision.actor) != (decision.source, decision.time, 8):
            continue
        suffix = verify_continuation(core, slot, world, movement.time, stop, final, through)
        result = dict(move=movement.id, mover=movement.actor, at_ms=movement.time, motivated_actor=decision.actor,
                      wake=decision.source, decision=decision.id, founder_receipts=meals, restored_suffix_sha256=suffix)
        return result | {"continued_meal": continued_meal(core, slot, world, meals)}
    require(core.call("CHECK_LEDGERS") == b"", "Contact replay changed the resource ledger")
    return dict(contact_wake=None, founder_receipts=meals)


def continued_meal(core, slot, world, meals):
    for fact, at, donor, amount in meals:
        core.call(f"LOAD_SNAPSHOT {slot} {world}")
        after = core.call(f"ADVANCE {at}")
        pending = [e for e in queue(after) if e[2:5] == (donor, 2, 12) and e[5] == at]
        if not pending:
            continue
        time, handle, *_ = pending[0]
        cursor = checkpoint(after)["cursor"]
        final = core.call(f"ADVANCE {time}")
        stop = checkpoint(final)["cursor"]
        for event in facts(core, stop, cursor):
            if event.source == handle and event.actor == donor and event.payload == 2 and KINDS[event.kind] == "NutritionTransferred":
                return dict(first=[fact, at, amount], next=[event.id, event.time, event.mass], donor=donor,
                            handling_ms=time-at, pending=handle,
                            restored_suffix_sha256=verify_continuation(core, slot, world, at, time, final, stop, restart_slot="e"*32))
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, default=core_path())
    parser.add_argument("--physics", type=int, choices=(88, 89, 90, 91), default=90)
    parser.add_argument("--verify", action="store_true", help="Require all registered witnesses")
    args = parser.parse_args()
    (ROOT/"out").mkdir(exist_ok=True)
    with TemporaryDirectory(dir=ROOT/"out", prefix="founding-inputs-") as scratch, closing(NativeCore(args.core.resolve(), scratch)) as core:
        folder = Path(scratch)
        internal = internal_crossings(core, folder, args.physics)
        result = dict(physics=args.physics, internal=internal, brood=hatch_signal(core, args.physics),
                      contact=observed_contact(core, folder, args.physics))
        if args.verify:
            require(set(internal["crossings"]) == {5, 6} and result["brood"] and result["contact"].get("move"),
                    "Missing registered hunger, thirst, brood or mouth-contact witness")
            if args.physics >= 90:
                require(result["contact"].get("continued_meal"), "No paid continuation in the contact witness")
        print(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
