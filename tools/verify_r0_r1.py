"""Audit the R0-r1 witnesses directly and optionally check native durable reproduction."""

from argparse import ArgumentParser
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
from math import prod
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from op0 import DAY
from op0.archive import PUBLISHED, digest_stream, file_hash, zip_inputs
from op0.cli import api_get
from op0.codec import decode_fact, require
from op0.index import Catalog
from op0.query import ReadAPI
from tools.run_r0_r1 import HOUR, shape


def worker_overlaps(frame):
    ants = [a for a in frame["ants"].values() if a["caste"] == 0 and a["stage"] == 3]
    geometry = frame["geometry"]
    quantum = geometry["quantum_m"]
    carriers = set(frame["soil_carriers"])
    half_widths = [quantum * geometry["loaded_half_q" if ant["id"] in carriers or any(ant["carried_ug"])
                                      else "body_half_q"] for ant in ants]
    positions = [ant["position_m"] for ant in ants]
    exact = sum(n*(n-1)//2 for n in Counter(positions).values())
    bodies = sum(all(abs(a-b) < half_widths[i]+half_widths[j]-1e-12 for a,b in zip(p,q,strict=True))
                 for i,p in enumerate(positions) for j,q in enumerate(positions[:i]))
    return dict(workers=len(ants), exact_pairs=exact, body_pairs=bodies, soil_carriers=len(carriers))


def inspect(path, expected):
    require(file_hash(path) == expected, f"Archive SHA-256 changed: {path.name}")
    with closing(zip_inputs(path)) as source:
        first, last, _, records, capture = next(source)
        require(capture["receipt_verified"] and first["time_ms"] == 0, "Missing initial state or verified member hashes")
        require(last["time_ms"] in (24*HOUR,90*DAY) and last["seed"] == 1, "Unexpected run horizon or seed")
        declared = capture["case"]
        seeded = declared["externally_seeded_workers"]
        require(seeded == worker_overlaps(first)["workers"], "Initial adult census disagrees with the declared inputs")
        edit_events = {e["event"]: e for e in last["edits"]}
        boundaries = Counter()
        evidence = Counter()
        checksum = sha256()
        previous_time = 0
        fact_count = 0
        for fact_count, (prefix, raw) in enumerate(records, 1):
            _, event = decode_fact(raw)
            require(event.id == fact_count and previous_time <= event.time <= last["time_ms"], "Fact order changed")
            previous_time = event.time
            checksum.update(prefix)
            checksum.update(raw)
            if event.kind == 4 and event.aux:
                motion = event.packet()["motion"]
                require(last["physics"] == 33 and 0 < motion["duration_ms"] <= event.time and
                        motion["turn_ms"] < motion["duration_ms"], "Invalid motor clock")
                evidence["timed_moves"] += 1
                evidence["timed_turns"] += bool(motion["turn_ms"])
            if event.outcome != 0:
                continue
            if edit := edit_events.pop(event.id, None):
                require((event.kind, event.source, event.actor, event.time, event.payload) ==
                        (23 if edit["kind"] == 0 else 26, edit["source"], edit["actor"], edit["time_ms"], edit["parcel"]),
                        "Geometry edit does not match its committed fact")
                q3 = edit["volume_q3"]
                box = edit["box_q"]
                require(0 < q3 <= prod(box[i+3]-box[i] for i in range(3)), "Soil volume exceeds committed edit bounds")
                boundaries[edit["kind"]] += q3
            if event.kind in (12,21,23,24,35,38):
                evidence[str(event.kind)] += 1
        require(fact_count == last["cursor"] and checksum.hexdigest() == capture["facts_expected"] and not edit_events,
                "Committed history does not match the final frame")
        initial, remaining, carried, deposited, excavated, filled = last["soil"]
        require(initial == remaining+carried+deposited and remaining == initial-excavated+filled and
                (excavated,filled) == (boundaries[0],boundaries[3]), "Soil conservation or edit totals differ")
        output = dict(physics=last["physics"], world=last["world"], events=fact_count, facts_sha256=checksum.hexdigest(),
                      soil_q3=last["soil"], census=worker_overlaps(last), evidence=dict(evidence))
        if seeded:
            require(evidence["23"] and evidence["24"], "Excavation witness has no real excavation and drop")
            final_shape = shape(last)
            output["section"] = dict(room_cores=len(final_shape["rooms"]), junctions=len(final_shape["junctions_q"]),
                                     area_mm2=final_shape["area_mm2"], workers=final_shape["supported_workers"])
        else:
            require(output["census"]["workers"] >= 10 and evidence["12"] and evidence["21"] and evidence["23"],
                    "Founding witness lacks workers or observed ecological actions")
            require(last["physics"] == 32 or evidence["timed_moves"], "No authoritative motor evidence")
        return output


def member_hashes(path):
    results = {}
    with ZipFile(path) as bundle:
        for name in PUBLISHED:
            with bundle.open(name) as stream:
                results[name] = digest_stream(stream)
    return results


def verify_api(path, digest, storage):
    catalog = Catalog(storage)
    art = catalog.register(path, expected=digest)
    meta = catalog.browse(art)[0][0]
    mark = next((m for m in meta["milestones"] if m["label"] == "Resting site with 10 or more workers"), None)
    require(mark, "No late committed underground move")
    segment = api_get(ReadAPI(catalog), f"world/{meta['key']}/rest-segment", id=mark["id"])
    require(segment and segment["start"]["time_ms"] == segment["move"]["motion"]["begins_ms"] and
            segment["move"]["position_m"] != segment["start"]["position_m"], "Observable timed movement differs from the Core")
    return dict(start=segment["start"]["id"], move=segment["move"]["id"], finish=mark["id"], actor=mark["ant"])


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("witnesses", type=Path)
    parser.add_argument("--replay", type=Path, help="Directory from the independent native --durable run")
    parser.add_argument("--scratch", type=Path, default=Path("out"))
    args = parser.parse_args()
    entries = [json.loads(line) for line in (args.witnesses/"archives.jsonl").read_text().splitlines()]
    expected = {f"motion-{layout}-{arm}.zip" for layout in ("shaft","dogleg") for arm in ("r0","motor")}
    expected.update(f"motion-shaft-{arm}-shorter.zip" for arm in ("r0","motor"))
    expected.update(f"dig-{size}-s1-{arm}.zip" for size in ("050","300") for arm in ("r0","full"))
    require(len(entries) == len(expected) and {r["archive"] for r in entries} == expected, "Incorrect archive roster")
    args.scratch.mkdir(parents=True, exist_ok=True)
    if args.replay:
        repeats = {r["case"]["case"]: r for r in map(json.loads, (args.replay/"runs.jsonl").read_text().splitlines())}
        require(set(repeats) == {"motion-shaft-motor","motion-dogleg-motor"}, "Incomplete durable replay")
    with TemporaryDirectory(dir=args.scratch, prefix="r0-r1-index-") as scratch:
        results = {}
        for item in entries:
            path = args.witnesses/item["archive"]
            info = inspect(path,item["sha256"])
            if item["case"] in ("motion-shaft-motor","motion-dogleg-motor"):
                info["segment"] = verify_api(path,item["sha256"],Path(scratch))
                if args.replay:
                    require(repeats[item["case"]]["sqlite"]["restore_ms"] > 0 and
                            member_hashes(path) == member_hashes(args.replay/path.name), "Durable continuation differs")
            results[path.stem] = info
            print(json.dumps(dict(case=path.stem, **info)),flush=True)
        for name, info in results.items():
            variant = "motor" if "-motor" in name else "full" if name.endswith("-full") else None
            if variant:
                control = results[name.replace(variant,"r0")]
                require((info["physics"], control["physics"]) == (33,32) and info["world"] == control["world"],
                        "Pair identity or version mismatch")
    print("PASS: verified R0-r1 roster, ordered facts, native edit ledgers and observable segments")


if __name__ == "__main__":
    main()
