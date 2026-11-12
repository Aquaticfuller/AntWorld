"""Verify WP-2 archives and derive activity, expenditure and care endpoints."""

import argparse
from collections import Counter, defaultdict
from contextlib import ExitStack
import csv
from dataclasses import dataclass, field
import json
import math
from pathlib import Path
import struct
from tempfile import TemporaryDirectory

from analyze_s6_4_rm02 import DAY, Output, copy_verified, get_json, get_row, ledger_record, mass, state_record
from read_s6_4_rm02_sidecar import CASTES, DEATHS, PROGRAMS, STAGES, decode_fact, open_sidecar, require
from run_s6_4_wp2 import ARTIFACTS, PROTOCOL, matrix, sha256


HOUR = DAY // 24
ACTS = ("Inactive", "Walk", "ApproachBrood", "InspectBrood", "ArrangeBrood", "CleanBrood",
        "TransportBrood", "FeedBrood", "CloseWorkerContact", "CollectFood", "DeliverFood",
        "IngestFood", "TransferNutrition", "Excavate", "HandleSoil", "RevisitBroodSite",
        "PickUpBrood", "PlaceBrood", "ReturnToCareShelter")
PHASES = ("Opportunity", "Selected", "Started", "Completed", "Interrupted")
ACTIVE_PROGRAMS = ("Nurse", "Forage", "Excavate")
MOVEMENT = {"Walk", "ApproachBrood", "TransportBrood", "RevisitBroodSite", "ReturnToCareShelter"}
MANIPULATION = {"InspectBrood", "ArrangeBrood", "CleanBrood"}
CONTACT = MANIPULATION | {"TransportBrood", "PickUpBrood", "FeedBrood"}
SEARCH = {"Walk", "ApproachBrood", "RevisitBroodSite"}
WORK = {"Moved", "BroodMoved", "Rested", "FoodCollected", "FoodDelivered", "NestIngested",
        "CargoIngested", "NutritionTransferred", "SoilExcavated", "SoilDropped", "SoilFilled",
        "SoilPickedUp", "ActionRejected", "CareTick", "NutritionDecision", "AutonomyDecision",
        "AntBorn", "AntDied", "StageChanged", "BehaviorChanged", "ProteinRecycled"}


@dataclass
class Individual:
    stage: str
    caste: str
    position: tuple
    stamp: int = 0
    colony: int = 0
    program: str = "Paused"
    rates: tuple | None = None
    initial: bool = True
    entry_stage: str = ""
    mother: int = 0
    born_ms: int = 0
    alive_ms: int = 0
    physiology_ms: int = 0
    adult_ms: int = 0
    program_ms: Counter = field(default_factory=Counter)
    work: Counter = field(default_factory=Counter)
    movement: Counter = field(default_factory=Counter)
    intervals: list = field(default_factory=list)
    pulse: Counter = field(default_factory=Counter)
    received: Counter = field(default_factory=Counter)
    initial_state: dict | None = None
    last_state: dict | None = None
    death: tuple | None = None

    def advance(self, end, begin):
        require(end >= self.stamp, "nonmonotonic individual facts")
        dt = max(0, end - max(self.stamp, begin))
        if self.stage != "dead":
            self.alive_ms += dt
            if self.rates is not None:
                self.physiology_ms += dt
                if self.stage == "adult":
                    self.adult_ms += dt
                    self.program_ms[self.program] += dt
        self.stamp = end


def initial_ants(path):
    with path.open(encoding="utf-8", newline="") as stream:
        for r in csv.DictReader(stream):
            rates = None
            if r["physiology"] == "1":
                rates = tuple(int(r[key]) for key in ("basal_nj_per_ms", "active_nj_per_ms",
                                                     "water_loss_ug_per_period", "water_loss_period_ms",
                                                     "absorption_period_ms"))
            stage = STAGES[int(r["stage"])]
            yield int(r["entity"]), Individual(stage, CASTES[int(r["caste"])],
                tuple(float(r[k]) for k in ("x_m", "y_m", "z_m")), colony=int(r["colony"]), rates=rates, entry_stage=stage)


def interval_time(intervals):
    elapsed, until = 0, 0
    for start, end in sorted(intervals):
        if end > until:
            elapsed += end - max(start, until)
            until = end
    return elapsed


def coverage(intervals, begin, end):
    classes = defaultdict(list)
    for left, right, act in intervals:
        clipped = max(begin, left), min(end, right)
        if clipped[1] > clipped[0]:
            classes["inactive" if act == "Inactive" else "active"].append(clipped)
            if act in MOVEMENT:
                classes["locomotor"].append(clipped)
    known = interval_time(classes["inactive"] + classes["active"])
    active = interval_time(classes["active"])
    inactive = interval_time(classes["inactive"])
    require(active + inactive == known, "overlapping active and inactive intervals")
    return dict(known_active_ms=active, known_inactive_ms=inactive,
                timed_locomotor_ms=interval_time(classes["locomotor"]), unobserved_activity_ms=end - begin - known)


def body_balance(ant, state):
    opening = ant.initial_state
    energy = (opening["energy_nj"] + ant.pulse["carb"] * state["yield_nj_per_ug"]
              - state["dissipated_nj"] + opening["dissipated_nj"] - state["exported_nj"] + opening["exported_nj"])
    water = opening["body_water_ug"] + ant.pulse["water"] - ant.work["egg_water"] - state["water_lost_ug"] + opening["water_lost_ug"]
    return energy == state["energy_nj"] and water == state["body_water_ug"]


class Trace:
    def __init__(self, case, config, manifest, ants, output):
        self.case = case | {"world_id": manifest["world_id"]}
        self.output = output
        self.ants = ants
        self.end = int(config["horizon_ms"])
        self.begin = int(config["input_ms"]) if case["mode"] == "b02" else 0
        self.source_world = manifest["world"]
        self.counts, self.phases = Counter(), Counter()
        self.phase_ms = Counter()
        self.last_event, self.last_time = 0, 0
        self.pending, self.started = {}, {}
        self.custody, self.after_place = {}, {}
        self.journeys = []
        self.targets = defaultdict(dict)
        self.transfer = {}
        self.motion_at_source = {}
        self.placed = set()
        self.first = {}
        self.care_ticks, self.care_selections = set(), set()

    def row(self, table, **row):
        self.output.row(table, self.case | row)

    def close_program(self, entity, ant, end, boundary):
        start = max(ant.stamp, self.begin)
        if ant.stage == "adult" and ant.rates is not None and end > start:
            self.row("program_intervals", entity=entity, caste=ant.caste, initial=int(ant.initial),
                     entry_stage=ant.entry_stage, program=ant.program, start_ms=start, end_ms=end, duration_ms=end-start,
                     endpoint=boundary, provenance="RECONSTRUCTED")
        ant.advance(end, self.begin)

    def life(self, f, ant):
        self.close_program(f.actor, ant, f.time, f.kind)
        prior = ant.stage
        if f.kind == "BehaviorChanged":
            ant.program = PROGRAMS[f.payload]
            ant.work["program_changes"] += f.time >= self.begin
        elif f.kind == "StageChanged":
            ant.stage = STAGES[f.stage]
        elif f.kind == "AntDied":
            ant.death = f.time, f.event, DEATHS[f.payload]
            ant.stage = "dead"
        self.row("transitions", sim_ms=f.time, event_id=f.event, source=f.source, entity=f.actor,
                 caste=ant.caste, fact=f.kind, from_stage=prior, to_stage=ant.stage,
                 program=ant.program, provenance="COMMITTED_FACT")

    def fact(self, f):
        ant = self.ants.get(f.actor)
        if f.kind == "AntBorn":
            mother = self.ants[f.payload]
            require(f.actor not in self.ants, "reused offspring identity")
            stage = STAGES[f.stage]
            ant = self.ants[f.actor] = Individual(stage, "worker", f.position, f.time, f.colony,
                                                rates=mother.rates, initial=False, entry_stage=stage,
                                                mother=f.payload, born_ms=f.time)
            mother.work["eggs_laid"] += 1
            mother.work["egg_water"] += f.mass[2]
        if f.kind in ("AntBorn", "BehaviorChanged", "StageChanged", "AntDied"):
            require(ant is not None, "unknown lifecycle or program actor")
            self.life(f, ant)
        if ant and f.kind == "PhysiologyUpdated":
            for key, value in zip(("carb", "protein", "water", "other"), f.mass):
                ant.pulse[key] += value
            ant.work["positive_uptake" if any(f.mass) else "zero_uptake"] += 1
            if f.mass[0]:
                ant.work["last_carb_uptake_event"] = f.event
                ant.work["last_carb_uptake_ms"] = f.time
        if f.kind == "NutritionTransferred":
            recipient = self.ants[f.payload]
            require(any(f.mass) and f.outcome in ("Success", "Partial"), "invalid positive transfer")
            for key, value in zip(("carb", "protein", "water", "other"), f.mass):
                recipient.received[key] += value
            recipient.work["last_gift_ms"] = f.time
            recipient.work["received_gifts"] += 1
            if recipient.stage == "larva":
                self.counts["positive_larval_gifts"] += 1
                self.counts["larval_protein_ug"] += f.mass[1]
            if f.source:
                self.transfer[f.source] = (f.actor, f.payload, f.mass)
        if f.kind in ("Moved", "BroodMoved"):
            require(ant is not None, "move lacks an initial or born identity")
            travelled = math.dist(ant.position, f.position)
            ant.position = f.position
            if f.time >= self.begin:
                label = ant.program if f.kind == "Moved" else "BroodMoved"
                ant.movement[label] += travelled
                if f.kind == "BroodMoved":
                    self.motion_at_source[f.source] = (f.actor, f.payload, travelled)
                    self.counts["brood_displacements"] += 1
        if f.time >= self.begin and f.kind in WORK:
            self.counts[f.kind] += 1
            if ant:
                ant.work[f"{ant.program}_{f.kind}"] += 1
            if f.kind == "CareTick":
                self.care_ticks.add(f.source)
        if f.kind == "BiologicalObservation":
            self.care(f)

    def care(self, f):
        phase_idx, act_idx, target, bout, began, known, *_ = f.care
        phase, act = PHASES[phase_idx], ACTS[act_idx]
        key = (f.actor, act, target, bout)
        ant = self.ants[f.actor]
        scored = f.time >= self.begin
        target_state = self.ants.get(target)
        phase_key = (ant.caste, ant.stage, target_state.stage if target_state else "", act, phase, f.outcome, int(known))
        if scored:
            self.phases[phase_key] += 1
        if phase == "Selected":
            if scored:
                self.care_selections.add(f.source)
                if act in SEARCH:
                    self.first.setdefault("first_search_selection_ms", f.time)
                    previous = self.after_place.pop(f.actor, None)
                    if previous:
                        previous.update(next_search_ms=f.time, next_search_status="SELECTED")
                if target_state and act in CONTACT | {"ApproachBrood"}:
                    self.targets[target].setdefault("first_target_selection_ms", f.time)
                    self.first.setdefault("first_target_selection_ms", f.time)
                if act == "PickUpBrood" and f.actor in self.after_place:
                    self.after_place.pop(f.actor)["next_search_status"] = "NEXT_PICKUP_WITHOUT_OBSERVED_SEARCH"
            self.pending[key] = f.time
        elif phase == "Opportunity" and scored and target_state and target_state.stage in ("larva", "pupa", "egg"):
            self.targets[target].setdefault("first_opportunity_ms", f.time)
        elif phase == "Started":
            self.pending.pop(key, None)
            if known:
                require(key not in self.started and began == f.time, "duplicate or mistimed care start")
                self.started[key] = f.time
            if scored and act in CONTACT and target_state and target_state.stage in ("egg", "larva", "pupa"):
                self.targets[target].setdefault("first_contact_proxy_ms", f.time)
                self.first.setdefault("first_contact_proxy_ms", f.time)
        elif phase in ("Completed", "Interrupted"):
            self.pending.pop(key, None)
            start = self.started.pop(key, None)
            if known:
                require(start == began and f.time >= began, "unmatched timed terminal")
                ant.intervals.append((start, f.time, act))
                if scored:
                    self.phase_ms[phase_key] += f.time - max(start, self.begin)
            if scored:
                if act == "ApproachBrood" and phase == "Completed" and start is not None:
                    trace = self.targets[target]
                    trace["approach_segments"] = trace.get("approach_segments", 0) + 1
                    trace["approach_ms"] = trace.get("approach_ms", 0) + f.time - start
                self.custody_event(f, act, phase, target, start)

    def custody_event(self, f, act, phase, target, start):
        if act == "FeedBrood" and phase == "Completed" and any(f.mass):
            require(self.transfer.get(f.source) == (f.actor, target, f.mass), "feed lacks matching conserved gift")
            self.counts["confirmed_feed_bouts"] += 1
        if act == "PickUpBrood" and phase == "Completed":
            require(f.actor not in self.custody, "overlapping pickup")
            self.targets[target].setdefault("first_pickup_ms", f.time)
            journey = dict(carrier=f.actor, target=target, pickup_event=f.event, pickup_ms=f.time,
                           pickup_start_ms=start if start is not None else "", loaded_segments=0, brood_path_m=0.0,
                           loaded_motion_ms=0, terminal_event="", terminal_start_ms="", terminal_ms="", outcome="", status="",
                           next_search_ms="", next_search_status="UNOBSERVED")
            self.journeys.append(journey)
            self.custody[f.actor] = journey
        journey = self.custody.get(f.actor)
        if not journey or journey["target"] != target:
            if phase == "Completed" and act in ("TransportBrood", "PlaceBrood"):
                self.counts["unlinked_transport_or_placement"] += 1
            return
        if act == "TransportBrood" and phase == "Completed":
            moved = self.motion_at_source.pop(f.source, None)
            require(moved is not None and moved[:2] == (target, f.actor), "loaded motion lacks matching brood displacement")
            journey["loaded_segments"] += 1
            journey["brood_path_m"] += moved[2]
            if start is not None:
                journey["loaded_motion_ms"] += f.time - start
        elif act in ("TransportBrood", "PlaceBrood") and phase == "Interrupted":
            self.close_journey(journey, f, start, "INTERRUPTED")
        elif act == "PlaceBrood" and phase == "Completed":
            self.close_journey(journey, f, start, "PLACED")
            self.targets[target].setdefault("first_placement_ms", f.time)
            self.first.setdefault("first_placement_ms", f.time)
            self.targets[target]["placements"] = self.targets[target].get("placements", 0) + 1
            self.placed.add(target)
            journey["next_search_status"] = "RIGHT_CENSORED"
            self.after_place[f.actor] = journey

    def close_journey(self, journey, f, start, status):
        journey.update(terminal_event=f.event, terminal_start_ms=start if start is not None else "",
                       terminal_ms=f.time, outcome=f.outcome, status=status)
        self.custody.pop(f.actor)

    def cut(self, cut):
        ledger = None
        for tag, data in cut["payload"]:
            if tag == 1:
                fact = decode_fact(data, self.source_world)
                require(max(cut["start"], self.last_event) < fact.event <= cut["cursor"] and
                        self.last_time <= fact.time <= cut["time"], "fact order differs")
                self.last_event, self.last_time = fact.event, fact.time
                self.fact(fact)
            elif tag == 2:
                entity, state = state_record(data)
                ant = self.ants[entity]
                pos = struct.unpack_from("<ddd", data, 7 * 8)
                require(pos == ant.position, f"unreconciled position for {entity}")
                if state:
                    require(state["stage"] == ant.stage, "focal stage mismatch")
                    if ant.initial_state is None:
                        require(cut["time"] == 0, "missing initial focal body state")
                        ant.initial_state = state
                    require(body_balance(ant, state), f"body ledger mismatch for {entity} at {cut['time']}")
                    ant.last_state = state
                    self.counts["focal_body_checks"] += 1
                    if self.case["mode"] not in ("activity", "integrated") or cut["time"] % DAY == 0:
                        self.row("body_cuts", sim_ms=cut["time"], event_cursor=cut["cursor"], entity=entity,
                                 provenance="CUT_SNAPSHOT", **state)
            elif tag == 3:
                require(ledger is None, "multiple ledgers at one cut")
                ledger = ledger_record(data)
        require(ledger is not None and not cut["dropped"], "incomplete sidecar cut")
        self.row("ledgers", sim_ms=cut["time"], event_cursor=cut["cursor"], provenance="CUT_SNAPSHOT", **ledger)
        self.counts.update(cuts=1, examined=cut["examined"], scoped_facts=cut["selected"],
                           payload_bytes=cut["raw_bytes"], stored_payload_bytes=cut["packed_bytes"])
        self.transfer.clear()
        self.motion_at_source.clear()

    def scans(self):
        if self.case["mode"] != "b01":
            return
        queen, = [a for a in self.ants.values() if a.caste == "queen"]
        windows = (2, 6, 24) if self.case["arm"] == "barrier" else (71, 96, 120)
        for window in windows:
            for minute in range(5, 55):
                left = window * HOUR + minute * 60000
                right = left + 10000
                alive = not queen.death or queen.death[0] >= right
                positive = any(act in MANIPULATION and t0 < right and t1 > left for t0, t1, act in queen.intervals)
                self.row("b01_scans", window_hour=window, minute=minute, start_ms=left, end_ms=right,
                         status="OBSERVED" if alive else "DEATH_TRUNCATED", positive=int(positive) if alive else "")

    def finish(self):
        for (entity, act, target, bout), selected in sorted(self.pending.items()):
            self.row("open_bouts", actor=entity, target=target, act=act, bout=bout, start_or_selection_ms=selected,
                     state="SELECTED_ONLY", endpoint_status="UNOBSERVED")
        for (entity, act, target, bout), start in sorted(self.started.items()):
            self.ants[entity].intervals.append((start, self.end, act))
            self.row("open_bouts", actor=entity, target=target, act=act, bout=bout, start_or_selection_ms=start,
                     state="STARTED", endpoint_status="RIGHT_CENSORED")
        for journey in self.journeys:
            if not journey["status"]:
                journey.update(terminal_ms=self.end, status="RIGHT_CENSORED")
            if journey["next_search_status"] == "RIGHT_CENSORED" and self.ants[journey["carrier"]].death:
                journey["next_search_status"] = "COMPETING_DEATH"
            self.row("custody", **journey)
        for key, count in sorted(self.phases.items()):
            caste, stage, target_stage, act, phase, outcome, known = key
            self.row("care_phases", caste=caste, stage=stage, target_stage=target_stage, act=act,
                     phase=phase, outcome=outcome, duration_known=known, events=count, observed_terminal_ms=self.phase_ms[key])
        for entity, ant in self.ants.items():
            if self.case["mode"] == "b02" and ant.stage in ("egg", "larva", "pupa"):
                target = self.targets[entity]
                self.row("retrieval_targets", entity=entity, colony=ant.colony, stage=ant.stage,
                         placement_status="PLACED" if entity in self.placed else "RIGHT_CENSORED",
                         **{key: target.get(key, "") for key in ("first_opportunity_ms", "first_target_selection_ms",
                           "first_contact_proxy_ms", "first_pickup_ms", "first_placement_ms")},
                         approach_segments=target.get("approach_segments", 0), approach_ms=target.get("approach_ms", 0),
                         placements=target.get("placements", 0))
            self.close_program(entity, ant, self.end, "HORIZON")
            begin = max(self.begin, ant.born_ms)
            end = max(begin, ant.death[0] if ant.death else self.end)
            activity = coverage(ant.intervals, begin, end)
            require(end - begin == ant.alive_ms, "lifetime exposure mismatch")
            state = ant.last_state or {}
            program = {f"{p}_ms": ant.program_ms[p] for p in PROGRAMS}
            active = sum(ant.program_ms[p] for p in ACTIVE_PROGRAMS)
            require(sum(program.values()) == ant.adult_ms, "program dwell does not cover adult physiology")
            spent = ("energy_nj", "body_water_ug", "dissipated_nj", "exported_nj", "water_lost_ug",
                     "crop_carb_ug", "crop_protein_ug", "tissue_protein_ug")
            self.row("individuals", entity=entity, colony=ant.colony, caste=ant.caste, stage=ant.stage,
                     entry_stage=ant.entry_stage,
                     initial=int(ant.initial), mother=ant.mother, alive_ms=ant.alive_ms, physiology_ms=ant.physiology_ms,
                     adult_physiology_ms=ant.adult_ms, active_program_ms=active, **program, **activity,
                     endpoint_status="DEATH" if ant.death else "RIGHT_CENSORED",
                     death_ms=ant.death[0] if ant.death else "", death_event=ant.death[1] if ant.death else "",
                     death_cause=ant.death[2] if ant.death else "",
                     nominal_basal_nj=ant.rates[0] * ant.physiology_ms if ant.rates is not None else "",
                     nominal_active_surcharge_nj=ant.rates[1] * active if ant.rates is not None else "",
                     movement_m=sum(ant.movement[p] for p in PROGRAMS), passive_brood_m=ant.movement["BroodMoved"],
                     program_changes=ant.work["program_changes"], eggs_laid=ant.work["eggs_laid"],
                     positive_pulses=ant.work["positive_uptake"], zero_pulses=ant.work["zero_uptake"],
                     received_gifts=ant.work["received_gifts"], last_gift_ms=ant.work.get("last_gift_ms", ""),
                     last_carb_uptake_ms=ant.work.get("last_carb_uptake_ms", ""),
                     last_carb_uptake_event=ant.work.get("last_carb_uptake_event", ""),
                     **{f"moves_{p}": ant.work[f"{p}_Moved"] for p in PROGRAMS},
                     **{f"path_{p}_m": ant.movement[p] for p in PROGRAMS},
                     **{k: state.get(k, "") for k in spent},
                     **mass("uptake", tuple(ant.pulse[c] for c in ("carb", "protein", "water", "other"))),
                     **mass("received", tuple(ant.received[c] for c in ("carb", "protein", "water", "other"))))
        self.scans()
        first = ("first_search_selection_ms", "first_target_selection_ms", "first_contact_proxy_ms", "first_placement_ms")
        return dict(**{k: self.first.get(k, "") for k in first}, placed=len(self.placed),
                    completed_placements=sum(j["status"] == "PLACED" for j in self.journeys),
                    open_bouts=len(self.pending) + len(self.started),
                    care_ticks_without_selection=len(self.care_ticks - self.care_selections),
                    **{key: self.counts[key] for key in sorted(WORK | {"cuts", "examined", "scoped_facts", "payload_bytes",
                       "stored_payload_bytes", "focal_body_checks", "positive_larval_gifts", "larval_protein_ug",
                       "confirmed_feed_bouts", "brood_displacements", "unlinked_transport_or_placement"})})


def read_catalog(root, expected=None):
    freeze = get_json(root / "freeze.json")
    cases = [c for c in matrix() if freeze["selection"] in ("full", c["mode"])]
    require(freeze["cases"] == cases and (expected is None or freeze["selection"] == expected)
            and freeze["protocol_sha256"] == sha256(PROTOCOL), "WP-2 matrix freeze differs")
    finished = get_json(root / "completed.json")
    codes = finished["exit_codes"]
    require(finished["ended_utc_ns"] > freeze["started_utc_ns"] and set(codes) == {c["case"] for c in cases},
            "WP-2 case index is incomplete")
    return cases, codes


def verify_attempt(root, case, status, temporary):
    folder = root / "raw" / case["case"]
    receipt = get_json(folder / "receipt.json")
    require(all(receipt[k] == v for k, v in case.items()) and status == receipt["exit_code"], "case receipt differs")
    copy_verified(folder, receipt, temporary)
    if not status:
        require(set(receipt["artifacts"]) == set(ARTIFACTS), "successful case is missing an archive")
    return folder, receipt


def analyze(root, case, code, temporary, output, prior=None):
    folder, receipt = verify_attempt(root, case, code, temporary)
    if code:
        output.row("incomplete", case | dict(exit_code=code, archive=root.name))
        return False
    config = get_row(folder / "configuration.csv")
    require(all(config[key] == str(value) for key, value in case.items() if key != "case"), "case configuration differs")
    result = get_row(folder / "summary.csv")
    if prior:
        previous = get_row(prior / "summary.csv")
        require(all(previous[key] == result[key] for key in ("state_hash", "trace_hash", "rng", "events"))
                and get_json(prior / "receipt.json")["artifacts"]["final.chk"]["sha256"] ==
                receipt["artifacts"]["final.chk"]["sha256"], "extra host cuts changed authoritative state or history")
    with open_sidecar(temporary) as (manifest, cuts), (folder / "cuts.csv").open(newline="", encoding="utf-8") as stream:
        require(manifest["world_id"] == config["world_id"] and manifest["seed"] == case["seed"] and
                manifest["activity_care"] and manifest["all_relevant"] and not manifest["origin"], "wrong sidecar scope")
        ants = dict(initial_ants(folder / "initial_ants.csv"))
        require(manifest["focal"] == tuple(sorted(ants)), "focal identities differ")
        trace = Trace(case, config, manifest, ants, output)
        cut, middle = None, None
        for cut, row in zip(cuts, csv.DictReader(stream), strict=True):
            require(int(row["sim_ms"]) == cut["time"] and
                    all(int(row[k]) == cut[k] for k in ("cursor", "examined", "selected", "records", "dropped")) and
                    int(row["payload_bytes"]) == cut["raw_bytes"], "cut receipt differs")
            require(int(row["soil_initial_q3"]) == sum(int(row[f"soil_{k}_q3"]) for k in ("remaining", "carried", "deposited")),
                    "soil volume differs")
            if cut["time"] == int(config["midpoint_ms"]):
                middle = cut["seq"]
            trace.cut(cut)
        hashes = receipt["artifacts"]
        require(cut and cut["time"] == int(config["horizon_ms"]) and str(cut["cursor"]) == result["events"] and
                str(cut["seq"]) == result["cuts"] and result["observer_off_equal"] == result["midpoint_rejoined"] == "1"
                and result["status"] == "PASS" and manifest["anchors"] ==
                {middle: hashes["midpoint.chk"]["sha256"], cut["seq"]: hashes["final.chk"]["sha256"]},
                "missing final/midpoint evidence or replay mismatch")
        outcome = trace.finish()
        trace.row("runs", **outcome, **{key: result[key] for key in ("state_hash", "trace_hash", "rng",
                  "peak_queued_bytes", "peak_rss_bytes", "closed_database_bytes", "wal_at_end_bytes")},
                  checkpoint_sha256=hashes["final.chk"]["sha256"], archive=root.name, rejoined=1, exact_off=1)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--supplement", type=Path, action="append", default=[])
    parser.add_argument("--case", action="append", default=[], help="verify named cases in a declared matrix")
    args = parser.parse_args()
    cases, codes = read_catalog(args.raw)
    supplements = {}
    for path in args.supplement:
        items, results = read_catalog(path)
        require(not supplements.keys() & results.keys() and results.keys() <= codes.keys(),
                "supplements must be complete disjoint original strata")
        supplements.update({case["case"]: (path, results[case["case"]]) for case in items})
    if args.case:
        require(set(args.case) <= codes.keys(), "unknown WP-2 case")
        cases = [case for case in cases if case["case"] in args.case]
    args.out.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory() as temp, ExitStack() as stack:
        tmp = Path(temp) / "observer.sqlite"
        out = Output(args.out, stack)
        counts = Counter()
        for case in cases:
            name = case["case"]
            path, code = supplements.get(name, (args.raw, codes[name]))
            prior = None
            if path != args.raw:
                folder, _ = verify_attempt(args.raw, case, codes[name], tmp)
                if not codes[name]:
                    prior = folder
            if analyze(path, case, code, tmp, out, prior):
                counts[case["mode"]] += 1
        report = dict(expected=len(cases), completed=sum(counts.values()), by_stratum=dict(counts),
                      original_incomplete=[case["case"] for case in cases if codes[case["case"]]],
                      supplemented=sum(case["case"] in supplements for case in cases), output_rows=dict(out.counts))
    (args.out / "analysis_receipt.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(report, indent=2))
    return int(report["completed"] != len(cases))


if __name__ == "__main__":
    raise SystemExit(main())
