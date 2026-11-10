"""Independently verify published v2 block and anchor bytes with Python."""

import argparse
import hashlib
import sqlite3
import struct
import uuid
import zlib
from pathlib import Path

from run_s6_3_4 import file_hash, write_json


ZERO = bytes(32)
BLOCK = struct.Struct("<8s4H4Q2q2I32s32s")
OBSERVATION = 42
MAX_RAW = 4096 * 214


def require(condition, message):
    if not condition:
        raise ValueError(message)


def key(text):
    value = int(text, 16)
    require(f"{value:016x}" == text, "noncanonical SQLite uint64")
    return value


def fnv(data):
    value = 14695981039346656037
    for byte in data:
        value = ((value ^ byte) * 1099511628211) & (2**64 - 1)
    return value


def open_readonly(path):
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)


def audit_world(db, manifest):
    world, tip_gen, tip_rev, tip_time, tip_cursor, tip_frame_hash = manifest
    identity = uuid.UUID(world).int
    hi, lo = identity >> 64, identity % (2**64)
    cursor = previous_time = previous_revision = raw_total = block_count = packed_total = 0
    tail = ZERO
    boundaries = {0: (tail, 0, 0)}
    facts = hashlib.sha256()
    for row in db.execute(
            "SELECT first_id,last_id,begin_ms,end_ms,raw_bytes,digest,envelope "
            "FROM fact_blocks WHERE world=? ORDER BY last_id", (world,)):
        first_key, last_key, first_time, last_time, raw_size, digest, envelope = row
        require(BLOCK.size <= len(envelope) <= BLOCK.size + MAX_RAW + 1024, "invalid envelope size")
        (magic, version, codec, schema, flags, b_hi, b_lo, first, last, begin, end,
         raw_bytes, packed, predecessor, digest_in_header) = BLOCK.unpack_from(envelope)
        compressed = envelope[BLOCK.size:]
        require((magic, version, codec, schema, flags) == (b"AWFACT01", 1, 1, 1, 0),
                "unexpected block format")
        require((b_hi, b_lo) == (hi, lo) and key(first_key) == first == cursor + 1
                and key(last_key) == last and 1 <= last - first + 1 <= 4096, "world or block cursor mismatch")
        require(previous_time <= begin == first_time <= end == last_time and
                raw_size == raw_bytes and 0 < raw_bytes <= MAX_RAW and packed == len(compressed),
                "block time or size mismatch")
        require(predecessor == tail and digest_in_header == digest
                and hashlib.sha256(envelope[:104] + compressed).digest() == digest,
                "block digest or predecessor mismatch")
        decoder = zlib.decompressobj()
        raw = decoder.decompress(compressed, raw_bytes + 1)
        require(len(raw) == raw_bytes and decoder.eof and not decoder.unconsumed_tail
                and not decoder.unused_data, "invalid bounded zlib stream")
        offset = 0
        for event_id in range(first, last + 1):
            size, = struct.unpack_from("<I", raw, offset)
            offset += 4
            require(size in (159, 210) and offset + size <= raw_bytes, "invalid canonical record size")
            fid, fhi, flo, time, _ = struct.unpack_from("<5Q", raw, offset)
            revision, = struct.unpack_from("<Q", raw, offset + 41)
            kind = raw[offset + 65]
            require((fid, fhi, flo) == (event_id, hi, lo) and previous_time <= time <= end and
                    revision > previous_revision and kind <= 43 and (size == 210) == (kind == OBSERVATION),
                    "canonical identity, time, schema or revision mismatch")
            if event_id == first:
                require(time == begin, "wrong first fact time")
            previous_time, previous_revision = time, revision
            offset += size
        require(offset == len(raw) and previous_time == end, "wrong block terminator")
        facts.update(raw)
        raw_total += raw_bytes
        block_count += 1
        packed_total += len(envelope)
        cursor, tail = last, digest
        boundaries[cursor] = (tail, previous_time, previous_revision)

    frames = []
    parent = ZERO
    for row in db.execute(
            "SELECT generation,revision,cursor,checkpoint_hash,time_ms,checkpoint,parent,tail,digest "
            "FROM generations JOIN history_anchors USING(world,generation) "
            "WHERE world=? ORDER BY generation", (world,)):
        gen, rev, cut, frame_hash = map(key, row[:4])
        time, frame, previous, ending, digest = row[4:]
        boundary, end_time, end_revision = boundaries[cut]
        require(frame[:8] == b"AWSTATE1" and fnv(frame) == frame_hash and
                fnv(frame[:-8]) == int.from_bytes(frame[-8:], "little"), "invalid frame encoding or checksum")
        if frames:
            last = frames[-1]
            require(gen == last["generation"] + 1 and time >= last["time_ms"] and
                    cut >= last["cursor"] and rev >= last["revision"], "invalid checkpoint order")
        require(time >= end_time and rev >= end_revision and previous == parent and ending == boundary,
                "checkpoint does not bind an exact fact cut")
        header = struct.pack("<8s7Q", b"AWANCH01", hi, lo, gen, rev, cut, frame_hash, time)
        require(hashlib.sha256(header + parent + ending + frame).digest() == digest, "wrong checkpoint anchor")
        frames.append({"generation": gen, "revision": rev, "cursor": cut, "time_ms": time,
                       "frame_hash": frame_hash, "frame_sha256": hashlib.sha256(frame).hexdigest(),
                       "anchor_sha256": digest.hex()})
        parent = digest
    require(frames, "missing frame history")
    last = frames[-1]
    require((last["generation"], last["revision"], last["cursor"], last["time_ms"], last["frame_hash"])
            == (key(tip_gen), key(tip_rev), key(tip_cursor), tip_time, key(tip_frame_hash))
            and cursor == last["cursor"], "manifest does not publish exact fact and frame tips")
    for table in ("generations", "history_anchors"):
        count, = db.execute(f"SELECT count(*) FROM {table} WHERE world=?", (world,)).fetchone()
        require(count == len(frames), "extra or unpaired frame data")
    return {"world": world, "facts": cursor, "blocks": block_count, "raw_bytes": raw_total,
            "packed_bytes": packed_total, "canonical_sha256": facts.hexdigest(), "tail_sha256": tail.hex(),
            "frames": frames}


def audit(path):
    with open_readonly(path) as db:
        db.execute("BEGIN")
        require(db.execute("PRAGMA quick_check").fetchall() == [("ok",)], "SQLite quick check failed")
        require(db.execute("PRAGMA foreign_key_check").fetchall() == [], "orphaned durable data")
        require(db.execute("PRAGMA application_id").fetchone() == (1096234835,) and
                db.execute("PRAGMA user_version").fetchone() == (2,), "expected AntWorld schema v2")
        manifests = db.execute("SELECT world,generation,revision,time_ms,cursor,checkpoint_hash "
                               "FROM worlds ORDER BY world").fetchall()
        require(manifests, "empty durable archive")
        return [audit_world(db, manifest) for manifest in manifests]


def legacy_canonical(path, world):
    digest = hashlib.sha256()
    count = 0
    with open_readonly(path) as db:
        require(db.execute("PRAGMA user_version").fetchone() == (1,), "expected legacy archive")
        for count, (id_hex, payload) in enumerate(db.execute(
                "SELECT id,payload FROM events WHERE world=? ORDER BY id", (world,)), 1):
            require(key(id_hex) == count == struct.unpack_from("<Q", payload)[0], "legacy cursor mismatch")
            digest.update(struct.pack("<I", len(payload)))
            digest.update(payload)
    return count, digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--legacy", type=Path, help="Original v1 source for shadow migration")
    args = parser.parse_args()
    results = audit(args.database)
    receipt = {"status": "PASS", "worlds": results}
    if args.legacy:
        for result in results:
            require(legacy_canonical(args.legacy, result["world"]) ==
                    (result["facts"], result["canonical_sha256"]), "shadow facts differ from legacy source")
        receipt["legacy_canonical_equal"] = True
        receipt["legacy_database_sha256"] = file_hash(args.legacy)
    write_json(args.receipt, receipt)


if __name__ == "__main__":
    main()
