"""Reevaluate the archived RM-02 measurements against the original written gates."""

import argparse
from collections import defaultdict
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import statistics

import analyze_s6_4_rm02_performance as historical
from analyze_s6_3_3_1_performance import digest, finite, load, read, telemetry
from analyze_s6_3_2_performance import quantile


ROOT = historical.ROOT
ARCHIVE = ROOT / "experiments/s6_4_rm02_sprint/performance"
OUTPUT = ROOT / "experiments/s6_4_rm02_r1/performance"
PROTOCOL = ROOT / "research/s6_4_rm02_sprint/FROZEN_ENGINEERING_PROTOCOL.md"
MAPPING = ROOT / "experiments/s6_2/hwinfo_columns_v2.json"
CONFIRMATION = ROOT / "experiments/s6_3_3_1/performance/instrument_v2_confirmation/receipt.json"
BATCHES = ("observer", "observer_encoded", "observer_background")
CELLS = historical.CELLS
SENSORS = ("package_temperature_c", "package_power_w", "p0_t0_effective_clock_mhz")
DRAIN_FIELDS = ("session", "sample", "cell", "block", "slot", "arm", "start_utc_ns", "end_utc_ns",
                "advance_ms", "total_ms", "flush_ms", "background_write_ms", "peak_queue_bytes",
                "sqlite_bytes", "wal_bytes_at_cut")
MIB = 1024 * 1024


def require(ok, message):
    if not ok:
        raise ValueError(message)


def verify_manifest(folder):
    path = folder / "public_export_manifest.json"
    rows = load(path)
    files = {file.relative_to(folder).as_posix(): file for file in folder.rglob("*") if file.is_file()}
    del files[path.name]
    require(len(rows) == len(files) and {r["path"] for r in rows} == files.keys(), "export manifest file set")
    for row in rows:
        file = files[row["path"]]
        require(file.stat().st_size == row["bytes"] and digest(file) == row["public_sha256"], f"changed export: {file}")
        require(row["process_inventory_removed"] or row["source_sha256"] == row["public_sha256"],
                f"unexplained source/export difference: {file}")
    return digest(path)


def matches_mapping(expected):
    # The collector froze the Windows copy. Git also permits an LF checkout of this file.
    lf = MAPPING.read_bytes().replace(b"\r\n", b"\n")
    return any(hashlib.sha256(data).hexdigest() == expected for data in (lf, lf.replace(b"\n", b"\r\n")))


def expected_schedule(session):
    rows = []
    for cell in (CELLS[::-1] if session == 2 else CELLS):
        for block in range(-1, 13):
            a, b = ("off-a", "off-b") if block == 0 else ("off", "on")
            if (session + block) % 2 == 0:
                a, b = b, a
            for slot, treatment in enumerate((a, b, b, a)):
                rows.append(dict(sample=str(len(rows)), session=str(session), cell=cell, block=str(block),
                                 slot=str(slot), treatment=treatment, arm="on" if treatment == "on" else "off"))
    return rows


def admission_checks(rows):
    checks = {}
    for key in ("system_busy_pct", "processor_busy_pct"):
        values = [float(r[key]) for r in rows if finite(r[key])]
        checks[key + "_complete"] = len(values) == 60
        checks[key + "_p50"] = statistics.median(values) if values else None
        checks[key + "_p95"] = quantile(values, .95) if values else None
    checks["native_intervals_valid"] = all(r["nonidle_wall_all_valid"] == "True" and
                                           800_000_000 <= int(r["wall_delta_ns"]) <= 1_200_000_000 for r in rows)
    checks["power_valid"] = all(r["ac"] == "1" and r["battery_saver"] == "0" for r in rows)
    checks["sensors_valid"] = all(finite(r["sensor_age_s"]) and -2 <= float(r["sensor_age_s"]) <= 10 and
                                  all(finite(r[key]) for key in SENSORS) for r in rows)
    admitted = all(value for key, value in checks.items() if not key.endswith(("_p50", "_p95"))) and all(
        value <= (10 if key.endswith("_p50") else 20)
        for key, value in checks.items() if key.endswith(("_p50", "_p95")))
    return checks, admitted


def verify_admissions(folder, receipt, selected):
    attempts = int(receipt["admission_attempt"])
    require(1 <= attempts <= 3, f"admission attempt count: {folder}")
    require(len(list(folder.glob("admission*.csv"))) == len(list(folder.glob("admission*_receipt.json"))) == attempts,
            f"admission archive incomplete: {folder}")
    previous_end = None
    results = []
    for number in range(1, attempts + 1):
        original = load(folder / f"admission{number}_receipt.json")
        rows = read(folder / f"admission{number}.csv")
        start, end = original["started_utc_ns"], original["ended_utc_ns"]
        stamps = [int(row["utc_ns"]) for row in rows]
        require(len(rows) == 60 and start <= stamps[0] < stamps[-1] <= end and stamps == sorted(set(stamps)),
                f"admission sample coverage: {folder} attempt {number}")
        require(previous_end is None or start - previous_end >= 300_000_000_000,
                f"admission cooldown: {folder} attempt {number}")
        require(original["source_header_sha256"] == load(MAPPING)["source_header_sha256"],
                f"HWiNFO source header: {folder}")
        require(all(not finite(row["processor_busy_pct"]) or (
            row["processor_busy_pct_status"] == "VALID" and
            row["processor_busy_pct"] == row[f"cpu{selected}_nonidle_wall_pct"]) for row in rows),
            f"selected logical CPU instrument: {folder}")
        checks, admitted = admission_checks(rows)
        require(original["attempt"] == number and admitted == original["admitted"] == (number == attempts),
                f"admission decision mismatch: {folder} attempt {number}")
        for key, value in checks.items():
            recorded = original["checks"][key]
            equal = math.isclose(value, recorded, rel_tol=1e-12) if type(value) is float else value == recorded
            require(equal, f"admission {key} mismatch: {folder} attempt {number}")
        results.append(dict(attempt=number, admitted=admitted, checks=checks))
        previous_end = end
    require(previous_end <= receipt["started_utc_ns"], f"admission overlaps timing: {folder}")
    return results


def verify_sample(row, cuts):
    label = f"session {row['session']} sample {row['sample']}"
    depot = row["cell"] == "depot32"
    on = row["arm"] == "on"
    end = 90 * 86_400_000 if depot else 10_000
    expected_times = list(range(0, end + 1, 86_400_000)) if depot else [end]
    require(int(row["sim_ms"]) == end and [int(c["sim_ms"]) for c in cuts] == (expected_times if on else []),
            f"missing or unexpected cuts: {label}")
    require(0 <= int(row["sqlite_bytes"]) <= 64 * MIB and bool(int(row["sqlite_bytes"])) == on,
            f"sidecar quota or missing database: {label}")
    require(0 <= int(row.get("peak_queue_bytes", 0)) <= 4 * MIB, f"queued payload budget: {label}")
    previous = 0
    cut_wall = 0
    for cut in cuts:
        require(all(cut[k] == row[k] for k in ("session", "cell", "block", "slot", "treatment", "arm")),
                f"capture identity mismatch: {label}")
        cursor, examined, selected = (int(cut[k]) for k in ("cursor", "examined", "selected"))
        require(0 <= selected <= examined == cursor - previous and int(cut["dropped"]) == 0 and
                int(cut["records"]) == selected + (34 if depot else 65) and 0 < int(cut["payload_bytes"]) <= 3 * MIB,
                f"cut coverage or payload quota: {label}")
        previous = cursor
        require(all(finite(cut[k]) and float(cut[k]) >= 0 for k in ("capture_ms", "publish_ms")),
                f"invalid cut timing: {label}")
        cut_wall += float(cut["capture_ms"]) + float(cut["publish_ms"])
    require(not on or previous == int(row["events"]), f"terminal event coverage: {label}")
    timings = ("setup_ms", "observer_init_ms", "advance_ms", "total_ms", "flush_ms", "checkpoint_ms", "restore_ms")
    require(all(finite(row[k]) and float(row[k]) >= 0 for k in timings), f"missing timing: {label}")
    require(float(row["total_ms"]) >= float(row["advance_ms"]) + cut_wall + float(row["flush_ms"]),
            f"total omits timed advance, foreground cuts or terminal persistence: {label}")
    return cut_wall


def frozen_gates(cell):
    return {
        "off_off_repeatability": .90 <= cell["control_p50_ratio"] <= 1.10,
        "total_p50": cell["ratios"]["p50"] <= 1.10,
        "total_p95": cell["ratios"]["p95"] <= 1.20,
        "foreground_p95": cell["foreground_cut_ms"]["p95"] <= 5,
        "foreground_max": cell["foreground_cut_ms"]["maximum"] <= 20,
        "incremental_peak_rss": cell["peak_paired_increment_bytes"] <= 16 * MIB,
    }


def verify_batch(folder, identities):
    manifest = verify_manifest(folder)
    freeze = load(folder / "freeze.json")
    require(freeze["configuration"] == "Release" and freeze["protocol_sha256"] == digest(PROTOCOL) and
            matches_mapping(freeze["sensor_mapping_sha256"]) and freeze["confirmation_sha256"] == digest(CONFIRMATION),
            f"frozen collection identity: {folder}")
    original = historical.verify(folder)
    require(original == load(folder.with_name(folder.name + "_analysis.json")), f"historical analysis changed: {folder}")
    require(original["completed_sessions"] == ["session1", "session2", "session3"] and original["measurements"] == 504
            and not original["errors"], f"incomplete or mismatched benchmark: {folder}")
    sessions, drains = [], []
    selected = load(folder / "configuration.json")["selected_logical"]
    for number in range(1, 4):
        session = folder / f"session{number}"
        receipt = load(session / "receipt.json")
        admissions = verify_admissions(session, receipt, selected)
        require(read(session / "schedule.csv") == expected_schedule(number), f"frozen paired schedule: {session}")
        hardware, ok = telemetry(session, receipt)
        require(ok, f"incomplete timing telemetry: {session}")
        captures = defaultdict(list)
        for cut in read(session / "captures.csv"):
            captures[cut["sample"]].append(cut)
        count = sum(map(len, captures.values()))
        for row in read(session / "samples.csv"):
            identity = tuple(row[key] for key in historical.IDENTITY)
            require(identity == identities.setdefault(row["cell"], identity), f"workload changed across builds: {session}")
            cut_wall = verify_sample(row, captures.pop(row["sample"], []))
            if float(row["flush_ms"]) > 20:
                drains.append(dict(batch=folder.name, **{key: row.get(key, "") for key in DRAIN_FIELDS},
                                   foreground_sum_ms=round(cut_wall, 9)))
        require(not captures, f"orphan capture: {session}")
        sessions.append(dict(session=number, attempts=admissions, captures=count, telemetry=hardware))
    cells = {}
    for name, stats in original["cells"].items():
        checks = frozen_gates(stats)
        status = "INCONCLUSIVE" if not checks["off_off_repeatability"] else "PASS" if all(checks.values()) else "FAIL"
        cells[name] = dict(stats, status=status, historical_status=stats["status"], checks=checks)
    statuses = {cell["status"] for cell in cells.values()}
    status = "FAIL" if "FAIL" in statuses else "INCONCLUSIVE" if "INCONCLUSIVE" in statuses else "PASS"
    return dict(status=status, historical_status=original["status"], timing_rows=504, retained_rows=432,
                source_commit=freeze["source_commit"], cpp_tree=freeze["cpp_tree"], binary_sha256=freeze["binary_sha256"],
                export_manifest_sha256=manifest, old_analysis_sha256=digest(folder.with_name(folder.name + "_analysis.json")),
                sessions=sessions, cells=cells), drains


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=ARCHIVE)
    parser.add_argument("--out", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true", help="compare with the published reconciliation")
    args = parser.parse_args()
    identities, results, drains = {}, {}, []
    for name in BATCHES:
        results[name], tail = verify_batch(args.archive / name, identities)
        drains.extend(tail)
    report = dict(protocol_sha256=digest(PROTOCOL), batches=results)
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, ("batch", *DRAIN_FIELDS, "foreground_sum_ms"), lineterminator="\n")
    writer.writeheader()
    writer.writerows(drains)
    args.out.mkdir(parents=True, exist_ok=True)
    for name, content in (("performance_reconciliation.json", json.dumps(report, indent=2) + "\n"),
                          ("terminal_drains_over_20ms.csv", stream.getvalue())):
        path = args.out / name
        if args.check:
            require(path.read_bytes() == content.encode(), f"reconciliation differs: {path}")
        else:
            path.write_bytes(content.encode())
    for name, result in results.items():
        print(f"{name}: {result['historical_status']} historical, {result['status']} written protocol; "
              f"{result['timing_rows']} rows, {result['retained_rows']} retained")
    return 0 if results[BATCHES[-1]]["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
