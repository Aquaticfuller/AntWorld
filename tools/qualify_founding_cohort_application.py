"""Run the inherited 720-sample application qualification without changed gates."""

import argparse
from pathlib import Path

import profile_s6_4_wp6b_r1 as assay
from analyze_founding_qualification_performance import SIGNATURE, key
from analyze_s6_3_3_1_performance import read
from analyze_s6_4_wp6b import check
from run_s6_4_wp6b import ROOT, write_json
from run_s6_4_wp6b_r2_performance import APPEND_LAYOUT, MAPPING, check_mapping
from s6_4_wp6b_r2_append_log import AppendLog


PROTOCOL = ROOT / "research/s6_4_integrated_founding/INTEGRATED_PERFORMANCE_PROTOCOL.md"


def verify_equal_work(out, analysis):
    historical = ROOT / "experiments/s6_4_founding_qualification/performance/application-inherited"
    identity = ("sample", "session", "model", "case", "block", "slot", "treatment", "observation")
    count = 0
    for session in range(1, 4):
        folder = f"session{session}"
        schedule = out / folder / "schedule.csv"
        check(schedule.read_bytes() == (historical / folder / "schedule.csv").read_bytes(), "approved sample order changed")
        samples = out / folder / "samples.csv"
        if not samples.exists():
            continue
        expected = read(historical / folder / "samples.csv")
        actual = read(samples)
        check(len(actual) <= len(expected), "too many measured samples")
        for before, after in zip(expected, actual):
            check(all(before[k] == after[k] for k in (*identity, "state_hash", "trace_hash")) and key(before) == key(after),
                  f"application work changed: {folder} sample {after['sample']}")
        count += len(actual)
    write_json(analysis / "historical_work_identity.json", dict(checked_samples=count, scheduled=720,
               fields=list(dict.fromkeys((*identity, *SIGNATURE, "state_hash", "trace_hash"))),
               reference=historical.relative_to(ROOT).as_posix()))


def main():
    options=argparse.ArgumentParser(add_help=False)
    options.add_argument("--hwinfo-csv",type=Path)
    options.add_argument("--out",type=Path)
    options.add_argument("--analysis",type=Path)
    args,_=options.parse_known_args()
    check_mapping()
    native=assay.native
    native.MAPPING=MAPPING
    assay.PROTOCOL=PROTOCOL
    assay.MODEL_ARGUMENTS["both"]=(*assay.NOMINAL,3)
    assay.MODEL_VERSIONS["both"]=3
    assay.ADDITIONAL_SOURCES=(Path(__file__).name,"run_s6_4_wp6b_r2_performance.py","s6_4_wp6b_r2_append_log.py")
    dependencies=native.dependencies
    native.dependencies=lambda: dependencies() | {APPEND_LAYOUT.name:native.digest(APPEND_LAYOUT)}
    if args.hwinfo_csv:
        sensor=AppendLog(args.hwinfo_csv.resolve(),native.load(APPEND_LAYOUT),native.load(MAPPING))
        native.sensor_tail,native.extract=sensor.tail,sensor.extract
    assay.main()
    if args.analysis:
        verify_equal_work(args.out.resolve(), args.analysis.resolve())


if __name__=="__main__":
    main()
