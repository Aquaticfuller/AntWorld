"""Verify admitted RM-02 observer samples and evaluate the frozen budgets."""

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import random
import statistics

from analyze_s6_3_2_performance import describe, quantile
from analyze_s6_3_3_1_performance import digest, load, read, telemetry


ROOT = Path(__file__).resolve().parents[1]
CELLS = ("dense512", "dense2048", "depot32")
REFERENCE = ROOT / "experiments/s6_4_rm01_r1/controlled/contacts/session1/contacts.csv"
DENSE_FIELDS = ("events", "pending", "checkpoint_bytes", "state_hash", "trace_hash", "decisions",
                "candidates", "bucket_queries", "tree_visits", "maximum_candidates")
IDENTITY = (*DENSE_FIELDS, "checkpoint_sha256", "sim_ms")


def ci(groups):
    rng = random.Random(63201)
    sessions = sorted(groups)
    stats = {field: [] for field in ("p50", "p95", "paired_p50")}
    for _ in range(4096):
        sample = [block for session in rng.choices(sessions, k=len(sessions))
                  for block in rng.choices(groups[session], k=12)]
        on = [v for block in sample for v in block["on"]]
        off = [v for block in sample for v in block["off"]]
        stats["p50"].append(statistics.median(on) / statistics.median(off))
        stats["p95"].append(quantile(on, .95) / quantile(off, .95))
        stats["paired_p50"].append(statistics.median(statistics.median(b["on"]) / statistics.median(b["off"])
                                                   for b in sample))
    return {field: [quantile(values, .025), quantile(values, .975)] for field, values in stats.items()}


def analyse_cell(samples, cuts, complete):
    groups = defaultdict(dict)
    time_stats = {}
    for row in samples:
        groups[int(row["session"])].setdefault(int(row["block"]), []).append(row)
    control = [r for r in samples if r["block"] == "0"]
    measure = [r for r in samples if int(r["block"]) > 0]
    measured_cuts = [r for r in cuts if int(r["block"]) > 0]
    metrics = ("setup_ms", "observer_init_ms", "advance_ms", "total_ms", "checkpoint_ms", "restore_ms",
               "peak_rss_bytes", "sqlite_bytes", "wal_bytes_at_cut", "flush_ms")
    for arm in ("off", "on"):
        arm_rows = [r for r in measure if r["arm"] == arm]
        if arm_rows:
            time_stats[arm] = {key: describe([float(r[key]) for r in arm_rows]) for key in metrics}
    if not complete:
        return dict(status="INCONCLUSIVE" if samples else "NOT_RUN", measured_rows=len(measure), statistics=time_stats)
    assert len(groups) == 3 and len(control) == 12 and len(measure) == 144
    control_ratio = statistics.median(float(r["total_ms"]) for r in control if r["treatment"] == "off-b") / (
        statistics.median(float(r["total_ms"]) for r in control if r["treatment"] == "off-a"))
    ratios = {label: time_stats["on"]["total_ms"][label] / time_stats["off"]["total_ms"][label]
              for label in ("p50", "p95", "p99")}
    pairs = []
    batch = defaultdict(list)
    peak = []
    for session, blocks in sorted(groups.items()):
        for number in range(1, 13):
            rows = blocks[number]
            assert len(rows) == 4
            values = {arm: [float(r["total_ms"]) for r in rows if r["arm"] == arm] for arm in ("off", "on")}
            batch[session].append(values)
            pairs.append(dict(session=session, block=number,
                              on_off_p50=statistics.median(values["on"]) / statistics.median(values["off"])))
            for left, right in ((0, 1), (2, 3)):
                on, off = sorted((rows[left], rows[right]), key=lambda r: r["arm"], reverse=True)
                assert on["arm"] == "on" and off["arm"] == "off"
                peak.append(int(on["peak_rss_bytes"]) - int(off["peak_rss_bytes"]))
    foreground = describe([float(r["capture_ms"]) for r in measured_cuts])
    submission = describe([float(r["publish_ms"]) for r in measured_cuts])
    stopped = describe([float(r["capture_ms"]) + float(r["publish_ms"]) for r in measured_cuts])
    flush_max = max(float(r["flush_ms"]) for r in measure if r["arm"] == "on")
    within = (ratios["p50"] <= 1.10 and ratios["p95"] <= 1.20 and stopped["p95"] <= 5 and
              max(stopped["maximum"], flush_max) <= 20 and max(peak) <= 16 * 1024 * 1024)
    return dict(status=("INCONCLUSIVE" if not .90 <= control_ratio <= 1.10 else "PASS" if within else "FAIL"),
                measured_rows=len(measure), control_p50_ratio=control_ratio, ratios=ratios, intervals_95=ci(batch),
                paired_p50=statistics.median(r["on_off_p50"] for r in pairs), pairs=pairs,
                peak_paired_increment_bytes=max(peak), foreground_capture_ms=foreground,
                durable_submission_ms=submission, foreground_cut_ms=stopped, maximum_final_flush_ms=flush_max,
                statistics=time_stats)


def verify(raw):
    freeze = load(raw / "freeze.json")
    start = load(raw / "batch_start.json")
    result = load(raw / "batch_result.json")
    assert start["freeze_sha256"] == digest(raw / "freeze.json")
    assert freeze["created_utc_ns"] < result["started_utc_ns"] == start["started_utc_ns"]
    config = load(raw / "configuration.json")
    assert config["binary_sha256"] == freeze["binary_sha256"]
    reference = {f"dense{r['population']}": r for r in read(REFERENCE)
                 if r["layout"] == "dense" and r["policy"] == "bounded"}
    records, all_cuts, valid, errors = [], [], [], []
    identities = {}
    for name, plan_hash in freeze["schedules"].items():
        folder = raw / name
        assert digest(folder / "schedule.csv") == plan_hash
        if not (folder / "receipt.json").exists():
            continue
        receipt = load(folder / "receipt.json")
        plan = read(folder / "schedule.csv")
        samples = read(folder / "samples.csv")
        cuts = read(folder / "captures.csv")
        assert len(samples) == receipt["rows"] <= len(plan)
        assert receipt["binary_sha256"] == freeze["binary_sha256"]
        admitted = load(folder / f"admission{receipt['admission_attempt']}_receipt.json")
        assert admitted["admitted"]
        assert len(read(folder / f"admission{receipt['admission_attempt']}.csv")) == 60
        assert admitted["ended_utc_ns"] <= receipt["started_utc_ns"]
        grouped_cuts = defaultdict(list)
        for row in cuts:
            grouped_cuts[row["sample"]].append(row)
        for row, scheduled in zip(samples, plan):
            assert all(row[k] == v for k, v in scheduled.items())
            cell = row["cell"]
            if cell in reference and any(row[key] != reference[cell][key] for key in DENSE_FIELDS):
                errors.append([name, row["sample"], "ARCHIVED_DENSE_WORKLOAD_MISMATCH"])
            identity = tuple(row[key] for key in IDENTITY)
            if identity != identities.setdefault(cell, identity) or row["exact_restore"] != "1" or row["conserved"] != "1":
                errors.append([name, row["sample"], "MATCHED_WORKLOAD_MISMATCH"])
            detail = grouped_cuts[row["sample"]]
            count = (91 if cell == "depot32" else 1) if row["arm"] == "on" else 0
            if len(detail) != count or any(int(d["dropped"]) for d in detail) or (
                    detail and (detail[-1]["cursor"] != row["events"] or
                                sum(int(d["examined"]) for d in detail) != int(row["events"]))):
                errors.append([name, row["sample"], "INCOMPLETE_OBSERVATION"])
            cpu = str(config["selected_logical"])
            if not (row["start_processor"] == row["end_processor"] == cpu and
                    receipt["started_utc_ns"] <= int(row["start_utc_ns"]) <= int(row["end_utc_ns"])
                    <= receipt["ended_utc_ns"]):
                errors.append([name, row["sample"], "TIMING_SCOPE_MISMATCH"])
        _, telemetry_ok = telemetry(folder, receipt)
        if telemetry_ok and receipt["exit_code"] == 0 and len(samples) == len(plan) == 168:
            valid.append(name)
        records.extend(samples)
        all_cuts.extend(cuts)
    assert valid == result["completed"]
    complete = len(valid) == 3 and not errors
    cells = {name: analyse_cell([r for r in records if r["cell"] == name],
                                [r for r in all_cuts if r["cell"] == name], complete) for name in CELLS}
    status = ("FAIL" if any(c["status"] == "FAIL" for c in cells.values()) else
              "PASS" if all(c["status"] == "PASS" for c in cells.values()) else
              "INCONCLUSIVE" if records else "NOT_RUN")
    return dict(status=status, completed_sessions=valid, measurements=len(records), errors=errors, cells=cells,
                raw_batch_sha256=hashlib.sha256((raw / "batch_result.json").read_bytes()).hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw", type=Path)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    report = verify(args.raw)
    encoded = json.dumps(report, indent=2) + "\n"
    args.report.write_text(encoded, encoding="utf-8", newline="\n")
    print(report["status"], report["measurements"])


if __name__ == "__main__":
    main()
