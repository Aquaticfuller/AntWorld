"""Verify the public native application qualification and its unchanged work."""

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from analyze_s6_4_wp6b import check
from qualify_founding_cohort_application import PROTOCOL
from reconcile_s6_4_rm02_performance import verify_manifest
from run_s6_4_wp6b import sha
from run_s6_4_wp6b_r2_performance import APPEND_LAYOUT, MAPPING
from verify_s6_4_wp6b_r2_performance import compare_outputs, run


def verify(archive, analysis):
    verify_manifest(archive)
    freeze = json.loads((archive / "freeze.json").read_bytes())
    check(freeze["protocol_sha256"] == sha(PROTOCOL) and freeze["mapping_sha256"] == sha(MAPPING)
          and freeze["sources"][APPEND_LAYOUT.name] == sha(APPEND_LAYOUT), "formal application protocol or telemetry changed")
    layout = json.loads(APPEND_LAYOUT.read_bytes())
    for provenance in archive.glob("session*/hwinfo_provenance.json"):
        check(json.loads(provenance.read_bytes())["append_layout"] == layout, "sample telemetry layout changed")
    with TemporaryDirectory() as scratch:
        rebuilt = Path(scratch) / "analysis"
        check(not run("qualify_founding_cohort_application", "--out", archive, "--analysis", rebuilt),
              "formal application analysis did not reproduce")
        compare_outputs(analysis, rebuilt)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("analysis", type=Path)
    args = parser.parse_args()
    verify(args.archive, args.analysis)
