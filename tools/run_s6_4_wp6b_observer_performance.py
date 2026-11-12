"""Requalify the protected observer workload on the opt-in F1 Core tree."""

from pathlib import Path

import run_s6_4_rm02_performance as collector


def main():
    sources = collector.sources
    collector.BASE = "d7b5948fd052b5620f461808e23d1c5dcaddf761"
    collector.PROTOCOL = Path(__file__).resolve().parents[1] / "research/s6_4_wp6b/FROZEN_PROTOCOL.md"
    collector.sources = lambda: sources() | {Path(__file__).name: collector.native.digest(Path(__file__))}
    collector.main()


if __name__ == "__main__":
    main()
