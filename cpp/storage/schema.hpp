#pragma once
namespace antworld::storage::detail {
inline constexpr const char *schema = R"SQL(
CREATE TABLE worlds(world TEXT PRIMARY KEY, seed TEXT NOT NULL, generation TEXT NOT NULL,
 revision TEXT NOT NULL, time_ms INTEGER NOT NULL, cursor TEXT NOT NULL, checkpoint_hash TEXT NOT NULL,
 prefix_hash TEXT NOT NULL, quantum_m REAL NOT NULL);
CREATE TABLE generations(world TEXT NOT NULL REFERENCES worlds(world), generation TEXT NOT NULL,
 revision TEXT NOT NULL, time_ms INTEGER NOT NULL, cursor TEXT NOT NULL, checkpoint_hash TEXT NOT NULL,
 checkpoint BLOB NOT NULL, PRIMARY KEY(world,generation));
CREATE TABLE events(world TEXT NOT NULL REFERENCES worlds(world), id TEXT NOT NULL, time_ms INTEGER NOT NULL,
 kind INTEGER NOT NULL, actor TEXT NOT NULL, related TEXT NOT NULL, colony TEXT NOT NULL, resource TEXT NOT NULL,
 source TEXT NOT NULL, revision TEXT NOT NULL, geometry_edit TEXT NOT NULL, parcel TEXT NOT NULL,
 payload BLOB NOT NULL, PRIMARY KEY(world,id));
CREATE INDEX events_time ON events(world,time_ms,id);
CREATE INDEX events_actor ON events(world,actor,id);
CREATE INDEX events_related ON events(world,related,id);
CREATE INDEX events_kind ON events(world,kind,id);
CREATE TABLE participants(world TEXT NOT NULL REFERENCES worlds(world), individual TEXT NOT NULL,
 event TEXT NOT NULL, PRIMARY KEY(world,individual,event));
CREATE TABLE individuals(world TEXT NOT NULL REFERENCES worlds(world), id TEXT NOT NULL, colony TEXT NOT NULL,
 caste INTEGER NOT NULL, seed_stage INTEGER NOT NULL, stage INTEGER NOT NULL, created_ms INTEGER NOT NULL,
 created_event TEXT NOT NULL, last_event TEXT NOT NULL, death_event TEXT NOT NULL, death_ms INTEGER NOT NULL,
 death_cause TEXT NOT NULL, PRIMARY KEY(world,id));
CREATE TABLE receipts(world TEXT NOT NULL REFERENCES worlds(world), command TEXT NOT NULL,
 event TEXT NOT NULL, resource TEXT NOT NULL, PRIMARY KEY(world,command), UNIQUE(world,event));
CREATE TABLE samples(world TEXT NOT NULL REFERENCES worlds(world), generation TEXT NOT NULL, owner TEXT NOT NULL,
 metric INTEGER NOT NULL, time_ms INTEGER NOT NULL, revision TEXT NOT NULL, cursor TEXT NOT NULL,
 value TEXT NOT NULL, definition INTEGER NOT NULL, PRIMARY KEY(world,generation,owner,metric));
CREATE INDEX sample_query ON samples(world,owner,metric,time_ms,generation);
CREATE TABLE observations(world TEXT NOT NULL REFERENCES worlds(world), generation TEXT NOT NULL,
 time_ms INTEGER NOT NULL, revision TEXT NOT NULL, cursor TEXT NOT NULL, quantum_m REAL NOT NULL,
 digest TEXT NOT NULL, PRIMARY KEY(world,generation));
CREATE TABLE flows(world TEXT NOT NULL REFERENCES worlds(world), owner TEXT NOT NULL, metric INTEGER NOT NULL,
 time_ms INTEGER NOT NULL, event TEXT NOT NULL, value TEXT NOT NULL, PRIMARY KEY(world,owner,metric,event));
CREATE INDEX flow_query ON flows(world,owner,metric,time_ms,event);
CREATE INDEX flow_evidence ON flows(world,event,owner,metric);
CREATE TABLE buckets(world TEXT NOT NULL REFERENCES worlds(world), owner TEXT NOT NULL, metric INTEGER NOT NULL,
 start_ms INTEGER NOT NULL, count TEXT NOT NULL, total TEXT NOT NULL, minimum TEXT NOT NULL, maximum TEXT NOT NULL,
 last TEXT NOT NULL, first_event TEXT NOT NULL, last_event TEXT NOT NULL,
 PRIMARY KEY(world,owner,metric,start_ms));
PRAGMA application_id=1096234835;
PRAGMA user_version=1;
)SQL";

// Installed before any v2 publication. A migration temporarily keeps the v1
// tables in its separate shadow file until the canonical conversion verifies.
inline constexpr const char *segmented_tables = R"SQL(
CREATE TABLE fact_blocks(world TEXT NOT NULL REFERENCES worlds(world) DEFERRABLE INITIALLY DEFERRED,
 first_id TEXT NOT NULL, last_id TEXT NOT NULL, begin_ms INTEGER NOT NULL, end_ms INTEGER NOT NULL,
 raw_bytes INTEGER NOT NULL, digest BLOB NOT NULL CHECK(length(digest)=32), envelope BLOB NOT NULL,
 PRIMARY KEY(world,last_id), UNIQUE(world,first_id)) WITHOUT ROWID;
CREATE INDEX fact_blocks_time ON fact_blocks(world,end_ms,last_id);
CREATE TABLE history_anchors(world TEXT NOT NULL, generation TEXT NOT NULL,
 parent BLOB NOT NULL CHECK(length(parent)=32), tail BLOB NOT NULL CHECK(length(tail)=32),
 digest BLOB NOT NULL CHECK(length(digest)=32),
 PRIMARY KEY(world,generation), FOREIGN KEY(world,generation) REFERENCES generations(world,generation)) WITHOUT ROWID;
CREATE TABLE geometry_evidence(world TEXT NOT NULL REFERENCES worlds(world), event TEXT NOT NULL,
 edit TEXT NOT NULL, volume TEXT NOT NULL, dry TEXT NOT NULL, water TEXT NOT NULL,
 PRIMARY KEY(world,event)) WITHOUT ROWID;
ALTER TABLE individuals ADD COLUMN seeded INTEGER NOT NULL DEFAULT 1 CHECK(seeded IN (0,1));
)SQL";
inline constexpr const char *finalize_segmented_schema = R"SQL(
DROP TABLE participants;
DROP TABLE events;
DROP TABLE flows;
PRAGMA user_version=2;
)SQL";
} // namespace antworld::storage::detail
