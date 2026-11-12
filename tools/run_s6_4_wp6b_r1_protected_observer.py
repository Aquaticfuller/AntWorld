"""Run the existing admitted protected observer workloads on the frozen R1 source."""

from pathlib import Path

import run_s6_4_rm02_performance as collector


if __name__ == "__main__":
    sources = collector.sources
    collector.BASE = "0de8a9951090d2120914721e539ba82304593bf7"
    collector.PROTOCOL = Path(__file__).resolve().parents[1] / "research/s6_4_wp6b_r1/FROZEN_R1_PROTOCOL.md"
    collector.sources = lambda: sources() | {Path(__file__).name: collector.native.digest(Path(__file__))}
    collector.main()
