# Live durable history architecture

The C++ Simulation Core retains authority over ecological mutations and committed facts. The application links `antworld_storage` and owns the SQLite file. The Core sees an immutable `EventPrefix` interface and has no SQLite, compression, file, network or background-thread dependency. Existing checkpoints keep their wire format. Published v2 cuts split the same continuation and the same ordered history.

## Ownership and publication

| Phase | Owner | Authority and failure outcome |
|---|---|---|
| Simulate | Application simulation thread | Transactions append committed facts. If a transaction reaches the hot-tail ceiling, the existing undo journal rolls the whole transaction back. Earlier committed facts remain available for capture. |
| Capture and enqueue | Simulation thread via `LiveHistoryWriter::try_submit` | Seal the current hot vector into immutable shared storage by moving its allocation. Serialize the continuation and snapshot actual gauges, geometry and identity data at the same cut. Later work may advance on the same runtime while the worker publishes this cut. |
| Encode and stage | Background thread with its own SQLite connection | Check the expected predecessor, verify any unrecognized prefix, seal blocks in order, and stage authoritative facts and associated state and observation rows. Readers on other connections see the previous commit. |
| Publish | Background thread, one local SQLite WAL transaction | `synchronous=FULL` makes the transaction durable at COMMIT, including block rows, anchors, checkpoint, observations and manifest. The manifest is published atomically with the blocks it names. An uncertain commit requires reopening and validating before retry. |
| Acknowledge | Simulation thread via `finish` | Open a verified read-only source for the published prefix, then retire exactly the captured hot chunks. Facts committed after capture stay hot. An exception before acknowledgement leaves the runtime's facts available. |

Use a single simulation writer for a runtime. Keep that runtime and its open archive available while a save is outstanding. Check `ready()` before `finish()` when avoiding an application wait. Writer destruction drains its outstanding task. `antworld_archive` uses v2 for new worlds, binds the hot-tail policy before advance, and waits for durability before its command returns. The v1 API and version detection stay available. Callers managing a v2 world over time use the live writer. The synchronous `Store::save` compatibility call alone publishes without retiring the owner's hot history. Explicit full checkpoint exports, full event-vector reads and the legacy-style synchronous durable command wrapper can allocate historical data.

The frozen live admission permits one in-flight capture, up to 600,000 unpublished facts and 256 MiB captured allocated data. While the queue is occupied, `try_submit` returns false. A capture exceeding the byte budget throws before admission. The caller can publish earlier cuts, finish an in-flight save, or report backpressure. A single indivisible simulation transaction larger than the configured hot allowance needs a suitable host budget. The owner cache holds one page of at most 4,096 decoded facts and durable storage holds the retired prefix. The foreground still serializes actual continuation state and copies current state metadata. Live footprint therefore also depends on queue, entities, geometry, active tasks, runtime budget and the underlying OS.

`Store` compares complete expected tokens. When acknowledgement was lost, a byte-identical retry may name the published tip or the original predecessor and receive the same generation. A conflicting continuation, stale predecessor or divergent canonical prefix fails. Independently reopened writers are serialized by SQLite and still require the same token check.

## Manifest, recovery and queries

`worlds` names the published tip. `generations` stores compact continuation frames. `history_anchors` binds each frame to its parent and fact prefix. `fact_blocks` is the immutable event authority. v2 retains all published frames, including cuts where time or scheduled work changes with no new fact. Each frame uses the existing Core continuation serializer, including event queue, RNG, all ID counters, revision, geometry edits, positions, resources, custody, clocks and reservations. The prefix supplies the facts the original Core validators need.

`Store::load` verifies the published anchor chain and the target fact prefix before restoring the continuation. `Store::recover(base, target)` restores the historical cut, verifies the contiguous blocks after its cursor and restores the target's authoritative continuation. This preserves pending work and randomness that observational facts cannot reconstruct by themselves. Recovery is available at published cuts, including the retained cuts of a verified migration. Intermediate states without a published frame and already-pruned v1 generations have no reconstructable continuation.

By-ID and by-time indexes locate candidate blocks. The query decodes facts and identifies participants, outcome and payload from canonical fields. Geometry edit references are indexed from authoritative geometric edits. Hour, day and arbitrary flow queries combine exact minute summaries with decoded boundary facts. Individual and derived index reconstruction uses the published journal, geometry and the retained, real checkpoint gauge observations. A new index can be rebuilt without fabricating a past gauge or rewriting fact blocks. Validation reads historical facts in bounded pages. Total validation time and some verification structures still scale with history. Exact sparse participant history can scan many candidate blocks and remains a long-scale measurement obligation.

## Limits

The deployment contract is one local SQLite database on a filesystem that honors SQLite's synchronization semantics, with the associated WAL files when in use. Physical power-loss behavior depends on the filesystem and hardware. The block and anchor hashes detect damage and cross-chain mismatch. They have no external signature or replication trust root. A missing or damaged required block or anchor causes an explicit load failure.

The standard headless archive fixture permits two million committed facts per world, with a separate compact frame limit. Embedders choose finite host limits explicitly. The measured qualification reaches one million facts. Continuous operation beyond the studied scales needs further checkpoint cadence, historical archive tiers, cold-query and bounded validation measurements. v2 retains all compact frames and canonical blocks as disk use grows.

[Frozen protocol](../../docs/64_S6_3_4_Frozen_Durable_History_Protocol.md) · [Live writer](../../cpp/storage/live_history.cpp) · [Store](../../cpp/storage/segmented_store.cpp) · [Canonical format](CANONICAL_EVENT_BLOCK_SPEC.md)
