"""Independently verify WP-4 archives, then reconcile joint budgets and outcomes."""

import argparse
from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict
from contextlib import closing, contextmanager
import csv
from dataclasses import asdict
import hashlib
import io
import json
from pathlib import Path
import shutil
import struct
import tarfile
from tempfile import TemporaryDirectory

from analyze_s6_4_rm02 import ledger_record, state_record
from read_s6_4_rm02_sidecar import CASTES, DEATHS, PROGRAMS, STAGES, open_sidecar, require
from run_s6_4_rm02 import sha256
from run_s6_4_wp4 import ARTIFACTS
from run_s6_4_wp4_performance import BASE, PROTOCOL
from s6_4_wp4_budget import Budgets, PARTS, ZERO, components, crop, death_code
from s6_4_wp4_cases import matrix
from verify_s6_3_4_archive import audit_world, open_readonly
from verify_s6_4_wp3 import canonical, load, row, rows, sequence


DAY = 86_400_000
AUTHORITY = dict(zip(("cpp/src", "cpp/include", "cpp/storage"),
    ("b5f20efbfcdd9baeebb8c6c43abcb12810e1c93d", "168ec1e9cb18edcb929507b8f3c8ecaf443bd0af",
     "14d0c32d3a0738dc2198a56b1ffd0fd4cad919bd")))
REFERENCE = PROTOCOL.parents[2] / "experiments/s6_4_rm02_r1/baseline/raw"
TIMED_FIELDS = {"capture_ms", "lineage_ms", "submission_ms"}
REQUIRED_FACTS = {
    "AntSeeded", "AntBorn", "StageChanged", "AntDied", "ActionRejected", "PhysiologyEnabled", "PhysiologyUpdated",
    "BehaviorChanged", "NutritionTransferred", "CargoIngested", "NestIngested", "ReproductionAttempt", "ProteinRecycled",
    "FoodCollected", "FoodDelivered", "ResourceReleased",
}


class Tables:
    def __init__(self):
        self.data = defaultdict(list)

    def add(self, name, case, **values):
        self.data[name].append(dict(case=case.key, world_id=case.world_id, **values))

    def save(self, path, check):
        if not check:
            path.mkdir(parents=True, exist_ok=True)
        for name, records in sorted(self.data.items()):
            fields = list(dict.fromkeys(key for record in records for key in record))
            stream = io.StringIO(newline="")
            writer = csv.DictWriter(stream, fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(records)
            data = stream.getvalue().encode()
            file = path / (name + ".csv")
            if check:
                require(data == file.read_bytes(), f"derived table differs: {name}")
            else:
                file.write_bytes(data)


class Run:
    def __init__(self, case, config):
        self.key, self.world_id = case.key, config["world_id"]
        self.horizon = int(config["horizon_ms"])
        self.queen = int(config["queen"])
        self.seeded_egg = int(config["seeded_egg"])


@contextmanager
def extract(root, case):
    folder = root / "raw" / case.key
    receipt = load(folder / "receipt.json")
    require(receipt["case"] == case.key and all(receipt[k] == v for k, v in asdict(case).items()),
            "archive identifies the wrong input")
    require(receipt["exit_code"] == receipt["program_exit_code"] == 0, f"failed case {case.key}")
    require(set(receipt["artifacts"]) == set(ARTIFACTS), "incomplete case evidence")
    path = folder / "raw.tar.gz"
    require(path.stat().st_size == receipt["archive_bytes"] and sha256(path) == receipt["archive_sha256"],
            "archive hash or length differs")
    with TemporaryDirectory(prefix="wp4-verify-") as tmp, tarfile.open(path, "r:gz") as bundle:
        members = sequence(bundle, lambda item: item.name)
        require(set(members) == set(ARTIFACTS), "unexpected archive member")
        dest = Path(tmp)
        for name, item in members.items():
            expected = receipt["artifacts"][name]
            require(item.isfile() and item.size == expected["bytes"] <= 128 * 1024 * 1024, "invalid archive member")
            with bundle.extractfile(item) as source, (dest / name).open("xb") as target:
                shutil.copyfileobj(source, target)
            require(sha256(dest / name) == expected["sha256"], f"artifact hash differs: {name}")
        yield dest


def integers(data, except_fields=()):
    return {k: int(v) for k, v in data.items() if k not in except_fields}


def focal_matches(record, state, spec):
    same = {"energy_nj": "energy_nj", "body_water_ug": "hydration_ug", "tissue_protein_ug": "tissue_ug",
            "oxidized_carb_ug": "oxidized_carbs_ug", "water_lost_ug": "lost_water_ug", "dissipated_nj": "dissipated_nj",
            "exported_nj": "exported_nj", "next_absorption_ms": "next_uptake_ms", "stage_progress_ms": "progress_ms"}
    require(all(record[k] == state[v] for k, v in same.items()), "focal state differs from lineage query")
    require((record["stage"], record["program"], record["death_cause"], record["caste"]) ==
            (STAGES[state["stage"]], PROGRAMS[state["program"]], DEATHS[state["death_cause"]], CASTES[state["caste"]]),
            "focal stage differs from lineage query")
    require((record["born_ms"], record["mother"], record["yield_nj_per_ug"]) ==
            (spec["born_ms"], spec["mother"], spec["yield_nj_per_ug"]), "lineage source differs")
    require((record["crop_carb_ug"], *(record[f"crop_{p}_ug"] for p in PARTS[1:])) == crop(state), "focal crop differs")


def world_balance(ledger, observed, accounts, cut):
    require(ledger["physiology_count"] == ledger["individuals"] == len(observed) and
            ledger["living"] == sum(q["stage"] != 4 for q in observed.values()), "world lineage census differs")
    for observed_key, ledger_key in (("energy_nj", "energy_body_nj"), ("dissipated_nj", "energy_dissipated_nj"),
                                     ("lost_water_ug", "water_lost_ug"), ("hydration_ug", "body_water_ug"),
                                     ("oxidized_carbs_ug", "oxidized_carb_ug"), ("tissue_ug", "tissue_protein_ug")):
        require(sum(q[observed_key] for q in observed.values()) == ledger[ledger_key], "world stock differs")
    for p, key in zip(PARTS, ("carb", *PARTS[1:]), strict=True):
        require(sum(q[f"crop_{p}_ug"] for q in observed.values()) == ledger[f"colony_crop_{key}_ug"], "world crop differs")
        require(cut[f"nest_{p}_ug"] == ledger[f"nest_stored_{key}_ug"], "world nest stock differs")
    require(cut["soil_initial_q3"] == sum(cut[k] for k in ("soil_remaining_q3", "soil_carried_q3",
                                                          "soil_deposited_q3")), "soil balance differs")
    inputs = sum(q["body_energy_input_nj"] - observed[actor]["exported_nj"] for actor, q in accounts.items())
    require(inputs == ledger["energy_input_nj"], "maternal export counted as external energy")


def durable_midpoint(path):
    # A SQLite connection context commits/rolls back; it does not close the handle.
    with closing(open_readonly(path)) as db:
        db.execute("BEGIN")
        require(db.execute("PRAGMA quick_check").fetchall() == [("ok",)] and
                not db.execute("PRAGMA foreign_key_check").fetchall() and
                db.execute("PRAGMA application_id").fetchone() == (1096234835,) and
                db.execute("PRAGMA user_version").fetchone() == (2,), "invalid midpoint world database")
        manifest, = db.execute("SELECT world,generation,revision,time_ms,cursor,checkpoint_hash FROM worlds").fetchall()
        return audit_world(db, manifest)


def examine_cuts(run, dest, tables):
    config, summary = row(dest / "configuration.csv"), row(dest / "summary.csv")
    state = defaultdict(dict)
    for r in rows(dest / "lineage.csv"):
        values = integers(r, ("x_m", "y_m", "z_m"))
        require(values["id"] not in state[values["cut"]], "duplicate lineage identity at cut")
        state[values["cut"]][values["id"]] = values
    specs = sequence((integers(r) for r in rows(dest / "lineage_inputs.csv")), lambda r: r["id"])
    cut_rows = sequence(rows(dest / "cuts.csv"), lambda r: int(r["cut"]))
    inputs = sequence(rows(dest / "inputs.csv"), lambda r: int(r["scheduled_id"]))
    budget = Budgets(specs, config)
    maternal, events, peak = [], [], Counter()
    with open_sidecar(dest / "observer.sqlite") as (metadata, cuts), closing(cuts):
        require(metadata["world_id"] == run.world_id and metadata["origin"] == 0 and not metadata["activity_care"]
                and metadata["seed"] == int(config["seed"])
                and metadata["all_relevant"] and metadata["lineage"] == "maternal-development", "wrong sidecar scope")
        facts = canonical(dest / "canonical.bin", metadata["world"])
        for cut in cuts:
            seq = cut["seq"]
            current = integers(cut_rows[seq], TIMED_FIELDS)
            observed = state[seq]
            end, at = cut["cursor"], cut["time"]
            expected = (end, at, cut["examined"], cut["selected"], cut["records"], cut["raw_bytes"])
            require(expected == tuple(current[k] for k in ("cursor", "sim_ms", "examined", "selected",
                                                           "records", "payload_bytes")), "cut cursor or payload differs")
            require(0 < current["lineage_bytes"] <= 256 * 1024 and cut["dropped"] == current["dropped"] == 0,
                    "incomplete sidecar or lineage")
            scoped = iter(bytes(record) for tag, record in cut["payload"] if tag == 1)
            candidate = next(scoped, None)
            for fact, encoded in facts[cut["start"]:end]:
                if candidate == encoded:
                    candidate = next(scoped, None)
                else:
                    require(fact.kind not in REQUIRED_FACTS, "missing required canonical fact in the sidecar")
                require(fact.time <= at, "fact lies after cut time")
                budget.read(fact, inputs)
            require(candidate is None, "sidecar fact differs from canonical sequence")
            require(set(observed) == set(budget.individuals) and len(observed) <= 128, "incomplete cut census")
            calculated = {}
            for actor, values in observed.items():
                require(values["cursor"] == end and values["sim_ms"] == at and specs[actor]["first_cut"] <= seq,
                        "misbound lineage cut")
                calculated[actor] = budget.individuals[actor].evaluate(values, at)
            focal = dict(state_record(record) for tag, record in cut["payload"] if tag == 2)
            require(set(focal) == set(metadata["focal"]), "focal state set differs")
            for actor, record in focal.items():
                focal_matches(record, observed[actor], specs[actor])
            ledger, = (ledger_record(record) for tag, record in cut["payload"] if tag == 3)
            world_balance(ledger, observed, calculated, current)
            if run.queen:
                q = budget.individuals[run.queen]
                state_row = dict(observed[run.queen])
                del state_row["id"]
                for metric in ("carbs", "protein", "water", "other"):
                    state_row[f"nest_{metric}_ug"] = current[f"nest_{metric}_ug"]
                link = dict(**state_row, **calculated[run.queen],
                            **components(q.flows["gift_in"], "received"), **components(q.flows["uptake"], "absorbed"),
                            **{f"world_{k}": v for k, v in ledger.items()}, eggs=q.birth_count,
                            snapshot_origin="CUT_SNAPSHOT", integral_origin="RECONSTRUCTED")
                tables.add("maternal_cuts", run, queen=run.queen, **link)
                maternal.append(link)
            for key in TIMED_FIELDS:
                peak[key] = max(peak[key], float(cut_rows[seq][key]))
            peak["lineage_bytes"] = max(peak["lineage_bytes"], current["lineage_bytes"])
            peak["payload_bytes"] = max(peak["payload_bytes"], current["payload_bytes"])
            census = Counter(q["stage"] for q in observed.values())
            tables.add("population_cuts", run, cut=seq, cursor=end, sim_ms=at,
                       **{name: census[i] for i, name in enumerate(STAGES)}, provenance="CUT_SNAPSHOT")
            events.append(cut)
            del cut["payload"]
        anchors = metadata["anchors"]
    require(len(events) == len(state) == len(cut_rows) == int(summary["cuts"])
            and end == len(facts) == int(summary["events"]) and at == run.horizon
            and summary["status"] == "PASS" and summary["exact_off"] == summary["sqlite_midpoint_exact"] == "1",
            "incomplete verified run")
    middle, final = sorted(anchors)
    require(final == len(events) and anchors[final] == sha256(dest / "final.chk")
            and anchors[middle] == sha256(dest / "midpoint.chk"), "sidecar/checkpoint anchor differs")
    restore = durable_midpoint(dest / "midpoint.sqlite")
    prefix = events[middle - 1]["cursor"]
    digest = hashlib.sha256()
    for _, data in facts[:prefix]:
        digest.update(struct.pack("<I", len(data)))
        digest.update(data)
    require((restore["world"], restore["facts"], restore["canonical_sha256"]) ==
            (run.world_id, prefix, digest.hexdigest()), "independent durable prefix verification failed")
    require(set(specs) == set(budget.individuals) and set(inputs) == budget.resolutions.keys(), "unresolved input or identity")
    require({s for s, attempt in budget.attempts.items() if attempt.payload} == budget.births.keys(),
            "funded attempt and committed child counts differ")
    return budget, maternal, observed, peak, inputs, sum(map(len, state.values()))


def export_endpoints(run, budget, maternal, observed, inputs, tables):
    counts = Counter()
    for actor, q in budget.individuals.items():
        if q.entry.stage != 0:
            continue
        for stage in range(4):
            endpoint = q.disposition(stage, run.horizon)
            if endpoint:
                tables.add("offspring_stages", run, entity=actor, mother=q.spec["mother"], **endpoint)
                counts[(endpoint["stage"], endpoint["endpoint"])] += 1
        state = observed[actor]
        tables.add("offspring_terminal", run, entity=actor, mother=q.spec["mother"], origin=q.entry.kind,
                   entry_ms=q.entry.time, first_event=q.entry.event, last_stage=STAGES[state["stage"]],
                   terminal_death_cause=DEATHS[state["death_cause"]],
                   **{f"egg_{k}": v for k, v in q.disposition(0, run.horizon).items()},
                   tissue_ug=state["tissue_ug"], energy_nj=state["energy_nj"], water_ug=state["hydration_ug"],
                   **components(q.flows["gift_in"], "received"), **components(q.flows["uptake"], "absorbed"))
    maternal_cursors = [q["cursor"] for q in maternal]
    for source, attempt in budget.attempts.items():
        egg = budget.births.get(source)
        bracket = bisect_left(maternal_cursors, (egg or attempt).event)
        require(0 < bracket < len(maternal), "attempt missing bracketing cuts")
        values = {}
        for prefix, snap in (("previous", maternal[bracket - 1]), ("following", maternal[bracket])):
            for key in ("sim_ms", "cursor", "energy_nj", "hydration_ug", "crop_protein_ug", "dissipated_nj"):
                values[f"{prefix}_{key}"] = snap[key]
        tables.add("reproduction_attempts", run, event_id=attempt.event, scheduled_id=source, at_ms=attempt.time,
                   mother=attempt.actor, child=egg.actor if egg else None, status="funded" if egg else "deferred",
                   committed_birth_event=egg.event if egg else None, egg_energy_nj=egg.auxiliary if egg else 0,
                   egg_heat_nj=int(budget.config["egg_heat_nj"]) if egg else 0,
                   **components(egg.mass if egg else ZERO, "exported"), **values,
                   guard_reason="UNOBSERVED", bracket_origin="CUT_SNAPSHOT")
    for source, request in inputs.items():
        fact = budget.resolutions[source]
        require(fact.time == int(request["execute_ms"]) and fact.actor == int(request["actor"]), "wrong input resolution")
        if request["kind"] == "gift":
            require(fact.payload == int(request["recipient"]), "wrong gift recipient")
        tables.add("fixture_inputs", run, event_id=fact.event, resolution=fact.kind, outcome=fact.outcome,
                   **components(fact.mass, "committed"), **request)
    for fact, stage in budget.gifts:
        tables.add("gifts", run, at_ms=fact.time, event_id=fact.event, source=fact.source, donor=fact.actor,
                   recipient=fact.payload, stage=STAGES[stage], outcome=fact.outcome, **components(fact.mass, "dose"))
    for actor, pulses in budget.uptake.items():
        for fact in pulses:
            if actor == run.queen or budget.individuals[actor].entry.stage == 0:
                tables.add("uptake", run, at_ms=fact.time, event_id=fact.event, actor=actor, stage=STAGES[fact.stage],
                           status="positive" if any(fact.mass) else "zero", **components(fact.mass, "uptake"))
    queen_pulses = [[f for f in budget.uptake[run.queen] if f.mass[i]] for i in range(len(PARTS))]
    pulse_ids = [[f.event for f in pulses] for pulses in queen_pulses]
    for fact, _ in budget.gifts:
        if fact.payload != run.queen:
            continue
        for i, component in enumerate(PARTS):
            if not fact.mass[i]:
                continue
            pulses = queen_pulses[i]
            where = bisect_right(pulse_ids[i], fact.event)
            next_pulse = pulses[where] if where < len(pulses) else None
            death = budget.individuals[run.queen].death
            stop = next_pulse or death
            tables.add("maternal_receipt_to_uptake", run, component=component, gift_event=fact.event, gift_ms=fact.time,
                       dose_ug=fact.mass[i], stop_ms=stop.time if stop else run.horizon,
                       delay_ms=(stop.time if stop else run.horizon) - fact.time,
                       stop_event=stop.event if stop else None, endpoint="later_positive_pulse" if next_pulse else
                       "competing_death" if death else "right_censored", provenance="TEMPORAL_ASSOCIATION")
    return counts


def case_result(case, dest, tables):
    config, summary = row(dest / "configuration.csv"), row(dest / "summary.csv")
    require(all(config[k] == str(v) for k, v in asdict(case).items()) and config["sidecar_scope"] == "RM02_NUTRITION",
            "configuration differs from frozen case")
    run = Run(case, config)
    budget, maternal, observed, peak, inputs, census_rows = examine_cuts(run, dest, tables)
    counts = export_endpoints(run, budget, maternal, observed, inputs, tables)
    queen = budget.individuals.get(run.queen)
    death = queen.death if queen else None
    if death:
        bracket = bisect_left([q["cursor"] for q in maternal], death.event)
        require(0 < bracket < len(maternal), "queen death missing bracketing cuts")
        for relation, snap in (("before", maternal[bracket - 1]), ("after", maternal[bracket])):
            tables.add("maternal_death_brackets", run, relation=relation, event_id=death.event, death_ms=death.time,
                       death_cause=DEATHS[death_code(death)], **snap)
    if case.family == "ecology" and case.workers and case.seed == 1:
        historical = f"ecology-{case.arm}-{case.workers}-1"
        accepted = load(REFERENCE / historical / "receipt.json")
        initial, final = (sha256(dest / name) for name in ("initial.chk", "final.chk"))
        require([initial, final] == [accepted["artifacts"][name]["sha256"] for name in ("initial.chk", "final.chk")],
                "matched RM-02-R1 ecology checkpoint changed")
        tables.add("historical_checkpoint_matches", run, reference_case=historical,
                   initial_sha256=initial, final_sha256=final)
    first = maternal[0] if maternal else {}
    last = maternal[-1] if maternal else {}
    stages = {f"{stage}_{end}": counts[stage, end] for stage in STAGES[:4]
              for end in ("transition", "death", "right_censored")}
    tables.add("case_results", run, **asdict(case), events=int(summary["events"]), horizon_ms=run.horizon,
               state_hash=summary["state_hash"], trace_hash=summary["trace_hash"], rng=summary["rng"],
               cuts=int(summary["cuts"]), budgets_checked=census_rows, attempts=len(budget.attempts),
               births=len(budget.births), **stages, gifts=budget.counts["NutritionTransferred"],
               rejected_actions=budget.counts["ActionRejected"], brood_moves=budget.counts["BroodMoved"],
               food_deliveries=budget.counts["FoodDelivered"], maternal_alive=(death is None) if queen else None,
               maternal_death=DEATHS[death_code(death)] if death else None, maternal_stop_ms=death.time if death else
               run.horizon if queen else None, initial_queen_energy_nj=first.get("energy_nj"),
               end_queen_energy_nj=last.get("energy_nj"), end_queen_water_ug=last.get("hydration_ug"),
               queen_export_nj=last.get("exported_nj"), queen_dissipated_nj=last.get("dissipated_nj"),
               queen_received_carbs_ug=last.get("received_carbs_ug"), queen_received_protein_ug=last.get("received_protein_ug"),
               queen_received_water_ug=last.get("received_water_ug"), queen_absorbed_carbs_ug=last.get("absorbed_carbs_ug"),
               queen_absorbed_protein_ug=last.get("absorbed_protein_ug"), queen_absorbed_water_ug=last.get("absorbed_water_ug"),
               **{f"peak_cut_{k}": v for k, v in sorted(peak.items())},
               **{k: summary[k] for k in ("advance_ms", "wall_ms", "midpoint_ms", "drain_ms", "writer_ms",
                                         "replay_and_canonical_ms", "peak_queue_bytes", "peak_rss_bytes",
                                         "observer_bytes", "midpoint_sqlite_bytes")})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--case", action="append", help="Verify specific case IDs and generate a separate analysis.")
    args = parser.parse_args()
    freeze = load(args.archive / "freeze.json")
    require(freeze["baseline"] == BASE and freeze["authority"] == AUTHORITY and
            freeze["protocol_sha256"] == sha256(PROTOCOL) and freeze["case_matrix_sha256"] ==
            sha256(Path(__file__).with_name("s6_4_wp4_cases.py")), "source or protocol identity differs")
    full = list(matrix())
    manifest = {c["case"]: c for c in freeze["cases"]}
    require(manifest == {c.key: dict(case=c.key, **asdict(c)) for c in full if c.key in manifest}
            and (freeze["selection"] != "full" or len(manifest) == len(full)), "frozen manifest differs")
    status = load(args.archive / "completed.json")["exit_codes"]
    require(status.keys() == manifest.keys() and not any(status.values()), "not all collected cases passed")
    chosen = set(args.case or manifest.keys())
    require(chosen and chosen <= manifest.keys(), "requested case was not collected")
    tables = Tables()
    for case in full:
        if case.key in chosen:
            with extract(args.archive, case) as dest:
                case_result(case, dest, tables)
    tables.save(args.output, args.check)
    print(f"Verified {len(chosen)} WP-4 cases, all durable prefixes, cut states and per-identity budgets.")


if __name__ == "__main__":
    main()
