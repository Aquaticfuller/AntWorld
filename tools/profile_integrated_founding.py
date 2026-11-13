"""Reuse the frozen F1 timing instrument for the integrated source assay."""

import argparse
from pathlib import Path
import sys

import profile_s6_4_wp6b_r1 as assay
from run_integrated_founding import MODELS, environments
from run_s6_4_wp6b_r2_performance import APPEND_LAYOUT, MAPPING, check_mapping
from s6_4_wp6b_r2_append_log import AppendLog


def integrated_workload():
    return {case["case"]: (identity,case) for identity,case in environments("nominal")
            if case["software_seed"]==1 and case["arm"] in ("integrated-balanced", "integrated-blocked")}


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("scope", choices=("inherited", "integrated"))
    parser.add_argument("--hwinfo-csv", type=Path)
    parser.add_argument("--analysis", type=Path)
    args, _ = parser.parse_known_args()
    sys.argv.pop(1)
    check_mapping()
    native = assay.native
    native.MAPPING = MAPPING
    assay.PROTOCOL = native.ROOT / "research/s6_4_integrated_founding/INTEGRATED_PERFORMANCE_PROTOCOL.md"
    assay.ADDITIONAL_SOURCES = (Path(__file__).name, "run_integrated_founding.py", "run_s6_4_wp6b_r2_performance.py",
                               "s6_4_wp6b_r2_append_log.py")
    dependencies = native.dependencies
    native.dependencies = lambda: dependencies() | {APPEND_LAYOUT.name: native.digest(APPEND_LAYOUT)}
    if not args.analysis:
        log = AppendLog(args.hwinfo_csv.resolve(), native.load(APPEND_LAYOUT), native.load(MAPPING))
        native.sensor_tail, native.extract = log.tail, log.extract
    if args.scope=="integrated":
        assay.workload = integrated_workload
        assay.MODEL_ARGUMENTS = {"resupply": (*assay.NOMINAL,3,*MODELS["resupply"])}
        assay.MODEL_VERSIONS = {"resupply":7}
    else:
        assay.MODEL_ARGUMENTS["both"] = (*assay.NOMINAL,3)
        assay.MODEL_VERSIONS["both"] = 3
    assay.main()


if __name__ == "__main__":
    main()
