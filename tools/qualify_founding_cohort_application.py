"""Run the inherited 720-sample application qualification without changed gates."""

import argparse
from pathlib import Path

import profile_s6_4_wp6b_r1 as assay
from run_founding_cohort_release import PROTOCOL
from run_s6_4_wp6b import ROOT
from run_s6_4_wp6b_r2_performance import APPEND_LAYOUT, MAPPING, check_mapping
from s6_4_wp6b_r2_append_log import AppendLog


def main():
    options=argparse.ArgumentParser(add_help=False)
    options.add_argument("--hwinfo-csv",type=Path)
    args,_=options.parse_known_args()
    check_mapping()
    native=assay.native
    native.MAPPING=MAPPING
    assay.PROTOCOL=ROOT/PROTOCOL
    assay.MODEL_ARGUMENTS["both"]=(*assay.NOMINAL,3)
    assay.MODEL_VERSIONS["both"]=3
    assay.ADDITIONAL_SOURCES=(Path(__file__).name,"run_s6_4_wp6b_r2_performance.py","s6_4_wp6b_r2_append_log.py")
    dependencies=native.dependencies
    native.dependencies=lambda: dependencies() | {APPEND_LAYOUT.name:native.digest(APPEND_LAYOUT)}
    if args.hwinfo_csv:
        sensor=AppendLog(args.hwinfo_csv.resolve(),native.load(APPEND_LAYOUT),native.load(MAPPING))
        native.sensor_tail,native.extract=sensor.tail,sensor.extract
    assay.main()


if __name__=="__main__":
    main()
