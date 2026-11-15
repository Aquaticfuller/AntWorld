"""Verify published R0 pairs and optionally compare native durable replay."""

from argparse import ArgumentParser
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from analyze_m0 import join_facts
from op0 import DAY
from op0.cli import api_get
from op0.codec import require
from op0.index import Catalog
from op0.query import ReadAPI
from verify_m0 import members


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("witnesses", type=Path)
    parser.add_argument("--replay", type=Path, help="Native durable reproduction directory")
    parser.add_argument("--scratch", type=Path, default=Path("out"))
    args = parser.parse_args()
    args.scratch.mkdir(parents=True, exist_ok=True)
    entries = {r["archive"]: r for r in map(json.loads, (args.witnesses / "archives.jsonl").read_text().splitlines())}
    require(set(entries) == {f"r0-{layout}-{version}.zip" for layout in ("shaft", "dogleg")
                             for version in ("reference", "candidate")}, "Wrong R0 witness roster")
    with TemporaryDirectory(dir=args.scratch, prefix="r0-index-") as scratch:
        cat = Catalog(Path(scratch))
        api = ReadAPI(cat)
        for layout in ("shaft", "dogleg"):
            worlds = []
            for variant, physics in (("candidate", 32), ("reference", 29)):
                archive = f"r0-{layout}-{variant}.zip"
                path = args.witnesses / archive
                metrics, cohort = join_facts(path)
                require(metrics["physics"] == physics and metrics["archive_sha256"] == entries[archive]["sha256"] and
                        metrics["resource_trips"] > 0 and metrics["excavation_drops"] > 0 and metrics["transfers"] > 0 and
                        metrics["arrangements"] > 0 and cohort, "R0 ecological witness is incomplete")
                identity = cat.register(path, expected=entries[archive]["sha256"])
                meta = cat.browse(identity)[0][0]
                worlds.append(meta)
                if variant == "candidate":
                    mark = next(m for m in meta["milestones"] if m["label"] == "Resting site with 10 or more workers")
                    segment = api_get(api, f"world/{meta['key']}/rest-segment", id=mark["id"])
                    require(segment and segment["move"]["position_m"] != segment["start"]["position_m"],
                            "The recorded rest segment has no physical displacement")
                    if args.replay:
                        restored = args.replay / archive
                        with ZipFile(restored) as bundle:
                            receipt = json.loads(bundle.read("receipt.json"))
                        require(receipt["mode"] == "durable" and float(receipt["summary"]["midpoint_restore_ms"]) > 0,
                                "Missing independent SQLite restore")
                        require(members(path) == members(restored), "R0 archive diverges after native restore")
                print(archive, metrics["canonical_sha256"], meta["final_population"], flush=True)
            comparison = api_get(api, "compare", left=worlds[0]["key"], right=worlds[1]["key"], time_ms=90*DAY, nest=1)
            require(all(w.get("nest") and w["state"]["ants"] for w in comparison["worlds"]) and
                    comparison["settings"]["geometry"]["status"] == "same" and
                    comparison["settings"]["initial_maternal"]["status"] == "same" and
                    comparison["settings"]["physics"]["status"] == "different", "R0 comparison attribution incomplete")


if __name__ == "__main__":
    main()
