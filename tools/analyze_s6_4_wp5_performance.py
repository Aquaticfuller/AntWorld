"""Verify the added bounded geometry probe and the accepted observer gates."""

import analyze_s6_4_wp2_performance as verifier
from analyze_s6_4_wp4_performance import verify_sample as inherited
from read_s6_4_rm02_sidecar import require
from run_s6_4_wp5_performance import PROTOCOL


def verify_sample(sample, cuts):
    inherited(sample, cuts)
    for cut in cuts:
        count = int(cut["probe_bytes"])
        require(0 < count <= 64 * 1024 if sample["cell"] == "depot32" else count == 0,
                "WP-5 geometry probe missing or over budget")


if __name__ == "__main__":
    verifier.PROTOCOL = PROTOCOL
    verifier.verify_sample = verify_sample
    raise SystemExit(verifier.main())
