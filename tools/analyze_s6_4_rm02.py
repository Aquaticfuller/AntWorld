"""Audit RM-02 sidecar digests and derive the frozen simulation diagnostics."""

import argparse
from bisect import bisect_right
from collections import Counter, defaultdict
from contextlib import ExitStack
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import random
import shutil
import statistics
from tempfile import TemporaryDirectory

from read_s6_4_rm02_sidecar import (
    CASTES, COMPONENTS, DEATHS, PROGRAMS, STAGES, decode_fact, numbers, open_sidecar, require,
)
from run_s6_4_rm02 import PROTOCOL, frozen_cases, sha256


DAY = 86_400_000
ZERO = (0, 0, 0, 0)
FACT, CUT, INFERRED, UNKNOWN = "COMMITTED_FACT", "CUT_SNAPSHOT", "RECONSTRUCTED", "UNOBSERVED"
TABLES = ("runs", "horizons", "body_cuts", "queen_timeseries", "gifts", "uptake", "requests",
          "opportunity_coverage", "queen_death_stocks", "queen_gift_followup", "paired_contrasts")
PACK = {"body_cuts", "gifts", "uptake", "opportunity_coverage"}


class Output:
    def __init__(self, folder, stack):
        self.folder = folder
        self.stack = stack
        self.writers = {}
        self.counts = Counter()

    def row(self, table, row):
        if table not in self.writers:
            base = self.folder / (table + ".csv")
            if table in PACK:
                data = self.stack.enter_context(base.with_suffix(".csv.gz").open("xb"))
                compressed = gzip.GzipFile(fileobj=data, mode="wb", filename="", mtime=0, compresslevel=6)
                stream = self.stack.enter_context(io.TextIOWrapper(compressed, encoding="utf-8", newline=""))
            else:
                stream = self.stack.enter_context(base.open("x", encoding="utf-8", newline=""))
            writer = self.writers[table] = csv.DictWriter(stream, list(row), lineterminator="\n")
            writer.writeheader()
        self.writers[table].writerow(row)
        self.counts[table] += 1


def mass(prefix, values):
    return {f"{prefix}_{component}_ug": value for component, value in zip(COMPONENTS, values)}


def state_record(data):
    values = numbers(data)
    entity, ant, physiology = values[:3]
    require(ant in (0, 1) and physiology in (0, 1) and len(values) == 3 + 11 * ant + 20 * physiology,
            "invalid focal-state record")
    if not ant or not physiology:
        return entity, {}
    _, born, stage, caste, _, _, _, *cargo = values[3:14]
    crop = values[14:18]
    mother, energy, water, tissue, oxidized, lost, dissipated, exported, program, death, next_abs, progress, \
        phys_sched, behavior_sched, decisions, yield_nj_ug = values[18:]
    return entity, dict(stage=STAGES[stage], caste=CASTES[caste], born_ms=born, mother=mother,
                        energy_nj=energy, body_water_ug=water, tissue_protein_ug=tissue,
                        oxidized_carb_ug=oxidized, water_lost_ug=lost, dissipated_nj=dissipated,
                        exported_nj=exported, program=PROGRAMS[program], death_cause=DEATHS[death],
                        next_absorption_ms=next_abs, stage_progress_ms=progress, physiology_schedule=phys_sched,
                        behavior_schedule=behavior_sched, decision_count=decisions, yield_nj_per_ug=yield_nj_ug,
                        **mass("crop", crop), **mass("cargo", cargo))


def ledger_record(data):
    values = numbers(data)
    require(len(values) == 34 and values[:4] == values[4:8] and values[28] == values[29] + values[30],
            "invalid or nonconserved nutrition ledger")
    labels = ("introduced", "accounted", "colony_crop", "external_available", "colony_carried", "nest_stored")
    output = {}
    for index, label in enumerate(labels):
        output.update(mass(label, values[4 * index:4 * index + 4]))
    output.update(zip(("body_water_ug", "tissue_protein_ug", "oxidized_carb_ug", "water_lost_ug",
                       "energy_input_nj", "energy_body_nj", "energy_dissipated_nj", "physiology_count",
                       "living", "individuals"), values[24:]))
    return output


class Trace:
    def __init__(self, case, config, manifest, output):
        self.case = case
        self.key = dict(case=case["case"], world_id=manifest["world_id"], workers=case["workers"],
                        arm=case["arm"], seed=case["seed"])
        self.config = config
        self.meta = manifest
        self.output = output
        self.queen = 0
        self.caste = {}
        self.stage = {}
        self.program = {}
        self.crop = {}
        self.net = Counter()
        self.coverage = Counter()
        self.gifts_to_queen = []
        self.queen_pulses = defaultdict(list)
        self.death = None
        self.pending = {}
        self.resolution = {}
        self.last_pending = set()
        self.last_fact = 0
        self.last_event_time = 0
        self.previous = None
        self.death_inventory_written = False
        self.damaged = bool(manifest["origin"])

    def write(self, table, **row):
        self.output.row(table, self.key | row)

    def crop_change(self, entity, values, sign):
        before = self.crop.get(entity) if not self.damaged else None
        if before is None:
            return {}, {}
        after = tuple(old + sign * delta for old, delta in zip(before, values))
        require(min(after) >= 0, f"{self.key['case']} crop underflow at fact {self.last_fact}")
        self.crop[entity] = after
        return mass("crop_before", before), mass("crop_after", after)

    def role(self, entity):
        if self.stage.get(entity) == 1:
            return "larva"
        return self.caste.get(entity, "worker" if self.case["mode"] == "dense" else UNKNOWN)

    def take_fact(self, fact):
        entity, payload, kind, values = fact.actor, fact.payload, fact.kind, fact.mass
        self.net[kind] += 1
        if kind in ("AntSeeded", "StageChanged", "AntBorn", "AntDied"):
            prior_stage = self.stage.get(entity)
            self.stage[entity] = fact.stage
            if kind == "AntBorn":
                self.caste[entity] = "worker"
                self.crop[entity] = ZERO
                self.crop_change(payload, (0, values[1], 0, 0), -1)
            if kind == "StageChanged":
                self.net[f"became_{STAGES[fact.stage]}"] += 1
            if kind == "AntDied":
                self.net[f"death_{DEATHS[payload]}"] += 1
                if prior_stage is not None:
                    self.net[f"died_as_{STAGES[prior_stage]}"] += 1
                if entity == self.queen:
                    self.death = (fact.time, fact.event, DEATHS[payload])
        if kind == "BehaviorChanged":
            self.program[entity] = PROGRAMS[payload]
            self.net[f"program_{PROGRAMS[payload]}"] += 1
        if kind in ("NutritionDecision", "AutonomyDecision"):
            self.net[kind + "_candidates_examined"] += fact.auxiliary
            self.net[kind + "_zero_examined"] += fact.auxiliary == 0
        if kind == "BiologicalObservation":
            phase, act = fact.care[:2]
            if phase == 0:
                self.net["typed_opportunities"] += 1
            elif phase == 1 and act in (7, 12):
                self.net["typed_gift_choices"] += 1
            elif phase == 1 and act == 0:
                self.net["typed_inactive_choices"] += 1
        if kind == "PhysiologyEnabled":
            self.crop[entity] = values
        if kind in ("NestIngested", "CargoIngested"):
            self.crop_change(entity, values, 1)
        if kind == "ProteinRecycled":
            self.crop_change(entity, values, -1)
        if kind in ("FoodCollected", "FoodDelivered", "NestIngested", "CargoIngested", "ProteinRecycled"):
            for component, amount in zip(COMPONENTS, values):
                self.net[f"{kind}_{component}_ug"] += amount
        if fact.source and kind in ("ActionRejected", "NutritionTransferred") and self.meta["pending"]:
            self.resolution[fact.source] = fact
        if kind == "NutritionTransferred":
            require(sum(values) > 0 and fact.outcome in ("Partial", "Success"), "invalid positive gift fact")
            target_before, target_after = self.crop_change(payload, values, 1)
            self.crop_change(entity, values, -1)
            route = f"{self.role(entity)}_to_{self.role(payload)}"
            self.net[route] += 1
            self.net["partial_gifts"] += fact.outcome == "Partial"
            for component, amount in zip(COMPONENTS, values):
                self.net[f"{route}_{component}_ug"] += amount
            self.write("gifts", sim_ms=fact.time, event_id=fact.event, schedule_id=fact.source, donor=entity,
                       recipient=payload, route=route, donor_program=self.program.get(entity, UNKNOWN),
                       outcome=fact.outcome, origin=FACT, crop_origin=INFERRED if target_before else UNKNOWN,
                       **mass("dose", values), **(target_before or mass("crop_before", ("",) * 4)),
                       **(target_after or mass("crop_after", ("",) * 4)))
            if payload == self.queen:
                self.gifts_to_queen.append(fact)
        if kind == "PhysiologyUpdated":
            before, after = self.crop_change(entity, values, -1)
            positive = sum(values) > 0
            self.net["positive_pulses" if positive else "zero_pulses"] += 1
            if entity == self.queen:
                for name, value in zip(COMPONENTS, values):
                    self.net[f"queen_uptake_{name}_ug"] += value
                    if value:
                        self.queen_pulses[name].append((fact.event, fact.time))
                if positive:
                    self.queen_pulses["any"].append((fact.event, fact.time))
            self.write("uptake", sim_ms=fact.time, event_id=fact.event, schedule_id=fact.source, entity=entity,
                       stage=STAGES[fact.stage], role=self.role(entity), origin=FACT,
                       status="POSITIVE_PULSE" if positive else "ZERO_PULSE",
                       crop_origin=INFERRED if before else UNKNOWN, **mass("uptake", values),
                       **(before or mass("crop_before", ("",) * 4)), **(after or mass("crop_after", ("",) * 4)),
                       exact_body_before_after=UNKNOWN)

    def cut(self, cut):
        payload = cut["payload"]
        at, seq = cut["time"], cut["seq"]
        if cut["dropped"]:
            self.damaged = True
        states = dict(state_record(data) for tag, data in payload if tag == 2)
        for entity, s in states.items():
            if s:
                self.caste[entity] = s["caste"]
                if s["caste"] == "queen":
                    self.queen = entity
        for tag, data in payload:
            if tag != 1:
                continue
            fact = decode_fact(data, self.meta["world"])
            require(max(self.last_fact, cut["start"]) < fact.event <= cut["cursor"]
                    and self.last_event_time <= fact.time <= at, "fact order outside its cut")
            self.last_fact, self.last_event_time = fact.event, fact.time
            self.take_fact(fact)
        ledgers = [ledger_record(data) for tag, data in payload if tag == 3]
        require(len(ledgers) <= 1 and (ledgers or self.damaged), "missing ledger cut")
        ledger = ledgers[0] if ledgers else {}
        requests = [numbers(data) for tag, data in payload if tag == 4]
        neighbors = [numbers(data) for tag, data in payload if tag == 5]
        require(all(len(r) == 7 for r in requests) and all(len(n) == 4 for n in neighbors), "invalid opportunity row")
        self.coverage[f"pending_status_{cut['pending']}"] += 1
        self.coverage[f"neighbor_status_{cut['neighbors']}"] += 1
        self.coverage.update(dict(cuts=1, examined=cut["examined"], scoped_facts=cut["selected"], lost=cut["dropped"],
                                  records=cut["records"], raw_bytes=cut["raw_bytes"], stored_bytes=cut["packed_bytes"]))
        self.last_pending = set()
        for scheduled, donor, target, dose, issued, due, position_revision in requests:
            self.last_pending.add(scheduled)
            row = (donor, target, dose, issued, due, position_revision)
            if scheduled not in self.pending:
                self.pending[scheduled] = [row, at, at, 0]
            record = self.pending[scheduled]
            require(record[0] == row, "pending request changed identity")
            record[2] = at
            record[3] += 1
        if self.meta["pending"] or self.meta["neighbor"]:
            self.write("opportunity_coverage", sim_ms=at, as_of_event=cut["cursor"], pending_status=cut["pending"],
                       pending_trophallaxis=len(requests), geometry_status=cut["neighbors"],
                       focal=self.meta["neighbor"], same_colony_geometric_neighbors=len(neighbors),
                       geometric_workers=sum(n[3] == 0 and n[2] == 3 for n in neighbors),
                       geometric_larvae=sum(n[2] == 1 for n in neighbors), origin=CUT)
        for entity, s in states.items():
            if not s:
                continue
            self.stage[entity] = STAGES.index(s["stage"])
            self.program[entity] = s["program"]
            crop = tuple(s[f"crop_{part}_ug"] for part in COMPONENTS)
            if entity in self.crop and not self.damaged:
                require(self.crop[entity] == crop, f"{self.key['case']} crop reconciliation at cut {seq} entity {entity}")
                self.coverage["crop_checks"] += 1
            self.crop[entity] = crop
            self.write("body_cuts", sim_ms=at, as_of_event=cut["cursor"], revision=cut["revision"], entity=entity,
                       origin=CUT, **s)
        if self.queen and self.queen in states and states[self.queen]:
            queen = states[self.queen]
            self.write("queen_timeseries", sim_ms=at, as_of_event=cut["cursor"], entity=self.queen, origin=CUT,
                       positive_gifts=self.net["worker_to_queen"],
                       received_carb_ug=self.net["worker_to_queen_carb_ug"],
                       received_protein_ug=self.net["worker_to_queen_protein_ug"],
                       received_water_ug=self.net["worker_to_queen_water_ug"],
                       absorbed_carb_ug=self.net["queen_uptake_carb_ug"], eggs_laid=self.net["AntBorn"],
                       eclosed=self.net["became_adult"], **queen)
            if self.death and not self.death_inventory_written and self.previous:
                earlier_at, earlier_cursor, earlier_ledger = self.previous
                death_at, death_fact, cause = self.death
                self.write("queen_death_stocks", death_ms=death_at, death_event_id=death_fact, death_cause=cause,
                           prior_cut_ms=earlier_at, prior_cursor=earlier_cursor, lag_ms=death_at-earlier_at,
                           next_cut_ms=at, next_cursor=cut["cursor"], next_cut_lag_ms=at-death_at, origin=CUT,
                           queen_dead_energy_nj=queen["energy_nj"], queen_dead_water_ug=queen["body_water_ug"],
                           **{f"queen_dead_{k}": v for k, v in queen.items() if k.startswith("crop_")},
                           **{f"prior_{k}": v for k, v in earlier_ledger.items()},
                           **{f"next_{k}": v for k, v in ledger.items()})
                self.death_inventory_written = True
            if self.case["mode"] == "ecology" and at in (90 * DAY, int(self.config["horizon_ms"])):
                self.horizon(at, queen, ledger, cut)
        self.previous = (at, cut["cursor"], ledger)

    def horizon(self, at, queen, ledger, cut):
        row = dict(sim_ms=at, as_of_event=cut["cursor"], queen=self.queen, queen_alive=int(queen["stage"] != "dead"),
                   observed_death_ms=self.death[0] if self.death else "",
                   death_cause=self.death[2] if self.death else "RIGHT_CENSORED",
                   queen_days_alive=(self.death[0] if self.death else at) / DAY,
                   queen_energy_nj=queen["energy_nj"], queen_water_ug=queen["body_water_ug"],
                   queen_crop_carb_ug=queen["crop_carb_ug"], queen_crop_protein_ug=queen["crop_protein_ug"],
                   events=cut["cursor"], eggs=self.net["AntBorn"], hatches=self.net["became_larva"],
                   pupae=self.net["became_pupa"], eclosed=self.net["became_adult"], larval_deaths=self.net["died_as_larva"],
                   partial_gifts=self.net["partial_gifts"], zero_pulses=self.net["zero_pulses"],
                   nutrition_decisions=self.net["NutritionDecision"],
                   nutrition_examined=self.net["NutritionDecision_candidates_examined"],
                   nutrition_zero_examined=self.net["NutritionDecision_zero_examined"],
                   foraging_switches=self.net["program_Forage"], nurse_switches=self.net["program_Nurse"],
                   **{f"queen_uptake_{part}_ug": self.net[f"queen_uptake_{part}_ug"] for part in COMPONENTS})
        for route in ("worker_to_worker", "worker_to_queen", "worker_to_larva"):
            row[f"{route}_gifts"] = self.net[route]
            row.update({f"{route}_{part}_ug": self.net[f"{route}_{part}_ug"] for part in COMPONENTS})
        self.write("horizons", **row, **ledger)

    def finish(self, horizon):
        for scheduled, (p, first, last, scans) in sorted(self.pending.items()):
            donor, target, dose, issue, due, posrev = p
            fact = self.resolution.get(scheduled)
            require(not fact or (fact.actor == donor and (fact.kind != "NutritionTransferred" or fact.payload == target)),
                    "scheduled gift resolved with a different identity")
            status = ("POSITIVE" if fact.kind == "NutritionTransferred" else "ZERO_COMMITTED_REJECTION") if fact else (
                "RIGHT_CENSORED" if scheduled in self.last_pending and due > horizon else UNKNOWN)
            self.coverage[f"request_{status}"] += 1
            self.write("requests", schedule_id=scheduled, donor=donor, recipient=target, requested_total_ug=dose,
                       issue_ms=issue, due_ms=due, position_revision=posrev, first_cut_ms=first, last_cut_ms=last,
                       cut_count=scans, selected_origin=CUT, result_origin=FACT if fact else CUT if
                       status == "RIGHT_CENSORED" else UNKNOWN, status=status, event_id=fact.event if fact else "",
                       actual_ms=fact.time if fact else "", outcome=fact.outcome if fact else "",
                       **mass("actual", fact.mass if fact else ("",) * 4))
        for gift in self.gifts_to_queen:
            for label in ("any", "carb", "water"):
                if label != "any" and not gift.mass[COMPONENTS.index(label)]:
                    continue
                pulses = self.queen_pulses[label]
                index = bisect_right(pulses, (gift.event, gift.time))
                found = pulses[index] if index < len(pulses) else None
                status = ("NEXT_POSITIVE_PULSE" if found else "COMPETING_DEATH" if self.death
                          else "RIGHT_CENSORED") if not self.damaged else UNKNOWN
                end = found[1] if found else self.death[0] if self.death else horizon
                self.write("queen_gift_followup", gift_event_id=gift.event, gift_ms=gift.time, queen=self.queen,
                           donor=gift.actor, component=label, end_event_id=found[0] if found else
                           self.death[1] if self.death else "", end_ms=end, elapsed_ms=end-gift.time,
                           status=status, origin=INFERRED, causal_bolus_assignment=UNKNOWN)


def get_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def get_row(path):
    with path.open(encoding="utf-8", newline="") as stream:
        row, = csv.DictReader(stream)
    return row


def copy_verified(folder, receipt, temporary):
    require(all(Path(a["path"]).name == a["path"] for a in receipt["artifacts"].values()), "invalid artifact path")
    for name, item in receipt["artifacts"].items():
        path = folder / item["path"]
        require(path.stat().st_size == item["archived_bytes"] and sha256(path) == item["archived_sha256"],
                f"artifact digest mismatch: {path}")
        if path.suffix != ".gz":
            require(item["sha256"] == item["archived_sha256"] and item["bytes"] == item["archived_bytes"],
                    "raw artifact receipt differs")
            continue
        with gzip.open(path, "rb") as source:
            if name == "observer.sqlite":
                with temporary.open("wb") as out:
                    shutil.copyfileobj(source, out)
                require(temporary.stat().st_size == item["bytes"] and sha256(temporary) == item["sha256"],
                        "restored sidecar differs")
            else:
                require(hashlib.file_digest(source, "sha256").hexdigest() == item["sha256"], "checkpoint digest differs")


def analyse_case(root, case, code, temporary, output):
    folder = root / "raw" / case["case"]
    receipt = get_json(folder / "receipt.json")
    require(all(receipt[k] == v for k, v in case.items()) and receipt["exit_code"] == code, "case manifest differs")
    copy_verified(folder, receipt, temporary)
    summary = receipt["summary"]
    status = "INCOMPLETE"
    coverage, facts = Counter(), Counter()
    if "observer.sqlite" in receipt["artifacts"]:
        config = get_row(folder / "configuration.csv")
        require(config["initial_sha256"] == receipt["artifacts"]["initial.chk"]["sha256"], "initial identity differs")
        with open_sidecar(temporary) as (manifest, cuts):
            require(manifest["world_id"] == config["world_id"] and manifest["seed"] == case["seed"]
                    and manifest["lineage"] == case["case"] and not manifest["origin"], "case scope differs")
            trace = Trace(case, config, manifest, output)
            tail = None
            for cut in cuts:
                trace.cut(cut)
                tail = cut
            if tail:
                trace.finish(tail["time"])
                coverage, facts = trace.coverage, trace.net
                if not code:
                    require(summary == get_row(folder / "summary.csv") and summary["status"] == "ENGINEERING_PASS"
                            and summary["observer_complete"] == summary["rejoined"] == summary["exact_off"] == "1"
                            and tail["cursor"] == int(summary["events"]) and tail["time"] == int(config["horizon_ms"])
                            and coverage["examined"] == tail["cursor"] and not coverage["lost"]
                            and manifest["anchors"].get(tail["seq"]) == summary["checkpoint_sha256"]
                            == receipt["artifacts"]["final.chk"]["sha256"], "incomplete exact assay evidence")
                    status = "PASS"
    output.row("runs", case | dict(status=status, exit_code=code, sim_ms=summary.get("sim_ms", ""),
        events=summary.get("events", ""), pending=summary.get("pending", ""), state_hash=summary.get("state_hash", ""),
        trace_hash=summary.get("trace_hash", ""), contact_decisions=summary.get("contact_decisions", ""),
        candidates_examined=summary.get("candidates", ""), maximum_candidates=summary.get("maximum_candidates", ""),
        exact_off=summary.get("exact_off", ""), rejoined=summary.get("rejoined", ""),
        **{name: coverage[name] for name in ("cuts", "examined", "scoped_facts", "lost", "records", "raw_bytes",
                                            "stored_bytes", "crop_checks", "pending_status_1", "neighbor_status_1",
                                            "request_POSITIVE", "request_ZERO_COMMITTED_REJECTION",
                                            "request_RIGHT_CENSORED", "request_UNOBSERVED")},
        **{name: facts[name] for name in ("NutritionDecision", "NutritionDecision_candidates_examined",
                                         "NutritionDecision_zero_examined", "typed_opportunities",
                                         "typed_gift_choices", "typed_inactive_choices", "ActionRejected",
                                         "NutritionTransferred", "positive_pulses", "zero_pulses", "ProteinRecycled")}))
    return status


def contrasts(folder, output, accepted):
    path = folder / "horizons.csv"
    if not path.exists():
        return
    with path.open(encoding="utf-8", newline="") as stream:
        rows = {(r["arm"], int(r["workers"]), int(r["seed"])): r for r in csv.DictReader(stream)
                if int(r["sim_ms"]) == 90 * DAY and r["case"] in accepted}
    endpoints = ("worker_to_queen_gifts", "worker_to_queen_carb_ug", "worker_to_queen_protein_ug",
                 "worker_to_larva_protein_ug", "queen_uptake_carb_ug", "queen_days_alive", "queen_alive",
                 "eggs", "eclosed", "larval_deaths", "nurse_switches", "foraging_switches")
    pairs = [((arm, n), ("ordinary", n)) for n in (8, 32) for arm in ("depot", "scarce", "empty")]
    pairs += [((arm, 32), (arm, 8)) for arm in ("ordinary", "depot", "scarce", "empty")]
    for lhs, rhs in pairs:
        for key in endpoints:
            diffs = [float(rows[(*lhs, seed)][key]) - float(rows[(*rhs, seed)][key])
                     for seed in range(1, 7) if (*lhs, seed) in rows and (*rhs, seed) in rows]
            ci = ["", ""]
            if len(diffs) == 6:
                rng = random.Random(63101)
                distribution = sorted(statistics.mean(rng.choices(diffs, k=6)) for _ in range(4096))
                ci = [distribution[102], distribution[3993]]
            output.row("paired_contrasts", dict(lhs_arm=lhs[0], lhs_workers=lhs[1], rhs_arm=rhs[0],
                rhs_workers=rhs[1], endpoint=key, paired_seeds=len(diffs),
                status="DESCRIPTIVE_SIMULATION_INTERVAL" if len(diffs) == 6 else "MISSING_PAIRS",
                mean_difference=statistics.mean(diffs) if diffs else "", ci_low=ci[0], ci_high=ci[1]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True)
    freeze = get_json(args.raw / "freeze.json")
    cases = frozen_cases()
    require(freeze["cases"] == cases and freeze["protocol_sha256"] == sha256(PROTOCOL), "frozen matrix differs")
    completed = get_json(args.raw / "completed.json")
    require(freeze["started_utc_ns"] < completed["ended_utc_ns"] and
            set(completed["exit_codes"]) == {case["case"] for case in cases}, "incomplete case index")
    accepted = set()
    with TemporaryDirectory() as temporary, ExitStack() as stack:
        output = Output(args.out, stack)
        for case in cases:
            status = analyse_case(args.raw, case, completed["exit_codes"][case["case"]],
                                  Path(temporary) / "trace.sqlite", output)
            if status == "PASS":
                accepted.add(case["case"])
        counts = output.counts.copy()
    with ExitStack() as stack:
        output = Output(args.out, stack)
        contrasts(args.out, output, accepted)
        counts.update(output.counts)
    data = dict(cases=len(cases), exact_accepted_cases=len(accepted),
                incomplete_cases=[c["case"] for c in cases if c["case"] not in accepted],
                analysis_rows={name: counts[name] for name in TABLES},
                source_freeze_sha256=sha256(args.raw / "freeze.json"))
    (args.out / "analysis_receipt.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
