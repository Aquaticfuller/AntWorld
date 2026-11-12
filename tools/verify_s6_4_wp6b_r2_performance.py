"""Recompute R2 public performance outputs while retaining negative verdicts."""

import argparse
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from run_s6_4_wp6b_r2_performance import MAPPING, PROTOCOL, check_mapping
from run_s6_4_wp6b import ROOT, sha


def run(script, *args):
    return subprocess.run([sys.executable, ROOT / "tools" / (script + ".py"), *args], cwd=ROOT).returncode


def check(root):
    check_mapping()
    native, observer, app = (root / name for name in ("core", "protected-observer", "application"))
    freezes = [json.loads((scope / "freeze.json").read_text(encoding="utf-8")) for scope in (native, observer, app)]
    if any(f.get("mapping_sha256", f.get("sensor_mapping_sha256")) != sha(MAPPING) for f in freezes):
        raise ValueError("mapped CPU telemetry differs from the frozen instrument")
    if any(f["protocol_sha256"] != sha(PROTOCOL) for f in freezes[1:]):
        raise ValueError("an observation protocol differs from the prospective freeze")
    if run("analyze_s6_3_3_1_performance", "--raw", native, "--out", root / "core-analysis", "--check"):
        raise ValueError("native analysis differs")
    report = root / "protected-observer-analysis.json"
    status = json.loads(report.read_text(encoding="utf-8"))["status"]
    controls = (root / "application-analysis/decision.json").read_text(encoding="utf-8")
    if json.loads(controls)["required"] != 720:
        raise ValueError("changed application performance denominator")
    with TemporaryDirectory() as location:
        # The protected analyzer exits 1 for a scientific/performance outcome other than PASS.
        reproduced = Path(location) / "protected.json"
        rc = run("s6_4_wp6b_r2_protected_observer", "--analyze", observer, reproduced)
        if rc != int(status != "PASS") or not reproduced.is_file() or reproduced.read_bytes() != report.read_bytes():
            raise ValueError("protected observer analysis differs")
        if sys.platform == "win32":
            calculated = Path(location) / "application"
            if run("profile_s6_4_wp6b_r2", "--out", app, "--analysis", calculated):
                raise ValueError("application analysis failed")
            published = root / "application-analysis"
            if {p.name: sha(p) for p in calculated.iterdir()} != {p.name: sha(p) for p in published.iterdir()}:
                raise ValueError("application analysis differs")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    check(parser.parse_args().archive)
