"""Replay matched supply failures and verify the founding trial panel."""

import argparse
from collections import Counter, defaultdict
from contextlib import closing
import gzip
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from op0 import DAY
from op0.archive import sqlite_inputs
from op0.codec import ACTS, KINDS, OUTCOMES, PHASES, STAGES, checkpoint, require
from op0.live import NativeCore, ROOT, core_path, founding_balance
from tools.compare_m0_worker_rhythm import facts
from tools.verify_first_meal import verify_inputs
from tools.verify_sustained_contact import EVIDENCE, fnv64


MODELS = {
    73: "exit-attachment",
    74: "confirmed-meal-route",
    75: "stationary-body",
    76: "feeding-stance",
    77: "founder-wick",
    78: "repeat-collection",
    79: "work-face-detour",
    80: "familiar-site-detour",
    81: "nursery-arrival",
    82: "local-stimulus",
    83: "stimulus-meal-priority",
    84: "stimulus-refill-intent",
    85: "stimulus-mouth-visibility",
    86: "stimulus-final-leg",
    87: "bounded-meal-route",
    88: "local-needs",
    89: "joint-meal-route",
    90: "continuous-meal",
    91: "floor-meal-stances",
}
WATER_CUT = EVIDENCE / "SEED2_SUPPLY_CONTINUITY_CUT.awstate.gz"
CUT_DIGEST = "305f0f042d97e675abbde25238c7e484d3c2c5c3f8287ac62be13f638b72356c"
WORLD = "00000000-0000-028d-0000-00fb0000264a"
STOP = 5_040_000_000
WORK_CUT = EVIDENCE / "SEED1_FIRST_WORKER_SUPPLY_CUT.awstate.gz"
WORK_DIGEST = "85c1e58c2d22e04e25a6036d703b9628d49baa9e56eb2ff101913fba19b8764b"
WORK_WORLD = "00000000-0000-028d-0000-010f00002649"
WORK_STOP = 5_491_046_651
ENERGY_CUTS = {
    3: ("8646f06da939b60db0c9d6cb078ea9af142fbc02c558797f78e94cb5454d2b11",
        "00000000-0000-028d-0000-010f0000264b", 6_790_256_746),
    17: ("b53684652fa1886ce428a98ba2f5e91dc1fcec6a71a8b7a61fb182536ca2dbe0",
         "00000000-0000-028d-0000-010f00002659", 6_260_648_409),
}


def fork_cut(core, folder, original, version, reference=73):
    """Change only the schema, physics and policy fields of a test fixture."""
    if version == reference:
        return original
    initial = []
    slot = "b" * 32
    path = folder / (slot + ".awstate")
    command = "NEW_PROVISIONED_NEST 1 2 250 80 plugged 1955 reachable nearby sheltered mineral {} wet-wick"
    for model in (MODELS[reference], MODELS[version]):
        core.call(command.format(model))
        core.call(f"SAVE_SNAPSHOT {slot}")
        initial.append(path.read_bytes()[:-8])
        path.unlink()
    old, new = initial
    changes = [(index, a, b) for index, (a, b) in enumerate(zip(old, new, strict=True)) if a != b]
    require([(a, b) for _, a, b in changes] ==
            [(reference-7, version-7), (reference, version), (reference-44, version-44)],
            "Fixture config fields changed unexpectedly")
    modified = bytearray(original)
    for offset, before, after in changes:
        # At a populated cut the preceding histories can shift the policy offset.
        if before == reference-44:
            prefix = old[offset-48:offset+1]
            require(modified.count(prefix) == 1, "Fixture policy is ambiguous")
            offset = modified.index(prefix) + 48
        require(modified[offset] == before, "Fixture model is inconsistent")
        modified[offset] = after
    modified[-8:] = fnv64(modified[:-8])
    return modified


def history_digest(core, after, through):
    digest=sha256()
    for cursor in range(after,through,512):
        digest.update(core.call(f"FACTS_AFTER {cursor} {min(through-cursor,512)}"))
    return digest.hexdigest()


def verify_continuation(core, slot, world, resume, stop, expected, cursor, *, restart_slot="d"*32):
    """Compare a split advance and a saved restart against the uninterrupted cut."""
    core.call(f"LOAD_SNAPSHOT {slot} {world}")
    before=core.call(f"ADVANCE {resume}")
    boundary=checkpoint(before)["cursor"]
    uninterrupted=core.call(f"ADVANCE {stop}")
    require(uninterrupted==expected,"Time partition changed the terminal frame")
    facts=history_digest(core,boundary,cursor)
    core.call(f"LOAD_SNAPSHOT {slot} {world}")
    require(core.call(f"ADVANCE {resume}")==before,"Different mid-action cut on replay")
    core.call(f"SAVE_SNAPSHOT {restart_slot}")
    require(core.call(f"LOAD_SNAPSHOT {restart_slot} {world}")==before,"Mid-action cut changed on load")
    require(core.call(f"ADVANCE {stop}")==expected and history_digest(core,boundary,cursor)==facts,
            "Restart changed the terminal frame or canonical facts")
    return facts


def replay(binary, version, original, verify_restore=False, *, energy_seed=None):
    reference = 73 if energy_seed is None else 78
    digest, world, stop = (CUT_DIGEST,WORLD,STOP) if energy_seed is None else ENERGY_CUTS[energy_seed]
    require(sha256(original).hexdigest() == digest, "Wrong matched terminal input")
    with TemporaryDirectory(dir=ROOT/"out") as temp, closing(NativeCore(binary, temp)) as core:
        folder = Path(temp)
        slot = "c"*32
        cut = fork_cut(core, folder, original, version, reference)
        (folder/(slot+".awstate")).write_bytes(cut)
        start = checkpoint(core.call(f"LOAD_SNAPSHOT {slot} {world}"))
        require(start["physics"] == version and start["time_ms"] == stop-21_600_001, "Wrong analysis boundary")
        end_raw = core.call(f"ADVANCE {stop}")
        end = checkpoint(end_raw)
        moves = defaultdict(list)
        reviews = Counter()
        actions = Counter()
        oral, direct, uptake, deaths = [], [], [], []
        collected = Counter()
        spare = None
        for fact in facts(core, end["cursor"], start["cursor"]):
            kind = KINDS[fact.kind]
            if kind == "Moved":
                moves[fact.actor].append(fact.position)
            elif kind == "AutonomyDecision":
                reviews[fact.actor] += 1
            elif kind == "FoodCollected" and fact.mass[0]:
                collected[fact.actor] += fact.mass[0]
            if fact.observation and (fact.actor == 2 or fact.related == 2):
                phase, act = fact.observation[:2]
                actions[f"{fact.actor}/{fact.related}/{ACTS[act]}/{PHASES[phase]}/{OUTCOMES[fact.outcome]}"] += 1
                if spare is None and PHASES[phase] == "Started":
                    spare = fact.time
            row = [fact.id, fact.time, fact.actor, list(fact.mass)]
            if kind == "NutritionTransferred" and fact.payload == 2:
                oral.append(row)
            if fact.actor == 2:
                if kind in ("FoundressWaterIngested", "FoundressNestMeal"):
                    direct.append(row)
                if kind in ("PhysiologyUpdated", "FoundingBoundaryUptake") and any(fact.mass):
                    uptake.append(row)
                if kind == "AntDied":
                    deaths.append([fact.id, fact.time, fact.payload])
        require(core.call("CHECK_LEDGERS") == b"", "Resource ledger mismatch")
        balances = founding_balance(core, end, 2)
        continuation = None
        if verify_restore and spare is not None:
            continuation=verify_continuation(core,slot,world,spare,stop,end_raw,end["cursor"])
        alive = STAGES[end["ants"][2]["stage"]] == "Adult"
        if version == 73:
            require(not oral and not direct and not uptake and deaths == [[268457, stop, 2]],
                    "Historical dehydration diverged")
        elif energy_seed is not None and version == reference:
            require(len(deaths)==1 and deaths[0][1:]==[stop,1] and not collected, "Historical energy failure diverged")
        if energy_seed is None and version in (76,78):
            require(alive and any(row[3][2] for row in direct) and any(row[3][2] for row in uptake),
                    "Founder failed to drink and absorb water")
        if energy_seed==3 and version==80:
            require(alive and collected[8]>=400 and any(row[3][0] for row in oral) and any(row[3][0] for row in uptake),
                    "Corrected depot visit failed to fund a founder meal")
        return dict(physics=version, cut_sha256=sha256(cut).hexdigest(), final_sha256=sha256(end_raw).hexdigest(),
                    alive=alive, deaths=deaths, final_balance=balances, mouth_receipts=oral, direct=direct, uptake=uptake,
                    collected_sugar_ug=dict(collected),
                    actions=dict(actions), reviews=dict(reviews), facts=end["cursor"]-start["cursor"],
                    movement={i: dict(moves=len(p), sites=len(set(p)),
                                      reversals=sum(p[k] == p[k-2] for k in range(2, len(p))))
                              for i, p in moves.items()}, restored_ms=spare if verify_restore else None,
                    restored_suffix_sha256=continuation)


def replay_first_worker(binary, version, original, verify_restore=False):
    require(sha256(original).hexdigest() == WORK_DIGEST, "Wrong first-worker input")
    events = ("Moved", "SoilExcavated", "SoilDropped", "ForagingStarted", "FoodCollected",
              "FoodDelivered", "CargoIngested", "NutritionTransferred", "AntDied")
    with TemporaryDirectory(dir=ROOT/"out") as temp, closing(NativeCore(binary, temp)) as core:
        folder = Path(temp)
        slot = "c"*32
        cut = fork_cut(core, folder, original, version, reference=78)
        (folder/(slot+".awstate")).write_bytes(cut)
        start = checkpoint(core.call(f"LOAD_SNAPSHOT {slot} {WORK_WORLD}"))
        require(start["physics"] == version and start["time_ms"] == 4_723_650_953, "Wrong worker boundary")
        end_raw = core.call(f"ADVANCE {WORK_STOP}")
        end = checkpoint(end_raw)
        receipt = defaultdict(list)
        counts = Counter()
        start_of_move = None
        totals = Counter()
        for f in facts(core,end["cursor"],start["cursor"]):
            kind = KINDS[f.kind]
            if kind in events and f.actor == 8:
                counts[kind] += 1
                totals[kind] += f.mass[0]
                if len(receipt[kind]) < 4:
                    receipt[kind].append([f.id, f.time, list(f.position), list(f.mass), f.payload, f.resource])
            if (f.actor == 8 and start_of_move is None and f.observation and
                    PHASES[f.observation[0]] == "Started" and ACTS[f.observation[1]] == "Move to a resting site"):
                start_of_move = f.time
        require(core.call("CHECK_LEDGERS") == b"", "Food or soil ledger mismatch")
        if version == 78:
            require(not counts["FoodCollected"] and counts["AntDied"] == 1, "Historical worker result changed")
        else:
            require(counts["SoilExcavated"] and counts["SoilDropped"] and totals["FoodCollected"] and
                    totals["CargoIngested"] and totals["NutritionTransferred"],"Detour did not close a real supply trip")
        continuation = None
        if verify_restore and start_of_move is not None:
            continuation=verify_continuation(core,slot,WORK_WORLD,start_of_move,WORK_STOP,end_raw,end["cursor"])
        return dict(physics=version, cut_sha256=sha256(cut).hexdigest(), final_sha256=sha256(end_raw).hexdigest(),
                    adult=STAGES[end["ants"][8]["stage"]]=="Adult", facts=end["cursor"]-start["cursor"],
                    counts=counts, sugar_ug=totals, first=dict(receipt), restored_ms=start_of_move if verify_restore else None,
                    restored_suffix_sha256=continuation)


def archive_first_worker(binary):
    """Restore the complete first-worker outing and independently ingest its facts."""
    with TemporaryDirectory(dir=ROOT/"out") as temp, closing(NativeCore(binary, temp)) as core:
        command = "NEW_PROVISIONED_NEST 1 1 250 80 plugged 1955 reachable nearby sheltered mineral work-face-detour wet-wick"
        first = checkpoint(core.call(command))
        cut_time = 4_741_859_619
        raw = core.call(f"ADVANCE {cut_time}")
        end = checkpoint(raw)
        collection, = [f for f in facts(core,end["cursor"],end["cursor"]-20)
                       if KINDS[f.kind] == "FoodCollected" and f.actor == 8 and f.time == cut_time]
        require(collection.mass[0] == 400, "Wrong first source debit")
        slot = "f"*32
        core.call(f"SAVE {slot}")
        path = Path(temp)/(slot+".sqlite")
        for _, tip, _, stream, _ in sqlite_inputs(path):
            count = sum(1 for _ in stream)
            require(count == end["cursor"] == tip["cursor"], "Incomplete independent archive read")
        continued = core.call(f"ADVANCE {cut_time+120_000}")
        require(core.call(f"LOAD {slot} {first['world']}") == raw, "Full checkpoint changed on load")
        require(core.call(f"ADVANCE {cut_time+120_000}") == continued and core.call("CHECK_LEDGERS") == b"",
                "Durable worker continuation changed")
        return dict(physics=79,cursor=end["cursor"],archive_bytes=path.stat().st_size,
                    frame_sha256=sha256(raw).hexdigest(),continued_sha256=sha256(continued).hexdigest())


def summarize_panel(binary, path):
    with gzip.open(EVIDENCE/"LOCAL_SOLICITATION_EXIT_TRIALS.jsonl.gz","rt") as source:
        baseline = [json.loads(line) for line in source]
    with gzip.open(path,"rt") as source:
        paired = [json.loads(line) for line in source]
    groups = {(r["seed"],r["supply"]) for r in baseline}
    horizons = {76: 90, 77: 90, 78: 730, 79: 730, 80: 730}
    require({r["physics"] for r in paired} == horizons.keys(), "Incomplete physics panel")
    inputs = verify_inputs(binary, baseline+paired)
    results = {}
    for version, horizon in horizons.items():
        trials = [r for r in paired if r["physics"]==version]
        require({(r["seed"],r["supply"]) for r in trials} == groups and len(trials)==len(groups), "Incomplete panel")
        screens = {r["census"][-1]["day"] for r in trials}
        require(screens == {horizon}, "Mismatched follow-up")
        for r in trials:
            ticks = {a["day"]:a for a in r["census"]}
            emerging = [life["Adult"][1] for life in r["lives"].values() if "Adult" in life]
            new_year = sum(365*DAY < time <= 730*DAY for time in emerging)
            alive = ticks[max(ticks)]["queen_alive"]
            qualifies=(730 in ticks and alive and new_year and
                       ticks[730]["workers"]>max(ticks[73]["workers"],ticks[365]["workers"]))
            results[f"{version}/{r['seed']}/{r['supply']}"] = dict(
                founder_death=r.get("queen_death"), new_year=new_year if 730 in ticks else None,
                first_eclosion_ms=min(emerging,default=None), workers=ticks[max(ticks)]["workers"],
                qualifies=bool(qualifies) if 730 in ticks else None, horizon=max(ticks))
    return {"input_identity":inputs,"worlds":results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, default=core_path())
    parser.add_argument("--version", type=int, choices=MODELS, action="append")
    parser.add_argument("--verify-restore", action="store_true")
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument("--first-worker", action="store_true")
    mode.add_argument("--archive", action="store_true")
    mode.add_argument("--panel", type=Path)
    mode.add_argument("--energy-seed", type=int, choices=ENERGY_CUTS)
    args = parser.parse_args()
    (ROOT / "out").mkdir(exist_ok=True)
    if args.archive or args.panel:
        result = (archive_first_worker(args.core.resolve()) if args.archive else
                  summarize_panel(args.core.resolve(),args.panel))
        print(json.dumps(result,separators=(",",":")))
        return
    source = WORK_CUT if args.first_worker else WATER_CUT
    if args.energy_seed is not None:
        source = EVIDENCE/f"SEED{args.energy_seed}_ENERGY_SUPPLY_CUT.awstate.gz"
    versions = (78,79) if args.first_worker else (78,80) if args.energy_seed is not None else MODELS
    cut = gzip.decompress(source.read_bytes())
    for version in args.version or versions:
        if args.first_worker:
            receipt = replay_first_worker(args.core.resolve(),version,cut,args.verify_restore)
        else:
            receipt = replay(args.core.resolve(),version,cut,args.verify_restore,energy_seed=args.energy_seed)
        print(json.dumps(receipt, separators=(",", ":")), flush=True)


if __name__ == "__main__":
    main()
