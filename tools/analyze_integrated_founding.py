"""Audit funded development and complete founding chains from canonical facts."""

import argparse
from collections import Counter, defaultdict
import csv
import gzip
from hashlib import sha256
import json
import math
from pathlib import Path
from struct import unpack_from
from tempfile import TemporaryDirectory
import zipfile

from analyze_s6_4_wp6b import (ANT_SEEDED, BIRTH, CARGO, COLLECTED, DELIVERED, DIED, F_BOUNDARY_UPTAKE, F_DIETARY_EGG,
                              F_NEST_MEAL, F_RATION, GIFT, MOVED, NEST, OBSERVATION, OBS_COMPLETED, RECYCLED, STAGE, UPTAKE,
                              assess, check, evaluate, facts, rows)
from run_integrated_founding import DAY, MODELS, SENSITIVITIES, environments
from run_s6_4_wp6b import input_bytes, sha, write_json


def located_facts(raw):
    offset = 0
    for event in facts(raw, F_BOUNDARY_UPTAKE):
        resource, x, y, z = unpack_from("<Qddd", raw, offset + 86)
        yield event, resource, (x, y, z)
        size, = unpack_from("<I", raw, offset)
        offset += size + 4


def verify_sources(raw, case, cuts, source_observer=None, observed_cargo=None):
    empty = (0, 0, 0, 0)
    seeded, reserve, on_site, cargo = None, empty, empty, defaultdict(lambda: empty)
    totals = [0, 0, 0, 0]
    cut_rows = iter(cuts)
    cut = next(cut_rows)
    last = 0

    def reconcile(event):
        nonlocal cut
        while cut and int(cut["cursor"]) < event:
            check(tuple(int(cut[f"available_{k}"]) for k in "cpwo") == on_site, "physical food inventory drift")
            if observed_cargo is not None:
                actual = {ant: mass for ant, mass in cargo.items() if any(mass)}
                check(observed_cargo[int(cut["time_ms"])] == actual, "carried food inventory drift")
            cut = next(cut_rows, None)

    def apply(stock, quantity, sign=1):
        result = tuple(x + sign*y for x, y in zip(stock, quantity, strict=True))
        check(min(result) >= 0, "unfunded external or carried quantity")
        return result

    for event, resource, position in located_facts(raw):
        last, _, _, kind, actor, _, _, _, _, mass, _ = event
        reconcile(last)
        if kind == 3:
            check(seeded is None and resource and abs(position[0]) == .03 and position[1:] == (0., 0.), "unexpected physical food source")
            seeded = resource
            on_site = tuple(case["external_food_components_ug"])
            check(on_site == mass, "source seed lacks exact material")
        elif kind == 36:
            daily = (188, 94, 563, 0) if case["arm"] == "integrated-limited" else tuple(m//4 for m in on_site)
            reserve = tuple(case.get("release_days",120)*m for m in daily)
            check(resource == seeded and mass == reserve, "food release source differs from the finite input")
        elif kind == 37:
            check(resource == seeded, "release lacks its finite source")
            reserve = apply(reserve, mass, -1)
            on_site = apply(on_site, mass)
        elif kind == COLLECTED:
            check(resource == seeded and abs(position[0]) >= .025, "collection did not occur at the external source")
            on_site = apply(on_site, mass, -1)
            cargo[actor] = apply(cargo[actor], mass)
        elif kind in (DELIVERED, CARGO):
            cargo[actor] = apply(cargo[actor], mass, -1)
            if kind == DELIVERED:
                for i, value in enumerate(mass):
                    totals[i] += value
        if source_observer and kind in (3,36,37,COLLECTED,DELIVERED,CARGO):
            source_observer(event,resource,position,reserve,on_site,cargo[actor])
    reconcile(last+1)
    check(cut is None and bool(seeded) == bool(case["external_food_ug"]), "missing source or terminal coverage")
    return dict(zip(("delivered_c", "delivered_p", "delivered_w", "delivered_o"), totals, strict=True))


def observe_chain(raw, case, queen, paths, snapshots):
    adults, birth = {}, {p["ant"]: p["birth_ms"] for p in paths}
    larva_paid, larva_uptake, queen_uptake = set(), set(), {}
    maternal_protein, forced_worker_protein = defaultdict(int), defaultdict(int)
    work_days, completed_days, trips = set(), defaultdict(set), []
    stages, previous = {}, {}
    dietary_eggs, flows, carb_deliveries = set(), [], []
    nest_carb, stock_depletions, empty_since, empty_intervals = 0, 0, None, []
    attempts = Counter()
    world = dict(first_delivery_ms=None, first_queen_gift_ms=None, first_queen_carb_ms=None, first_queen_water_ms=None,
                 first_larval_worker_protein_ms=None, first_larval_worker_uptake_ms=None)
    queen_death = None
    for event, _, position in located_facts(raw):
        event_id, t, _, kind, ant, payload, _, stage, outcome, amount, obs = event
        if kind == ANT_SEEDED:
            check(ant == queen and stage == 3 and not previous, "an ant was pre-seeded beyond the foundress")
            previous[ant] = position
        if kind in (ANT_SEEDED, BIRTH, STAGE, DIED):
            stages[ant] = stage
        if kind == F_DIETARY_EGG:
            dietary_eggs.add(payload)
        if kind in (DELIVERED, RECYCLED, NEST, F_NEST_MEAL) and amount[0]:
            old_stock=nest_carb
            nest_carb += amount[0] if kind in (DELIVERED, RECYCLED) else -amount[0]
            check(nest_carb>=0,"negative depot carbohydrate")
            if old_stock and not nest_carb:
                empty_since=t
                stock_depletions+=1
            elif nest_carb and empty_since is not None:
                empty_intervals.append(t-empty_since)
                empty_since=None
        if kind in (GIFT, F_RATION, F_DIETARY_EGG, F_NEST_MEAL, UPTAKE, F_BOUNDARY_UPTAKE) and (any(amount) or kind in (F_RATION,F_DIETARY_EGG)):
            target = payload if kind in (GIFT,F_RATION,F_DIETARY_EGG) else ant
            if ant==queen or target==queen or stages.get(target)==1:
                flows.append(dict(event=event_id,time_ms=t,kind=kind,actor=ant,recipient=target,stage=stages[target],
                                  c=amount[0],p=amount[1],w=amount[2],o=amount[3]))
        if kind == STAGE and stage == 3:
            check(ant in birth and ant not in adults, "adult identity lacks an actual birth")
            adults[ant] = dict(ant=ant, eclose_ms=t, birth_ms=birth[ant], death_ms=None, death_cause=None,
                               first_collection_ms=None, first_delivery_ms=None, first_carb_ms=None, first_water_ms=None,
                               trips=0, moves=0, care_acts=0, carb_ug=0, water_ug=0, collected_ug=0, delivered_ug=0,
                               outbound=False, loaded=False, returning=False)
            previous[ant] = position
        if kind == GIFT and ant in adults and world["first_delivery_ms"] is not None:
            if payload == queen:
                world["first_queen_gift_ms"] = world["first_queen_gift_ms"] or t
                attempts["queen_gifts"] += 1
            if stages[payload] == 1 and amount[1]:
                larva_paid.add(payload)
                world["first_larval_worker_protein_ms"] = world["first_larval_worker_protein_ms"] or t
        if kind == F_RATION:
            maternal_protein[payload] += amount[1]
        if kind in (UPTAKE, F_BOUNDARY_UPTAKE):
            if ant == queen and world["first_delivery_ms"] is not None:
                for label, qty in (("carb", amount[0]), ("water", amount[2])):
                    if qty and label not in queen_uptake:
                        queen_uptake[label] = t
                        world[f"first_queen_{label}_ms"] = t
            elif stages[ant] == 1 and amount[1]:
                # Spending all possible maternal crop first gives a conservative lower bound.
                other = min(amount[1], maternal_protein[ant])
                maternal_protein[ant] -= other
                forced_worker_protein[ant] += amount[1] - other
                if ant in larva_paid and forced_worker_protein[ant]:
                    larva_uptake.add(ant)
                    world["first_larval_worker_uptake_ms"] = world["first_larval_worker_uptake_ms"] or t
        if kind == DIED and ant == queen:
            queen_death = t
            world["depot_c_at_queen_death_ug"]=nest_carb
            if empty_since is not None:
                world["depot_c_empty_before_death_ms"]=t-empty_since
        if ant not in adults:
            continue
        individual = adults[ant]
        if kind == DIED:
            individual["death_ms"], individual["death_cause"] = t, payload
        elif kind == MOVED and previous[ant] != position:
            individual["moves"] += 1
            individual["returning" if individual["loaded"] else "outbound"] = True
            previous[ant] = position
        elif kind == COLLECTED and any(amount):
            individual["first_collection_ms"] = individual["first_collection_ms"] or t
            individual["collected_ug"] += sum(amount)
            individual["loaded"] = True
            attempts["collections"] += 1
        elif kind == DELIVERED and any(amount):
            check(individual["loaded"] and math.dist(position, (0, -.004, 0)) <= .002, "delivery lacks a load or nest contact")
            if individual["outbound"] and individual["returning"]:
                individual["trips"] += 1
                completed_days[ant].add(t//DAY)
                trips.append(dict(ant=ant, delivery_event=event_id, delivery_ms=t, c=amount[0], p=amount[1], w=amount[2]))
                if amount[0] and queen_death is None:
                    carb_deliveries.append(t)
            individual["first_delivery_ms"] = individual["first_delivery_ms"] or t
            individual["delivered_ug"] += sum(amount)
            world["first_delivery_ms"] = world["first_delivery_ms"] or t
            work_days.add(t//DAY)
            individual["outbound"] = individual["returning"] = individual["loaded"] = False
            attempts["deliveries"] += 1
        elif kind == CARGO:
            attempts["cargo_uses"] += 1
        elif kind in (UPTAKE, F_BOUNDARY_UPTAKE):
            individual["carb_ug"] += amount[0]
            individual["water_ug"] += amount[2]
            if amount[0] and individual["first_carb_ms"] is None:
                individual["first_carb_ms"] = t
            if amount[2] and individual["first_water_ms"] is None:
                individual["first_water_ms"] = t
        elif kind == OBSERVATION and obs[0] == OBS_COMPLETED and outcome <= 1 and 1 <= obs[1] <= 10:
            individual["care_acts"] += 1
            work_days.add(t//DAY)
        elif kind == 6:
            attempts[f"rejected_{outcome}"] += 1
    for ant, individual in adults.items():
        terminal = individual["death_ms"]
        age = (case["horizon_ms"] if terminal is None else terminal) - individual["eclose_ms"]
        individual.update(terminal_age_ms=age, distinct_delivery_days=len(completed_days[ant]), censored=int(terminal is None))
        for key in ("outbound", "loaded", "returning"):
            del individual[key]
    first_adult = min((w["eclose_ms"] for w in adults.values()), default=None)
    paired_uptake = max(queen_uptake.values()) if len(queen_uptake) == 2 else None
    late = [w for w in adults.values() if paired_uptake is not None and w["birth_ms"] > paired_uptake]
    alive = {d: (sum(int(row["mother"]) == queen and row["stage"] == "3" for row in snapshots[d]),
                 any(int(row["id"]) == queen and row["stage"] == "3" for row in snapshots[d])) for d in (120, 150)}
    sustained = [w for w in adults.values() if w["terminal_age_ms"] >= 7*DAY and w["distinct_delivery_days"] >= 2
                 and w["carb_ug"] and w["water_ug"]]
    work_span = max(work_days)-min(work_days) if work_days else 0
    terminal = queen_death or case["horizon_ms"]
    gaps=[b-a for a,b in zip(carb_deliveries,carb_deliveries[1:])]
    gates = (first_adult is not None and first_adult <= 90*DAY, bool(trips), bool(sustained),
             world["first_queen_gift_ms"] is not None, paired_uptake is not None, bool(larva_uptake), bool(late),
             all(n and q for n, q in alive.values()), len(work_days) >= 4 and work_span >= 14)
    if case["arm"] in ("integrated-blocked", "integrated-absent"):
        check(not attempts["collections"] and not attempts["deliveries"] and not gates[1], "negative control collected food")
    world.update(dict(zip(("g_eclosion", "g_actual_trip", "g_sustained_worker", "g_queen_receipt", "g_queen_uptake",
                          "g_larval_uptake", "g_late_eclosion", "g_joint_survival", "g_work_span"), map(int, gates), strict=True)))
    world.update(complete=int(all(gates)), born=len(birth), eclosed=len(adults), queen_death_ms=queen_death,
                 adults_120=alive[120][0], adults_150=alive[150][0], queen_alive_120=int(alive[120][1]),
                 queen_alive_150=int(alive[150][1]), work_days=len(work_days), work_span_days=work_span, valid_loaded_trips=len(trips),
                 late_born_adults=len(late), late_first_worker_ms=min((w["eclose_ms"] for w in late), default=None),
                 late_adults_from_dietary_eggs=sum(w["ant"] in dietary_eggs for w in late),
                 preterminal_carb_delivery_gaps=len(gaps), preterminal_max_carb_gap_ms=max(gaps,default=None),
                 terminal_gap_since_carb_delivery_ms=terminal-carb_deliveries[-1] if carb_deliveries else None,
                 depot_c_depletions=stock_depletions, depot_c_max_observed_empty_ms=max(empty_intervals,default=None),
                 workers_with_adult_cw=sum(w["carb_ug"] > 0 and w["water_ug"] > 0 for w in adults.values()),
                 workers_alive_7d=sum(w["terminal_age_ms"] >= 7*DAY for w in adults.values()),
                 workers_censored=sum(w["censored"] for w in adults.values()), larvae_fed_by_workers=len(larva_paid),
                 larvae_with_worker_protein_uptake=len(larva_uptake), worker_protein_assimilated_lower_bound_ug=sum(forced_worker_protein.values()),
                 **attempts)
    return world, adults.values(), trips, flows


def dump(path, records):
    if records:
        with path.open("x",encoding="utf-8",newline="") as output:
            columns = list(dict.fromkeys(k for row in records for k in row))
            writer = csv.DictWriter(output, columns, lineterminator="\n")
            writer.writeheader()
            writer.writerows(records)


def verify(archive, output, cases=()):
    with TemporaryDirectory(dir=output.parent if output.parent.is_dir() else None) as scratch:
        path=Path(scratch)/"nutrition.csv.gz"
        with gzip.open(path,"xt",encoding="utf-8",newline="") as stream:
            columns=("model","matrix","case","arm","population","group","care","profile","seed","status","process_wall_ms","exit_code",
                     "event","time_ms","kind","actor","recipient","stage","c","p","w","o")
            writer=csv.DictWriter(stream,columns,lineterminator="\n")
            writer.writeheader()
            verify_events(archive,output,cases,writer)
        if json.loads((archive/"run.json").read_text(encoding="utf-8"))["matrix"]!="closed":
            # Use a streamed copy so the evidence is independent of temporary-file placement.
            with path.open("rb") as source, (output/"nutrition.csv.gz").open("xb") as destination:
                while block:=source.read(1024*1024):
                    destination.write(block)


def verify_events(archive, output, cases, nutrition_writer):
    meta, completed = (json.loads((archive/name).read_text(encoding="utf-8")) for name in ("run.json", "completed.json"))
    model, matrix = meta.get("model", "r2"), meta["matrix"]
    universe = {c["case"]: (identity,c) for identity,c in environments(matrix)}
    expect = [name for name in universe if model not in SENSITIVITIES or name.endswith("-balanced")]
    check(completed["attempts"]==len(meta["cases"])==len(set(meta["cases"])), "attempt count differs from the frozen inputs")
    if not meta["selected_subset"]:
        check(meta["cases"] == expect, "frozen world coverage changed")
    check(set(meta["cases"]) == completed["statuses"].keys() and meta["arguments"][4:] == list(MODELS[model]), "input/model coverage mismatch")
    selected = set(cases) if cases else set(meta["cases"])
    check(selected <= set(meta["cases"]),"unknown representative case")
    check(not cases or matrix!="closed","closed-stock qualification requires its full denominator")
    all_worlds, workers, trips, census_rows, stage_rows, offspring = [], [], [], [], [], []
    checked_files = checked_facts = 0
    seen = set()
    for filename, digest in sorted(completed["archives"].items()):
        file = archive/filename
        check(sha(file)==digest, f"archive SHA-256 mismatch: {file}")
        with zipfile.ZipFile(file) as bundle:
            members = set(bundle.namelist())
            for name in sorted(x.split("/")[0] for x in members if x.endswith("/receipt.json")):
                check(name not in seen and name in completed["statuses"], f"unknown or duplicate world: {name}")
                seen.add(name)
                if name not in selected:
                    continue
                prefix = name + "/"
                receipt = json.loads(bundle.read(prefix+"receipt.json"))
                identity, case = universe[name]
                check(receipt["status"] == completed["statuses"][name] and receipt["identity"]==identity and
                      json.loads(bundle.read(prefix+"case.json"))==case, "receipt or case identity changed")
                blobs = {key: bundle.read(prefix+key) for key in receipt["artifacts"]}
                check({key for key in members if key.startswith(prefix)} == {prefix+"receipt.json",*(prefix+key for key in blobs)},
                      "unexpected files in the canonical archive")
                for key, blob in blobs.items():
                    check(receipt["artifacts"][key] == dict(bytes=len(blob),sha256=sha256(blob).hexdigest()), f"bad artifact checksum: {name}/{key}")
                checked_files += len(blobs)
                check(blobs["parameters.txt"]==input_bytes(identity,case), "changed resolved input")
                common = dict(model=model,matrix=matrix,case=name,arm=case.get("arm","ordinary").removeprefix("integrated-"),
                              population=case["population"],group=case["group"],care=int(case["care_enabled"]),
                              profile=case.get("profile_index"),seed=case["software_seed"],status=receipt["status"],
                              process_wall_ms=receipt["elapsed_ms"],exit_code=receipt["exit_code"])
                if receipt["status"] != "COMPLETE":
                    all_worlds.append(common | dict(complete=0))
                    continue
                raw, summary = blobs["facts.bin"], receipt["summary"]
                case = case | dict(early_access_mask=3, carbohydrate_yield_nj_per_ug=int(MODELS[model][1]) if MODELS[model] else 1_000_000)
                version = (7 if model.startswith("resupply") else 6 if model.startswith("uptake") else
                           3 if model=="r2" else 4 if len(MODELS[model])==2 else 5)
                measure, lives, paths, censuses = assess(case,summary,raw,blobs["cuts.csv"],blobs["individuals.csv"],version)
                checked_facts += measure["source_facts"]
                census_rows.extend(common | r for r in censuses)
                stage_rows.extend(common | r for r in lives)
                offspring.extend(common | r for r in paths)
                if matrix == "closed":
                    all_worlds.append(common | measure | dict(complete=0))
                    continue
                cuts, people = rows(blobs["cuts.csv"]), rows(blobs["individuals.csv"])
                snapshots = {d: [r for r in people if int(r["time_ms"]) == d*DAY] for d in (120,150)}
                source = verify_sources(raw,case,cuts)
                observed, histories, loads, meals = observe_chain(raw,case,int(summary["queen"]),paths,snapshots)
                workers.extend(common | r for r in histories)
                trips.extend(common | r for r in loads)
                nutrition_writer.writerows(common | r for r in meals)
                all_worlds.append(common | measure | observed | source | dict(
                    archive_file=filename, canonical_sha256=receipt["artifacts"]["facts.bin"]["sha256"],
                    **{k:summary[k] for k in ("advance_ms","peak_rss_bytes","midpoint_save_ms","midpoint_restore_ms","facts_bytes","frame_bytes")}))
    check(seen == completed["statuses"].keys(), "incomplete archive")
    output.mkdir(parents=True)
    for key, dataset in (("worlds",all_worlds),("workers",workers),("loaded_trips",trips),("censuses",census_rows),
                         ("stages",stage_rows),("offspring",offspring)):
        dump(output/f"{key}.csv",dataset)
    if matrix == "closed":
        evaluate(output,all_worlds,stage_rows,census_rows)
    result = dict(model=model, matrix=matrix, input_attempts=len(seen), audited_attempts=len(selected),
                  complete_worlds=sum(r["complete"] for r in all_worlds),
                  checked_files=checked_files, checked_facts=checked_facts, profile_pass={}, group_rows=[])
    for population, arm in sorted({(r["population"],r["arm"]) for r in all_worlds}):
        group = [r for r in all_worlds if (r["population"],r["arm"])==(population,arm)]
        result["group_rows"].append(dict(population=population,arm=arm,worlds=len(group),chain=sum(r["complete"] for r in group),
             first_delivery=sum(bool(r.get("first_delivery_ms")) for r in group), queen_uptake=sum(r.get("g_queen_uptake",0) for r in group),
             late_eclosion=sum(r.get("g_late_eclosion",0) for r in group), queen_150=sum(r.get("queen_alive_150",0) for r in group)))
        if matrix == "factorial" and arm == "balanced":
            result["profile_pass"][population] = {i:sum(r["complete"] for r in group if r["profile"]==i)
                                                  for i in sorted({r["profile"] for r in group})}
    write_json(output/"audit.json", result)
    print(model, matrix, "worlds",len(seen),"facts",checked_facts,"chains",result["complete_worlds"],"factorial",result["profile_pass"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--case",action="append",default=[])
    args = parser.parse_args()
    verify(args.archive, args.output,args.case)
