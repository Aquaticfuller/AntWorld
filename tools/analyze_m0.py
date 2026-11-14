"""Recompute MicroWorld cohort, material and work observations from native archives."""

import argparse
from collections import Counter
import csv
from hashlib import sha256
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from op0 import DAY
from op0.archive import file_hash, zip_inputs
from op0.codec import DEATHS, decode_fact
from op0.index import Catalog
from op0.query import ReadAPI


def require(predicate, message):
    if not predicate:
        raise ValueError(message)


def join_facts(archive):
    with zip_inputs(archive) as (initial, tip, _, facts, capture):
        case = capture["case"]
        queen = next(iter(initial["ants"]))
        totals = Counter()
        offspring, cohort, positions = {}, {}, {}
        apparent_stage = {}
        start, expected, last_time = None, 1, 0
        first_workers, soil_carrier = [], {}
        visited_surface, collected = set(), set()
        complete_deliveries, complete_soil = 0, 0
        checksum, prefix = sha256(), sha256()
        world = initial["world"].replace("-", "")
        identity = tuple(int(world[i:i+16],16) for i in (0,16))
        for head, raw in facts:
            ids, f = decode_fact(raw)
            require(f.id == expected and f.time >= last_time and ids == identity, "Fact sequence differs from its world")
            expected, last_time = expected+1, f.time
            checksum.update(head); checksum.update(raw)
            if f.id<=initial["cursor"]:
                prefix.update(head); prefix.update(raw)
            totals[f.kind] += 1
            if f.kind in (2,35,4,43):
                positions[f.actor] = f.position
            if f.kind == 35:
                if start is None:
                    start = f.time
                row = dict(id=f.actor, mother=f.related, egg_ms=f.time, egg_event=f.id, egg_position_m=f.position,
                           hatch_ms=None, pupation_ms=None, adult_ms=None, death_ms=None, death_cause=None,
                           first_contact_event=None, first_selection_event=None, first_started_event=None,
                           first_paid_event=None, first_paid_ms=None, first_protein_uptake_ms=None, first_water_uptake_ms=None,
                           maternal_lipid_ug=0, maternal_protein_ug=0, maternal_water_ug=0, absorbed_protein_ug=0,
                           absorbed_water_ug=0, other_received_protein_ug=0, other_received_water_ug=0,
                           maternal_feed_count=0, maternal_protein_feeds=0, energy_mobilizations=0, handling_interrupted=0,
                           feeding_steps=[], last_daily_observation=None, mother_last_daily=None)
                offspring[f.actor] = row
                apparent_stage[f.actor] = f.stage
                if f.time < start + DAY:
                    cohort[f.actor] = row
            if f.kind == 34 and f.outcome == 10:
                totals["space_deferred"] += 1
            if f.kind == 42:
                phase, act, target, _, _, known, *_ = f.observation
                if phase == 3 and act == 4 and known:
                    totals["arrangements"] += 1
                if target in offspring and apparent_stage[target]==1 and f.actor == queen:
                    row = offspring[target]
                    if phase == 0:
                        row["first_contact_event"] = row["first_contact_event"] or f.id
                    if act == 7 and phase in (1,2,4):
                        if phase==4:
                            row["handling_interrupted"] += 1
                        else:
                            field = "first_selection_event" if phase==1 else "first_started_event"
                            row[field] = row[field] or f.id
            if f.kind in (48,21) and f.related in offspring and apparent_stage[f.related]==1:
                row = offspring[f.related]
                row["feeding_steps"].append([f.id,f.time,f.actor,*f.mass,f.aux if f.kind==48 else 0])
                if f.kind==48:
                    row["first_paid_event"] = row["first_paid_event"] or f.id
                    if row["first_paid_ms"] is None:
                        row["first_paid_ms"] = f.time
                    row["maternal_feed_count"] += 1
                    row["maternal_protein_feeds"] += bool(f.mass[1])
                    row["maternal_lipid_ug"] += f.aux
                    row["maternal_protein_ug"] += f.mass[1]
                    row["maternal_water_ug"] += f.mass[2]
                else:
                    row["other_received_protein_ug"] += f.mass[1]
                    row["other_received_water_ug"] += f.mass[2]
            if f.actor in offspring:
                row = offspring[f.actor]
                if f.kind==7:
                    row[("egg_ms","hatch_ms","pupation_ms","adult_ms")[f.stage]] = f.time
                    apparent_stage[f.actor] = f.stage
                    if f.stage==3 and len(first_workers)<3:
                        first_workers.append((f.actor, f.time))
                if f.kind==8:
                    row["death_ms"], row["death_cause"] = f.time, DEATHS[f.payload]
                    apparent_stage[f.actor] = 4
                if f.kind==16 and apparent_stage[f.actor]==1:
                    row["absorbed_protein_ug"] += f.mass[1]
                    row["absorbed_water_ug"] += f.mass[2]
                    for field, value in (("first_protein_uptake_ms", f.mass[1]), ("first_water_uptake_ms", f.mass[2])):
                        if value and row[field] is None:
                            row[field] = f.time
                if f.kind==49 and apparent_stage[f.actor]==1:
                    row["energy_mobilizations"] += 1
            if f.kind==4 and f.position[1]>0:
                visited_surface.add(f.actor)
            if f.kind==5 and f.actor in visited_surface and sum(f.mass):
                collected.add(f.actor)
            if f.kind==12 and f.actor in collected and f.position[1]<0 and sum(f.mass):
                complete_deliveries += 1
                collected.discard(f.actor)
            if f.kind==23:
                soil_carrier[f.payload] = f.actor
            if f.kind==24 and soil_carrier.get(f.payload)==f.actor:
                complete_soil += 1
        require(expected-1 == tip["cursor"] and checksum.hexdigest()==capture["facts_expected"] and
                prefix.hexdigest()==capture["initial_prefix"], "Canonical bytes do not match archive and initial cut")
        queen_samples = {}
        for cut in capture["cuts"]:
            c = {key:int(cut[key]) for key in ("energy_input_nj","body_energy_nj","dissipated_nj","initial_q3","remaining_q3",
                 "carried_q3","deposited_q3")}
            require(all(cut[f"introduced_{key}"]==cut[f"accounted_{key}"] for key in "cpwo") and
                    c["energy_input_nj"]==c["body_energy_nj"]+c["dissipated_nj"] and
                    c["initial_q3"]==c["remaining_q3"]+c["carried_q3"]+c["deposited_q3"], "A recorded cut is unbalanced")
        fields = ("time_ms","cursor","energy_nj","hydration_ug","crop_w","crop_p","lipid_ug","mobile_protein_ug",
                  "tissue_protein_ug","dissipated_nj","lost_water_ug")
        for sample in capture["people"]:
            actor, at = int(sample["id"]), int(sample["time_ms"])
            values = {field:sample.get(field) for field in fields}
            if actor==queen:
                queen_samples[at] = values
            elif actor in cohort:
                row = cohort[actor]
                if row["death_ms"] is None or at < row["death_ms"]:
                    row["last_daily_observation"] = values
        for row in cohort.values():
            at = row["death_ms"] if row["death_ms"] is not None else tip["time_ms"]
            prior = [t for t in queen_samples if t<=at]
            row["mother_last_daily"] = queen_samples[max(prior)] if prior else None
            row["status"] = "DIED" if row["death_ms"] is not None else "RIGHT_CENSORED_AT_END"
        summary = dict(case=case["case"], physics=tip["physics"], world_id=tip["world"], facts=tip["cursor"],
            state_workers=sum(a["stage"]==3 and a["caste"]==0 for a in tip["ants"].values()),
            eggs=len(offspring), cohort_eggs=len(cohort), cohort_hatch=sum(r["hatch_ms"] is not None for r in cohort.values()),
            cohort_pupa=sum(r["pupation_ms"] is not None for r in cohort.values()),
            cohort_adult=sum(r["adult_ms"] is not None for r in cohort.values()),
            cohort_deaths=sum(r["death_ms"] is not None for r in cohort.values()),
            cohort_energy_deaths=sum(r["death_cause"]==DEATHS[1] for r in cohort.values()),
            cohort_water_deaths=sum(r["death_cause"]==DEATHS[2] for r in cohort.values()),
            cohort_hatched_without_maternal_feed=sum(r["hatch_ms"] is not None and not r["maternal_feed_count"] for r in cohort.values()),
            cohort_protein_uptake=sum(bool(r["absorbed_protein_ug"]) for r in cohort.values()),
            cohort_water_uptake=sum(bool(r["absorbed_water_ug"]) for r in cohort.values()),
            queen_living=tip["ants"][queen]["stage"]==3, first_workers=first_workers, arrangements=totals["arrangements"],
            brood_moves=totals[43], maternal_rations=totals[48], water_sips=totals[58], transfers=totals[21],
            excavation_drops=complete_soil, resource_trips=complete_deliveries, space_deferred=totals["space_deferred"],
            hatch_cues=totals[50], archive_sha256=file_hash(archive), canonical_sha256=checksum.hexdigest(), end_ms=tip["time_ms"],
            right_censored=sum(r["death_ms"] is None for r in cohort.values()))
        return summary, list(cohort.values())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archives", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--worker-windows", default=[], action="append", help="Index a selected case and derive 1- and 4-day windows.")
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--retry", type=Path, help="Use explicit retry receipts for failed cases from the same frozen panel.")
    args = parser.parse_args()
    require(not args.worker_windows or args.cache, "Worker queries need a disposable browse cache path")
    args.output.mkdir(parents=True, exist_ok=True)
    summaries, cohort, workers = [], {}, {}
    def entries(directory):
        return [json.loads(line) for line in (directory/"archives.jsonl").read_text(encoding="utf-8").splitlines()]
    manifest = entries(args.archives)
    replacements = {row["receipt"]["case"]:row for row in entries(args.retry)} if args.retry else {}
    require(set(replacements) <= {row["receipt"]["case"] for row in manifest if row["receipt"]["status"] != "COMPLETE"},
            "Retry collection may only supply earlier engineering failures")
    for entry in manifest:
        case = entry["receipt"]["case"]
        if case in replacements:
            original = file_hash(args.archives/entry["archive"])
            require(original==entry["sha256"], "Original failed capture changed")
            entry = replacements[case]
            path = args.retry/entry["archive"]
        else:
            path = args.archives/entry["archive"]
        require(file_hash(path)==entry["sha256"], f"Archive hash changed for {case}")
        if entry["receipt"]["status"]!="COMPLETE":
            summaries.append(dict(case=case,status=entry["receipt"]["status"]))
            continue
        summary, cohort[case] = join_facts(path)
        summary |= dict(status="COMPLETE", advance_ms=entry["receipt"]["summary"]["advance_ms"],
            peak_rss_bytes=entry["receipt"]["summary"]["peak_rss_bytes"], archive_bytes=path.stat().st_size)
        summaries.append(summary)
        if case in args.worker_windows:
            catalog = Catalog(args.cache)
            archive = catalog.register(path,expected=entry["sha256"])
            key = catalog.browse(archive)[0][0]["key"]
            api = ReadAPI(catalog)
            workers[case] = [api.dispatch(f"/api/v1/world/{key}/individual-window?id={actor}&begin_ms={start}"
                              f"&end_ms={min(summary['end_ms'],start+DAY*days)}")["data"]
                             for actor,start in summary["first_workers"] for days in (1,4)]
    for name, content in (("cohort-trajectories.json",cohort),("worker-windows.json",workers)):
        (args.output/name).write_text(json.dumps(content,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    fields = list(dict.fromkeys(field for row in summaries for field in row))
    with (args.output/"worlds.csv").open("w",encoding="utf-8",newline="") as out:
        writer = csv.DictWriter(out,fields,lineterminator="\n")
        writer.writeheader()
        writer.writerows(summaries)


if __name__=="__main__":
    main()
