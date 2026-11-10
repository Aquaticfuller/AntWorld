# Recovery and migration validation

## Process and I/O controls

| Injection or interrupted operation | Required authoritative outcome | Automated evidence |
|---|---|---|
| Exit before staging fact blocks | Previous cut | `S6_3_4_CRASH`, hook `BeforeBlocks`, exit 77 |
| Exit after staging fact blocks | Previous cut | `S6_3_4_CRASH`, hook `AfterBlocks` |
| Exit before or after staging the manifest and checkpoint | Previous cut | `S6_3_4_CRASH`, hooks `BeforeManifest`, `AfterManifest` and `BeforeCommit` |
| Exit immediately after successful durable COMMIT | Entire new cut | `S6_3_4_CRASH`, hook `AfterCommit` |
| Exit inside the SQLite WAL VFS write path | Previous cut | `S6_3_4_WAL_CRASH`, partial physical write and exit 78 |
| SQLite VFS `xWrite` and `xSync` errors | Entire old or entire new cut according to the verified COMMIT outcome. A returned success requires the new cut | `S6_3_4_IO_FAILURE`, sequential fault positions until an unfailed publication |
| Inject exception after staging manifest in the background writer | Keep the previous published cut and every in-memory fact for retry | `S6_3_4_LIVE` |
| Repeat an identical publication after losing its acknowledgement | Return the same generation with no duplicated blocks or facts | `S6_3_4_LIVE` |
| Damage, drop, reorder or replace a block, parent anchor or manifest mirror | Explicit validation failure on read and index rebuild | `S6_3_4_CODEC`, `S6_3_4_CORRUPT` |

The VFS sweep and process crashes open a fresh connection. They compare exported Core bytes, including canonical facts. The staged-visibility control deliberately blocks the worker after inserting blocks and advances the owner by two facts. A concurrent reader observes the prior manifest, the single save slot refuses another request, and acknowledgement leaves precisely those two later facts unpublished. A queue byte-limit failure and an overfull transaction keep the pre-existing state and history intact.

The final Windows Release sweep reached 67 injected write positions and two injected sync positions before a clean publication. The first-build sweep reached 65 write positions and two sync positions. Damage controls covered the encoded envelope, missing first block, substituted block, mismatched index digest, broken anchor parent, missing anchor and altered manifest quantum. All seven rejected both load and index rebuild. [Raw process, I/O and corruption output](../../experiments/s6_3_4/portable/verification/fault-and-recovery.log)

## Recovery of ecological state

- `S6_3_4_custody` uses the R1 diagonal and turning carriers with held brood. It compares compact and complete states through SQLite, then finishes the interrupted physical placements. The finite grip and true clearance constraints are inherited.
- `S6_3_4_connectivity` persists a loaded worker with a filled passage and pending work, recovers the blocked continuation, and verifies the same worker delivers after excavation restores its remembered physical route. Original barriers, resource and soil accounting stay authoritative.
- `S6_3_4_MIGRATION` includes a carried soil parcel and two queued events. It verifies all retained legacy frames, captures a real command receipt, validates the new frame and event stream, then resumes both timelines. It also verifies earlier frames of a v1 file that has already pruned an older generation, and rejects an existing destination.
- The migrated query comparison includes filtered actor and related-entity history, all gauge and flow families for world and colony, minute bucket samples/sum/minimum/maximum/last, event range and identities. It exercises index rebuilding and checks the exported checkpoint against the same pinned v1 snapshot used for backup.
- The 21-day and 180-day comparisons in the main report restore and advance the same live identities through real day boundaries. The online state frame, ordered canonical event records, fact counts, state/trace hashes and physical ledgers agree with the uninterrupted reference. Python independently reads the archive and verifies all committed block and anchor bytes.

## Using a legacy archive

`antworld_archive inspect` detects the file format. `antworld_archive migrate LEGACY_DATABASE NEW_SHADOW_DATABASE` uses SQLite backup under a pinned read transaction. Supply a fresh path on a local filesystem. The command validates each retained v1 cut, writes and validates v2 in the shadow, compares exported Core bytes and checkpoints its WAL. A failed or interrupted migration leaves the original source available. Choose the new file only after the command and integrity check succeed. The v1 database and the converted v2 database have different storage hashes by design. Canonical facts, generation numbers, cursor, time and replayable state agree.

The historical pressure file itself was migrated. Its main file is 1,072,361,472 B and its historical reported archive size included sidecars. The 5,169,152 B shadow main file contains 122 blocks for all 498,598 original facts. The SHA-256 of the original and recovered length-prefixed stream is `edcaad96310fb2d398ead023731838ab5ba9020ad5ce2c277f22ce4bbf54655a`. The first process returned successful migration, then the outer audit treated a newly created empty WAL as a durable change. The corrected audit compares the main file and any nonempty WAL. The main file SHA-256 is identical before and after. The final migration took 42.265 s during the correctness run. The initial audit and corrected receipts both remain available. [Initial migration evidence](../../experiments/s6_3_4/migration) · [Final verified shadow](../../experiments/s6_3_4/portable/migration/migration.json)

An unpublished runtime may have legitimately committed facts newer than the last durable cut. Its owner retains them after save failure. Following a process crash, recovery uses the newest complete durable publication, or an explicitly requested older anchor. Authoritative continuations exist at published cuts. A later frame and its bound fact suffix preserve pending state that cannot be derived from observational facts alone.

```sh
ctest --test-dir build/release -V -L '^S6[.]3[.]4$'
antworld_archive migrate old.sqlite new-shadow.sqlite
python tools/verify_s6_3_4_archive.py new-shadow.sqlite new-shadow-integrity.json --legacy old.sqlite
```

[Fault logs and test results](../../experiments/s6_3_4/portable/verification) · [Block and anchor specification](CANONICAL_EVENT_BLOCK_SPEC.md)
