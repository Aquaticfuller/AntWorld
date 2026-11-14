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


def first_difference(reference, reproduced, member):
    offset = 0
    with ZipFile(reference) as left, ZipFile(reproduced) as right:
        with left.open(member) as a, right.open(member) as b:
            while block_a := a.read(65536):
                block_b = b.read(len(block_a))
                if block_a != block_b:
                    first = next((i for i, (x, y) in enumerate(zip(block_a, block_b)) if x != y), len(block_b))
                    return offset + first
                offset += len(block_a)
    return offset


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("demos", type=Path)
    p.add_argument("--replay", type=Path)
    p.add_argument("--portable-care", action="store_true", help="Require physics 29 for new-mode witnesses.")
    args = p.parse_args()
    rows = [json.loads(line) for line in (args.demos/"archives.jsonl").read_text(encoding="utf-8").splitlines()]
    require(tuple(row["receipt"]["case"] for row in rows)==DEMO_NAMES, "Unexpected demo roster")
    for entry in rows:
        source = args.demos/entry["archive"]
        world, cohort = join_facts(source)
        case = world["case"]
        require(world["archive_sha256"]==entry["sha256"] and world["eggs"]>1 and cohort, f"Invalid origin in {case}")
        if case.endswith("-slots"):
            require(world["physics"]==(29 if args.portable_care else 27) and world["brood_moves"]>0 and world["arrangements"]>0 and
                    world["transfers"]>0 and world["resource_trips"]>0 and world["excavation_drops"]>0 and
                    len({tuple(ant["egg_position_m"]) for ant in cohort})==len(cohort), f"Incomplete visible ecology in {case}")
            if args.replay:
                target = args.replay/entry["archive"]
                with ZipFile(target) as reproduced:
                    receipt = json.loads(reproduced.read("receipt.json"))
                require(receipt["mode"]=="durable" and float(receipt["summary"]["midpoint_restore_ms"])>0,
                        f"Missing native recovery in {case}")
                expected, actual = members(source), members(target)
                changes = [f"{name} at byte {first_difference(source, target, name)} (SHA-256 {expected[name]} != {actual[name]})"
                           for name in expected if expected[name] != actual[name]]
                require(not changes, f"Native bytes diverged in {case}: " + "; ".join(changes))
        if case.endswith("-blocked"):
            require(world["resource_trips"]==0, "The sealed witness delivered exterior food")
        if case.endswith("-reference"):
            require(world["physics"]==25 and len({tuple(ant["egg_position_m"]) for ant in cohort})==1,
                    "Legacy placement has changed")
        print(case, world["physics"], world["facts"], world["canonical_sha256"])


if __name__=="__main__":
    main()
