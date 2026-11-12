"""Collect the frozen WP-4 publisher benchmark with the accepted native collector."""

from pathlib import Path


BASE = "562cd6a65d075e1f3f9de2c5184975d41f104dd6"
PROTOCOL = Path(__file__).resolve().parents[1] / "research/s6_4_wp4/FROZEN_PROTOCOL.md"


def main():
    import run_s6_4_rm02_performance as collector
    from run_s6_4_rm02 import sha256

    dependencies = collector.sources
    collector.BASE = BASE
    collector.PROTOCOL = PROTOCOL
    collector.sources = lambda: dependencies() | {Path(__file__).name: sha256(Path(__file__))}
    collector.main()


if __name__ == "__main__":
    main()
