# S1 implementation decisions and review response

Status: implemented for S1 review. The user explicitly authorized S1 after conditional S0 acceptance. Design baseline remains v0.8; this document refines the implemented subset of documents 17, 18, 19 and 22. S2 is not authorized.

S2 note: this document preserves the reviewed S1 baseline. Document 27 extends local motion, physical nest storage, autonomous scheduling and map journals, and supersedes checkpoint v2 with v3. S1's rollback, ordering, arbitration and conservation mechanisms remain.

## ADR-S1-01: bounded undo journal instead of copying State

The single calling thread owns WorldRuntime. Each public mutation creates one private RAII transaction. AdvanceTo holds one transaction for the whole call, including all intermediate timestamps. State is noncopyable at compile time.

The transaction retains a small metadata before-image (clock, counters, RNG, execution watermark, living count and material ledger), original append-only store/journal lengths, before-images for each touched ant/food row, and queue undo records. Removed map nodes remain owned by the transaction. Inserted queue nodes are fully allocated before insertion; undo entries are allocated before the corresponding mutation. Rollback restores rows in reverse order, truncates appended rows/facts, reverses queue edits using retained nodes, and restores metadata. Rollback does not allocate. Allocation failure or any invariant/counter/budget exception therefore restores the complete pre-call authoritative state. Retained vector capacity is nonauthoritative and may grow after a failed attempt.

MSVC Debug allocates iterator proxies even for empty vectors, while its default vector constructor is noexcept. Core vectors therefore explicitly use the potentially throwing zero-count constructor, including transaction scratch buffers and decoding state. This lets injected proxy-allocation failures unwind instead of terminating. Iterator debugging remains enabled. See the [Microsoft STL implementation](https://github.com/microsoft/STL/blob/main/stl/inc/vector). The failure test installs a terminating diagnostic handler so an unexpected noexcept failure exits with its scenario/allocation point instead of hanging on a CRT dialog.

Ants use grouped SoA columns for identity, lifecycle, position and inventory, with stable-ID-to-row maps. Small colony/food records use dense vectors plus ID maps; splitting those records further has no measured benefit in this batch. Dead rows remain present. Queue cancellation uses a separate ScheduledId index, eliminating the S0 linear scan. That index is reconstructed on load and is not separately authoritative.

Costs: schedule/cancel are O(log Q), an entity lookup is O(log N), and transaction memory is O(touched rows + queue changes + appended facts). A batch with A proposals sorts O(A log A); it never copies unrelated entities or the old journal. Store growth has amortized allocation cost. A very long AdvanceTo can still retain substantial undo data; splitting observation targets bounds this memory without changing a prequeued trajectory. Checkpoint encoding/decoding and audit snapshot hashing remain O(world + history), intentionally outside the mutation hot path. summary() and events_after(cursor, limit) avoid whole-history reads.

## ADR-S1-02: persisted execution boundary

The current timestamp retains its last executed full EventKey and count across AdvanceTo calls and checkpoints. A new event at now must sort strictly after that key, including phase, priority and tie. Future timestamps start a new boundary; idle advancement beyond the last event clears the current boundary. Repeated AdvanceTo(now) with no work remains a no-op.

All phase-4 actions at a timestamp form one arbitration group. Diagnostic phase-4 events retain their diagnostic ordering; action facts are appended only after the group is gathered. Completing an action group seals phases 0-4 with the phase-5 minimum key. Already queued commit/publish/reschedule diagnostics then execute normally. New same-time contenders and earlier lifecycle events are rejected rather than reopening the group. Later same-phase diagnostic work is allowed only after the full key and within the cumulative timestamp budget.

The S0 CORE_EDGE_CASES assertion that added priority zero after priority nine intentionally changes: it now checks rejection and then schedules a legal later key. All original T00-T13 cases remain present. These rules also prevent resetting the runaway-event guard through repeated calls or reloads.

## ADR-S1-03: engineering entities and identity

ColonyId, ResourceId and EntityId draw from one monotonic world-local allocator, with typed references including WorldId at public boundaries. Aborted, unobservable allocations roll back; committed/reserved IDs never get reused. Internal references omit the redundant world field because all rows belong to the checkpoint's single WorldId. External queries reject foreign-world references. Detached query results cannot mutate the world.

Seeds are permitted only at time zero before any event executes. ColonySeeded, AntSeeded and FoodSeeded facts record actual creation, with source scheduled ID zero. This is fixture construction, not a player/GM placement API. Colony species is explicitly LasiusNigerEngineeringFixture. No rate, capacity, speed or dimension is a calibrated species constant. AntSeed/WorldConfig numeric defaults and every automated scenario are ENGINEERING_FIXTURE.

Lifecycle fixture events execute in phase 1. Ordered Egg -> Larva -> Pupa -> Adult retains the same ID and birth time. Any living stage may become Dead; subsequent deaths produce an AlreadyDead rejection, never another death fact. No spontaneous development or mortality is implemented. Death preserves carried material in the retained ant inventory; decomposition, dropping and corpse interactions are deferred. Living population is a cached aggregate maintained only by committed lifecycle changes and verified against rows/facts on restore.

## ADR-S1-04: minimal move and collect transactions

Submission returns a pending ScheduledId, with no success fact or material change. The proposal records issued_at and the actor's observed position revision. Resolution revalidates actor life, supported stage/caste, position version, spatial bounds/contact and resource/capacity. Rejected execution emits an ActionRejected outcome fact, not a successful ecological action. Invalid submission throws before commit and consumes no IDs.

Only adult workers execute S1 actions. One actor can execute at most one action per timestamp; its earliest submitted proposal wins that local choice, and others receive DuplicateAction. This is a reversible engineering restriction, not behavior selection.

Move uses an event-based straight segment in a convex, obstacle-free fixture AABB. Its endpoint must be in bounds; distance divided by elapsed proposal time must not exceed the configured speed. The committed position changes at arrival; no interpolation or intermediate collision is modeled. A prior committed movement invalidates older queued proposals via position_revision. This establishes a duration/speed/boundary-validated move, not S2 navigation, near-field collision, autonomous planning or pathfinding. Coordinates are meters, X east/Y up/Z north.

CollectFood requires contact distance and transfers at most min(request, source stock, free carrying capacity). Partial transfer is explicit. Food has carbohydrate, protein, water and other components, each integer micrograms; total is derived, not a fifth mutable balance. Food carried by ants is material inventory, not body energy, a crop model, or a second colony pool.

The implementation uses checked uint64 nonnegative stocks, rather than the draft's usual int64 ledger choice. World total must also fit uint64. There are no signed physiological flows in S1. Addition, subtraction and aggregate totals check overflow/underflow. Transfers apportion components by exact largest remainders, with carbohydrate/protein/water/other as the remainder tie order. A portable integer multiply/divide routine avoids floating-point conservation and compiler-specific 128-bit types. Tests include UINT64_MAX material and small remainder ties.

For each resource, contenders sort by a stateless SplitMix64-v1 rank from (seed, SimTime, ResourceId, EntityId), then EntityId and sequence for exact collisions/duplicate actions. Specifically: a=SplitMix64(seed XOR time).next(); b=SplitMix64(a XOR resource).next(); rank=SplitMix64(b XOR actor).next(). Resources sort by ResourceId. Actor rank is independent of enqueue order and does not consume the diagnostic world RNG. Across seeds/timestamps the low ID has no fixed priority. Determinism is tested with identical inputs; fairness is checked across 256 seeds and 256 timestamp fixtures, not inferred from one winner. This is a versioned engineering tie-break, not biological dominance or a statistical calibration.

## ADR-S1-05: checkpoint v2 and host budgets

Schema and physics versions are both 2; RNG version remains 1. The v2 magic is AWCKPT2 followed by zero. S0 v1 saves are explicitly rejected, not silently reinterpreted; no migration is supplied in S1. Historical S0 artifacts/results remain unchanged.

Encoding is canonical little-endian unsigned integers, nonnegative int64 milliseconds encoded as 8 bytes, and IEEE-754 binary64 bit patterns for positions/configuration. The complete body is followed by an 8-byte FNV-1a checksum. This detects accidental corruption, not malicious forgery or authenticity. Cross-platform floating-point bit-identical trajectories are not promised.

Field order:

1. Magic (8); schema/physics/RNG versions (4 each); world high/low, seed, now, revision, next entity/scheduled/event/sequence IDs, RNG state (8 each).
2. Queue count (8); sorted scheduled records (115 bytes each): ID, EventKey (time8, phase4, priority4, tie8, sequence8), diagnostic action1/payload8, kind1, actor8, resource8, destination24, request8, issued_at8, observed position revision8, stage1.
3. Fact count (8); committed records (148 bytes each): ID/world/time/source, diagnostic action1, revision/payload/random value, kind1, actor/colony/resource, position24, transfer32, stage1, outcome1. Unmarked scalar integers here are 8 bytes.
4. World configuration (min/max positions, speed and contact distance: 64 bytes); watermark-present byte and optional EventKey; cumulative timestamp count and living count; introduced/available/carried ingredient ledgers (32 bytes each).
5. Colony count and records (17 bytes: ID8, species1, founding time8); ant count and records (98 bytes: ID8, colony8, birth8, stage1, caste1, position24, position revision8, capacity8, cargo32); food count and records (96 bytes: ID8, position24, initial32, remaining32).
6. Checksum8. Runtime host limits and derived ID indexes are not serialized.

Decode builds and validates a replacement before swapping it into the live owner. Checks include versions, bounds/finite numbers, count/byte budgets, global ID uniqueness, cross-store relationships, queue order/cursor/phase, event ID/source uniqueness and chronology, material and population balances, retained stage/position/inventory against committed facts, and absence of trailing bytes. The history check covers the minimal S1 facts; it is not a general event-sourcing claim or the S5 persistence layer.

RuntimeLimits provides host policies for live entity count, pending events, committed events, events per timestamp, and checkpoint bytes. Defaults (65,536 entities/events, 1,024 events per timestamp, 16 MiB checkpoint) are temporary operational bounds, NOT biological limits or fixed schema maxima. Callers can raise limits explicitly; the receiving runtime decides load budgets. Tests save/restore 150,000 pending records exceeding 16 MiB with raised budgets and reject them atomically under defaults. Journals remain in memory; pruning, streaming, SQLite and long-world retention are S5 work.

## Verification and stage gate

S1_ENTITIES, MOVEMENT, COMPETITION, FAILURES, FAIRNESS, LIFECYCLE, PHASES, ROLLBACK, PERSISTENCE, ARITHMETIC, BUDGETS and ALLOCATION_FAILURE cover the implemented SCH-03/06/07/08 mechanisms, plus S0 review regressions. The allocation test injects failure at every allocation point until success for creation, SoA growth, enqueue, cancellation, action submission, multi-event advance and restore. It compares canonical pre/post checkpoints after each failed operation.

GitHub Actions runs Linux/Windows Debug and Release, plus Linux Clang ASan/UBSan. External action code is pinned to a commit, workflow permissions are read-only, and the C++ build has no downloaded third-party dependencies. Hosted compiler/image revisions may change; job logs identify the actual compiler. Windows local portable tools remain release/hash pinned. Actual local/remote results and performance measurements belong in S1_RESULTS.md, not in this normative decision record.

Stop after S1 review delivery. S2 sensing/exploration/trails, S3 physiology, S4 geometry, S5 durable persistence, Unity and GM integrations remain unimplemented and unauthorized in this batch.
