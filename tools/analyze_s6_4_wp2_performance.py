"""Verify WP-2 native samples using the reconciled RM-02 gate semantics."""

import argparse
from collections import defaultdict
import json
from pathlib import Path

import analyze_s6_4_rm02_performance as previous
from analyze_s6_3_3_1_performance import digest, load, read, telemetry
from reconcile_s6_4_rm02_performance import (
    CONFIRMATION, expected_schedule, frozen_gates, matches_mapping, verify_admissions, verify_manifest, verify_sample,
)
from read_s6_4_rm02_sidecar import require
from run_s6_4_wp2 import PROTOCOL


def verify(root):
    manifest_hash = verify_manifest(root)
    freeze = load(root / "freeze.json")
    require(freeze["protocol_sha256"] == digest(PROTOCOL) and matches_mapping(freeze["sensor_mapping_sha256"])
            and freeze["confirmation_sha256"] == digest(CONFIRMATION) and freeze["configuration"] == "Release",
            "invalid formal freeze")
    old = previous.verify(root)
    if len(old["completed_sessions"]) != 3 or old["errors"]:
        return dict(status="INCONCLUSIVE" if old["measurements"] else "NOT_RUN",
                    original_evaluator=old, manifest_sha256=manifest_hash)
    sessions = []
    selected = load(root / "configuration.json")["selected_logical"]
    for number in range(1, 4):
        folder = root / f"session{number}"
        require(read(folder / "schedule.csv") == expected_schedule(number), "wrong WP-2 paired schedule")
        receipt = load(folder / "receipt.json")
        attempts = verify_admissions(folder, receipt, selected)
        hardware, qualified = telemetry(folder, receipt)
        require(qualified, "incomplete native telemetry")
        grouped = defaultdict(list)
        for cut in read(folder / "captures.csv"):
            grouped[cut["sample"]].append(cut)
        samples = read(folder / "samples.csv")
        for sample in samples:
            verify_sample(sample, grouped.pop(sample["sample"], []))
        require(not grouped, "orphan foreground cut")
        sessions.append(dict(session=number, rows=len(samples), attempts=attempts, telemetry=hardware))
    cells = {}
    for name, info in old["cells"].items():
        checks = frozen_gates(info)
        status = "INCONCLUSIVE" if not checks["off_off_repeatability"] else "PASS" if all(checks.values()) else "FAIL"
        cells[name] = info | dict(status=status, checks=checks)
    statuses = {info["status"] for info in cells.values()}
    result = "FAIL" if "FAIL" in statuses else "INCONCLUSIVE" if "INCONCLUSIVE" in statuses else "PASS"
    return dict(status=result, timing_rows=old["measurements"], retained_rows=432, sessions=sessions, cells=cells,
                binary_sha256=freeze["binary_sha256"], source_commit=freeze["source_commit"],
                manifest_sha256=manifest_hash)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("report", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = verify(args.archive)
    data = (json.dumps(report, indent=2) + "\n").encode()
    if args.check:
        require(args.report.read_bytes() == data, "WP-2 performance report differs")
    else:
        args.report.write_bytes(data)
    print(report["status"], report.get("timing_rows", 0))
    return int(report["status"] != "PASS")


if __name__ == "__main__":
    raise SystemExit(main())
