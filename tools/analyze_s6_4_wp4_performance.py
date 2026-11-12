"""Check WP-4 lineage coverage and the inherited native publisher gates."""

import analyze_s6_4_wp2_performance as verifier
from read_s6_4_rm02_sidecar import require
from run_s6_4_wp4_performance import PROTOCOL


def verify_sample(sample, cuts):
    inherited(sample, cuts)
    for cut in cuts:
        count = int(cut["lineage_bytes"])
        require(0 < count <= 256 * 1024 if sample["cell"] == "depot32" else count == 0,
                "WP-4 lineage capture missing or over budget")


inherited = verifier.verify_sample

if __name__ == "__main__":
    verifier.PROTOCOL = PROTOCOL
    verifier.verify_sample = verify_sample
    raise SystemExit(verifier.main())
