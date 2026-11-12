"""Use the accepted native collector with the WP-5 publisher benchmark."""

from pathlib import Path


BASE = "6774a5123824b3e654da6a4048f038f61d2650a2"
PROTOCOL = Path(__file__).resolve().parents[1] / "research/s6_4_wp5/FROZEN_PROTOCOL.md"


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
