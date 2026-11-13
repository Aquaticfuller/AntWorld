"""Recompute R2 public performance outputs while retaining negative verdicts."""

import argparse
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from reconcile_s6_4_rm02_performance import verify_manifest
from run_s6_4_wp6b_r2_performance import APPEND_LAYOUT, MAPPING, PROTOCOL, check_mapping
from run_s6_4_wp6b import ROOT, sha


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def run(script, *args):
    return subprocess.run([sys.executable, ROOT / "tools" / (script + ".py"), *args], cwd=ROOT).returncode


def compare_outputs(published, calculated):
    if {p.name: sha(p) for p in calculated.iterdir()} != {p.name: sha(p) for p in published.iterdir()}:
        raise ValueError(f"reproduced output differs: {published}")


def check_append_log(archive, freeze, source_key):
    layout = load(APPEND_LAYOUT)
    if freeze[source_key][APPEND_LAYOUT.name] != sha(APPEND_LAYOUT):
        raise ValueError("append-layout receipt differs from the frozen source")
    for session in sorted(archive.glob("session*")):
        if load(session / "hwinfo_provenance.json")["append_layout"] != layout:
            raise ValueError(f"append-layout provenance changed: {session.name}")


def check(root):
    check_mapping()
    native, observer, app = (root / name for name in ("core", "protected-observer", "application"))
    freezes = [load(scope / "freeze.json") for scope in (native, observer, app)]
    if any(f.get("mapping_sha256", f.get("sensor_mapping_sha256")) != sha(MAPPING) for f in freezes):
        raise ValueError("mapped CPU telemetry differs from the frozen instrument")
    if any(f["protocol_sha256"] != sha(PROTOCOL) for f in freezes[1:]):
        raise ValueError("an observation protocol differs from the prospective freeze")
    if run("analyze_s6_3_3_1_performance", "--raw", native, "--out", root / "core-analysis", "--check"):
        raise ValueError("native analysis differs")
    report = root / "protected-observer-analysis.json"
    status = load(report)["status"]
    if load(root / "application-analysis/decision.json")["required"] != 720:
        raise ValueError("changed application performance denominator")
    births, resumed = (root / name for name in ("append-births", "append-application"))
    birth_freeze, resumed_freeze = load(births / "freeze.json"), load(resumed / "freeze.json")
    verify_manifest(births)
    verify_manifest(resumed)
    check_append_log(births / "births", birth_freeze, "script_sha256")
    # The native manifest is at the batch root, while telemetry is below its workload folder.
    check_append_log(resumed, resumed_freeze, "sources")
    if birth_freeze["executables"] != {"births": freezes[0]["executables"]["births"]}:
        raise ValueError("the separate birth workload or executable changed")
    if run("analyze_s6_3_3_1_performance", "--raw", births, "--out", root / "append-births-analysis", "--check"):
        raise ValueError("birth-only analysis differs")
    if any(resumed_freeze[key] != freezes[2][key] for key in ("binary_sha256", "schedules", "cpp_tree", "protocol_sha256")):
        raise ValueError("the continued application workload changed")
    prior, after = app / "session1", resumed / "session1"
    for name, key in (("admission1.csv", "samples_sha256"), ("admission1_receipt.json", "receipt_sha256")):
        if sha(prior / name) != sha(after / name) or sha(after / name) != resumed_freeze["prior_first_admission"][key]:
            raise ValueError("the original declined application admission was replaced")
    if load(after / "admission2_receipt.json")["started_utc_ns"] - load(prior / "admission1_receipt.json")["ended_utc_ns"] < 300_000_000_000:
        raise ValueError("the prior application's retry delay was not honored")
    with TemporaryDirectory() as location:
        # The protected analyzer exits 1 for a scientific/performance outcome other than PASS.
        reproduced = Path(location) / "protected.json"
        rc = run("s6_4_wp6b_r2_protected_observer", "--analyze", observer, reproduced)
        if rc != int(status != "PASS") or not reproduced.is_file() or reproduced.read_bytes() != report.read_bytes():
            raise ValueError("protected observer analysis differs")
        if sys.platform == "win32":
            for source, suffix in ((app, "application"), (resumed, "append-application")):
                calculated = Path(location) / suffix
                if run("profile_s6_4_wp6b_r2", "--out", source, "--analysis", calculated):
                    raise ValueError("application analysis failed")
                compare_outputs(root / f"{suffix}-analysis", calculated)
            experiments = root.parent.parent
            costs = Path(location) / "costs"
            if run("summarize_s6_4_wp6b_r1_costs", "--raw", resumed, "--out", costs,
                   "--v1", experiments / "s6_4_wp6b/formal", "--r1", experiments / "s6_4_wp6b_r1/formal",
                   "--both", root.parent / "both"):
                raise ValueError("application reference equality or phase analysis failed")
            compare_outputs(root / "append-application-costs", costs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    check(parser.parse_args().archive)
