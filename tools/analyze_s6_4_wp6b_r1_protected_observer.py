"""Apply the inherited protected observer gate to the R1 qualification batch."""

from pathlib import Path

import analyze_s6_4_wp2_performance as verifier
from analyze_s6_4_wp5_performance import verify_sample


if __name__ == "__main__":
    verifier.PROTOCOL = Path(__file__).resolve().parents[1] / "research/s6_4_wp6b_r1/FROZEN_R1_PROTOCOL.md"
    verifier.verify_sample = verify_sample
    raise SystemExit(verifier.main())
