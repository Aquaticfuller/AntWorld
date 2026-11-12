"""Collect the frozen WP-2 scope benchmark with the accepted native collector."""

from pathlib import Path

import run_s6_4_rm02_performance as collector
from run_s6_4_wp2 import BASE, PROTOCOL, sha256


def main():
    dependencies = collector.sources
    collector.BASE = BASE
    collector.PROTOCOL = PROTOCOL
    collector.sources = lambda: dependencies() | {Path(__file__).name: sha256(Path(__file__))}
    collector.main()


if __name__ == "__main__":
    main()
