# S0 implementation decisions (2026-11-08)

These reversible engineering decisions refine the v0.8 baseline without adding biology, geometry, persistence services or clients.

## ADR-013: repository language and provenance

All tracked content and commit messages are English; conversation with the user remains Chinese. Translate and consolidate the imported design while preserving confirmed decisions, statuses, equations, test IDs and reference links. Keep the original archive locally under ignored handoff/ and preserve historical Git commits. Rename README_HANDOFF_CN.md to README_HANDOFF.md. Regenerate the handoff manifest for the maintained English files; it no longer claims to match untranslated archive bytes.

## ADR-014: dependencies and Windows build

The runtime and CLI use only the C++ standard library. Tests use a small assertion runner plus CMake scripts, not a downloaded test framework. The CLI JSON reader is bounded and separate from antworld_core.

For this Windows machine, use portable LLVM-MinGW 20261104 (Clang 23.1.5), CMake 3.31.10 and Ninja 1.13.2. tools/bootstrap_windows.ps1 pins official release URLs and SHA-256 digests. Install only into ignored .tools; build_windows.ps1 sets process-local PATH and restores it. Standard CMake builds can use another C++20 toolchain; report untested platforms/compiler families explicitly.

## ADR-015: RNG and hashing

Use SplitMix64 with a single 64-bit state and fixed unsigned arithmetic, labeled splitmix64-v1. Freeze four outputs for each of five seeds (0, 1, 12345, 0x123456789abcdef0 and UINT64_MAX). Vectors were independently evaluated with Python integer arithmetic and masks, then embedded in C++ tests. Reference: https://prng.di.unimi.it/splitmix64.c . This is a small S0 diagnostic stream; later species/subsystem streams require an explicit versioned design. No std::uniform distributions.

State and trace hashes use FNV-1a-64 over canonical little-endian fields, labeled fnv1a64-le-v1. They detect regressions/corruption, not malicious tampering. Trace hashes cover committed diagnostic facts; state hashes additionally cover time, allocators, RNG and pending work. Hashes exclude wall-clock time and filesystem paths.

## ADR-016: authority, identity and revision

WorldRuntime owns all state with no exposed mutable pointer. Snapshots and event queries return detached owning values. Public mutations validate first and edit a private candidate State; publish by swapping only after success. A failed AdvanceTo, including a recursion/record budget error, rolls back the entire call. This intentionally favors simple correctness over throughput; copying state per mutation is not a production scaling strategy.

EntityId, ScheduledId, committed EventId and queue sequence have distinct monotonic allocators starting at 1. Only a successful diagnostic execution assigns a fact EventId. Cancellation does not recycle any ID. UINT64_MAX is a reserved exhausted counter sentinel; attempts to increment it fail, never wrap.

Revision increases for entity-ID allocation, event scheduling, successful cancellation and committed event execution. Merely moving the empty clock does not add a revision. This makes equivalent time advancement partitions produce identical final state. Pending scheduling is authoritative state but is not a fabricated biological fact.

## ADR-017: same-time behavior and limits

Order by full (time, phase, priority, tie, sequence), ascending; sequence is assigned internally. A repeated target with no new due work is a no-op. If new work has been scheduled at now between calls, AdvanceTo(now) drains it. This resolves the broad no-op wording against the current-boundary due-work requirement in document 18.

S0 exposes only Record, DrawRandom and RepeatSameTime diagnostic actions, with numeric payloads and no callbacks into arbitrary code. The last deliberately exercises zero-time failure protection; its descendants retain the same time/phase/priority/tie and receive new identities/sequences. It cannot reenter an earlier phase. Later biological proposal barriers remain S1+ work.

Engineering limits: 1,024 executed events per timestamp per advance; 65,536 queued records and 65,536 retained facts; 16 MiB checkpoint input; 1 MiB scenario input; JSON nesting depth 32. Exceeding limits gives a diagnostic and preserves the prior runtime state. These are S0 test-safety budgets, not biological or full-world performance promises. Boundaries/version migrations must be reviewed before scaling.

## ADR-018: checkpoint v1

Canonical little-endian binary encoding, never raw struct memory. Eight-byte magic: the seven ASCII characters AWCKPT1 and a zero terminator; then uint32 schema=1, physics=1, RNG=1. Then uint64 world high/low, seed, nonnegative int64-range time represented in eight bytes, revision, next entity/scheduled/fact/sequence IDs and RNG state. Follow with uint64 queue count, sorted queue records, uint64 fact count, facts, then a uint64 FNV-1a checksum of preceding bytes.

A queue record is scheduled ID, time, uint32 phase/priority, uint64 tie/sequence, uint8 diagnostic action and uint64 payload. A fact is event ID, world high/low, time, scheduled source, uint8 action, revision, payload and random result. A non-random fact has random result zero. No pointers, ABI layout or padding are serialized.

Decode into temporary state; validate size/checksum/versions, IDs, ranges, phase/actions, unique schedule IDs/sequences, canonical ordering, future timestamps, fact chronology/world/revision and exact input consumption. Restore then swaps the whole state including identity. The format contains complete S0 diagnostic history, not an assertion that high-level future biological events can regenerate a world. SQLite, commands, geometry, entity stores and durable crash recovery are not implemented.

## ADR-019: constrained S0 scenario profile

The P0 schema remains the later-stage superset. S0 validates required/unknown fields at root, world and bounds, JSON types, UUID, fixture label, units, finite increasing bounds and numeric ranges. It explicitly rejects nonempty colonies or food_sources because those need S1+. Seed and time use decimal integer tokens, bounded by uint64 and nonnegative int64 respectively; fractional/exponent spelling for these fields is rejected to avoid silently losing integer precision. This is a documented stricter S0 profile, not a silent schema rewrite.

scenario_name, model_version and bounds are validated metadata; they do not create geometry or alter S0 physics. The running core reports its own fixed schema/physics versions. Unicode JSON strings are validated; duplicate keys, malformed encodings and trailing data fail. Optional --diagnostic-events creates an explicitly diagnostic RNG-event sequence at milliseconds 1..N, outside the biological scenario schema. JSON stdout/file results are deterministic; the requested output path is printed separately on stderr. Input scenarios cannot be overwritten through the output option.

## Next gate

S0 technical completion permits review, not automatic S1. S1 must introduce actual entities, proposals, resource arbitration and fairness tests, and decide how diagnostic-only actions remain isolated from production behavior.
