"""Verify paired identities, archived physics 36 bytes and complete M1 witnesses."""

import argparse
from base64 import b64decode
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from op0.archive import file_hash, prefixed
from op0.index import Catalog
from op0.live import ROOT
from op0.query import ReadAPI
from tools.run_m1_habitat import cases


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines()]


def require(test, message):
    if not test:
        raise ValueError(message)


def scenario_rows(path, series):
    actual = read_jsonl(path)
    expected = list(cases(series))
    require(len(actual) == len(expected), f"{path.name}: number of rows disagrees with the frozen protocol")
    for row, (name, command, horizon, publish) in zip(actual, expected):
        inputs, final = row["inputs"], row["cuts"][-1]
        require((inputs["case"], inputs["command"], inputs["horizon_days"]) == (name, command, horizon), name)
        require(final["day"] == row["last_confirmed_day"], name)
        if row["status"] == "COMPLETE":
            require(final["day"] == horizon and bool(row.get("witness")) == publish, name)
            require(horizon == 90 or [cut["day"] for cut in row["cuts"][:2]] == [90, 150], name)
        else:
            require(row["status"] == "STOPPED" and row["stop_reason"], name)
    return actual


def verify_physics36(reference, rerun):
    a, b = (scenario_rows(path, "archive36") for path in (reference, rerun))
    for old, new in zip(a, b):
        require(old["inputs"] == new["inputs"] and old["inputs"]["physics"] == 36 and
                old["status"] == new["status"] == "COMPLETE", "Physics 36 starting inputs changed")
        for k in ("canonical_sha256", "frame_sha256"):
            require(old["cuts"][0][k] == new["cuts"][0][k], f"Physics 36 {k} changed for {old['inputs']['case']}")
    return len(a)


def verify_witness(catalog, path, receipt):
    digest = file_hash(path)
    require(digest == receipt["witness"]["sha256"], "Published M1 archive hash mismatch")
    (meta,), _, _ = catalog.browse(catalog.register(path, expected=digest))
    endpoint = receipt["cuts"][-1]
    require(meta["facts"] == endpoint["cursor"] and meta["integrity"] == "VERIFIED_PUBLISHED", path.name)
    seen = sha256()
    with ZipFile(path) as archive:
        require(sha256(archive.read("final.frame")).hexdigest() == endpoint["frame_sha256"], "Terminal frame mismatch")
        with archive.open("facts.bin") as raw:
            for head, body in prefixed(raw):
                seen.update(head)
                seen.update(body)
    require(seen.hexdigest() == endpoint["canonical_sha256"], "Canonical history digest mismatch")
    api = ReadAPI(catalog)
    url = f"/api/v1/world/{meta['key']}"
    nest = api.dispatch(f"{url}/volume?time_ms={endpoint['time_ms']}")["data"]
    terrain = api.dispatch(f"{url}/geometry?time_ms={endpoint['time_ms']}")["data"]
    require(nest["world_id"] == receipt["inputs"]["world_id"] and nest["revision"] == terrain["revision"] == endpoint["soil_edits"],
            "Geometry observations disagree with the committed archive")
    state = api.dispatch(f"{url}/state?time_ms={endpoint['time_ms']}")["data"]
    require(bool(state["population"]["queens_alive"]) == endpoint["queen_alive"], "Queens disagree with the receipt")
    require(state["population"]["workers"] == endpoint["live"].get("Worker", 0), "Workers disagree with the receipt")
    return dict(archive=path.name, sha256=digest, cursor=meta["facts"], world_id=meta["world_id"],
                geometry_revision=nest["revision"], volume_bytes=len(b64decode(nest["materials_b64"])),
                source_check=meta["integrity"], indexing=meta["timings"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "experiments/m1")
    parser.add_argument("--scratch", type=Path, default=ROOT / "out")
    parser.add_argument("--rerun", type=Path)
    args = parser.parse_args()
    root = args.data
    checked = verify_physics36(root / "baseline-native.jsonl", args.rerun or root / "baseline-final.jsonl")
    if args.rerun:
        print(json.dumps({"physics36_byte_exact": checked}))
        return
    paired = scenario_rows(root / "paired.jsonl", "paired")
    extended = scenario_rows(root / "extended.jsonl", "extended")
    supplement = scenario_rows(root / "witness90.jsonl", "witness90")
    before, published = extended[2], supplement[0]
    require(published["status"] == "COMPLETE" and before["inputs"]["initial"] == published["inputs"]["initial"],
            "The bounded shallow-plug witness did not complete or has different initial bytes")
    observed = next(cut for cut in before["cuts"] if cut["day"] == 90)
    require(all(observed[field] == published["cuts"][0][field] for field in ("frame_sha256", "canonical_sha256")),
            "The bounded witness disagrees with the historical day-90 cut")
    for row in paired:
        inputs, cuts = row["inputs"], row["cuts"]
        require(inputs["physics"] == (37 if "reachable" in inputs["command"] else 36), "Experimental version changed")
        if " blocked " in inputs["command"]:
            require(all(not cut["counts"].get("worker_surface_entries") and not sum(cut["delivered_ug"]) for cut in cuts),
                    "A blocked control accessed the external supply")
    args.scratch.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=args.scratch, prefix="m1-verify-") as temp:
        catalog = Catalog(Path(temp))
        reports = [verify_witness(catalog, root / "witnesses" / row["witness"]["name"], row)
                   for row in extended + supplement if "witness" in row]
    print(json.dumps(dict(physics36_byte_exact=checked, paired=len(paired), extended=len(extended), witnesses=reports), indent=2))


if __name__ == "__main__":
    main()
