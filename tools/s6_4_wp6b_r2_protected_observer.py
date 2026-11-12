"""Collect or analyze the inherited protected observer workload on R2."""

import sys
from pathlib import Path

from run_s6_4_wp6b_r2_performance import MAPPING, PROTOCOL, check_mapping


def main():
    if "--analyze" in sys.argv:
        import analyze_s6_4_wp2_performance as verifier
        from analyze_s6_4_wp5_performance import verify_sample
        import reconcile_s6_4_rm02_performance as instrument

        sys.argv.remove("--analyze")
        check_mapping()
        instrument.MAPPING = MAPPING
        verifier.PROTOCOL = PROTOCOL
        verifier.verify_sample = verify_sample
        raise SystemExit(verifier.main())

    import run_s6_4_rm02_performance as collector

    sources = collector.sources
    # Freeze the current opt-in Core and let the inherited verifier check the legacy workload bytes.
    collector.BASE = collector.native.git("rev-parse", "HEAD")
    collector.PROTOCOL = PROTOCOL
    collector.sources = lambda: sources() | {name: collector.native.digest(Path(__file__).with_name(name))
                                             for name in (Path(__file__).name, "run_s6_4_wp6b_r2_performance.py")}
    collector.main()


if __name__ == "__main__":
    main()
