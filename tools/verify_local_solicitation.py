"""Replay a founder's terminal encounter and compare a matched two-year panel."""

import argparse
from contextlib import closing
import gzip
from hashlib import sha256
import json
from math import dist
from pathlib import Path
from tempfile import TemporaryDirectory

from op0.codec import ACTS, KINDS, OUTCOMES, PHASES, checkpoint, require
from op0.live import NativeCore, ROOT, core_path, live_bodies
from tools.compare_m0_worker_rhythm import facts
from tools.verify_sustained_contact import EVIDENCE, experimental_fork, feeding_summary, replay
from tools.verify_first_meal import verify_inputs


def terminal(binary, version):
    raw = gzip.decompress((EVIDENCE / "SEED2_STALLED_PAIR_CUT.awstate.gz").read_bytes())
    world = "00000000-0000-028d-0000-00e30000264a"
    slot = "e" * 32
    stop = 7_088_150_452
    with TemporaryDirectory(dir=ROOT/"out") as temp, closing(NativeCore(binary, temp)) as core:
        folder = Path(temp)
        if version != 67:
            raw = experimental_fork(core, folder, raw, 67, version)
        (folder/(slot+".awstate")).write_bytes(raw)
        def load():
            return checkpoint(core.call(f"LOAD_SNAPSHOT {slot} {world}"))
        start = load()
        final = core.call(f"ADVANCE {stop}")
        end = checkpoint(final)
        stream = list(facts(core, end["cursor"], start["cursor"]))
        gifts = [f for f in stream if KINDS[f.kind]=="NutritionTransferred" and f.payload==2 and f.mass[0]]
        deaths = [[f.id,f.time] for f in stream if KINDS[f.kind]=="AntDied" and f.actor==2]
        if version==67:
            require(not gifts and deaths==[[131278, stop]], "Published failure changed")
        else:
            require(gifts and not deaths, "Local encounter did not deliver sugar before starvation")
        load()
        witnessed = []
        for gift in gifts:
            before = checkpoint(core.call(f"ADVANCE {gift.time-1}"))
            poses = live_bodies(core.call("BODY_STATES"), before)
            oral = next(r.split() for r in core.call("ORAL_ACCESS").splitlines() if int(r.split()[0])==gift.actor)
            require(oral[1:3]==[b"1",b"1"], "Gift lacks previous mouth contact")
            after = checkpoint(core.call(f"ADVANCE {gift.time}"))
            for who, sign in ((gift.actor,-1), (2,1)):
                a,b = before["ants"][who]["crop_ug"],after["ants"][who]["crop_ug"]
                require([sign*(y-x) for x,y in zip(a,b)]==list(gift.mass), "Unbalanced oral transfer")
            witnessed.append(dict(id=gift.id, time_ms=gift.time, donor=gift.actor, dose_ug=gift.mass,
                                  mouth_mm=1000*dist(poses["2"]["mouth_m"],poses[str(gift.actor)]["mouth_m"])))
        require(core.call(f"ADVANCE {stop}")==final and core.call("CHECK_LEDGERS")==b"", "Continuation or ledger differs")
        uptake = sum(f.mass[0] for f in stream if f.actor==2 and KINDS[f.kind] in
                     ("FoundingBoundaryUptake","PhysiologyUpdated"))
        if gifts:
            require(uptake>0, "Sugar stayed in the founder crop")
            load()
            cut_time = gifts[0].time-1
            pending = core.call(f"ADVANCE {cut_time}")
            saved = "f"*32
            core.call(f"SAVE_SNAPSHOT {saved}")
            require(core.call(f"LOAD_SNAPSHOT {saved} {world}")==pending, "Pending meal lost in snapshot")
            require(core.call(f"ADVANCE {stop}")==final, "Resume changed outcome")
        return dict(version=version, cut_sha256=sha256(raw).hexdigest(), final_sha256=sha256(final).hexdigest(),
                    deaths=deaths, payments=witnessed, sugar_uptake_ug=uptake, final_energy_nj=end["ants"][2]["energy_nj"],
                    final_body_water_ug=end["ants"][2]["hydration_ug"])


def panel(binary, path):
    with gzip.open(EVIDENCE/"SUSTAINED_CONTACT_TRIALS.jsonl.gz", "rt") as source:
        old = [row for line in source if (row:=json.loads(line))["physics"]==67]
    with gzip.open(path, "rt") as source:
        new = [json.loads(line) for line in source]
    pairs = {(r["seed"],r["supply"]) for r in old}
    versions = {68:"local-solicitation", 69:"source-refill", 71:"trip-load", 72:"founder-route"}
    require(len(pairs)==6 and len(new)==len(pairs)*len(versions) and
            {(r["physics"],r["seed"],r["supply"]) for r in new}==
            {(v,seed,supply) for v in versions for seed,supply in pairs}, "Missing paired worlds")
    for row in new:
        baseline = next(r for r in old if (r["seed"],r["supply"])==(row["seed"],row["supply"]))
        args = row["command"].split()
        expected = baseline["command"].split()
        require(args[:1]+args[2:-2]+args[-1:]==expected[:1]+expected[2:-2]+expected[-1:] and
                args[-2]==versions[row["physics"]] and row["census"][-1]["day"]==730,
                "Changed environment, treatment or observation window")
        if row["supply"]=="absent":
            require(not row["founder_feeding_by_day"], "Unfunded sugar in absent-food control")
        paid = sum(v["sugar_ug"] for k,v in row["sugar_flux"].items()
                   if k.startswith("NutritionTransferred/") and k.endswith("/2"))
        require(paid==sum(day["sugar_ug"] for day in row["founder_feeding_by_day"].values()),
                "Actor flux disagrees with the founder meal ledger")
        for entry in row["sugar_flux"].values():
            require(0<=entry["before_founder_death_ug"]<=entry["sugar_ug"] and entry["count"]>0 and
                    entry["first"]<=entry["last"], "Invalid sugar flux interval")
    worlds = []
    for row in old + new:
        summary = feeding_summary(row)
        summary["death_cause"] = row["queen_death"][2] if "queen_death" in row else None
        worlds.append(summary)
    growth = {}
    for version in (67, *versions):
        supplied = [w for w in worlds if w["physics"] == version and w["supply"] == "nearby"]
        passed = [w["seed"] for w in supplied if w["sustained"]]
        growth[version] = dict(supplied=len(supplied), passing_seeds=passed, required=3, passed=len(passed) >= 3)
    return dict(inputs=verify_inputs(binary, old+new), worlds=worlds, growth=growth)


def earlier_cut(binary):
    raw = gzip.decompress((EVIDENCE / "SEED2_SIX_HOUR_CUT.awstate.gz").read_bytes())
    with TemporaryDirectory(dir=ROOT/"out") as temp, closing(NativeCore(binary, temp)) as core:
        folder = Path(temp)
        return [replay(core, folder, raw if v == 63 else experimental_fork(core, folder, raw, 63, v), v)
                for v in (63, 68, 69, 70)]


def trip_cycle(binary):
    """Replay the worker that repeatedly returned with sugar left over from a previous trip."""
    original = gzip.decompress((EVIDENCE/"SEED17_EMPTY_RETURN_CUT.awstate.gz").read_bytes())
    world = "00000000-0000-028d-0000-00ef00002659"
    stop = 6_231_109_932
    slot = "9"*32
    results = []
    with TemporaryDirectory(dir=ROOT/"out") as temp, closing(NativeCore(binary,temp)) as core:
        for version in (70,71):
            raw = original if version == 70 else experimental_fork(core,Path(temp),original,70,71)
            (Path(temp)/(slot+".awstate")).write_bytes(raw)
            def load():
                return checkpoint(core.call(f"LOAD_SNAPSHOT {slot} {world}"),forager_routes=True)
            start = load()
            require(all(not r["enabled"] for r in start["forager_routes"].values()),
                    "Cannot assume an empty trip on a fork with active collectors")
            require(start["ants"][11]["crop_ug"][0] == 13, "Changed residual sugar")
            final = core.call(f"ADVANCE {stop}")
            end = checkpoint(final)
            stream = list(facts(core,end["cursor"],start["cursor"]))
            trips = [f for f in stream if f.actor == 11 and KINDS[f.kind] == "BehaviorChanged" and f.payload == 3]
            collections = [f for f in stream if f.actor == 11 and KINDS[f.kind] == "FoodCollected" and f.mass[0]]
            source_sugar = {}
            for f in stream:
                if KINDS[f.kind] == "FoodCollected" and f.mass[0]:
                    source_sugar[f.actor] = source_sugar.get(f.actor, 0) + f.mass[0]
            ingested = [f for f in stream if f.actor == 11 and KINDS[f.kind] == "CargoIngested" and f.mass[0]]
            meals = [f for f in stream if KINDS[f.kind] == "NutritionTransferred" and f.payload == 2 and f.mass[0]]
            deaths = [f.id for f in stream if KINDS[f.kind] == "AntDied" and f.actor == 2]
            donors = sorted({f.actor for f in meals})
            absorbed = sum(f.mass[0] for f in stream if f.actor == 2 and
                           KINDS[f.kind] in ("FoundingBoundaryUptake", "PhysiologyUpdated"))
            if version == 70:
                require(len(trips) == 24 and not collections and deaths == [750405], "Empty trips did not reproduce")
            else:
                require(collections and ingested, "No new source debit or crop intake")
                load()
                mid = core.call(f"ADVANCE {ingested[0].time}")
                require(checkpoint(mid,forager_routes=True)["forager_routes"][11]["current_trip_liquid"],
                        "Committed liquid intake did not mark the outing")
                saved = "8"*32
                core.call(f"SAVE_SNAPSHOT {saved}")
                require(core.call(f"LOAD_SNAPSHOT {saved} {world}") == mid and core.call(f"ADVANCE {stop}") == final,
                        "Mid-trip continuation changed")
            require(core.call("CHECK_LEDGERS") == b"", "Food or soil ledger mismatch")
            results.append(dict(version=version, trips=len(trips), source_sugar_ug=source_sugar,
                                collections_ug=sum(f.mass[0] for f in collections),
                                ingested_ug=sum(f.mass[0] for f in ingested), deaths=deaths,
                                founder_sugar_ug=sum(f.mass[0] for f in meals), founder_absorbed_ug=absorbed,
                                donor_sugar_ug={i:sum(f.mass[0] for f in meals if f.actor == i) for i in donors},
                                from_worker_11_ug=sum(f.mass[0] for f in meals if f.actor == 11),
                                first_collection=[collections[0].id,collections[0].time] if collections else None,
                                final_sha256=sha256(final).hexdigest()))
    return results


def water_access(binary, version=71, seed=2):
    """Measure water paid to a founder on an identified six-hour dehydration cut."""
    cases = {
        1: ("SEED1_WATER_RELAY_CUT.awstate.gz", "00000000-0000-028d-0000-00f700002649", 5_411_520_000, 72),
        2: ("SEED2_WATER_ACCESS_CUT.awstate.gz", "00000000-0000-028d-0000-00f30000264a", 5_402_880_000, 71),
    }
    name, world, stop, original = cases[seed]
    raw = gzip.decompress((EVIDENCE / name).read_bytes())
    slot = "3" * 32
    with TemporaryDirectory(dir=ROOT/"out") as temp, closing(NativeCore(binary,temp)) as core:
        if version != original:
            raw = experimental_fork(core, Path(temp), raw, original, version)
        (Path(temp)/(slot+".awstate")).write_bytes(raw)
        start = checkpoint(core.call(f"LOAD_SNAPSHOT {slot} {world}"))
        require(start["physics"] == version and start["time_ms"] == stop-21_600_001, "Unexpected water cut")
        last = core.call(f"ADVANCE {stop-1}")
        last_frame = checkpoint(last)
        final = core.call(f"ADVANCE {stop}")
        end = checkpoint(final)
        stream = list(facts(core,end["cursor"],start["cursor"]))
        payments = [dict(event=f.id, time_ms=f.time, donor=f.actor, water_ug=f.mass[2])
                    for f in stream if KINDS[f.kind] == "NutritionTransferred" and f.payload == 2 and f.mass[2]]
        absorbed = sum(f.mass[2] for f in stream if f.actor == 2 and
                       KINDS[f.kind] in ("PhysiologyUpdated", "FoundingBoundaryUptake"))
        drunk = sum(f.mass[2] for f in stream if f.actor == 2 and KINDS[f.kind] == "FoundressWaterIngested")
        deaths = [f.id for f in stream if f.actor == 2 and KINDS[f.kind] == "AntDied"]
        decisions = {}
        approaches = {}
        moves = {}
        for f in stream:
            if KINDS[f.kind] == "AutonomyDecision" and f.actor in (2, 8, 9):
                decisions[f.actor] = decisions.get(f.actor, 0) + 1
            if KINDS[f.kind] == "Moved" and f.actor in (2, 8, 9):
                moves.setdefault(f.actor, []).append(tuple(f.position))
            if not f.observation or (f.actor != 2 and f.related != 2):
                continue
            phase, act = f.observation[:2]
            if ACTS[act] in ("Approach a nestmate", "Approach the depot"):
                key = f"{f.actor}/{f.related}/{ACTS[act]}/{PHASES[phase]}/{OUTCOMES[f.outcome]}"
                approaches[key] = approaches.get(key, 0) + 1
        require(core.call("CHECK_LEDGERS") == b"", "Water trial ledger mismatch")
        positions = {actor: dict(segments=len(seq), distinct_arrivals=len(set(seq)),
                                 backtracks=sum(a == c and a != b for a,b,c in zip(seq,seq[1:],seq[2:])),
                                 first=seq[:4]) for actor,seq in moves.items()}
        draws = [dict(event=f.id, time_ms=f.time, worker=f.actor, water_ug=f.mass[2]) for f in stream
                 if KINDS[f.kind] == "WorkerWaterIngested" and f.mass[2]]
        if version == 72 and seed == 2:
            require(drunk > 0 and absorbed > 0 and not deaths and end["ants"][2]["hydration_ug"] > 0,
                    "Founder did not obtain usable water before dehydration")
            debit = start["sources"][3]["stock_ug"][2] - end["sources"][3]["stock_ug"][2]
            all_draws = sum(f.mass[2] for f in stream if f.resource == 3 and KINDS[f.kind] in
                            ("FoundressWaterIngested", "WorkerWaterIngested"))
            require(debit == all_draws and debit >= drunk, "Wick water lacks a matching source debit")
            first = next(f for f in stream if f.actor == 2 and KINDS[f.kind] == "FoundressWaterIngested")
            core.call(f"LOAD_SNAPSHOT {slot} {world}")
            pending = core.call(f"ADVANCE {first.time-1}")
            saved = "4"*32
            core.call(f"SAVE_SNAPSHOT {saved}")
            require(core.call(f"LOAD_SNAPSHOT {saved} {world}") == pending and core.call(f"ADVANCE {stop}") == final,
                    "Mid-approach restore changed delivery or hydration")
        return dict(physics=version, seed=seed, worker_draws=draws, movement=positions, cut_sha256=sha256(raw).hexdigest(), before_sha256=sha256(last).hexdigest(),
                    final_sha256=sha256(final).hexdigest(), payments=payments, absorbed_water_ug=absorbed,
                    wick_intake_ug=drunk, decisions=decisions, approaches=approaches, deaths=deaths, before_body_water_ug=last_frame["ants"][2]["hydration_ug"],
                    end_body_water_ug=end["ants"][2]["hydration_ug"], events=end["cursor"]-start["cursor"])


def loaded_archive(binary):
    """Check full history validation at the first liquid intake, including its trip bit."""
    from tools.measure_single_nest_lifecycle import TREATMENTS, WORLD_BASES
    identifier = WORLD_BASES["nearby"] + 2 + TREATMENTS.index("trip-load") * 2**34 + 2**39
    command = f"NEW_PROVISIONED_NEST {identifier} 2 250 80 plugged 1955 reachable nearby sheltered mineral trip-load wet-wick"
    slot = "7"*32
    with TemporaryDirectory(dir=ROOT/"out") as temp, closing(NativeCore(binary,temp)) as core:
        core.call(command)
        at = 3_925_849_836
        raw = core.call(f"ADVANCE {at}")
        cut = checkpoint(raw,forager_routes=True)
        require(cut["forager_routes"][8]["current_trip_liquid"], "Missing liquid intake before archive")
        core.call(f"SAVE {slot}")
        later = core.call(f"ADVANCE {at+120_000}")
        require(core.call(f"LOAD {slot} {cut['world']}") == raw and core.call(f"ADVANCE {at+120_000}") == later
                and core.call("CHECK_LEDGERS") == b"", "Verified SQLite continuation changed a loaded outing")
        return dict(time_ms=at, worker=8, history_cursor=cut["cursor"], sha256=sha256(raw).hexdigest())


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core",type=Path,default=core_path())
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--panel",type=Path)
    mode.add_argument("--earlier-cut", action="store_true", help="Replay the two-worker day-91 encounter")
    mode.add_argument("--trip-cycle", action="store_true", help="Replay the old-load return loop and a mid-trip save")
    mode.add_argument("--water-relay", action="store_true", help="Measure the seed-1 terminal relay cut")
    mode.add_argument("--measure-water-cut", action="store_true", help="Measure a disposable probe on the physics 71 input")
    mode.add_argument("--water-cut", action="store_true", help="Measure funding, uptake and survival on the day-62 water cut")
    args=parser.parse_args()
    binary=args.core.resolve()
    (ROOT/"out").mkdir(exist_ok=True)
    if args.panel:
        result = panel(binary, args.panel)
    elif args.earlier_cut:
        result = earlier_cut(binary)
    elif args.trip_cycle:
        result = dict(terminal=trip_cycle(binary), archive=loaded_archive(binary))
    elif args.water_relay:
        result = water_access(binary, version=72, seed=1)
    elif args.measure_water_cut:
        result = water_access(binary)
    elif args.water_cut:
        result = [water_access(binary,v) for v in (71,72)]
        require(result[0]["deaths"] == [381412] and not result[0]["payments"] and result[0]["wick_intake_ug"] == 0,
                "Original dehydration case changed")
    else:
        result = [terminal(binary,v) for v in (67,68,69,70)]
    print(json.dumps(result,indent=2))
