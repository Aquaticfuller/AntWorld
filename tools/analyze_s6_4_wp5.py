"""Reconcile inherited survival and new WP-5 canonical, storage and spatial evidence."""

import argparse
from collections import Counter, defaultdict
from contextlib import closing, contextmanager
from dataclasses import asdict
import hashlib
from pathlib import Path
import shutil
import struct
import tarfile
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from analyze_s6_4_rm02 import ledger_record, state_record
from analyze_s6_4_wp4 import AUTHORITY, REQUIRED_FACTS, Tables, durable_midpoint, extract, focal_matches, integers, world_balance
from read_s6_4_rm02_sidecar import open_sidecar, require
from run_s6_4_rm02 import sha256
from run_s6_4_wp5 import ARTIFACTS
from run_s6_4_wp5_performance import BASE, PROTOCOL
from s6_4_wp4_budget import Budgets
from s6_4_wp4_cases import SEEDS, matrix as inherited_matrix
from s6_4_wp5_cases import matrix
from s6_4_wp5_cohorts import LANDMARK, paired, run_cohort, summarize
from s6_4_wp5_geometry import MaterialReplay
from verify_s6_4_wp3 import canonical, load, row, rows, sequence


TIMINGS = {"capture_ms", "lineage_ms", "probe_ms", "submission_ms"}


def run_identity(case, config):
    return SimpleNamespace(key=case.key, world_id=config["world_id"], horizon=int(config["horizon_ms"]))


@contextmanager
def unpack(root, case):
    folder = root / "raw" / case.key
    receipt = load(folder / "receipt.json")
    require(receipt["case"] == case.key and all(receipt[key] == value for key, value in asdict(case).items()),
            "wrong assay receipt identity")
    require(receipt["exit_code"] == receipt["program_exit_code"] == 0, "assay did not complete")
    archive = folder / "raw.tar.gz"
    require(archive.stat().st_size == receipt["archive_bytes"] and sha256(archive) == receipt["archive_sha256"],
            "archive identity differs")
    expected = receipt["artifacts"]
    with TemporaryDirectory(prefix="wp5-verify-") as tmp, tarfile.open(archive, "r:gz") as tar:
        dest = Path(tmp)
        members = sequence(tar, lambda item: item.name)
        require(set(members) == set(expected) == set(ARTIFACTS), "incomplete case archive")
        for name, member in members.items():
            require(member.isfile() and member.size == expected[name]["bytes"] <= 128 * 1024 * 1024,
                    "invalid archive member")
            with tar.extractfile(member) as source, (dest / name).open("xb") as target:
                shutil.copyfileobj(source, target)
            require(sha256(dest / name) == expected[name]["sha256"], "archive member hash differs")
        yield dest


def states_from(dest):
    state, spec = defaultdict(dict), sequence((integers(r) for r in rows(dest / "lineage_inputs.csv")), lambda r: r["id"])
    for r in rows(dest / "lineage.csv"):
        q = integers(r, ("x_m", "y_m", "z_m"))
        require(q["id"] not in state[q["cut"]], "duplicate actor cut")
        state[q["cut"]][q["id"]] = q
    return state, spec


def inherited(case, dest, tables):
    config = row(dest / "configuration.csv")
    run = run_identity(case, config)
    with open_sidecar(dest / "observer.sqlite") as (metadata, cuts), closing(cuts):
        facts = [fact for fact, _ in canonical(dest / "canonical.bin", metadata["world"])]
    state, specs = states_from(dest)
    budget, by_actor = Budgets(specs, config), defaultdict(list)
    for f in facts:
        budget.read(f, {})
    for at in sorted(state):
        for actor, q in state[at].items():
            by_actor[actor].append(q)
    require(set(specs) == set(by_actor) == set(budget.individuals), "inherited census has a lineage gap")
    outcomes = run_cohort(run, budget, by_actor, facts, tables)
    return summarize(run, outcomes, by_actor, facts, config, tables)


def validate_gate(material, routes, tables, run):
    expected = {"mine": ("SoilExcavated", "Success"), "fill": ("SoilFilled", "Success"),
                "attempt_crossing": ("ActionRejected", "Blocked"), "future_revision": ("ActionRejected", "StaleGeometry"),
                "reopen": ("SoilExcavated", "Success"), "too_fast_reopened": ("ActionRejected", "TooFast"),
                "cross_reopened": ("Moved", "Success"), "drop": ("SoilDropped", "Success"),
                "pickup": ("SoilPickedUp", "Success")}
    actual = {}
    for source, request in material.schedules.items():
        fact = material.resolutions[source]
        label = request["kind"]
        require(label not in actual and fact.time == int(request["execute_ms"]), "wrong gate event time")
        actual[label] = fact.kind, fact.outcome
        tables.add("gate_witness", run, **request, event=fact.event, event_kind=fact.kind, outcome=fact.outcome)
    require(actual == expected, "gate mechanism did not reproduce the expected controls")
    by_time = {int(r["sim_ms"]): r["found"] for r in routes.values()}
    require((by_time[100], by_time[300], by_time[700]) == ("1", "0", "1"), "gate connectivity differs")


def verify_new(case, dest, tables):
    config, summary = row(dest / "configuration.csv"), row(dest / "summary.csv")
    require(all(config[key] == str(value) for key, value in asdict(case).items())
            and config["classification"] == "ENGINEERING_FIXTURE", "wrong WP-5 run configuration")
    run = run_identity(case, config)
    states, specs = states_from(dest)
    cuts = sequence(rows(dest / "cuts.csv"), lambda r: int(r["cut"]))
    routes = sequence(rows(dest / "routes.csv"), lambda r: int(r["cut"]))
    budget, by_actor = Budgets(specs, config), defaultdict(list)
    material = MaterialReplay(dest, run, tables)
    nest = (6, 12, 12) if case.family == "gate" else (8, 12, 12) if case.family in {"excavation", "joint"} else (16, 12, 12)
    ends = {}
    with open_sidecar(dest / "observer.sqlite") as (metadata, published), closing(published):
        require((metadata["world_id"], metadata["seed"], metadata["origin"], metadata["lineage"],
                 metadata["all_relevant"], metadata["activity_care"]) ==
                (run.world_id, case.seed, 0, "survival-excavation", True, False), "wrong Sidecar plan")
        encoded_facts = canonical(dest / "canonical.bin", metadata["world"])
        for cut in published:
            seq, at, end = cut["seq"], cut["time"], cut["cursor"]
            ends[seq] = end, at
            current = integers(cuts[seq], TIMINGS)
            fields = ("cursor", "sim_ms", "examined", "selected", "records", "payload_bytes")
            require(tuple(current[k] for k in fields) == (end, at, cut["examined"], cut["selected"], cut["records"], cut["raw_bytes"]),
                    "inconsistent cut payload or cursor")
            require(current["dropped"] == cut["dropped"] == 0 and 0 < current["lineage_bytes"] <= 256 * 1024
                    and 0 < current["probe_bytes"] <= 64 * 1024, "incomplete or over-budget view")
            scoped = iter(bytes(value) for tag, value in cut["payload"] if tag == 1)
            expected = next(scoped, None)
            for fact, encoded in encoded_facts[cut["start"]:end]:
                if encoded == expected:
                    expected = next(scoped, None)
                else:
                    require(fact.kind not in REQUIRED_FACTS, "required nutrient fact not published")
                require(fact.time <= at, "future fact in cut")
                budget.read(fact, {})
                material.read(fact)
            require(expected is None, "sidecar fact has no canonical origin")
            observed = states[seq]
            require(set(observed) == set(budget.individuals) and len(observed) <= 128, "incomplete lineage cut")
            calculated = {}
            for actor, q in sorted(observed.items()):
                require((q["cursor"], q["sim_ms"]) == (end, at), "lineage cut identity differs")
                calculated[actor] = budget.individuals[actor].evaluate(q, at)
                by_actor[actor].append(q)
            focal = dict(state_record(value) for tag, value in cut["payload"] if tag == 2)
            require(set(focal) == set(metadata["focal"]), "focal set differs")
            for actor, record in focal.items():
                focal_matches(record, observed[actor], specs[actor])
            ledger, = (ledger_record(value) for tag, value in cut["payload"] if tag == 3)
            world_balance(ledger, observed, calculated, current)
            material.check_cut(current, routes[seq], ledger, nest)
            stages = Counter(q["stage"] for q in observed.values())
            tables.add("population_timeline", run, cut=seq, cursor=end, sim_ms=at, egg=stages[0], larva=stages[1],
                       pupa=stages[2], adult=stages[3], dead=stages[4], provenance="CUT_SNAPSHOT")
        anchors = metadata["anchors"]
    require(set(ends) == set(states) == set(cuts) == set(routes) and len(ends) == int(summary["cuts"]), "missing run cuts")
    require(set(specs) == set(by_actor) and summary["status"] == "PASS" and
            summary["exact_off"] == summary["sqlite_midpoint_exact"] == "1", "inexact continuation or lineage")
    middle, final = sorted(anchors)
    end, horizon = ends[final]
    require(final == len(ends) and end == len(encoded_facts) == int(summary["events"]) and horizon == run.horizon
            and ends[middle][1] == int(config["midpoint_ms"]), "wrong anchors or endpoints")
    require(anchors[final] == sha256(dest / "final.chk") and anchors[middle] == sha256(dest / "midpoint.chk"),
            "Sidecar checkpoint anchor mismatch")
    durable = durable_midpoint(dest / "midpoint.sqlite")
    prefix = ends[middle][0]
    digest = hashlib.sha256()
    for _, data in encoded_facts[:prefix]:
        digest.update(struct.pack("<I", len(data)))
        digest.update(data)
    require((durable["world"], durable["facts"], durable["canonical_sha256"]) == (run.world_id, prefix, digest.hexdigest()),
            "midpoint database canonical prefix differs")
    facts = [f for f, _ in encoded_facts]
    for (kind, outcome), count in sorted(Counter((f.kind, f.outcome) for f in facts).items()):
        tables.add("event_counts", run, event_kind=kind, outcome=outcome, events=count)
    results = material.finish(dest)
    seen_work = set()
    for r in rows(dest / "excavators.csv"):
        seq, actor, cursor, enabled = (int(r[key]) for key in ("cut", "actor", "cursor", "enabled"))
        require((seq, actor) not in seen_work and actor in states[seq] and cursor == ends[seq][0]
                and enabled in (0, 1), "excavator snapshot not bound to a unique cut")
        require(states[seq][actor]["stage"] != 4 or not enabled, "dead actor retained an active excavation program")
        seen_work.add((seq, actor))
    if case.family == "gate":
        validate_gate(material, routes, tables, run)
    if case.arm in {"isolated", "shielded"}:
        require(results["digs"] == 0, "unreachable arm created a dig fact")
    outcomes = run_cohort(run, budget, by_actor, facts, tables)
    obs = summarize(run, outcomes, by_actor, facts, config, tables)
    counts = Counter(f.kind for f in facts)
    first_death = next((f.event for f in facts if f.kind == "AntDied"), len(facts) + 1)
    soil_after_death = sum(f.kind == "SoilExcavated" and f.event > first_death for f in facts)
    obs |= results | {"soil_digs_after_first_death": soil_after_death, "food_deliveries": counts["FoodDelivered"]}
    tables.add("excavation_runs", run, family=case.family, arm=case.arm, workers=case.workers, seed=case.seed,
               horizon_ms=horizon, deaths=obs["deaths_by_cutoff"], food_deliveries=obs["food_deliveries"],
               food_collections=counts["FoodCollected"], foraging_starts=counts["ForagingStarted"],
               crop_ingestions=counts["CargoIngested"], positive_gifts=counts["NutritionTransferred"],
               soil_digs_after_first_death=soil_after_death, **results)
    tables.add("run_identity", run, initial_sha256=sha256(dest / "initial.chk"), final_sha256=anchors[final],
               midpoint_sha256=anchors[middle], canonical_sha256=sha256(dest / "canonical.bin"),
               midpoint_fact_sha256=digest.hexdigest(), state_hash=summary["state_hash"], trace_hash=summary["trace_hash"],
               events=end, cuts=final, midpoint_events=prefix, observed_individuals=len(specs))
    tables.add("assay_costs", run, family=case.family, arm=case.arm, workers=case.workers, seed=case.seed,
               **{key: summary[key] for key in ("advance_ms", "wall_ms", "midpoint_ms", "drain_ms", "writer_ms",
                   "replay_and_canonical_ms", "peak_queue_bytes", "rss_bytes", "peak_rss_bytes", "observer_bytes", "midpoint_sqlite_bytes")},
               canonical_bytes=(dest / "canonical.bin").stat().st_size, events=end,
               maximum_foreground_ms=round(max(sum(float(r[key]) for key in TIMINGS) for r in cuts.values()), 8),
               maximum_route_capture_ms=max(float(r["probe_ms"]) for r in cuts.values()),
               maximum_probe_bytes=max(int(r["probe_bytes"]) for r in cuts.values()))
    return obs


def compare(tables, old, new):
    scope = SimpleNamespace(key="PAIRED_CASES", world_id="MULTIPLE")
    def pairs(label, group, a, b, keys):
        require(set(a) == set(b) == set(SEEDS), "missing paired inputs")
        for name in keys:
            values = [a[s][name] - b[s][name] for s in SEEDS]
            effect, lo, hi = paired(values)
            tables.add("paired_contrasts", scope, comparison=label, group=group, metric=name, paired_worlds=6,
                       mean_difference=effect, ci95_lo=lo, ci95_hi=hi, differences=";".join(map(str, values)))

    def group(family, arm, workers):
        return {s: new[f"{family}-{arm}-{workers}-{s}"] for s in SEEDS}

    pairs("care_on_minus_off", 0, group("founding", "on", 0), group("founding", "off", 0),
          ("birth_by_cutoff", "queen_at_day21", "queen_actual_care_completed", "deaths_by_cutoff"))
    for n in (8, 32):
        reference = {s: old[f"ecology-ordinary-{n}-legacy-{s}"] for s in SEEDS}
        pairs("half_worker_reserve_minus_inherited", n, group("worker-reserve", "half", n), reference,
              ("survival_workers_day21", "queen_at_day21", "birth_by_cutoff", "deaths_by_cutoff"))
        pairs("depot_minus_empty_joint", n, group("joint", "depot", n), group("joint", "empty", n),
              ("survival_workers_day21", "food_deliveries", "excavated_q3", "drops", "soil_digs_after_first_death"))
    for n in (4, 8, 32):
        for arm in ("wet", "roomy", "isolated", "shielded"):
            pairs(f"{arm}_minus_compact", n, group("excavation", arm, n), group("excavation", "compact", n),
                  ("decisions", "excavated_q3", "excavated_water_ug", "drops", "loaded_moves", "soil_rejections"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wp4", type=Path)
    parser.add_argument("wp5", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--smoke", action="store_true", help="Verify selected WP-5 archives without the inherited full matrix.")
    args = parser.parse_args()
    tables = Tables()
    freeze, completed = load(args.wp5 / "freeze.json"), load(args.wp5 / "completed.json")
    require(freeze["authority"] == AUTHORITY and freeze["baseline"] == BASE and freeze["protocol_sha256"] == sha256(PROTOCOL)
            and freeze["case_matrix_sha256"] == sha256(Path(__file__).with_name("s6_4_wp5_cases.py"))
            and freeze["runner_sha256"] == sha256(Path(__file__).with_name("run_s6_4_wp5.py")), "collection identity differs")
    inherited_results, new_results = {}, {}
    chosen = set(completed["exit_codes"])
    cases = [c for c in matrix() if c.key in chosen]
    require(freeze["cases"] == [dict(case=c.key, **asdict(c)) for c in cases] and chosen == {c.key for c in cases},
            "incorrect declared case set")
    require({p.name for p in (args.wp5 / "raw").iterdir()} == chosen and all(v == 0 for v in completed["exit_codes"].values()),
            "raw case evidence differs or has a failed execution")
    if not args.smoke:
        require(len(cases) == 139 and freeze["selection"] == "full", "not a full WP-5 collection")
        for case in inherited_matrix():
            with extract(args.wp4, case) as dest:
                inherited_results[case.key] = inherited(case, dest, tables)
        require(len(inherited_results) == 104, "missing inherited control")
    for case in cases:
        try:
            with unpack(args.wp5, case) as dest:
                new_results[case.key] = verify_new(case, dest, tables)
        except (KeyError, ValueError, AssertionError) as error:
            raise ValueError(f"{case.key}: {error}") from error
    if not args.smoke:
        compare(tables, inherited_results, new_results)
    tables.save(args.output, args.check)
    print(f"Verified {len(inherited_results)} inherited and {len(new_results)} new cases with {len(tables.data['cohort_intervals'])} stage intervals")


if __name__ == "__main__":
    main()
