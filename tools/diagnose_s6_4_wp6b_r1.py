"""Reconstruct funded larval paths from canonical F1 archives without rerunning choices."""

import argparse
from collections import Counter, defaultdict
from contextlib import ExitStack, contextmanager
import csv
import gzip
from hashlib import sha256
import io
import json
from pathlib import Path
from statistics import median
import zipfile

from analyze_s6_4_wp6b import (BIRTH, DIED, F_CONVERT, F_EGG, F_RATION, F_SEED, FEED,
                              GIFT, OBSERVATION, STAGE, UPTAKE, check, facts, rows)
from run_s6_4_wp6b import sha, write_json


CARE_TICK, CARE_WAKE = 41, 19
MILESTONES = ("opportunity", "selected", "feed_selected", "feed_started", "first_meal", "first_uptake", "tissue_met")


@contextmanager
def sheet(path, columns):
    with path.open("xb") as raw, gzip.GzipFile(fileobj=raw, filename="", mtime=0) as compressed:
        with io.TextIOWrapper(compressed, encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, columns.split(), lineterminator="\n")
            writer.writeheader()
            yield writer.writerow


def gini(values):
    values = sorted(values)
    return (sum((2*i - len(values) - 1)*v for i, v in enumerate(values, 1)) / (len(values)*sum(values))
            if sum(values) else None)


def read_case(case, summary, raw, cuts, write):
    name, queen, p = case["case"], int(summary["queen"]), case["parameters"]
    larvae, wakes = {}, {}
    selection_wake = {}
    census = {(int(row["id"]), int(row["time_ms"])): row for row in rows(cuts)}
    daily = [time for ant, time in census if ant == queen]
    alive_larvae = set()
    maternal_p = maternal_lipid = 0
    queen_death = None
    counts = Counter()
    source_meals = {}

    def mark(record, endpoint, time, event):
        record["first"].setdefault(endpoint, (time, event))

    for event, time, source, kind, actor, payload, value, stage, outcome, mass, obs in facts(raw):
        if kind == F_SEED:
            maternal_p, maternal_lipid = mass[1], payload
        elif kind == BIRTH:
            check(payload == queen and actor not in larvae, "duplicate or nonmaternal birth")
            larvae[actor] = dict(birth_ms=time, birth_event=event, hatch_ms=None, hatch_event=None,
                                 exit_ms=None, exit_event=None, outcome="RIGHT_CENSORED", cause=None,
                                 first={}, meals=[], protein_tissue=mass[1], crop_p=0, worker_p=0,
                                 opportunities=[], selections=[], failures=0, adult_ms=None)
            counts["births"] += 1
        elif kind == F_EGG:
            maternal_p -= p["egg_protein"]
            maternal_lipid -= value
        elif kind == F_CONVERT and actor == queen:
            maternal_lipid -= payload
        elif kind == STAGE and actor in larvae:
            target = larvae[actor]
            if stage == 1:
                target.update(hatch_ms=time, hatch_event=event)
                alive_larvae.add(actor)
            elif stage == 2:
                target.update(exit_ms=time, exit_event=event, outcome="PUPATED")
                alive_larvae.remove(actor)
            elif stage == 3:
                target["adult_ms"] = time
        elif kind == DIED:
            if actor == queen:
                queen_death = time
            if actor in larvae and larvae[actor]["exit_ms"] is None:
                larvae[actor].update(exit_ms=time, exit_event=event, outcome="DIED", cause=payload)
                alive_larvae.discard(actor)
        elif kind == CARE_TICK and actor == queen and payload == CARE_WAKE:
            wakes[source] = dict(case=name, wake=source, tick_event=event, time_ms=time, annotation=value,
                                 living_larvae=len(alive_larvae), maternal_mobile_p_ug=maternal_p,
                                 maternal_lipid_ug=maternal_lipid, visible=[], eligible_p=[], target=None,
                                 selected_act=None, selected_event=None)
        elif kind == F_RATION:
            check(actor == queen and payload in alive_larvae and source not in source_meals, "ration outside larval care")
            target = larvae[payload]
            target["crop_p"] += mass[1]
            maternal_p -= mass[1]
            maternal_lipid -= value
            dose = dict(case=name, ant=payload, meal=len(target["meals"])+1, event=event, time_ms=time,
                        source=source, lipid_ug=value, protein_ug=mass[1], water_ug=mass[2],
                        bout=None, completed_event=None, next_positive_protein_uptake_event=None,
                        next_positive_protein_uptake_ms=None, next_seen_ms=None, next_selected_ms=None)
            target["meals"].append(dose)
            source_meals[source] = dose
            mark(target, "first_meal", time, event)
        elif kind == GIFT and payload in alive_larvae:
            larvae[payload]["worker_p"] += mass[1]
            larvae[payload]["crop_p"] += mass[1]
        elif kind == UPTAKE and actor in alive_larvae and mass[1]:
            target = larvae[actor]
            target["protein_tissue"] += mass[1]
            target["crop_p"] -= mass[1]
            check(target["crop_p"] >= 0, "larval protein uptake has no recorded intake")
            mark(target, "first_uptake", time, event)
            if target["protein_tissue"] >= p["larval_tissue_target"]:
                mark(target, "tissue_met", time, event)
            for dose in target["meals"]:
                if dose["protein_ug"] and dose["next_positive_protein_uptake_event"] is None:
                    dose["next_positive_protein_uptake_event"] = event
                    dose["next_positive_protein_uptake_ms"] = time
        elif kind == OBSERVATION and actor == queen:
            phase, act, ant, bout, *_ = obs
            target = larvae.get(ant)
            if source in wakes and phase == 0 and ant in alive_larvae:
                wake = wakes[source]
                wake["visible"].append(ant)
                if maternal_p and target["protein_tissue"] + target["crop_p"] < p["larval_tissue_target"]:
                    wake["eligible_p"].append(ant)
                mark(target, "opportunity", time, event)
                target["opportunities"].append(time)
                for dose in target["meals"]:
                    if dose["next_seen_ms"] is None:
                        dose["next_seen_ms"] = time
            elif source in wakes and phase == 1:
                wakes[source].update(target=ant, selected_act=act, selected_event=event)
                selection_wake[bout] = source
                if ant in alive_larvae:
                    target["selections"].append(time)
                    mark(target, "selected", time, event)
                    if act == FEED:
                        mark(target, "feed_selected", time, event)
                        counts["feed_selected"] += 1
                    for dose in target["meals"]:
                        if dose["next_selected_ms"] is None:
                            dose["next_selected_ms"] = time
            elif target and act == FEED:
                if phase == 2:
                    mark(target, "feed_started", time, event)
                    counts["feed_started"] += 1
                elif phase == 3:
                    dose = source_meals.get(source)
                    check(dose and dose["ant"] == ant and bout in selection_wake, "meal without observed bout")
                    dose.update(bout=bout, completed_event=event)
                    counts["feed_completed"] += 1
                elif phase == 4:
                    target["failures"] += 1
                    counts["feed_interrupted"] += 1
    check(all(dose["completed_event"] for dose in source_meals.values()), "unobserved completion")
    for wake in wakes.values():
        check(len(set(wake["visible"])) == len(wake["visible"]), "duplicate same-wake opportunity")
        counts["wakes"] += 1
        counts["wakes_with_contact"] += bool(wake["visible"])
        counts["visible_opportunities"] += len(wake["visible"])
        counts["protein_deficit_stock_opportunities"] += len(wake["eligible_p"])
        counts["selected_contact_larva"] += wake["target"] in wake["visible"]
        counts["selected_deficit_stock_larva"] += wake["target"] in wake["eligible_p"]
        for key in ("visible", "eligible_p"):
            wake[key] = " ".join(map(str, wake[key]))
        write["wakes"](wake)
    cut_q = census[(queen, daily[-1])]
    masses, gaps, windows, retarget = [], [], [], []
    for ant, target in larvae.items():
        if target["hatch_ms"] is None:
            continue
        exposure_end = target["exit_ms"] if target["exit_ms"] is not None else case["horizon_ms"]
        repeat_end = min(exposure_end, queen_death) if queen_death is not None else exposure_end
        doses = [dose for dose in target["meals"] if dose["protein_ug"]]
        length = len(doses)
        masses.append(sum(dose["protein_ug"] for dose in doses))
        counts[f"doses_{min(length, 6)}"] += 1
        counts["tissue_met"] += "tissue_met" in target["first"]
        counts["hatch"] += 1
        counts["pupa"] += target["outcome"] == "PUPATED"
        counts["eclosed"] += target["adult_ms"] is not None
        counts[f"larval_{target['outcome'].lower()}"] += 1
        counts[f"larval_death_cause_{target['cause']}"] += target["outcome"] == "DIED"
        for dose in target["meals"]:
            if dose["next_seen_ms"] is not None:
                counts["meals_seen_again"] += 1
            if dose["next_selected_ms"] is not None:
                counts["meals_selected_again"] += 1
                retarget.append(dose["next_selected_ms"]-dose["time_ms"])
            write["meals"](dict(**dose, follow_end_ms=repeat_end))
        gaps.extend(b["time_ms"]-a["time_ms"] for a, b in zip(doses, doses[1:]))
        remaining = exposure_end-doses[3]["time_ms"] if length >= 4 else None
        if length == 4 and target["outcome"] == "DIED":
            windows.append(remaining)
        final = census[(ant, daily[-1])]
        write["larvae"](dict(case=name, ant=ant, mother=queen, birth_ms=target["birth_ms"], birth_event=target["birth_event"],
                             hatch_ms=target["hatch_ms"], hatch_event=target["hatch_event"], end_ms=exposure_end,
                             end_event=target["exit_event"], outcome=target["outcome"], death_cause=target["cause"],
                             adult_ms=target["adult_ms"], contact_wakes=len(target["opportunities"]),
                             selected_wakes=len(target["selections"]), total_meals=len(target["meals"]),
                             effective_protein_meals=length, maternal_protein_ug=masses[-1], worker_protein_ug=target["worker_p"],
                             observed_tissue_ug=target["protein_tissue"], feed_interrupted=target["failures"],
                             fourth_to_endpoint_ms=remaining, fourth_meal_ms=doses[3]["time_ms"] if length >= 4 else None,
                             last_meal_to_endpoint_ms=exposure_end-doses[-1]["time_ms"] if length else None,
                             final_energy_nj=final["energy_nj"], final_water_ug=final["hydration_ug"],
                             **{f"{key}_{unit}": target["first"].get(key, (None, None))[i]
                                for key in MILESTONES for i, unit in enumerate(("ms", "event"))}))
    check(counts["feed_completed"] == len(source_meals), "feeding denominator differs from the archive")
    return dict(case=name, group=case["group"], population=case["population"],
                care=int(case["care_enabled"]), seed=case["software_seed"],
                arm=case.get("arm", "ordinary"), first_egg_ms=min((l["birth_ms"] for l in larvae.values()), default=None),
                queen_death_ms=queen_death, queen_terminal_lipid_ug=cut_q["lipid_ug"],
                queen_terminal_p_ug=cut_q["mobile_protein_ug"], queen_terminal_water_ug=cut_q["hydration_ug"],
                queen_terminal_energy_nj=cut_q["energy_nj"], protein_gini_including_zeros=gini(masses),
                median_interdose_ms=median(gaps) if gaps else None,
                median_retarget_ms=median(retarget) if retarget else None,
                median_fourth_to_death_ms=median(windows) if windows else None, **counts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    index = json.loads((args.archive / "completed.json").read_text(encoding="utf-8"))
    args.output.mkdir(parents=True)
    fields = dict(
        wakes="case wake tick_event time_ms annotation living_larvae maternal_mobile_p_ug maternal_lipid_ug visible eligible_p target selected_act selected_event",
        meals="case ant meal event time_ms source lipid_ug protein_ug water_ug bout completed_event next_positive_protein_uptake_event next_positive_protein_uptake_ms next_seen_ms next_selected_ms follow_end_ms",
        larvae=("case ant mother birth_ms birth_event hatch_ms hatch_event end_ms end_event outcome death_cause adult_ms contact_wakes selected_wakes total_meals effective_protein_meals maternal_protein_ug worker_protein_ug observed_tissue_ug feed_interrupted fourth_to_endpoint_ms fourth_meal_ms last_meal_to_endpoint_ms final_energy_nj final_water_ug " +
                " ".join(f"{key}_{unit}" for key in MILESTONES for unit in ("ms", "event"))))
    case_rows, seen = [], set()
    with ExitStack() as stack:
        writers = {key: stack.enter_context(sheet(args.output / f"{key}.csv.gz", value)) for key, value in fields.items()}
        for filename, digest in index["archives"].items():
            path = args.archive / filename
            check(sha(path) == digest, f"archive digest changed: {filename}")
            with zipfile.ZipFile(path) as archive:
                for item in (name for name in archive.namelist() if name.endswith("/receipt.json")):
                    record = json.loads(archive.read(item))
                    name = record["case"]
                    check(name not in seen and record["status"] == index["statuses"][name], "archive case mismatch")
                    seen.add(name)
                    if record["status"] != "COMPLETE":
                        continue
                    data = {}
                    for member in ("case.json", "facts.bin", "individuals.csv"):
                        data[member] = archive.read(f"{name}/{member}")
                        check(sha256(data[member]).hexdigest() == record["artifacts"][member]["sha256"],
                              f"diagnosis input digest differs: {name}/{member}")
                    case_rows.append(read_case(json.loads(data["case.json"]), record["summary"],
                                               data["facts.bin"], data["individuals.csv"], writers))
            print(f"{len(seen)}/{index['attempts']} {filename}", flush=True)
    check(seen == set(index["statuses"]) and len(seen) == index["attempts"], "incomplete baseline")
    columns = list(dict.fromkeys(k for row in case_rows for k in row))
    with (args.output / "cases.csv").open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(case_rows)
    write_json(args.output / "receipt.json", dict(archive_index_sha256=sha(args.archive / "completed.json"),
                                                  attempted=len(seen), complete=len(case_rows),
                                                  outputs={p.name: sha(p) for p in sorted(args.output.iterdir())}))


if __name__ == "__main__":
    main()
