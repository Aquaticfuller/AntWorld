"""Qualify the shipped MicroWorld witnesses and native recovery replay."""

import argparse
from pathlib import Path
import json
from zipfile import ZipFile

from analyze_m0 import join_facts, require
from op0.archive import digest_stream
from run_m0 import DEMO_NAMES


def members(path):
    result = {}
    with ZipFile(path) as archive:
        for name in ("parameters.txt", "initial.chk", "final.frame", "facts.bin", "cuts.csv", "individuals.csv", "geometry_edits.csv"):
            with archive.open(name) as stream:
                result[name] = digest_stream(stream)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("demos", type=Path)
    p.add_argument("--replay", type=Path)
    args = p.parse_args()
    rows = [json.loads(line) for line in (args.demos/"archives.jsonl").read_text(encoding="utf-8").splitlines()]
    require(tuple(row["receipt"]["case"] for row in rows)==DEMO_NAMES, "Unexpected demo roster")
    for entry in rows:
        source = args.demos/entry["archive"]
        world, cohort = join_facts(source)
        case = world["case"]
        require(world["archive_sha256"]==entry["sha256"] and world["eggs"]>1 and cohort, f"Invalid origin in {case}")
        if case.endswith("-slots"):
            require(world["physics"]==27 and world["brood_moves"]>0 and world["arrangements"]>0 and
                    world["transfers"]>0 and world["resource_trips"]>0 and world["excavation_drops"]>0 and
                    len({tuple(ant["egg_position_m"]) for ant in cohort})==len(cohort), f"Incomplete visible ecology in {case}")
            if args.replay:
                target = args.replay/entry["archive"]
                with ZipFile(target) as reproduced:
                    receipt = json.loads(reproduced.read("receipt.json"))
                require(receipt["mode"]=="durable" and float(receipt["summary"]["midpoint_restore_ms"])>0 and
                        members(target)==members(source), f"Native recovery or canonical bytes diverged in {case}")
        if case.endswith("-blocked"):
            require(world["resource_trips"]==0, "The sealed witness delivered exterior food")
        if case.endswith("-reference"):
            require(world["physics"]==25 and len({tuple(ant["egg_position_m"]) for ant in cohort})==1,
                    "Legacy placement has changed")
        print(case, world["physics"], world["facts"], world["canonical_sha256"])


if __name__=="__main__":
    main()
