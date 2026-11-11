"""Verify and decode closed RM-02 sidecars without the simulator."""

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
from pathlib import Path
import sqlite3
import struct
from uuid import UUID


FACT = struct.Struct("<QQQqQBQQQBQQQdddQQQQBBBBdB")
CARE = struct.Struct("<BBQQqBddd")
HEADER = struct.Struct("<14Q")
RECORD = struct.Struct("<BI")
KINDS = (
    "Diagnostic", "ColonySeeded", "AntSeeded", "FoodSeeded", "Moved", "FoodCollected",
    "ActionRejected", "StageChanged", "AntDied", "SurfaceConfigured", "ForagingStarted",
    "ForagingDecision", "FoodDelivered", "Rested", "TrailMaintenance", "PhysiologyEnabled",
    "PhysiologyUpdated", "BehaviorChanged", "NutritionDecision", "CargoIngested", "NestIngested",
    "NutritionTransferred", "GeometryConfigured", "SoilExcavated", "SoilDropped", "SoilPickedUp",
    "SoilFilled", "ExcavationDecision", "FoodPlaced", "SocialConfigured", "AutonomyChanged",
    "AutonomyDecision", "LongTermConfigured", "ReproductionEnabled", "ReproductionAttempt", "AntBorn",
    "ResourceCycleConfigured", "ResourceReleased", "ProteinRecycled", "BiologyConfigured",
    "CareProgramChanged", "CareTick", "BiologicalObservation", "BroodMoved",
)
STAGES = ("egg", "larva", "pupa", "adult", "dead")
CASTES = ("worker", "queen", "male")
OUTCOMES = (
    "Success", "Partial", "MissingEntity", "DeadActor", "InvalidStage", "OutOfBounds",
    "TooFast", "StalePosition", "OutOfReach", "Depleted", "Capacity", "DuplicateAction",
    "InvalidTransition", "AlreadyDead", "Blocked", "NonLocalMove", "NotAtNest", "EmptyInventory",
    "StaleGeometry", "NonDiggable", "InvalidGeometry", "InsufficientEnergy",
)
DEATHS = ("none", "energy_depleted", "dehydrated", "fixture")
PROGRAMS = ("Paused", "Rest", "Nurse", "Forage", "Excavate")
COMPONENTS = ("carb", "protein", "water", "other")


def require(condition, message):
    if not condition:
        raise ValueError(message)


@dataclass(frozen=True, slots=True)
class Fact:
    event: int
    time: int
    source: int
    revision: int
    actor: int
    payload: int
    auxiliary: int
    kind: str
    mass: tuple
    stage: int
    outcome: str
    care: tuple


def decode_fact(data, world):
    require(len(data) >= FACT.size, "short canonical fact")
    row = FACT.unpack_from(data)
    require(row[1:3] == world, "canonical fact WorldId mismatch")
    kind = KINDS[row[9]]
    care = ()
    if kind == "BiologicalObservation":
        require(len(data) == FACT.size + CARE.size, "wrong care record size")
        care = CARE.unpack_from(data, FACT.size)
    else:
        require(len(data) == FACT.size, "unexpected canonical fact suffix")
    return Fact(row[0], row[3], row[4], row[6], row[10], row[7], row[8],
                kind, row[16:20], row[20], OUTCOMES[row[21]], care)


def unpack(payload, version, limit):
    if version == 1 or not payload or payload[0]:
        require(len(payload) <= limit, "raw cut exceeds manifest limit")
        return payload
    require(len(payload) >= 5, "short packed cut")
    size = int.from_bytes(payload[1:5], "little")
    require(len(payload) < size <= min(limit, 400 * 1024), "invalid packed cut size")
    result = bytearray(size)
    at = 5
    for first in range(0, size, 8):
        require(at < len(payload), "missing sparse mask")
        mask = payload[at]
        at += 1
        require(mask < (1 << min(8, size - first)), "sparse mask exceeds raw length")
        while mask:
            bit = mask & -mask
            require(at < len(payload) and payload[at] != 0, "missing or redundant sparse value")
            result[first + bit.bit_length() - 1] = payload[at]
            at += 1
            mask ^= bit
    require(at == len(payload), "trailing sparse bytes")
    return result


def records(payload):
    at = 0
    while at < len(payload):
        require(len(payload) - at >= RECORD.size, "incomplete record header")
        tag, size = RECORD.unpack_from(payload, at)
        at += RECORD.size
        require(1 <= tag <= 5 and 0 < size <= len(payload) - at, "invalid record tag or length")
        yield tag, memoryview(payload)[at:at + size]
        at += size


def numbers(data):
    require(len(data) % 8 == 0, "invalid observation word count")
    return struct.unpack(f"<{len(data) // 8}Q", data)


@contextmanager
def open_sidecar(path):
    uri = Path(path).resolve().as_uri() + "?mode=ro"
    db = sqlite3.connect(uri, uri=True)
    try:
        app_id, = db.execute("PRAGMA application_id").fetchone()
        version, = db.execute("PRAGMA user_version").fetchone()
        require(app_id == 1096241714 and version in (1, 2), "foreign sidecar format")
        identity, origin = db.execute("SELECT identity,origin FROM manifest WHERE id=1").fetchone()
        magic, lineage, world, seed, all_relevant, pending, late, neighbor, limit, *focal = identity.splitlines()
        require(magic == "RM02-SIDECAR-1" and 0 <= origin, "invalid sidecar manifest")
        require(all(v in ("0", "1") for v in (all_relevant, pending, late)), "invalid manifest scope flags")
        entity_ids = tuple(map(int, focal))
        require(len(entity_ids) <= 64 and entity_ids == tuple(sorted(set(entity_ids))), "invalid focal scope")
        limit = int(limit)
        require(0 < limit <= 3 * 1024 * 1024, "invalid payload limit")
        world_id = UUID(world).int
        anchors = {seq: value.hex() for seq, value in db.execute("SELECT seq,checkpoint_sha256 FROM anchors")}
        metadata = dict(world_id=world, world=(world_id >> 64, world_id & (2**64 - 1)), seed=int(seed),
                        lineage=lineage, origin=origin, focal=entity_ids, all_relevant=all_relevant == "1",
                        pending=pending == "1", late=late == "1", neighbor=int(neighbor),
                        limit=limit, version=version, anchors=anchors)
        yield metadata, read_cuts(db, identity, metadata)
    finally:
        db.close()


def read_cuts(db, identity, manifest):
    cursor = manifest["origin"]
    prior = hashlib.sha256(identity.encode() + struct.pack("<Q", cursor)).digest()
    previous = (0, 0)
    sql = ("SELECT seq,sim_ms,revision,cursor,rng,from_cursor,examined,selected,records,dropped,"
           "pending,neighbors,payload,digest FROM cuts ORDER BY seq")
    for expected, row in enumerate(db.execute(sql), 1):
        seq, at, revision, end, rng, start, examined, selected, count, dropped, pending, neighbors, raw, digest = row
        require(seq == expected and start == cursor and at >= previous[0] and revision >= previous[1]
                and 0 <= selected <= examined == end - start and 0 <= pending <= 3 and 0 <= neighbors <= 3,
                "invalid or noncontiguous cut")
        require(len(rng) == 16 and rng == f"{int(rng, 16):016x}", "invalid RNG identity")
        header = HEADER.pack(seq, *manifest["world"], at, revision, end, int(rng, 16), start, examined,
                             selected, count, dropped, pending, neighbors)
        require(digest == hashlib.sha256(prior + header + raw).digest(), "invalid cut digest")
        data = unpack(raw, manifest["version"], manifest["limit"])
        parsed = list(records(data))
        fact_count = sum(tag == 1 for tag, _ in parsed)
        require(len(parsed) == count and fact_count <= selected <= fact_count + dropped, "cut coverage differs")
        yield dict(seq=seq, time=at, revision=revision, cursor=end, start=start, examined=examined,
                   selected=selected, records=count, dropped=dropped, pending=pending, neighbors=neighbors,
                   raw_bytes=len(data), packed_bytes=len(raw), digest=digest.hex(), payload=parsed)
        cursor, previous, prior = end, (at, revision), digest
