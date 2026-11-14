# OP0 observation data contract v1

The terminal calls the same dispatcher used for HTTP. The server binds to IPv4 loopback and serves bundled assets and GET endpoints. The JSON envelope contains `schema: "antworld.observation.v1"` and either `data` or `error`. Events are anchored to the original WorldId. Every world URL also carries an archive-specific key, including when two source files reuse a WorldId.

English and Simplified Chinese are presentation preferences. The local message catalogue is shared by both viewers. API fields, event names, checkpoint versions, IDs, hashes and numeric values use the same schema for both languages.

| Endpoint under /api/v1 | Inputs and output |
| --- | --- |
| `catalog` | Registered archives, source SHA-256 and verified worlds if their cache is ready |
| `archive/{archive}` | Validate or open an archive. Lists each world in a multi-world SQLite backup |
| `world/{world}/meta` | Initial geometry, case inputs, source hashes, version IDs, final population and milestones |
| `world/{world}/state` | `time_ms` or exact `event`, population, coordinates, resources, cumulative facts and last queen sample |
| `world/{world}/event` | Exact `id`, including referenced recruitment facts and parcel edits when recorded |
| `world/{world}/adjacent` | `event` or `time_ms`, `direction` (next/previous), `mode` (outcomes/movement), optional `ant`. Returns one matching fact or null. Equal timestamps retain distinct EventIds |
| `world/{world}/activity` | `day`, zero-indexed. Returns 24 hourly bins and total committed records, moves, collections, deliveries and observation facts for the archived part of that day |
| `world/{world}/motion` | `event` or `time_ms`. Recent committed movement points, with `window_ms` (up to one hour) and `limit` (up to 200), in commit order. A truncation flag identifies omitted earlier points in the requested window |
| `world/{world}/events` | `after`, `since_ms`, `until_ms`, `group`, `ant`, `cut_event` and `limit` (1–200). Returns `next_after` when more records match |
| `world/{world}/ant` | `id`, `time_ms` or `event`. Identity, stage, death if recorded by the cut, lifetime milestones and recent committed facts |
| `world/{world}/path` | `id`, `time_ms` or `event`, `limit` (1–200). Returns bounded lists of actual position facts |
| `world/{world}/series` | Population and resource series at daily or comparable bounded cuts. Recorded queen physiology is separate |
| `world/{world}/geometry` | `time_ms` or `event`, `axis` (x/y/z), `layer_q`, optional `window=u0,v0,u1,v1` and `clearance=1` |
| `world/{world}/cohort` | `time_ms` or `event`. First recorded living larval census and its outcomes through the cursor. Requires daily individual data |
| `compare` | `left`, `right` and `time_ms`. Compares aggregate evidence and effective input fields |

Time is integer simulation milliseconds. A clock query includes all facts committed at or before that time. An event query stops at its exact EventId, including when later facts share its timestamp. Results use canonical EventId order. IDs are decimal strings at the browser interface. Coordinates are meters, X east, Y up and Z north. The UI shows positions in millimeters and removed volume in mm³. Nutrient arrays are in µg in carbohydrate, protein, water, other order. Body energy is in nJ. Program labels come from `BehaviorChanged`. Foraging decision modes, physical actions and encounters are separate records.

- `COMMITTED_FACT` is a byte-decoded event. Source, actors, participants, result and quantities come from that event. Recruitment references lead to a preceding committed cue or scout delivery.
- `RECONSTRUCTED` denotes a deterministic projection, such as a position through the selected cursor or geometry from the initial solid and ordered edits. Space shows soil, void and rock. Clearance tests the static unloaded body cube. It does not imply a navigable route.
- The map groups coincident projected positions at the current zoom without moving or merging source individuals. The group can be opened to inspect its individual IDs, stages and states.
- `CUT_SNAPSHOT` is a published physiology sample with its own time and cursor. The newest available sample can precede the requested time by hours or days. Positions and physiology are never interpolated.
- `Not recorded` appears for absent fields and histories. Recorded zeroes stay zero. A first-census feeding record requires a positive transferred mass and does not establish subsequent absorption.

### Import and integrity

Published ZIP witnesses include `initial.chk`, `final.frame`, length-prefixed canonical `facts.bin` and a receipt. OP0 checks the repository manifest's outer SHA-256 for demos, every attested member's SHA-256, native frame checksums, event order and identity, initial prefix and terminal individuals, food stocks and geometry. Daily cuts cross-check life stage, position, stock and geometry at their EventId. The browser lists member hashes. User archives without a receipt are checked for local consistency. A supplied receipt establishes member agreement and does not verify authorship.

SQLite v1 uses the committed event journal and legacy generations. v2 uses durable blocks and frames. OP0 uses a private copy, SQLite integrity and reference checks, and a read-only transaction. v1 checks the manifest and its canonical prefix. v2 verifies block SHA-256, lengths, time, order and parent, and then the generation anchor chain and placements. Each is a browse projection. It cannot certify a store for resumed simulation.

The derived SQLite index uses the cache format, source path and input hashes as its identity, including WAL where applicable. It stores query metadata and compressed, bounded blocks of the original canonical bytes. A restart re-fingerprints registered sources. Cache removal after closing OP0 causes reindexing. Keep the original archive for later launches. Recreate the index in a new directory if it is damaged or externally modified.

### Limits

- OP0 replays archives with no live advancement or command API. Supported checkpoint families start at schema 8 and extend through 22. Local tests cover legacy physics 9, physics 24–26 and SQLite v1/v2. Unknown encodings fail explicitly.
- Event pages are bounded and share a 12-block cache. Validation streams facts. It loads native frames and sampled cuts during indexing, with a 768 MiB frame limit, 8 GiB member limit and 64 MiB limit per sample CSV. Temporary disk space is needed for a SQLite copy and its index.
- Space is a set of axis-aligned slices of the quantized 3D material. OP0 does not reconstruct unknown trajectories, free-form chambers or an animated mesh. Large slices crop to the first 480 quanta along each displayed axis. The API can request a smaller window elsewhere. Roof openings show actual void at the top material. Surface-only nest markers use recorded Core locations.
- Cross-world identities remain separate. Similar settings do not establish equality of all input fields. Physical and physiological observations describe a particular simulated world.
