"""Collect the frozen diagnostic subset with the original Windows instrument."""

import argparse
from pathlib import Path
import sys

from run_s6_4_wp6b import ROOT, frozen_cases


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
PROTOCOL = ROOT / "research/s6_4_founding_qualification/FROZEN_CLOSURE_PROTOCOL.md"


def diagnostic_schedule(session):
    # The Windows collector freezes this order from the existing inherited matrix.
    cases=[case["case"] for _,case in frozen_cases() if case["software_seed"]==1 and
           ((case["group"]=="micro" and case["arm"]=="nominal") or
            (case["group"]=="early" and case["arm"] in ("depot","empty")))]
    models=("v1","r1","both")
    if session==2:
        cases.reverse()
        models=models[::-1]
    rows=[]
    for case in cases:
        for model in models:
            if (case,model) not in CELLS:
                continue
            for block,(first,second) in enumerate((("off-a","off-b"),("off","on"))):
                if (session+block)%2==0:
                    first,second=second,first
                for slot,treatment in enumerate((first,second,second,first)):
                    rows.append(dict(sample=len(rows),session=session,model=model,case=case,block=block,slot=slot,
                                     treatment=treatment,observation="observed" if treatment=="on" else "unobserved"))
    return rows


def configure(assay, hw):
    from run_s6_4_wp6b_r2_performance import APPEND_LAYOUT, MAPPING, check_mapping
    from s6_4_wp6b_r2_append_log import AppendLog

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

    previous_schedule=assay.schedule
    for session in (1,2,3):
        filtered=[r for r in previous_schedule(session) if (r["case"],r["model"]) in CELLS]
        if diagnostic_schedule(session)!=[r | dict(sample=i) for i,r in enumerate(filtered)]:
            raise ValueError("diagnostic order differs from the inherited schedule")
    assay.schedule = diagnostic_schedule
    log = AppendLog(hw.resolve(), native.load(APPEND_LAYOUT), native.load(MAPPING))
    native.sensor_tail, native.extract = log.tail, log.extract


def main():
    if sys.platform!="win32":
        raise SystemExit("Live hardware timing requires the approved Windows host")
    import profile_s6_4_wp6b_r1 as assay

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--hwinfo-csv", type=Path, required=True)
    options, _ = parser.parse_known_args()
    configure(assay, options.hwinfo_csv)

    def prepare(args):
        if "ANTWORLD_STORAGE_TIMING:BOOL=ON" not in (args.build/"CMakeCache.txt").read_text(encoding="utf-8"):
            raise ValueError("diagnostic executable requires ANTWORLD_STORAGE_TIMING")
        assay.prepare(args)

    assay.main(on_prepare=prepare)


if __name__ == "__main__":
    main()
