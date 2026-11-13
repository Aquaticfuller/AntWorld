"""Build disposable browse indexes from canonical facts and committed cuts."""

from collections import Counter, defaultdict
from contextlib import closing
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from threading import Lock
from time import perf_counter
from uuid import UUID
import zlib

from . import DAY
from .archive import fingerprint, json_bytes, read_db, source_inputs
from .codec import ArchiveError, DEATHS, HIGHLIGHTS, decode_fact, label, require, sql_id


CACHE_VERSION = 6
BLOCK_RECORDS = 2048
META = "meta.json"
TABLES = """
CREATE TABLE facts(id INTEGER PRIMARY KEY, time INTEGER NOT NULL, kind INTEGER NOT NULL, actor INTEGER, related INTEGER,
                   offset INTEGER NOT NULL);
CREATE TABLE blocks(first INTEGER PRIMARY KEY, last INTEGER NOT NULL, packed BLOB NOT NULL);
CREATE TABLE ants(id INTEGER PRIMARY KEY, mother TEXT, colony TEXT NOT NULL, born INTEGER NOT NULL, birth_event INTEGER NOT NULL,
                  caste INTEGER NOT NULL, seeded INTEGER NOT NULL, dead INTEGER, death_event INTEGER, death INTEGER);
CREATE TABLE changes(ant INTEGER, event INTEGER, x REAL, y REAL, z REAL, stage INTEGER, program INTEGER,
                     PRIMARY KEY(ant,event)) WITHOUT ROWID;
CREATE TABLE samples(ant INTEGER, time INTEGER, cursor INTEGER, value TEXT, PRIMARY KEY(ant,time,cursor)) WITHOUT ROWID;
CREATE TABLE daily(time INTEGER PRIMARY KEY, cursor INTEGER, value TEXT);
CREATE TABLE edits(event INTEGER PRIMARY KEY, value TEXT NOT NULL, parcel INTEGER NOT NULL);
CREATE TABLE sources(id INTEGER PRIMARY KEY, x REAL, y REAL, z REAL, created INTEGER);
CREATE TABLE source_history(source INTEGER, event INTEGER, c INTEGER, p INTEGER, w INTEGER, o INTEGER,
                            PRIMARY KEY(source,event)) WITHOUT ROWID;
CREATE TABLE nest_history(event INTEGER PRIMARY KEY, c INTEGER, p INTEGER, w INTEGER, o INTEGER);
CREATE TABLE feedings(ant INTEGER NOT NULL, event INTEGER, PRIMARY KEY(ant,event)) WITHOUT ROWID;
"""
INDEXES = """
CREATE INDEX by_time ON facts(time,id);
CREATE INDEX by_kind ON facts(kind,id);
CREATE INDEX by_actor ON facts(actor,id) WHERE actor IS NOT NULL;
CREATE INDEX by_participant ON facts(related,id) WHERE related IS NOT NULL;
CREATE INDEX by_parcel ON edits(parcel,event);
"""
COUNTERS = {5: "collections", 12: "deliveries", 21: "trophallaxis", 23: "excavations", 24: "soil_drops",
            26: "soil_fills", 35: "births", 48: "maternal_rations", 54: "signals", 55: "exposures", 56: "activations"}
LEDGER = ("carbohydrate", "protein", "water", "other")


def sample_from_csv(row):
    result = {}
    for dest, col in (("energy_nj", "energy_nj"), ("hydration_ug", "hydration_ug"), ("tissue_protein_ug", "tissue_protein_ug"),
                      ("lipid_ug", "lipid_ug"), ("mobile_protein_ug", "mobile_protein_ug"), ("lost_water_ug", "lost_water_ug"),
                      ("stage_progress_ms", "stage_progress_ms"), ("dissipated_nj", "dissipated_nj")):
        result[dest] = int(row[col]) if row.get(col) else None
    for dest, key in (("crop_ug", "crop"), ("carried_ug", "carried")):
        result[dest] = [int(row[f"{key}_{k}"]) if row.get(f"{key}_{k}") else None for k in "cpwo"]
    return result


def sampled(capture, checkpoints, end):
    cuts, people = {}, defaultdict(list)
    for r in capture["cuts"]:
        time, cursor = int(r["time_ms"]), int(r["cursor"])
        require(0 <= time <= end and (time, cursor) not in cuts, "Invalid or duplicate daily cut")
        sets = {name: [int(r[f"{key}_{k}"]) for k in "cpwo"] for name, key in (("external_ug", "available"), ("nest_ug", "nest"))
                if all(r.get(f"{key}_{k}") is not None for k in "cpwo")}
        cuts[time, cursor] = dict(**sets, living=int(r["living"]), geometry_revision=int(r["geometry_revision"])
                                  if r.get("geometry_revision") else None,
                                  soil_remaining_q3=int(r["remaining_q3"]) if r.get("remaining_q3") else None)
    for row in capture["people"]:
        time, cursor = int(row["time_ms"]), int(row["cursor"])
        require((time, cursor) in cuts, "Individual sample lacks its committed cut")
        position = tuple(float(row[f"{axis}_m"]) for axis in "xyz")
        require(all(map(isfinite, position)), "Invalid sampled position")
        item = sample_from_csv(row)
        people[time, cursor].append((int(row["id"]), int(row["stage"]), position, item))
    for cut in checkpoints:
        time, cursor = cut["time_ms"], cut["cursor"]
        if (time, cursor) not in cuts:
            sets = dict(external_ug=cut["available"], nest_ug=cut["stored"], living=cut["living"],
                        geometry_revision=len(cut["edits"]), soil_remaining_q3=cut["soil"][1] if cut["soil"] else None)
            cuts[time, cursor] = sets
            people[time, cursor] = [(i, ant["stage"], ant["position_m"], dict(energy_nj=ant.get("energy_nj"), hydration_ug=ant.get("hydration_ug"),
                             tissue_protein_ug=ant.get("tissue_protein_ug"), crop_ug=ant.get("crop_ug"), carried_ug=ant["carried_ug"]))
                            for i, ant in cut["ants"].items()]
    return cuts, people


def as_key(path, members):
    return sha256(json_bytes([CACHE_VERSION, 0, str(path), members])).hexdigest()[:24]


class IndexBuilder:
    def __init__(self, database, tip, capture, checkpoints):
        self.db = database
        self.tip = tip
        self.source = capture
        self.ants = tip["ants"]
        self.positions, self.stages, self.programs, self.ownership = {}, {}, {}, {}
        self.external, self.nest = (0, 0, 0, 0), (0, 0, 0, 0)
        self.stocks, self.deaths, self.fed = {}, Counter(), set()
        self.counts, self.totals = Counter(), Counter()
        self.cohort = None
        self.milestones = {}
        self.edits = {r["event"]: r for r in tip["edits"]}
        self.edits_seen, self.excavated, self.filled = 0, 0, 0
        self.samples, self.sample_people = sampled(capture, checkpoints, tip["time_ms"])
        self.sample_cuts = iter(sorted(self.samples, key=lambda cut: (cut[1], cut[0])))
        self.next_sample = next(self.sample_cuts, None)
        self.queen_samples = {}
        self.recorded_day_cuts = {int(row["time_ms"]) for row in capture["cuts"]} if capture["people"] else set()
        end = tip["time_ms"]
        step = max(DAY, (end + 179) // 180)
        self.timeline = iter(sorted(set(range(0, end + 1, step)) | {time for time, _ in self.samples} | {end}))
        self.next_cut = next(self.timeline, None)
        self.identity = UUID(tip["world"]).int
        self.cached = []
        self.raw = bytearray()
        self.first = 1

    def milestone(self, name, fact):
        self.milestones.setdefault(name, dict(label=name, id=str(fact.id), time_ms=fact.time, ant=str(fact.actor) if fact.actor else None))

    def flush(self):
        if self.cached:
            self.db.executemany("INSERT INTO facts VALUES(?,?,?,?,?,?)", self.cached)
            self.db.execute("INSERT INTO blocks VALUES(?,?,?)", (self.first, self.cached[-1][0], zlib.compress(self.raw, 3)))
            self.first = self.cached[-1][0] + 1
            self.cached.clear()
            self.raw.clear()

    def commit_samples(self, cursor, before, after):
        # Several persisted generations can have the same millisecond but different committed prefixes.
        while self.next_sample is not None and self.next_sample[1] == cursor:
            time, _ = self.next_sample
            require(before <= time <= after, "Sample time does not match the committed prefix")
            detail = self.samples[self.next_sample]
            require(detail["living"] == sum(self.counts.values()), "Living population differs from committed facts")
            for field, known in (("external_ug", self.external), ("nest_ug", self.nest), ("geometry_revision", self.edits_seen)):
                sampled_value = detail.get(field)
                if sampled_value is not None:
                    require((tuple(sampled_value) if isinstance(known, tuple) else sampled_value) == known,
                            f"Sample projection disagrees: {field}")
            seen = set()
            for aid, stage, position, value in self.sample_people[self.next_sample]:
                require(aid not in seen and aid in self.stages and self.stages[aid] == stage and self.positions[aid] == position,
                        "Sampled individual differs from committed life or motion")
                seen.add(aid)
                self.db.execute("INSERT INTO samples VALUES(?,?,?,?)", (sql_id(aid), time, cursor, json_bytes(value)))
                if self.ants[aid]["caste"] == 1 and stage == 3:
                    self.queen_samples.setdefault(self.next_sample, value)
            if time in self.recorded_day_cuts and self.cohort is None and self.counts[1] and self.sample_people[self.next_sample]:
                self.cohort = dict(time_ms=time, cursor=str(cursor), members=[aid for aid, stage in self.stages.items() if stage == 1])
            if detail.get("soil_remaining_q3") is not None and self.tip["geometry"]:
                initial = self.tip["soil"][0]
                require(detail["soil_remaining_q3"] == initial - self.excavated + self.filled, "Sample soil differs from ordered edits")
            self.next_sample = next(self.sample_cuts, None)

    def cut(self, time, cursor):
        value = dict(population=self.population(), external_ug=self.external, nest_ug=self.nest,
                     cumulative=self.totals, deaths=self.deaths, excavated_q3=self.excavated, filled_q3=self.filled,
                     geometry_revision=self.edits_seen, recorded_sample=(time, cursor) in self.samples,
                     queen_sample=self.queen_samples.get((time, cursor)))
        self.db.execute("INSERT INTO daily VALUES(?,?,?)", (time, cursor, json_bytes(value)))

    def population(self):
        result = {name: self.counts[i] for i, name in enumerate(("eggs", "larvae", "pupae", "adults"))}
        queens = [str(a) for a, s in self.stages.items() if s == 3 and self.ants[a]["caste"] == 1]
        result["queens_alive"] = queens
        result["workers"] = sum(s == 3 and self.ants[a]["caste"] == 0 for a, s in self.stages.items())
        return result

    def ant_event(self, f):
        aid, kind = f.actor, f.kind
        if kind not in (2, 35, 4, 7, 8, 10, 15, 17, 43):
            return
        if kind in (2, 35):
            require(aid not in self.stages and aid in self.ants and f.stage < 4, "Duplicate or invalid individual origin")
            a = self.ants[aid]
            require(a["born_ms"] == f.time and a["colony"] == str(f.colony), "Individual origin differs from final checkpoint")
            self.stages[aid], self.positions[aid], self.counts[f.stage] = f.stage, f.position, self.counts[f.stage] + 1
            self.programs[aid] = None
            self.db.execute("INSERT INTO ants VALUES(?,?,?,?,?,?,?,NULL,NULL,NULL)",
                            (sql_id(aid), str(f.related) if f.related else None, a["colony"], f.time, f.id, a["caste"], int(kind == 2)))
            if kind == 35:
                self.milestone("First egg laid", f)
        else:
            require(aid in self.stages, "Event references an unborn individual")
            previous = self.stages[aid]
            if kind in (7, 8):
                require(previous < 4 and f.stage > previous, "Invalid life transition in archive")
                self.counts[previous] -= 1
                if f.stage < 4:
                    self.counts[f.stage] += 1
                self.stages[aid] = f.stage
                if f.stage == 4:
                    self.deaths[label(DEATHS, f.payload)] += 1
                    self.db.execute("UPDATE ants SET dead=?,death_event=?,death=? WHERE id=?", (f.time, f.id, f.payload, sql_id(aid)))
                    self.milestone("First recorded death", f)
                    if previous == 1:
                        self.milestone("First larval death", f)
                    if self.ants[aid]["caste"] == 1:
                        self.milestone("Queen died", f)
                elif f.stage == 3 and self.ants[aid]["caste"] == 0:
                    self.milestone("First worker eclosed", f)
                elif f.stage in (1, 2):
                    self.milestone("First hatch" if f.stage == 1 else "First pupation", f)
            if kind in (4, 43):
                require(previous < 4, "Dead individual has moved")
                self.positions[aid] = f.position
            if kind == 17:
                self.programs[aid] = f.payload
            elif kind == 8:
                self.programs[aid] = None
        self.db.execute("INSERT INTO changes VALUES(?,?,?,?,?,?,?)", (sql_id(aid), f.id, *self.positions[aid],
                        self.stages[aid], self.programs[aid]))

    @staticmethod
    def changed(stock, mass, sign):
        data = tuple(a + b * sign for a, b in zip(stock, mass, strict=True))
        require(min(data) >= 0, "Committed transfer overdraws its source")
        return data

    def resources(self, f):
        if f.kind in (3, 28, 37, 5, 58):
            if f.kind in (3, 28):
                require(f.resource not in self.stocks, "Duplicate source identity")
                self.stocks[f.resource] = (0, 0, 0, 0)
                self.db.execute("INSERT INTO sources VALUES(?,?,?,?,?)", (sql_id(f.resource), *f.position, f.id))
            require(f.resource in self.stocks, "Unseeded resource")
            sign = -1 if f.kind in (5, 58) else 1
            self.stocks[f.resource] = self.changed(self.stocks[f.resource], f.mass, sign)
            self.external = self.changed(self.external, f.mass, sign)
            self.db.execute("INSERT INTO source_history VALUES(?,?,?,?,?,?)", (sql_id(f.resource), f.id, *self.stocks[f.resource]))
        if f.kind in (12, 38, 20, 51):
            self.nest = self.changed(self.nest, f.mass, 1 if f.kind in (12, 38) else -1)
            self.db.execute("INSERT INTO nest_history VALUES(?,?,?,?,?)", (f.id, *self.nest))
        if f.kind in (21, 48) and any(f.mass):
            self.fed.add(f.related)
            self.db.execute("INSERT INTO feedings VALUES(?,?)", (sql_id(f.related), f.id))

    def geometry_event(self, f):
        edit = self.edits.get(f.id)
        if f.kind in (23, 26) or edit:
            require(edit and f.kind == (23 if edit["kind"] == 0 else 26) and edit["edit"] == self.edits_seen + 1 and
                    (edit["actor"], edit["source"], edit["parcel"], edit["time_ms"]) == (f.actor, f.source, f.payload, f.time),
                    "Geometry edit lacks its canonical event")
            self.edits_seen += 1
            if f.kind == 23:
                self.excavated += edit["volume_q3"]
            else:
                self.filled += edit["volume_q3"]
            self.db.execute("INSERT INTO edits VALUES(?,?,?)", (f.id, json_bytes(edit), sql_id(f.payload)))

    def index(self, records):
        checksum, prefix = sha256(), sha256()
        previous, last, revision = 0, 0, 0
        scan = perf_counter()
        for head, payload in records:
            ids, fact = decode_fact(payload)
            require(len(payload) == (210 if fact.observation else 159) and (ids[0] << 64) | ids[1] == self.identity
                    and fact.id == last + 1 and previous <= fact.time <= self.tip["time_ms"] and
                    revision < fact.revision <= self.tip["revision"], "Canonical sequence, world or time mismatch")
            if self.next_sample is not None and self.next_sample[1] == last:
                self.commit_samples(last, previous, fact.time)
            while self.next_cut is not None and self.next_cut < fact.time:
                self.cut(self.next_cut, last)
                self.next_cut = next(self.timeline, None)
            checksum.update(head)
            checksum.update(payload)
            if fact.id <= self.source.get("initial_cursor", 0):
                prefix.update(head)
                prefix.update(payload)
            offset = len(self.raw) + len(head)
            self.raw.extend(head)
            self.raw.extend(payload)
            self.cached.append((fact.id, fact.time, fact.kind, sql_id(fact.actor) if fact.actor else None,
                                sql_id(fact.related) if fact.related else None, offset))
            if len(self.cached) == BLOCK_RECORDS:
                self.flush()
            self.ant_event(fact)
            self.resources(fact)
            self.geometry_event(fact)
            if fact.kind in COUNTERS:
                self.totals[COUNTERS[fact.kind]] += 1
            milestone = {5: "First food collection", 12: "First food delivered", 21: "First trophallaxis", 23: "First excavation",
                         24: "First soil placement", 48: "First maternal ration", 56: "First recruitment activation"}.get(fact.kind)
            if milestone:
                self.milestone(milestone, fact)
            previous, last, revision = fact.time, fact.id, fact.revision
        self.flush()
        self.commit_samples(last, previous, self.tip["time_ms"])
        require(self.next_sample is None, "Snapshot cursor is beyond the verified history")
        while self.next_cut is not None:
            self.cut(self.next_cut, last)
            self.next_cut = next(self.timeline, None)
        require(last == self.tip["cursor"] and self.external == self.tip["available"] and self.nest == self.tip["stored"] and
                self.edits_seen == len(self.edits) and all(self.stages.get(i) == a["stage"] and self.positions.get(i) == a["position_m"]
                for i, a in self.ants.items()), "Canonical projection does not reproduce the terminal frame")
        value = checksum.hexdigest()
        if self.source.get("initial_prefix") is not None:
            require(prefix.hexdigest() == self.source["initial_prefix"], "Initial checkpoint does not match canonical prefix")
        expected = self.source["facts_expected"]
        require(expected is None or value == expected, "Canonical facts SHA-256 mismatch")
        self.source["hashes"]["facts.bin"] = value
        if self.cohort:
            aid = self.cohort["members"]
            marks = self.cohort
            marks.update(members=[str(a) for a in aid], ever_eclosed=sum(self.db.execute(
                "SELECT 1 FROM changes WHERE ant=? AND stage=3 LIMIT 1", (sql_id(a),)).fetchone() is not None for a in aid),
                never_observed_fed=sum(a not in self.fed for a in aid),
                deaths=dict(Counter(label(DEATHS, row[0]) for a in aid
                                    if (row := self.db.execute("SELECT death FROM ants WHERE id=? AND death_event IS NOT NULL", (sql_id(a),)).fetchone()))))
        return perf_counter() - scan


def write_cache(db_path, first, tip, checkpoints, records, capture):
    with closing(sqlite3.connect(db_path)) as db:
        db.executescript("PRAGMA journal_mode=OFF; PRAGMA synchronous=OFF; PRAGMA cache_size=-16384; PRAGMA temp_store=FILE;" + TABLES)
        builder = IndexBuilder(db, tip, capture, checkpoints)
        scan_s = builder.index(records)
        started = perf_counter()
        db.executescript(INDEXES)
        db.commit()
        index_s = perf_counter() - started
    case = capture["case"]
    settings = dict(checkpoint_schema=tip["schema"], physics=tip["physics"], inner_physics=tip["inner_physics"], seed=str(tip["seed"]),
                    geometry=tip["geometry"], initial_maternal=case.get("parameters"), initial_external_ug=case.get("external_food_components_ug"),
                    ecological=tip["flags"], condition=case.get("condition"), care_enabled=case.get("care_enabled"),
                    initial_workers=case.get("externally_seeded_workers"), program_source="BehaviorChanged only",
                    initial_sources=sorted([dict(position_m=s["position_m"], stock_ug=s["stock_ug"])
                                            for s in first["sources"].values()], key=lambda s: (s["position_m"], s["stock_ug"])))
    surface = tip["surface"]
    if surface:
        blocked = [i for i, b in enumerate(surface["walkable"]) if b == 0]
        surface = {k: v for k, v in surface.items() if k != "walkable"} | {"blocked": blocked}
    return dict(world_id=tip["world"], name=case.get("case"), scenario=case.get("arm"), population=case.get("population"),
                layout=case.get("layout"), supply=case.get("source"), settings=settings, start_ms=0, end_ms=tip["time_ms"],
                first_state_cut_ms=first["time_ms"], facts=tip["cursor"], final_population=builder.population(),
                archive_kind=capture["kind"], receipt_verified=capture["receipt_verified"], member_sha256=capture["hashes"],
                readiness="ENGINEERING_ONLY", biological_status="BIOLOGICAL_BLOCKED", b06="INSUFFICIENT", release="FAIL",
                comparable=capture["comparable"], surface=surface, bounds_m=(tip["world_min_m"], tip["world_max_m"]),
                colonies=list(tip["colonies"].values()), milestones=list(builder.milestones.values()), first_cohort=builder.cohort,
                parameters_text=capture.get("parameters_text"), provenance=capture.get("provenance"),
                surface_entrances_m=[c["position_m"] for c in tip["colonies"].values()
                                     if surface and c["position_m"][1] == surface["origin_m"][1]],
                initial_queens=[str(i) for i, a in first["ants"].items() if a["caste"] == 1 and a["stage"] != 4],
                timings=dict(scan_ms=round(scan_s * 1000, 2), index_ms=round(index_s * 1000, 2), cache_bytes=db_path.stat().st_size))


class Catalog:
    def __init__(self, cache):
        self.root = cache.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.import_lock = Lock()
        self.entries = {}

    def register(self, path, title=None, expected=None, description=None, producer=None):
        path = path.resolve(strict=True)
        require(path.is_file(), "Select a regular ZIP or SQLite file")
        members = fingerprint(path)
        if expected:
            require(members["archive"] == expected, "Published archive SHA-256 mismatch")
        archive = as_key(path, members)
        if archive not in self.entries:
            self.entries[archive] = dict(path=path, title=title or path.stem, description=description, members=members,
                                         verified_source=bool(expected), producer=producer)
        return archive

    def browse(self, archive):
        require(archive in self.entries, "Unknown archive")
        entry = self.entries[archive]
        cache = self.root / archive
        started = perf_counter()
        if (cache / META).is_file():
            return self.cached(cache), True, (perf_counter() - started) * 1000
        with self.import_lock:
            if (cache / META).is_file():
                return self.cached(cache), True, (perf_counter() - started) * 1000
            with TemporaryDirectory(dir=self.root, prefix="build-") as temp:
                work = Path(temp) / "complete"
                work.mkdir()
                with source_inputs(entry["path"], Path(temp), entry["members"]) as inputs:
                    result = []
                    for i, (first, tip, cuts, records, capture) in enumerate(inputs):
                        data = write_cache(work / f"{i}.sqlite", first, tip, cuts, records, capture)
                        title = entry["title"] if i == 0 else f"{entry['title']} · world {i + 1}"
                        data.update(key=f"{archive}.{i}", title=title, description=entry["description"],
                                    archive_sha256=entry["members"]["archive"], source_wal_sha256=entry["members"].get("wal"),
                                    producer=entry["producer"],
                                    integrity="VERIFIED_PUBLISHED" if entry["verified_source"] and data["receipt_verified"] else
                                               "VERIFIED_RECEIPT" if data["receipt_verified"] else "VERIFIED_INTERNAL")
                        result.append(data)
                require(fingerprint(entry["path"]) == entry["members"], "Source changed during import; import a stable backup")
                elapsed = (perf_counter() - started) * 1000
                for data in result:
                    data["timings"]["total_import_ms"] = round(elapsed, 2)
                (work / META).write_bytes(json_bytes(result))
                try:
                    work.rename(cache)
                except OSError:
                    if not (cache / META).is_file():
                        raise
                    return self.cached(cache), True, (perf_counter() - started) * 1000
        return result, False, elapsed

    @staticmethod
    def cached(cache):
        result = json.loads((cache / META).read_bytes())
        require(bool(result) and all((cache / f"{i}.sqlite").is_file() for i in range(len(result))),
                "Browse index is incomplete; use a new cache directory")
        return result

    def data(self, world):
        archive, _, number = world.partition(".")
        require(number.isdecimal(), "Invalid archive world key")
        metadata, _, _ = self.browse(archive)
        index = int(number)
        require(index < len(metadata) and metadata[index]["key"] == world, "Unknown archive world index")
        return metadata[index], read_db(self.root / archive / f"{index}.sqlite")

    def list(self):
        result = []
        for key, entry in self.entries.items():
            cached = self.root / key / META
            result.append(dict(key=key, title=entry["title"], description=entry["description"],
                               preview=entry.get("preview"),
                               worlds=json.loads(cached.read_bytes()) if cached.is_file() else [],
                               archive_sha256=entry["members"]["archive"]))
        return result
