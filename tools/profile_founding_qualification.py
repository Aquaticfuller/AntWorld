"""Collect the frozen diagnostic subset with the original Windows instrument."""

import argparse
from pathlib import Path

import profile_s6_4_wp6b_r1 as assay
from run_s6_4_wp6b_r2_performance import APPEND_LAYOUT, MAPPING, check_mapping
from s6_4_wp6b_r2_append_log import AppendLog


CELLS = {
    ("borisovka-micro-nominal-0-1", "r1"),
    ("borisovka-early-depot-8-1", "v1"),
    ("borisovka-early-depot-32-1", "both"),
    ("st_petersburg-micro-nominal-0-1", "v1"),
    ("st_petersburg-micro-nominal-0-1", "both"),
    ("st_petersburg-early-depot-8-1", "v1"),
    ("st_petersburg-early-empty-32-1", "v1"),
    ("borisovka-micro-nominal-0-1", "v1"),
    ("st_petersburg-early-depot-32-1", "both"),
}
ROOT = assay.native.ROOT
PROTOCOL = ROOT / "research/s6_4_founding_qualification/FROZEN_CLOSURE_PROTOCOL.md"
BASE_SCHEDULE = assay.schedule


def diagnostic_schedule(session):
    rows = [row for row in BASE_SCHEDULE(session, ("v1", "r1", "both")) if (row["case"], row["model"]) in CELLS]
    return [row | dict(sample=index) for index, row in enumerate(rows)]


def configure(hw):
    check_mapping()
    native = assay.native
    native.MAPPING = MAPPING
    assay.PROTOCOL = PROTOCOL
    assay.MODEL_ARGUMENTS["both"] = (*assay.NOMINAL, 3)
    assay.MODEL_VERSIONS["both"] = 3
    assay.DIAGNOSTIC_STORAGE = True
    assay.ADDITIONAL_SOURCES = (Path(__file__).name, "run_s6_4_wp6b_r2_performance.py", "s6_4_wp6b_r2_append_log.py")
    dependencies = native.dependencies
    native.dependencies = lambda: dependencies() | {APPEND_LAYOUT.name: native.digest(APPEND_LAYOUT)}

    assay.schedule = diagnostic_schedule
    log = AppendLog(hw.resolve(), native.load(APPEND_LAYOUT), native.load(MAPPING))
    native.sensor_tail, native.extract = log.tail, log.extract


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--hwinfo-csv", type=Path, required=True)
    options, _ = parser.parse_known_args()
    configure(options.hwinfo_csv)

    def prepare(args):
        if "ANTWORLD_STORAGE_TIMING:BOOL=ON" not in (args.build/"CMakeCache.txt").read_text(encoding="utf-8"):
            raise ValueError("diagnostic executable requires ANTWORLD_STORAGE_TIMING")
        assay.prepare(args)

    assay.main(on_prepare=prepare)


if __name__ == "__main__":
    main()
