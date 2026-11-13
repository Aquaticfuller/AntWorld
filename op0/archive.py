"""Stream source archives through integrity checks before publishing a browse cache."""

from contextlib import closing, contextmanager
import csv
from hashlib import sha256
import io
import json
from pathlib import Path
import shutil
import sqlite3
from struct import Struct
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile, is_zipfile
import zlib

from .codec import FACT, OBS, U32, U64, checkpoint, fnv, require, world_id


MAX_FRAME = 768 * 1024**2
MAX_MEMBER = 8 * 1024**3
MAX_SAMPLES = 64 * 1024**2  # Individual cuts are held while facts are streamed.
BLOCK = Struct("<8s4H4Q2q2I32s32s")
ANCHOR = Struct("<8s7Q")
ZERO = bytes(32)
SQLITE_ID = 1096234835
PUBLISHED = ("initial.chk", "final.frame", "facts.bin")
OPTIONAL = ("case.json", "parameters.txt", "summary.csv", "cuts.csv", "individuals.csv", "geometry_edits.csv", "space_cuts.csv")


def file_hash(path):
    with path.open("rb") as stream:
        return digest_stream(stream)


def digest_stream(stream):
    checksum = sha256()
    while chunk := stream.read(1024 * 1024):
        checksum.update(chunk)
    return checksum.hexdigest()


def json_bytes(value):
    return json.dumps(value, ensure_ascii=True, allow_nan=False, separators=(",", ":")).encode()


def read_db(path):
    db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    db.execute("PRAGMA trusted_schema=OFF")
    db.execute("PRAGMA query_only=ON")
    return db


def csv_rows(archive, name):
    if name in archive.namelist():
        with archive.open(name) as f, io.TextIOWrapper(f, encoding="utf-8-sig", newline="") as stream:
            yield from csv.DictReader(stream)


def member(archive, name, maximum=MAX_FRAME):
    require(archive.getinfo(name).file_size <= maximum, f"Archive member exceeds the size limit: {name}")
    return archive.read(name)


def cut_rows(archive, name):
    if name in archive.namelist():
        require(archive.getinfo(name).file_size <= MAX_SAMPLES, f"Snapshot CSV exceeds the OP0 limit: {name}")
    return list(csv_rows(archive, name))


def prefixed(stream):
    while head := stream.read(4):
        require(len(head) == 4, "Truncated event length")
        size = U32.unpack(head)[0]
        require(size in (FACT.size, FACT.size + OBS.size), "Unsupported event size")
        payload = stream.read(size)
        require(len(payload) == size, "Truncated canonical event")
        yield head, payload


def checkpoint_history(raw, cut):
    position = cut["fact_offset"]
    for _ in range(cut["cursor"]):
        size = FACT.size + (OBS.size if raw[position + 65] == 42 else 0)
        yield U32.pack(size), memoryview(raw)[position:position + size]
        position += size


def zip_terminal_frame(path):
    # The checked-in catalogue can show the terminal snapshot before indexing its entire history.
    with ZipFile(path) as archive:
        return checkpoint(member(archive, "final.frame", 8 * 1024**2))


def zip_inputs(path):
    """Yield one projection input while the checked ZIP is open."""
    with ZipFile(path) as f:
        names = f.namelist()
        require(len(set(names)) == len(names), "Duplicate ZIP member")
        require(all(i.file_size <= MAX_MEMBER and not i.flag_bits & 1 for i in f.infolist()), "Oversized or encrypted ZIP member")
        require(all(name in names for name in PUBLISHED), "ZIP needs initial.chk, final.frame and facts.bin")
        receipt = json.loads(member(f, "receipt.json", 2 * 1024**2)) if "receipt.json" in names else {}
        if receipt:
            signed = receipt.get("artifacts", {})
            require(set(signed) == set(names) - {"receipt.json"}, "Receipt member list differs from ZIP")
            require(receipt.get("status", "COMPLETE") == "COMPLETE", "This archive contains a partial engineering run")
        else:
            signed = {}
        hashes = {}
        for name in names:
            if name == "facts.bin":
                continue
            with f.open(name) as stream:
                hashes[name] = digest_stream(stream)
            if name in signed:
                require(signed[name] == dict(sha256=hashes[name], bytes=f.getinfo(name).file_size), f"Member hash mismatch: {name}")
        initial_raw, final_raw = (member(f, name) for name in PUBLISHED[:2])
        initial, final = checkpoint(initial_raw), checkpoint(final_raw)
        require(not initial["framed"] and final["framed"] and initial["world"] == final["world"] and
                initial["physics"] == final["physics"] and initial["seed"] == final["seed"] and
                initial["cursor"] <= final["cursor"] and initial["time_ms"] <= final["time_ms"], "ZIP checkpoint identity mismatch")
        initial_prefix = digest(checkpoint_history(initial_raw, initial))
        case = json.loads(member(f, "case.json", 2 * 1024**2)) if "case.json" in names else {}
        summary = next(csv_rows(f, "summary.csv"), None)
        if summary:
            require((summary.get("world"), int(summary["time_ms"]), int(summary["events"]), int(summary["seed"])) ==
                    (final["world"], final["time_ms"], final["cursor"], final["seed"]), "Archive summary disagrees with committed frame")
        capture = dict(kind="ZIP", hashes=hashes, receipt_verified=bool(signed), initial_prefix=initial_prefix,
                       initial_cursor=initial["cursor"], facts_expected=signed.get("facts.bin", {}).get("sha256"),
                       cuts=cut_rows(f, "cuts.csv"), people=cut_rows(f, "individuals.csv"),
                       comparable=bool(case.get("parameters") and receipt), case=case, provenance=receipt.get("identity"))
        if "parameters.txt" in names:
            capture["parameters_text"] = member(f, "parameters.txt", 2 * 1024**2).decode("utf-8")
        with f.open("facts.bin") as source:
            yield initial, final, [initial, final], prefixed(source), capture


def key(text):
    value = int(text, 16)
    require(f"{value:016x}" == text, "Noncanonical SQLite uint64")
    return value


def digest(records):
    checksum = sha256()
    for head, payload in records:
        checksum.update(head)
        checksum.update(payload)
    return checksum.hexdigest()


def fact_blocks(db, world, boundaries, schema):
    after = previous_time = 0
    predecessor = ZERO
    for first_key, last_key, start, end, size, checksum, envelope in db.execute(
            "SELECT first_id,last_id,begin_ms,end_ms,raw_bytes,digest,envelope FROM fact_blocks WHERE world=? ORDER BY last_id", (world,)):
        require(BLOCK.size <= len(envelope) <= BLOCK.size + 4096 * 214 + 1024, "Unsupported block size")
        magic, encoding, codec, fact_schema, reserved, hi, lo, first, last, begin, finish, raw_size, packed, parent, own = BLOCK.unpack_from(envelope)
        compressed = memoryview(envelope)[BLOCK.size:]
        require(1 <= fact_schema <= 9 and magic == f"AWFACT{fact_schema:02d}".encode() and encoding == fact_schema and codec == 1 and
                reserved == 0 and (fact_schema == schema or max(fact_schema, schema) <= 2), "Unsupported SQLite block format")
        require(world_id(hi, lo) == world and first == key(first_key) == after + 1 and last == key(last_key) and
                1 <= last - first + 1 <= 4096 and previous_time <= begin == start <= finish == end and
                size == raw_size and (last - first + 1) * 163 <= size <= (last - first + 1) * 214 and
                len(compressed) == packed and predecessor == parent and own == checksum and
                sha256(envelope[:104] + compressed).digest() == own, "SQLite block identity or digest mismatch")
        decoder = zlib.decompressobj()
        raw = decoder.decompress(compressed, size + 1)
        require(len(raw) == size and decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail,
                "Invalid bounded SQLite zlib stream")
        offset = 0
        for event_id in range(first, last + 1):
            require(offset + 4 <= len(raw), "Truncated block length")
            length = U32.unpack_from(raw, offset)[0]
            stop = offset + length + 4
            require(length in (159, 210) and stop <= len(raw), "Invalid block event size")
            start_record = offset + 4
            identifier, _, _, time = Struct("<4Q").unpack_from(raw, start_record)
            require(identifier == event_id and begin <= time <= finish and (event_id != first or time == begin) and
                    (event_id != last or time == finish), "Block event disagrees with envelope boundaries")
            yield raw[offset:start_record], memoryview(raw)[start_record:stop]
            offset = stop
        require(offset == len(raw), "Trailing bytes in canonical block")
        after, previous_time, predecessor = last, finish, own
        boundaries[last] = own, finish


def read_anchors(db, manifest, version):
    world, gen, rev, stamp, cursor, checksum, prefix = manifest
    position = "world,generation,revision,cursor,checkpoint_hash,time_ms,checkpoint"
    tables = "generations JOIN history_anchors USING(world,generation)" if version == 2 else "generations"
    fields = position + (",parent,tail,digest" if version == 2 else "")
    anchors, snapshots, parent, legacy = {}, [], ZERO, None
    for _, generation, revision, boundary, frame_hash, at, raw, *chain in db.execute(
            f"SELECT {fields} FROM {tables} WHERE world=? ORDER BY generation", (world,)):
        require(len(raw) <= MAX_FRAME and fnv(raw) == key(frame_hash), "SQLite checkpoint hash mismatch or too large")
        cut = checkpoint(raw)
        require(cut["world"] == world and (cut["revision"], cut["time_ms"], cut["cursor"]) == (key(revision), at, key(boundary))
                and cut["framed"] == (version == 2), "SQLite anchor disagrees with frame")
        if chain:
            previous, tail, checksum_bytes = chain
            identity = int(world.replace("-", ""), 16)
            header = ANCHOR.pack(b"AWANCH01", identity >> 64, identity & ((1 << 64) - 1), key(generation), key(revision),
                                 key(boundary), key(frame_hash), at)
            require(parent == previous and sha256(header + previous + tail + raw).digest() == checksum_bytes, "SQLite anchor chain mismatch")
            parent = checksum_bytes
            anchors[cut["cursor"]] = tail, cut["time_ms"]
        else:
            legacy = raw
        if snapshots:
            before = snapshots[-1]
            require(before["time_ms"] <= at and before["cursor"] <= cut["cursor"] and before["physics"] == cut["physics"],
                    "SQLite generation order or physics mismatch")
        snapshots.append(cut)
        tip = generation, revision, at, boundary, frame_hash
    require(snapshots and tip == (gen, rev, stamp, cursor, checksum), "SQLite manifest has no matching published tip")
    if version == 2:
        count, = db.execute("SELECT count(*) FROM generations WHERE world=?", (world,)).fetchone()
        require(count == len(snapshots), "SQLite generation is missing an anchor")
    return snapshots, anchors, legacy


def legacy_records(db, world):
    for identifier, raw in db.execute("SELECT id,payload FROM events WHERE world=? ORDER BY id", (world,)):
        require(len(raw) in (159, 210) and U64.unpack_from(raw)[0] == key(identifier), "SQLite row disagrees with canonical event")
        yield U32.pack(len(raw)), raw


def sqlite_inputs(path):
    with closing(read_db(path)) as db:
        db.execute("BEGIN")
        application, = db.execute("PRAGMA application_id").fetchone()
        version, = db.execute("PRAGMA user_version").fetchone()
        require(application == SQLITE_ID and version in (1, 2), "Unsupported AntWorld SQLite store")
        require(db.execute("PRAGMA quick_check").fetchone() == ("ok",) and db.execute("PRAGMA foreign_key_check").fetchone() is None,
                "SQLite integrity or reference check failed")
        manifests = db.execute("SELECT world,generation,revision,time_ms,cursor,checkpoint_hash,prefix_hash,seed,quantum_m "
                               "FROM worlds ORDER BY world").fetchall()
        require(manifests, "SQLite store contains no published worlds")
        for manifest in manifests:
            world = manifest[0]
            cuts, anchors, legacy = read_anchors(db, manifest[:7], version)
            first, tip = cuts[0], cuts[-1]
            quantum = tip["geometry"]["quantum_m"] if tip["geometry"] else 0
            require(tip["seed"] == key(manifest[7]) and quantum == manifest[8], "SQLite manifest configuration disagrees with frame")
            if version == 1:
                payload = memoryview(legacy)[tip["fact_offset"]:tip["fact_end"]]
                require(fnv(payload) == key(manifest[6]), "SQLite legacy prefix hash mismatch")
            else:
                require(key(manifest[6]) == 0, "Unexpected legacy prefix in segmented SQLite")
            boundaries = {0: (ZERO, 0)}
            facts_schema = min(9, max(1, tip["schema"] - 13 if tip["schema"] >= 15 else 1))
            records = (fact_blocks(db, world, boundaries, facts_schema) if version == 2 else legacy_records(db, world))
            capture = dict(kind=f"SQLite v{version}", hashes={}, receipt_verified=False, cuts=[], people=[], comparable=False, case={},
                           facts_expected=digest(checkpoint_history(legacy, tip)) if legacy is not None else None)
            yield first, tip, cuts, records, capture
            for cursor, (tail, at) in anchors.items():
                require(cursor in boundaries and boundaries[cursor][0] == tail and boundaries[cursor][1] <= at,
                        "SQLite anchor does not bind its committed prefix")


def fingerprint(path):
    members = {"archive": file_hash(path)}
    wal = path.with_name(path.name + "-wal")
    if wal.is_file() and not is_zipfile(path):
        members["wal"] = file_hash(wal)
    return members


@contextmanager
def source_inputs(path, scratch, fingerprinted):
    if is_zipfile(path):
        with closing(zip_inputs(path)) as inputs:
            yield inputs
        return
    with TemporaryDirectory(dir=scratch, prefix="source-") as folder:
        copy = Path(folder) / "input.sqlite"
        shutil.copyfile(path, copy)
        require(file_hash(copy) == fingerprinted["archive"], "Source SQLite changed during copy; import a stable backup")
        if "wal" in fingerprinted:
            wal = path.with_name(path.name + "-wal")
            copy_wal = copy.with_name(copy.name + "-wal")
            shutil.copyfile(wal, copy_wal)
            require(file_hash(copy_wal) == fingerprinted["wal"], "Source WAL changed during copy; import a stable backup")
        with closing(sqlite_inputs(copy)) as inputs:
            yield inputs


def pack(directory, output):
    """Package real Core export members without running or modifying the world."""
    require(all((directory / n).is_file() for n in PUBLISHED), "Native output is missing a checkpoint, frame or canonical history")
    names = [n for n in (*PUBLISHED, *OPTIONAL) if (directory / n).is_file()]
    artifacts = {n: dict(sha256=file_hash(directory / n), bytes=(directory / n).stat().st_size) for n in names}
    with ZipFile(output, "x", compression=ZIP_DEFLATED, compresslevel=3) as bundle:
        for name in names:
            bundle.write(directory / name, name)
        bundle.writestr("receipt.json", json_bytes(dict(status="COMPLETE", artifacts=artifacts, provenance="OP0 native export")))
