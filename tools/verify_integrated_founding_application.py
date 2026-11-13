"""Recompute both public application qualification receipts and every timing tail."""

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from reconcile_s6_4_rm02_performance import verify_manifest
from run_s6_4_wp6b_r2_performance import APPEND_LAYOUT, MAPPING, check_mapping
from run_s6_4_wp6b import ROOT, sha
from verify_s6_4_wp6b_r2_performance import compare_outputs, run


def verify(root):
    check_mapping()
    protocol = ROOT / "research/s6_4_integrated_founding/INTEGRATED_PERFORMANCE_PROTOCOL.md"
    layout = json.loads(APPEND_LAYOUT.read_text(encoding="utf-8"))
    with TemporaryDirectory() as scratch:
        for scope, expected in (("inherited", 720), ("integrated", 96)):
            name = f"application-{scope}"
            archive = root / name
            verify_manifest(archive)
            freeze = json.loads((archive / "freeze.json").read_text(encoding="utf-8"))
            if (freeze["protocol_sha256"] != sha(protocol) or freeze["mapping_sha256"] != sha(MAPPING)
                    or freeze["sources"][APPEND_LAYOUT.name] != sha(APPEND_LAYOUT)):
                raise ValueError(f"{name}: qualification or telemetry freeze changed")
            for provenance in archive.glob("session*/hwinfo_provenance.json"):
                if json.loads(provenance.read_text(encoding="utf-8"))["append_layout"] != layout:
                    raise ValueError(f"{name}: telemetry layout changed")
            calculated = Path(scratch) / f"{name}-analysis"
            if run("profile_integrated_founding", scope, "--out", archive, "--analysis", calculated):
                raise ValueError(f"{name}: analysis could not be reproduced")
            compare_outputs(root / calculated.name, calculated)
            decision = json.loads((calculated / "decision.json").read_text(encoding="utf-8"))
            if decision["required"] != expected:
                raise ValueError(f"{name}: qualification denominator changed")
            phases = Path(scratch) / f"{name}-phase-diagnosis"
            if run("summarize_integrated_founding_performance", archive, phases):
                raise ValueError(f"{name}: phase diagnosis could not be reproduced")
            compare_outputs(root / phases.name, phases)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    verify(parser.parse_args().archive.resolve())
