"""Apply the unchanged protected observer gate to WP-6B measurement receipts."""

import analyze_s6_4_wp2_performance as verifier
from analyze_s6_4_wp5_performance import verify_sample
from pathlib import Path


if __name__ == "__main__":
    verifier.PROTOCOL = Path(__file__).resolve().parents[1] / "research/s6_4_wp6b/FROZEN_PROTOCOL.md"
    verifier.verify_sample = verify_sample
    raise SystemExit(verifier.main())
