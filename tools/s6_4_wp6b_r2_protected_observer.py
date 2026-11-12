"""Collect or analyze the inherited protected observer workload on R2."""

import sys
from pathlib import Path

from profile_s6_4_wp6b_r2 import PROTOCOL


if __name__ == "__main__":
    if "--analyze" in sys.argv:
        import analyze_s6_4_wp2_performance as verifier
        from analyze_s6_4_wp5_performance import verify_sample

        sys.argv.remove("--analyze")
        verifier.PROTOCOL = PROTOCOL
        verifier.verify_sample = verify_sample
        raise SystemExit(verifier.main())

    import run_s6_4_rm02_performance as collector

    sources = collector.sources
    # Freeze the current opt-in Core and let the inherited verifier check the legacy workload bytes.
    collector.BASE = collector.native.git("rev-parse", "HEAD")
    collector.PROTOCOL = PROTOCOL
    collector.sources = lambda: sources() | {Path(__file__).name: collector.native.digest(Path(__file__))}
    collector.main()
