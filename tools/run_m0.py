"""Run the frozen MicroWorld cases and keep one lossless archive per world."""

import argparse
from itertools import product
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

from founding_qualification_witnesses import COMMAND
from run_integrated_founding import DAY, environments
from run_s6_4_wp6b import ROOT, git, run_one, sha, write_json


PROTOCOL = ROOT / "research/m0/FROZEN_PROTOCOL.md"
PORTABLE_PROTOCOL = ROOT / "research/m0/PORTABLE_REPLAY_PROTOCOL.md"
DEMO_NAMES = ("borisovka-shaft-1-slots", "st_petersburg-dogleg-1-slots",
              "borisovka-shaft-1-reference", "borisovka-shaft-1-no-protein", "borisovka-shaft-1-blocked")
R0_PROTOCOL = ROOT / "research/r0/PROTOCOL.md"


def roster(portable=False):
    originals = {(row["population"], row["software_seed"], row["arm"].removeprefix("integrated-")): row
                 for _, row in environments("nominal")}

    def make(population, layout, seed, variant, treatment="slots", source="balanced", h2=True, r1=True,
             care=True, lipid=5500):
        original = originals[population, seed, source]
        identity = 270000 + 10_000 * (population != "borisovka") + 1000 * (layout == "dogleg") + seed
        if variant not in ("slots", "reference"):
            identity += 100 * (1 + ("h0r0", "h0r1", "h1r0", "no-care", "absent", "no-protein", "blocked", "wet",
                                    "low-lipid").index(variant))
        name = f"{population}-{layout}-{seed}-{variant}"
        variant_name = treatment if h2 else "nocue"
        if portable and treatment != "reference":
            variant_name = "portable" + variant_name
        case = original | dict(case=name, arm=f"micro-m0-{layout}-{variant_name}-{source}", layout=layout,
                               source=source, horizon_ms=90*DAY, care_enabled=care, h2=h2, r1=r1,
                               condition="ENGINEERING_FIXTURE", parameters=original["parameters"] | {"maternal_lipid": lipid})
        args = list(COMMAND)
        args[1] = "750000" if r1 else "0"
        return identity, case, args

    for population, layout, seed in product(("borisovka", "st_petersburg"), ("shaft", "dogleg"), (1, 7)):
        for variant in ("reference", "slots"):
            yield make(population, layout, seed, variant, treatment=variant)
    for seed in (1, 7):
        for h2, r1 in ((False, False), (False, True), (True, False)):
            yield make("borisovka", "shaft", seed, f"h{int(h2)}r{int(r1)}", h2=h2, r1=r1)
    for variant in ("no-care", "absent", "no-protein", "blocked", "wet", "low-lipid"):
        source = variant if variant in ("absent", "no-protein", "blocked") else "balanced"
        yield make("borisovka", "shaft", 1, variant, treatment="wet" if variant == "wet" else "slots",
                   source=source, care=variant != "no-care", lipid=4500 if variant == "low-lipid" else 5500)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--case", action="append", default=[])
    parser.add_argument("--durable", action="store_true", help="Save and reload a midpoint SQLite publication.")
    parser.add_argument("--portable-care", action="store_true", help="Opt into physics 29/30 portable care motion.")
    parser.add_argument("--r0", action="store_true", help="Export paired local nest activity witnesses.")
    args = parser.parse_args()
    binary = args.binary.resolve(strict=True)
    destination = args.output.resolve()
    candidates = roster(args.portable_care)
    protocol = PROTOCOL
    if args.r0:
        candidates = r0_roster()
        protocol = R0_PROTOCOL
    cases = [(i, c, command) for i, c, command in candidates if not args.case or c["case"] in args.case]
    if not cases or set(args.case) - {c["case"] for _, c, _ in cases}:
        parser.error("unknown MicroWorld case")
    mode = "durable" if args.durable else "observed"
    destination.mkdir(parents=True)
    write_json(destination / "run.json", dict(source=git("rev-parse", "HEAD"), cpp_tree=git("rev-parse", "HEAD:cpp"),
        binary_sha256=sha(binary), protocol_sha256=sha(protocol), mode=mode,
        **(dict(portable_protocol_sha256=sha(PORTABLE_PROTOCOL)) if args.portable_care else {}),
        cases=[c["case"] for _, c, _ in cases], dirty=git("status", "--porcelain", "--", "cpp", "tools/run_m0.py")))
    failed = False
    with (destination / "archives.jsonl").open("x", encoding="utf-8", newline="\n") as manifest:
        for identity, case, command in cases:
            with TemporaryDirectory(dir=destination) as temp:
                work = Path(temp) / "world"
                receipt = run_one(binary, work, identity, case, mode, command)
                archive = destination / f"{case['case']}.zip"
                with ZipFile(archive, "x", ZIP_DEFLATED, compresslevel=4) as bundle:
                    for path in sorted(work.iterdir()):
                        if path.is_file():
                            bundle.write(path, path.name)
                print(json.dumps(dict(archive=archive.name, sha256=sha(archive), receipt=receipt), sort_keys=True),
                      file=manifest, flush=True)
                print(case["case"], receipt["status"], receipt["summary"]["events"] if receipt["summary"] else
                      (work / "program.log").read_text(encoding="utf-8", errors="replace").strip(), flush=True)
                failed |= receipt["status"] != "COMPLETE"
    return int(failed)


def r0_roster():
    for identity, base, command in roster(portable=True):
        if base["case"] not in ("borisovka-shaft-1-slots", "borisovka-dogleg-1-slots"):
            continue
        for form in ("reference", "candidate"):
            name = f"r0-{base['layout']}-{form}"
            arm = base["arm"] if form == "reference" else base["arm"].replace("portableslots", "portablenest")
            yield identity, base | {"case": name, "arm": arm, "r0_variant": form}, command


if __name__ == "__main__":
    raise SystemExit(main())
