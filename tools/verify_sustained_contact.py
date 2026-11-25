"""Replay the six-hour seed-2 intervention on a disposable, content-addressed cut."""

import argparse
from contextlib import closing
import gzip
from hashlib import sha256
import json
from math import dist
from pathlib import Path
from tempfile import TemporaryDirectory

from op0 import DAY
from op0.codec import ACTS, KINDS, PHASES, checkpoint, require
from op0.live import NativeCore, ROOT, core_path, live_bodies
from tools.compare_m0_worker_rhythm import facts
from tools.summarize_first_meals import outcome
from tools.verify_first_meal import verify_inputs


EVIDENCE = ROOT / "research/single_nest"
WORLD = "00000000-0000-028d-0000-00d30000264a"
START = 7_845_622_429
END = 7_867_222_430
CUT_HASH = "23bae7f931aa605e0b81b215d3757c876b9c481f0fa1b2fa2b9699ce497418dc"
LAST_ALIVE_HASH = "dfade043e7169f4f43b6ce5386c6a09fb0be6db201f33af961c8cf31b1b37b2d"
CHAMBER_HASH = "a14db6174a95874736cf46b8daab1cc0f6a3d3305561f1febf84bad81ccbcc28"
DOCK_HASH = "7580f25bd7bb0b02cb42ba613915f4fe3d8ee3c5f343244face09822aba1c930"


def fnv64(data):
    value = 14695981039346656037
    for byte in data:
        value = ((value ^ byte) * 1099511628211) & ((1 << 64) - 1)
    return value.to_bytes(8, "little")


def experimental_fork(core, folder, original, version=63, target=None):
    """Change only three declared config bytes in a pinned research fixture."""
    require(sha256(original).hexdigest() == {63:CUT_HASH, 64:DOCK_HASH, 66:CHAMBER_HASH}[version], "Unexpected research fixture")
    command = next(row["command"] for line in (EVIDENCE / "WORKED_EXIT_TRIALS.jsonl").read_text().splitlines()
                   if (row := json.loads(line))["physics"] == 63 and row["seed"] == 2 and row["supply"] == "nearby")
    initial = []
    slot = "a" * 32
    target = version + 1 if target is None else target
    models = {63:"worked-exit", 64:"sustained-contact", 65:"yielding-return", 66:"chamber-handoff", 67:"body-orientation"}
    for model in (models[version], models[target]):
        core.call(command.replace("worked-exit", model))
        core.call(f"SAVE_SNAPSHOT {slot}")
        file = folder / (slot + ".awstate")
        initial.append(file.read_bytes()[:-8])
        file.unlink()
    old, candidate = initial
    changes = [(i, a, b) for i, (a, b) in enumerate(zip(old, candidate, strict=True)) if a != b]
    require([(a,b) for _,a,b in changes] == [(version-7,target-7), (version,target), (version-44,target-44)],
            "Unexpected layout difference")
    modified = bytearray(original)
    for offset, before, after in changes:
        if before == version-44:
            config_suffix = old[offset-48:offset+1]
            require(modified.count(config_suffix) == 1, "Ambiguous immutable configuration")
            offset = modified.index(config_suffix) + 48
        require(modified[offset] == before, "Unexpected source field")
        modified[offset] = after
    modified[-8:] = fnv64(modified[:-8])
    return modified


def replay(core, folder, raw, physics):
    slot = str(physics) * 16
    (folder / (slot + ".awstate")).write_bytes(raw)
    def load():
        return checkpoint(core.call(f"LOAD_SNAPSHOT {slot} {WORLD}"))
    start = load()
    require(start["physics"] == physics and start["time_ms"] == START, "Wrong starting conditions")
    before_death = core.call(f"ADVANCE {END-1}")
    if physics == 63:
        require(sha256(before_death).hexdigest() == LAST_ALIVE_HASH, "Original history diverged")
    last_raw = core.call(f"ADVANCE {END}")
    end = checkpoint(last_raw)
    stream = list(facts(core, end["cursor"], start["cursor"]))
    payments = [f for f in stream if KINDS[f.kind] == "NutritionTransferred" and f.payload == 2 and f.mass[0]]
    deaths = [f.id for f in stream if KINDS[f.kind] == "AntDied" and f.actor == 2]
    if physics == 63:
        require(deaths == [469357] and not payments, "Old failure changed")
    else:
        require(not deaths and any(f.actor in (8,9) for f in payments), "Real founder meal missing")
    approaches = [[f.id, f.time, f.actor, f.observation[2], f.outcome, list(f.position)]
                  for f in stream if f.observation and ACTS[f.observation[1]] == "Approach a nestmate"
                  and PHASES[f.observation[0]] == "Completed" and f.actor in (8,9) and f.observation[2] == 2]
    load()
    witnessed = []
    for meal in payments:
        prior = checkpoint(core.call(f"ADVANCE {meal.time-1}"))
        bodies = live_bodies(core.call("BODY_STATES"), prior)
        pair, = [line.split() for line in core.call("ORAL_ACCESS").splitlines() if int(line.split()[0]) == meal.actor]
        require(pair[1:3] == [b"1", b"1"], "Missing visible contact before payment")
        after = checkpoint(core.call(f"ADVANCE {meal.time}"))
        def crop_change(actor):
            return [b-a for a,b in zip(prior["ants"][actor]["crop_ug"], after["ants"][actor]["crop_ug"], strict=True)]
        require(crop_change(2) == list(meal.mass) == [-v for v in crop_change(meal.actor)], "Unequal crop payment")
        gap = 1000 * dist(bodies[str(meal.actor)]["mouth_m"], bodies["2"]["mouth_m"])
        witnessed.append(dict(event=meal.id, time_ms=meal.time, donor=meal.actor, receiver=2,
                              mass_ug=meal.mass, mouth_gap_mm=gap))
    require(core.call(f"ADVANCE {END}") == last_raw and core.call("CHECK_LEDGERS") == b"",
            "Partitioned replay or ledger mismatch")
    uptake = [[f.id,f.time,f.mass[0]] for f in stream if f.actor == 2 and f.mass[0]
              and KINDS[f.kind] in ("PhysiologyUpdated","FoundingBoundaryUptake")]
    return dict(physics=physics, start_cursor=start["cursor"], end_cursor=end["cursor"], deaths=deaths,
                payments=witnessed, founder_uptake=uptake, approaches=approaches, final_sha256=sha256(last_raw).hexdigest())


def verify(binary, scratch):
    original = gzip.decompress((EVIDENCE / "SEED2_SIX_HOUR_CUT.awstate.gz").read_bytes())
    with TemporaryDirectory(dir=scratch) as temp, closing(NativeCore(binary, temp)) as core:
        folder = Path(temp)
        results = [replay(core, folder, original, 63)]
        for version in ((64,66,67) if core.body_orientation else (64,66) if core.chamber_handoff else (64,)):
            branch = experimental_fork(core, folder, original, 63, version)
            results.append(replay(core, folder, branch, version))
        return results


def verify_debits(core, payments):
    for meal in payments:
        prior = checkpoint(core.call(f"ADVANCE {meal.time-1}"))
        pair = next(line.split() for line in core.call("ORAL_ACCESS").splitlines()
                    if int(line.split()[0]) == meal.actor)
        paid = checkpoint(core.call(f"ADVANCE {meal.time}"))
        for i, mass in enumerate(meal.mass):
            require(pair[1:3]==[b"1",b"1"] and
                    prior["ants"][meal.actor]["crop_ug"][i]-paid["ants"][meal.actor]["crop_ug"][i]==mass and
                    paid["ants"][2]["crop_ug"][i]-prior["ants"][2]["crop_ug"][i]==mass,
                    "Chamber payment was not an equal debit and credit at contact")


def verify_entrance(binary, scratch):
    original = gzip.decompress((EVIDENCE/"SEED2_ENTRANCE_CUT.awstate.gz").read_bytes())
    world = "00000000-0000-028d-0000-00d70000264a"
    end_ms = 7_082_242_171
    with TemporaryDirectory(dir=scratch) as temp, closing(NativeCore(binary, temp)) as core:
        folder = Path(temp)
        results = []
        versions = (64,65,66,67) if core.body_orientation else (64,65,66) if core.chamber_handoff else (64,65)
        for version in versions:
            cut = original if version==64 else experimental_fork(core, folder, original, 64, version)
            slot = str(version)*16
            (folder/(slot+".awstate")).write_bytes(cut)
            before = checkpoint(core.call(f"LOAD_SNAPSHOT {slot} {world}"))
            require(before["physics"] == version and before["time_ms"] == end_ms-6*3_600_000-1, "Wrong entrance cut")
            after = core.call(f"ADVANCE {end_ms}")
            stream = list(facts(core, checkpoint(after)["cursor"], before["cursor"]))
            moves = [f for f in stream if KINDS[f.kind]=="Moved" and f.actor in (8,9)]
            deliveries = [f for f in stream if KINDS[f.kind]=="FoodDelivered" and f.actor==8]
            payments = [f for f in stream if KINDS[f.kind]=="NutritionTransferred" and f.payload==2 and f.mass[0]]
            deaths = [f for f in stream if KINDS[f.kind]=="AntDied" and f.actor==2]
            if version == 64:
                require(not moves and not payments and [f.id for f in deaths]==[512193], "Reference jam changed")
            else:
                require({f.actor for f in moves} == {8,9} and deliveries and moves[0].actor==9
                        and moves[0].position[1]<before["ants"][9]["position_m"][1], "Carrier jam persisted")
                core.call(f"LOAD_SNAPSHOT {slot} {world}")
                prior = core.call(f"ADVANCE {moves[0].time-1}")
                pending_slot = "f"*32
                core.call(f"SAVE_SNAPSHOT {pending_slot}")
                require(core.call(f"LOAD_SNAPSHOT {pending_slot} {world}") == prior and
                        core.call(f"ADVANCE {end_ms}") == after, "Pending return diverged after restore")
                (folder/(pending_slot+".awstate")).unlink()
                if version == 65:
                    require(not payments and deaths, "Yield-only negative outcome changed")
                else:
                    require({f.actor for f in payments} >= {8,9} and not deaths, "Missing chamber payments")
                    core.call(f"LOAD_SNAPSHOT {slot} {world}")
                    verify_debits(core, payments)
                    require(core.call(f"ADVANCE {end_ms}")==after, "Payment replay changed final state")
            require(core.call("CHECK_LEDGERS")==b"", "Ledger failure at entrance")
            results.append(dict(physics=version, starting_loads={i:before["ants"][i]["carried_ug"] for i in (8,9)},
                                starting_crops={i:before["ants"][i]["crop_ug"] for i in (8,9)},
                                moves={i:sum(f.actor==i for f in moves) for i in (8,9)},
                                first_move=[moves[0].id,moves[0].time,moves[0].actor,moves[0].position] if moves else None,
                                deliveries=[[f.id,f.time,f.actor,f.mass] for f in deliveries],
                                payments=[[f.id,f.time,f.actor,f.mass] for f in payments],
                                paid_sugar_ug=sum(f.mass[0] for f in payments), founder_death=[[f.id,f.time] for f in deaths],
                                final_sha256=sha256(after).hexdigest()))
        return results


def verify_orientation(binary, scratch):
    cut = gzip.decompress((EVIDENCE/"SEED2_CHAMBER_CUT.awstate.gz").read_bytes())
    end_ms = 7_611_862_301
    world = "00000000-0000-028d-0000-00df0000264a"
    results = []
    with TemporaryDirectory(dir=scratch) as temp, closing(NativeCore(binary, temp)) as core:
        folder = Path(temp)
        for version in (66,67):
            slot = str(version)*16
            (folder/(slot+".awstate")).write_bytes(cut if version==66 else experimental_fork(core,folder,cut,66,67))
            def reload():
                return checkpoint(core.call(f"LOAD_SNAPSHOT {slot} {world}"))
            before = reload()
            require(before["time_ms"] == end_ms-6*3_600_000-1, "Wrong chamber cut")
            final = core.call(f"ADVANCE {end_ms}")
            fs = list(facts(core,checkpoint(final)["cursor"],before["cursor"]))
            meals = [f for f in fs if KINDS[f.kind]=="NutritionTransferred" and f.payload==2 and f.mass[0]]
            deaths = [f.id for f in fs if KINDS[f.kind]=="AntDied" and f.actor==2]
            if version==66:
                require(deaths==[660563] and not meals, "Reference chamber failure changed")
            else:
                require(not deaths and meals, "Orientation failed to supply the founder")
                reload()
                verify_debits(core,meals)
                require(core.call(f"ADVANCE {end_ms}")==final, "Orientation replay changed the final state")
            require(core.call("CHECK_LEDGERS")==b"", "Orientation ledger failure")
            results.append(dict(physics=version, start_ms=before["time_ms"], end_ms=end_ms, deaths=deaths,
                                payments=[[f.id,f.time,f.actor,list(f.mass)] for f in meals],
                                final_sha256=sha256(final).hexdigest()))
    return results


def feeding_summary(row):
    summary = outcome(row)
    days = sorted((int(day), b) for day, b in row["founder_feeding_by_day"].items())
    stop = row["queen_death"][1] if "queen_death" in row else 730 * DAY
    total = sum(b["sugar_ug"] for _, b in days)
    require(total == summary["sugar_gifts_ug"].get("Queen", 0), "Founder/donor daily ledger mismatch")
    gaps = []
    for i, (day, b) in enumerate(days):
        require(day == b["first_ms"] // DAY == b["last_ms"] // DAY and b["last_ms"] <= stop
                and b["count"] > 0 and b["sugar_ug"] > 0, "Invalid daily founder meal")
        gaps.append(b["max_internal_gap_ms"])
        if i:
            gaps.append(b["first_ms"] - days[i-1][1]["last_ms"])
    return dict(physics=row["physics"], seed=row["seed"], supply=row["supply"],
                sugar_ug=total, paid_days=len(days), payments=sum(b["count"] for _, b in days),
                first_meal_day=days[0][1]["first_ms"]/DAY if days else None,
                last_meal_day=days[-1][1]["last_ms"]/DAY if days else None,
                longest_intermeal_hours=max(gaps)/3_600_000 if gaps else None,
                terminal_gap_hours=(stop-days[-1][1]["last_ms"])/3_600_000 if days else None,
                death_day=summary["founder_death_day"], workers=summary["workers"],
                later_emerged_alive=summary["later_emerged_alive"],
                year_two=sum("Adult" in ant and ant["Adult"][1]>365*DAY for ant in row["lives"].values()))


def verify_panel(binary, path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        rows = [json.loads(line) for line in f]
    expected = {(s,"nearby") for s in (1,2,3,17,29)} | {(2,"absent")}
    old = {}
    for line in (EVIDENCE/"WORKED_EXIT_TRIALS.jsonl").read_text().splitlines():
        row = json.loads(line)
        if row["physics"] == 63:
            old[row["seed"], row["supply"]] = row
    require(len(rows) == 5*len(expected), "Incomplete panel")
    for version, model in ((63,"worked-exit"), (64,"sustained-contact"), (65,"yielding-return"), (66,"chamber-handoff"), (67,"body-orientation")):
        arm = [row for row in rows if row["physics"] == version]
        require({(r["seed"],r["supply"]) for r in arm} == expected, "Missing paired world")
        for row in arm:
            key = row["seed"],row["supply"]
            command = row["command"].split()
            require(command[:1]+command[2:] == ["NEW_PROVISIONED_NEST",str(row["seed"]),"250","80","plugged",
                    "1955","reachable",row["supply"],"sheltered","mineral",model,"wet-wick"], "Changed conditions")
            require(row["census"][-1]["day"] == 730, "Incomplete follow-up")
            if version == 63:
                require(all(row[k]==v for k,v in old[key].items() if k != "executable_sha256"),
                        "Different historical outcome")
            if row["supply"] == "absent":
                require(not row["founder_feeding_by_day"], "Unfunded founder sugar")
    return dict(inputs=verify_inputs(binary, rows), worlds=[feeding_summary(r) for r in rows])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, default=core_path())
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--panel", type=Path, help="Check all six matched cases across all five versions")
    group.add_argument("--entrance", action="store_true", help="Replay two competing surface carriers")
    group.add_argument("--orientation", action="store_true", help="Replay a meeting with a locally sensed body")
    args = parser.parse_args()
    binary = args.core.resolve()
    result = verify_panel(binary,args.panel) if args.panel else (verify_orientation if args.orientation else verify_entrance if args.entrance else verify)(binary,ROOT/"out")
    print(json.dumps(result, indent=2))
