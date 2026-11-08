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
} // namespace antworld::storage::detail
