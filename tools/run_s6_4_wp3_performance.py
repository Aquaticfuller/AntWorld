"""Collect the frozen WP-3 publisher benchmark with the accepted native collector."""

from pathlib import Path

import run_s6_4_rm02_performance as collector
from run_s6_4_rm02 import sha256


BASE = "e2094fbf95dbe61855472b7509da19a221b1ecbb"
PROTOCOL = collector.native.ROOT / "research/s6_4_wp3/FROZEN_PROTOCOL.md"


def main():
    dependencies = collector.sources
    collector.BASE = BASE
    collector.PROTOCOL = PROTOCOL
    collector.sources = lambda: dependencies() | {Path(__file__).name: sha256(Path(__file__))}
    collector.main()


if __name__ == "__main__":
    main()
