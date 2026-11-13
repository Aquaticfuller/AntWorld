"""Read the original integration facts and verify the joint readiness endpoints."""

import argparse
from collections import Counter, defaultdict
from contextlib import closing
import csv
from hashlib import sha256
import json
import math
from pathlib import Path
from struct import pack, unpack_from
from tempfile import TemporaryDirectory
import uuid
from zipfile import ZipFile
import zlib

from analyze_integrated_founding import located_facts, observe_chain, verify_sources
from analyze_s6_4_wp6b import ANT_SEEDED, BIRTH, COLLECTED, DELIVERED, DIED, MOVED, OBSERVATION, RESTED, STAGE, assess, check, rows
from final_core_integration import PANELS, REFERENCE, cases
from founding_qualification_witnesses import COMMAND, archive_members, table
from run_integrated_founding import DAY
from run_s6_4_wp6b import ROOT, input_bytes, run_one, sha, write_json
from s6_4_wp5_geometry import Grid
from verify_s6_3_4_archive import BLOCK, MAX_RAW, ZERO, fnv, key, open_readonly


PUBLISHED = ROOT / "experiments/s6_4_final_core_readiness"
INHERITED = ROOT / "experiments/s6_4_integrated_founding/raw_index/world_receipts.jsonl"
AUTHORITY = ("initial.chk", "final.frame", "facts.bin")
SOIL = {23, 24, 25, 26}
EXCAVATE, DROP_SOIL, PICK_UP_SOIL, FILL_SOIL, EXCAVATION_DECISION = range(23, 28)
REJECTED, FORAGING_STARTED, FORAGING_DECISION, BEHAVIOR_CHANGED, BROOD_MOVED = 6, 10, 11, 17, 43
PROGRAMS = {0: "paused", 1: "rest", 2: "nurse", 3: "forage", 4: "excavate"}
DEPOT = (0., -.004, 0.)


def jsonl(path):
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            yield json.loads(line)


def check_identity(left, right, label):
    for name in AUTHORITY:
        check(left["artifacts"][name] == right["artifacts"][name], f"{label}: different {name}")
    for key in ("world", "seed", "queen", "state_hash", "trace_hash", "rng", "events", "time_ms"):
        check(left["summary"][key] == right["summary"][key], f"{label}: different {key}")


def replay_witness(directory, output, binary, panel):
    name = "borisovka-1-" + PANELS[panel][3]
    identity, case, _ = next((i,c,m) for i,c,m in cases(panel) if c["case"] == name)
    original = next(r["receipt"] for r in jsonl(directory / "archives.jsonl") if r["receipt"]["case"] == name)
    with TemporaryDirectory(dir=output) as scratch:
        actual = run_one(binary.resolve(strict=True), Path(scratch)/name, identity, case, "durable-split", COMMAND)
        check(actual["status"] == "COMPLETE", "fresh durable witness replay failed")
        check_identity(actual, original, name)
    write_json(output/"fresh_replay.json",dict(reference=original, rerun=actual, binary_sha256=sha(binary)))


def verify_midpoint(database, original, summary, cuts, work):
    """Check the actual published midpoint and its facts against the uninterrupted world."""
    cut = next(row for row in cuts if int(row["time_ms"]) == 75*DAY)
    db_path = work/"midpoint.sqlite"
    db_path.write_bytes(database)
    world, now, cursor = summary["world"], int(cut["time_ms"]), int(cut["cursor"])
    identity = uuid.UUID(world).int
    tail, fact, consumed = ZERO, 0, 0
    with closing(open_readonly(db_path)) as db:
        check(db.execute("PRAGMA quick_check").fetchall() == [("ok",)] and not db.execute("PRAGMA foreign_key_check").fetchall(),
              "midpoint database failed SQLite integrity")
        manifest, = db.execute("SELECT world,generation,revision,time_ms,cursor,checkpoint_hash FROM worlds").fetchall()
        check((manifest[0],key(manifest[1]),manifest[3],key(manifest[4])) == (world,1,now,cursor), "wrong durable cut")
        revision = key(manifest[2])
        for first_id,last_id,at_start,at_end,raw_bytes,index_digest,envelope in db.execute(
                "SELECT first_id,last_id,begin_ms,end_ms,raw_bytes,digest,envelope FROM fact_blocks WHERE world=? ORDER BY last_id",(world,)):
            fields = BLOCK.unpack_from(envelope)
            magic, version, codec, schema, flags, hi, lo, first, last, begin, end, count, packed, predecessor, digest = fields
            content = envelope[BLOCK.size:]
            check((magic,version,codec,schema,flags) == (b"AWFACT08",8,1,8,0) and (hi<<64 | lo)==identity and
                  (first,last)==(key(first_id),key(last_id)) and first==fact+1 and begin<=end<=now and
                  (begin,end,count,digest)==(at_start,at_end,raw_bytes,index_digest) and
                  0<count<=MAX_RAW and packed==len(content) and tail==predecessor and
                  digest==sha256(envelope[:104]+content).digest(), "invalid midpoint block identity")
            inflate=zlib.decompressobj()
            raw=inflate.decompress(content,count+1)
            check(len(raw)==count and inflate.eof and not inflate.unused_data and not inflate.unconsumed_tail and
                  raw==original[consumed:consumed+count], "midpoint bytes differ from canonical uninterrupted prefix")
            tail, fact, consumed = digest,last,consumed+count
        checkpoint, = db.execute("SELECT generation,revision,cursor,checkpoint_hash,time_ms,checkpoint,parent,tail,digest "
                                 "FROM generations JOIN history_anchors USING(world,generation) WHERE world=?",(world,)).fetchall()
        generation,frame_revision,frame_cursor,frame_hash = map(key,checkpoint[:4])
        at,frame,parent,anchor_tail,anchor = checkpoint[4:]
        check((generation,frame_revision,frame_cursor,frame_hash,at)==(1,revision,cursor,key(manifest[5]),now) and
              parent==ZERO and anchor_tail==tail and frame[:8]==b"AWSTATE1" and fnv(frame)==frame_hash and
              fnv(frame[:-8])==int.from_bytes(frame[-8:],"little"),"midpoint checkpoint is not bound to its facts")
        header = pack("<8s7Q",b"AWANCH01",identity>>64,identity%2**64,generation,revision,cursor,frame_hash,now)
        check(sha256(header+parent+anchor_tail+frame).digest()==anchor,"invalid midpoint anchor")
    check(fact==cursor and (consumed==len(original) or unpack_from("<Q",original,consumed+28)[0]>now),
          "midpoint prefix does not stop at the complete committed cut")
    return dict(time_ms=now,cursor=cursor,revision=revision,world=world,canonical_bytes=consumed,
                canonical_sha256=sha256(original[:consumed]).hexdigest(),tail=tail.hex(),anchor=anchor.hex(),
                checkpoint_sha256=sha256(frame).hexdigest())


def initial_geometry(name):
    def layout(kind, minimum, maximum):
        return dict(kind=kind, **{f"{label}_{axis}_q":value for label,point in (("min",minimum),("max",maximum))
                                for axis,value in zip("xyz",point,strict=True)})

    if "-shaft-" in name:
        voids = (((14,6,14),(18,16,18)),)
    elif name.endswith("-roomy"):
        voids = (((8,4,8),(24,12,24)),((12,4,12),(20,16,20)))
    else:
        voids = (((14,4,14),(18,16,18)),((12,5,14),(20,11,18)))
    return Grid([layout("solid",(0,0,0),(32,16,32)),*(layout("void",low,high) for low,high in voids)])


def verify_actions(raw, cuts, space, edits, name):
    """Replay soil parcels and separate real actions from labels and opportunities."""
    cut_iter = iter(zip(cuts, space, strict=True))
    cut = next(cut_iter)
    initial_soil = int(cuts[0]["initial_q3"])
    geometry = initial_geometry(name)
    check(initial_soil == len(geometry.soil), "initial material differs from the frozen geometric fixture")
    remaining, carried, deposited = initial_soil, 0, 0
    parcels, holds, dig_starts = {}, {}, set()
    excavation_q3, fill_q3, revision, deposit_units = 0, 0, 0, 0.
    soil_edits = {int(row["event"]): row for row in edits}
    check(len(soil_edits) == len(edits), "nonunique geometry evidence")
    outcome, phases = Counter(), Counter()
    completed, positions, programs, entries = set(), {}, {}, {}
    activity = defaultdict(Counter)
    starts, ready, first_marker = set(), set(), None
    exact_start = {}
    trail_labeled, naive_first_choices, naive_first_delivery = set(), set(), set()
    eclosed, early_adult_deaths = set(), set()
    adult_exposure = 0
    is_blocked = name.endswith("-blocked")
    is_silent = name.endswith(("roomy", "compact-silent"))

    def reconcile(next_event):
        nonlocal cut
        while cut and int(cut[0]["cursor"]) < next_event:
            budget, sample = cut
            check(budget["cursor"] == sample["cursor"] and budget["time_ms"] == sample["time_ms"], "space cut identity drift")
            check((remaining, carried, deposited) == tuple(int(budget[k]) for k in ("remaining_q3", "carried_q3", "deposited_q3")),
                  "replayed soil budget differs at observation")
            check((revision, len(parcels), excavation_q3, fill_q3) == tuple(int(sample[k]) for k in
                  ("geometry_revision", "parcels", "excavated_q3", "filled_q3")), "soil fact-to-edit history differs")
            check(math.isclose(deposit_units, float(sample["deposited_units"]), abs_tol=1e-12), "trail deposit sum differs")
            check(int(sample["shaft_open"]) and bool(int(sample["strip_open"])) != is_blocked, "assay access changed")
            check(geometry.swept((16,8,16),(16,18,16),2), "independent loaded shaft replay is blocked")
            if is_silent:
                check(not deposit_units and not int(sample["trail_cells"]), "signal in disabled control")
            cut = next(cut_iter, None)

    offset, event_id = 0, 0
    for event, resource, position in located_facts(raw):
        event_id, time, source, kind, actor, target, _, stage, result, amount, obs = event
        _, reason, units = unpack_from("<BBd", raw, offset + 152)
        offset += 4 + (210 if kind == OBSERVATION else 159)
        reconcile(event_id)
        previous = positions.get(actor)
        row = activity[actor] if actor else None
        if kind in (ANT_SEEDED, BIRTH, BROOD_MOVED):
            positions[actor] = position
        if kind == STAGE and stage == 3:
            eclosed.add(actor)
            positions[actor] = position
            programs[actor], entries[actor] = 0, time
        if kind in (BEHAVIOR_CHANGED, DIED) and actor in eclosed:
            program = programs.pop(actor)
            duration = time - entries.pop(actor)
            check(duration >= 0, "negative program residence")
            row[PROGRAMS[program] + "_residence_ms"] += duration
            adult_exposure += duration
            if kind == BEHAVIOR_CHANGED:
                programs[actor], entries[actor] = target, time
                row["program_changes"] += 1
            else:
                early_adult_deaths.add(actor)
        if kind == EXCAVATION_DECISION:
            dig_starts.add(actor)
            row["dig_decisions"] += 1
        if kind == FORAGING_STARTED:
            starts.add(actor)
        if kind == FORAGING_DECISION:
            row["local_cues"] += bool(resource)
            row["trail_labels"] += reason == 3
            row["memory_labels"] += reason == 4
            if reason == 3:
                trail_labeled.add(actor)
                if actor not in ready:
                    naive_first_choices.add(actor)
        if kind == MOVED:
            check(previous is not None, "move has no authority origin")
            distance = math.dist(position, previous)
            row["moves"] += distance > 0
            row["path_m"] += distance
            if actor in holds and distance > 0:
                parcel = parcels[holds[actor]]
                parcel[3] |= parcel[2] == actor
                row["soil_carry_moves"] += 1
            if previous == DEPOT and distance > 0 and actor in starts and actor not in exact_start:
                exact_start[actor] = (event_id, time, first_marker)
            positions[actor] = position
            if units and first_marker is None:
                first_marker = (event_id, time, actor)
            deposit_units += units
            row["marked_moves"] += units > 0
        if kind in (COLLECTED, DELIVERED):
            row["collections" if kind == COLLECTED else "deliveries"] += 1
            if kind == COLLECTED:
                ready.add(actor)
            elif actor in naive_first_choices:
                naive_first_delivery.add(actor)
        if kind == RESTED:
            row["committed_rests"] += 1
        if kind == REJECTED:
            outcome[result] += 1
        if kind == OBSERVATION and obs[1] in (2, 3, 4, 5, 6, 7, 16, 17):
            phases[obs[0]] += 1
            if obs[0] == 3 and result <= 1:
                row["care_completed"] += 1
                if obs[5]:
                    row["care_known_ms"] += time - obs[4]
        if kind not in SOIL:
            continue
        check(actor in eclosed and actor not in early_adult_deaths and result <= 1, "invalid soil actor or result")
        row["soil_facts"] += 1
        if kind in (EXCAVATE, FILL_SOIL):
            revision += 1
            edit = soil_edits.pop(event_id)
            check(tuple(int(edit[k]) for k in ("id", "source", "actor", "parcel", "kind", "time_ms")) ==
                  (revision, source, actor, target, 0 if kind == EXCAVATE else 3, time), "geometry edit does not match its fact")
            volume = int(edit["volume_q3"])
            check(volume == geometry.edit(edit,kind==EXCAVATE), "edited volume differs from reconstructed material")
        if kind == EXCAVATE:
            check(target not in parcels and actor in dig_starts and actor not in holds,
                  f"{name}, event {event_id}: unfunded or overlapping excavation")
            parcels[target] = [volume, "carried", actor, False]
            holds[actor] = target
            remaining -= volume
            carried += volume
            excavation_q3 += volume
        elif kind == DROP_SOIL:
            volume, state, miner, moved = parcels[target]
            check(state == "carried" and holds.pop(actor) == target, "drop has no matching soil load")
            carried -= volume
            deposited += volume
            parcels[target] = [volume, "deposited", miner, moved]
            if miner == actor and moved:
                completed.add(target)
                row["complete_soil_chains"] += 1
        elif kind == PICK_UP_SOIL:
            volume, state, miner, moved = parcels[target]
            check(state == "deposited" and actor not in holds, "pickup has no deposited soil")
            deposited -= volume
            carried += volume
            parcels[target] = [volume, "carried", miner, moved]
            holds[actor] = target
        else:
            old, state, miner, moved = parcels[target]
            check(state == "carried" and volume <= old and holds.get(actor) == target, "fill has no matching material")
            carried -= volume
            remaining += volume
            fill_q3 += volume
            parcels[target] = [old-volume, "carried" if old > volume else "exhausted", miner, moved]
            if old == volume:
                del holds[actor]
    reconcile(event_id + 1)
    check(cut is None and not soil_edits and offset == len(raw), "incomplete geometry or fact evidence")
    for actor, program in programs.items():
        duration = 150*DAY - entries[actor]
        check(duration >= 0,"negative final program residence")
        activity[actor][PROGRAMS[program] + "_residence_ms"] += duration
        adult_exposure += duration
    totals = Counter()
    for actor in eclosed:
        totals.update(activity[actor])
    return dict(soil_edits=revision, excavated_q3=excavation_q3, filled_q3=fill_q3, completed_soil_parcels=len(completed),
                eclosed_workers=len(eclosed), worker_deaths=len(early_adult_deaths), forager_activations=len(starts),
                observed_departures=len(exact_start), departures_after_other_mark=sum(marker is not None and actor != marker[2]
                    for actor, (_, _, marker) in exact_start.items()),
                deposited_units=deposit_units, workers_with_trail_label=len(trail_labeled),
                naive_trail_label_before_first_collection=len(naive_first_choices),
                naive_trail_label_then_delivery=len(naive_first_delivery), worker_rejections=sum(outcome.values()),
                **{f"care_phase_{i}": phases[i] for i in range(5)},
                **{f"worker_{k}": totals[k] for k in ("moves", "path_m", "committed_rests", "program_changes", "care_completed",
                   "care_known_ms", "dig_decisions", "soil_carry_moves", "local_cues", "trail_labels", "memory_labels")},
                **{f"worker_{k}_residence_ms": totals[f"{k}_residence_ms"] for k in PROGRAMS.values()}), activity, adult_exposure


def analyze_case(identity, case, record, blobs):
    check(json.loads(blobs["case.json"]) == case and blobs["parameters.txt"] == input_bytes(identity, case), "case input changed")
    case = case | dict(arm=case["supply_arm"], early_access_mask=3, carbohydrate_yield_nj_per_ug=8_000_000)
    raw, summary = blobs["facts.bin"], record["summary"]
    result, exposures, offspring, matched = assess(case, summary, raw, blobs["cuts.csv"], blobs["individuals.csv"], 7)
    cuts = rows(blobs["cuts.csv"])
    cargo = defaultdict(dict)
    snapshots = defaultdict(list)
    first_larval_cut = matched[1]["first_larva_ms"]
    first_census = set()
    for cut in cuts:
        cargo[int(cut["time_ms"])].clear()
    for ant in rows(blobs["individuals.csv"]):
        time = int(ant["time_ms"])
        if time in (120*DAY, 150*DAY):
            snapshots[time//DAY].append(ant)
        if time == first_larval_cut and ant["stage"] == "1" and ant["mother"] == summary["queen"]:
            first_census.add(int(ant["id"]))
        mass = tuple(int(ant[f"carried_{part}"]) for part in "cpwo")
        if any(mass):
            cargo[time][int(ant["id"])] = mass
    material = verify_sources(raw, case, cuts, observed_cargo=cargo)
    chain, adults, trips, flows = observe_chain(raw, case, int(summary["queen"]), offspring, snapshots)
    actions, activity, exposure = verify_actions(raw, cuts, rows(blobs["space_cuts.csv"]), rows(blobs["geometry_edits.csv"]), case["case"])
    if case["arm"] == "integrated-no-protein":
        check(chain["worker_protein_assimilated_lower_bound_ug"] == 0, "worker-derived protein entered a protein-free assay")
    check(len(adults) == actions["eclosed_workers"], "inconsistent number of workers")
    check(sum(w["terminal_age_ms"] for w in adults) == exposure, "adult exposure and life history disagree")
    check(len(first_census) == matched[1]["k"], "first larval census changed")
    row = dict(case=case["case"], population=case["population"], seed=case["software_seed"],
               events=result["source_facts"], births=result["births"], hatch=result["hatch"], pupation=result["pupation"],
               first_worker_ms=result["first_worker_ms"], queen_death_cause=result["queen_death_cause"],
               adult_energy_deaths=sum(w["death_cause"] == 1 for w in adults),
               adult_water_deaths=sum(w["death_cause"] == 2 for w in adults),
               joint_chain=int(chain["complete"] and actions["completed_soil_parcels"] > 0))
    row.update(first_census_k=len(first_census), first_census_eclosed=sum(w["ant"] in first_census for w in adults),
               exact_larval_census_days=matched[1]["larva_d"], exact_total_census_days=matched[1]["total_d"],
               at_least_larval_census_days=matched[0]["larva_d"], at_least_total_census_days=matched[0]["total_d"])
    row.update(chain | actions | material)
    finished_first = [w for w in adults if w["first_delivery_ms"] is not None]
    first_delivery = min(finished_first,key=lambda w:w["first_delivery_ms"],default=None)
    row["first_load_to_delivery_ms"] = first_delivery["first_delivery_ms"]-first_delivery["first_collection_ms"] if first_delivery else None
    for key in ("depot_c_at_queen_death_ug", "depot_c_empty_before_death_ms", "collections", "deliveries", "queen_gifts", "cargo_uses"):
        row.setdefault(key, None)
    return {k: v for k, v in row.items() if not k.startswith("rejected_")}, (exposures, adults, trips, flows, activity)


def verify(directory, output, witness_only=False, panel="primary"):
    expected = {c["case"]: (i, c, mode) for i, c, mode in cases(panel)}
    archive_rows = list(jsonl(directory / "archives.jsonl"))
    records = {row["receipt"]["case"]: row for row in archive_rows}
    protocol, _, _, marked, witnesses = PANELS[panel]
    check(len(archive_rows) == len(records), "duplicate integration receipt")
    check(expected.keys() == records.keys(), "wrong number of frozen integration cases")
    run = json.loads((directory/"run.json").read_bytes())
    check(run["roster"] == [dict(case=name,identity=i,mode=m) for name,(i,_,m) in expected.items()] and
          run["protocol_sha256"] == sha(protocol) and run["reference"] == REFERENCE and
          run["arguments"] == COMMAND, "changed frozen collector identity or roster")
    inherited = {row["receipt"]["case"]: row["receipt"] for row in jsonl(INHERITED) if row["batch"] == "resupply-nominal"}
    output.mkdir(parents=True, exist_ok=True)
    check(not (output/"consistency.json").exists(), "use a fresh evidence output directory")
    result, failures, equivalences = [], [], []
    for name, (identity, case, mode) in expected.items():
        manifest = records[name]
        record = manifest["receipt"]
        check((record["identity"], record["mode"]) == (identity, mode), "execution identity or mode changed")
        if record["status"] != "COMPLETE":
            failures.append(dict(case=name, mode=mode, status=record["status"], exit_code=record["exit_code"]))
        elif name.endswith("-roomy"):
            check_identity(record, inherited[case["authority_reference"]], name)
            equivalences.append(dict(case=name, reference=case["authority_reference"], equal=True))
        elif mode != "observed":
            primary = records[name.removesuffix("-" + mode)]["receipt"]
            if primary["status"] == "COMPLETE":
                check_identity(record, primary, name)
                equivalences.append(dict(case=name, reference=primary["case"], equal=True))
        is_witness = (case["population"], case["software_seed"], case["arm"].removeprefix("readiness-")) in witnesses
        is_saved_witness = panel != "primary" and name == f"borisovka-1-{marked}-durable-split"
        if witness_only and not (is_witness and mode == "observed" or is_saved_witness):
            continue
        path = directory / manifest["archive"]
        check(sha(path) == manifest["archive_sha256"], f"{name}: archive SHA-256 changed")
        blobs = archive_members(path, name, record)
        if is_saved_witness:
            observed = records[name.removesuffix("-durable-split")]
            with ZipFile(directory/observed["archive"]) as archive:
                cuts = rows(archive.read(observed["receipt"]["case"]+"/cuts.csv"))
            with TemporaryDirectory(dir=output) as scratch:
                audit = verify_midpoint(blobs["midpoint.sqlite"],blobs["facts.bin"],record["summary"],cuts,Path(scratch))
            if witness_only:
                check(audit==json.loads((directory/"durable_prefix.json").read_bytes()),"published midpoint evidence changed")
            write_json(output/"durable_prefix.json",audit)
        if mode == "observed" and record["status"] == "COMPLETE":
            row, detail = analyze_case(identity, case, record, blobs)
            result.append(row)
            if is_witness:
                exposures, adults, trips, flows, activity = detail
                for suffix, rows_ in (("stages", exposures), ("trips", trips), ("nutrition", flows),
                                      ("workers", [{**w, **activity[w["ant"]]} for w in adults])):
                    rows_ = list(rows_)
                    if rows_:
                        keys = tuple(dict.fromkeys(key for item in rows_ for key in item))
                        (output / f"{name}-{suffix}.csv").write_bytes(table(rows_, keys))
            print(name, "chain", row["complete"], "soil", row["completed_soil_parcels"], flush=True)
    if witness_only:
        with (directory / "worlds.csv").open(newline="", encoding="utf-8") as stream:
            published = {r["case"]: r for r in csv.DictReader(stream)}
        for row in result:
            check({k: "" if v is None else str(v) for k, v in row.items()} == published[row["case"]], "derived public witness statistics changed")
        check(len(result) == len(witnesses), "missing fixed public witness")
    (output / "worlds.csv").write_bytes(table(result, tuple(dict.fromkeys(key for row in result for key in row))))
    write_json(output / "consistency.json", dict(equal=equivalences, failures=failures, verified=len(result),
        primary=len(expected)-4, repeats=4))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--witness-only", action="store_true")
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument("--shaft", action="store_const", const="shaft", dest="panel")
    choice.add_argument("--clock", action="store_const", const="clock", dest="panel")
    parser.add_argument("--replay", type=Path)
    args = parser.parse_args()
    panel = args.panel or "primary"
    verify(args.directory, args.output, args.witness_only, panel)
    if args.replay:
        replay_witness(args.directory, args.output, args.replay,panel)
