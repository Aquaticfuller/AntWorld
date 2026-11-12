"""Check the R2 frozen case roster, archive bytes, independent budgets and timing gates."""

import argparse
from pathlib import Path

import run_s6_4_wp6b_r2 as frozen
from verify_s6_4_wp6b_r1 import verify


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--case", action="append", default=[])
    args = parser.parse_args()
    verify(args.archive, args.out, args.case, r2=frozen)
