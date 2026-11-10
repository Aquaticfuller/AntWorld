# Development stages and exit gates (v0.8)

Authorize one stage at a time. Each stage delivers implementation, runnable tests, exact commands, documentation updates and evidence. Passing a technical gate does not silently authorize the next stage. Long-term requirements are not concurrent P0 scope.

## S0: core infrastructure

C++20/CMake/CTest; independent antworld_core and antworld_headless. Strong IDs, clock/revision, versioned reproducible RNG vectors, deterministic future-event ordering, empty world, AdvanceTo, detached read-only snapshots, diagnostic committed events and JSON output. In-memory checkpoint restores time, allocators, RNG, queues, sequence and revision. Cover T00-T13 and applicable SCH-01/02/12/19/20/22; same seed/input yields the same trace hash.

No ant behavior, Unity, SDF, SQLite or Agent. The C ABI header remains a later draft; no DLL export is required. Stop for review after S0.

## S1: entities and action transactions

Minimal ant/colony/resource SoA, continuous identity/life stages, queries, Move/CollectFood proposals. Same-time arbitration, explicit outcomes, conserved ledgers and fair deterministic ties. Gate: SCH-03/06/07/08, query invariance and initial material accounting.

## S2: sensing, exploration and trails

Local reachable map/navigation; explore, discover, collect and return; sparse surface pheromone and limited memory. Multi-seed feature-on/off comparisons; no global food oracle. Gate: F1/F2/F3 with traceable facts and meaningful aggregate differences, without promising optimal paths.

## S3: physiology, nutrition, trophallaxis and brood

Energy/hydration integration, crop separated from body energy, conserved actual transfers, development progress and events. Gate: SCH-05/07/23, document-21 N1/N2, nutrition/water balance and explicit step-size error bounds.

## S4: 3D excavation and connectivity

InitialSolid, local ExcavatePatch, material ledger, carried soil, ordered edits and progressively introduced local SDF. Real clearance/portals; invalidate affected paths after edits and support fill/blockage. Gate: SCH-04/09/16/26, G1/G2 and applicable document-12 tests. Prioritize numerical/topological correctness over finished rendering.

## S5: durable saves, history and analytics

Structured events, metric definitions and checkpoint serializer; application-layer SQLite atomic save/recovery and command ledger. Reconcile metrics with actual entities/events; do not pretend high-level events are full event sourcing. Gate: SCH-10/17/19/20/21/25/27, timing/size evidence and matching restored continuation.

## S6: integrated ecological loop

Use the biology fixture and multiple seeds to cover autonomous exploration -> collection -> return -> actual transfer -> brood nutrition/development -> reachable excavation -> facts/statistics. Test fixtures cover every required operation without demanding a fixed story from all random runs.

Gate: applicable implemented P0 mechanisms and SCH-01-23/25-27/29-30. Defer unimplemented LOD tests SCH-14/15 explicitly; do not report them passed.

Before S6.4 Core Readiness acceptance, implement and qualify the live, versioned, lossless durable history specified in the [TD-11 R1 design](../research/s6_3_3_3_r1/TD_11_R1_DURABLE_HISTORY.md). Acceptance requires canonical fact equivalence, ordered replay, exact analytics, compatible recovery, fault injection and bounded measured storage and memory. The offline experiment archive is evidence for the design. This prerequisite requires separate implementation authorization.

## S7: C ABI and Unity read-only integration

Versioned snapshots/dirty geometry, C# P/Invoke and true 3D observation, local mesh revisions and following. Gate: layout/ownership tests, stale packet rejection and camera invariance.

## S8: Game Master minimum tool chain

Typed World API, statistics, authorized PlaceFood and tracking, initially using a fake Agent to verify protocol. Select a harness after an independent comparison; S0-S6 do not need to choose it. Gate: real evidence, idempotency, uninterrupted core under API failure and rejected unauthorized changes. Longer memory, initiative and voice follow incrementally.

## S9: precision, time, pressure and map expansion

Grow from a small controlled scene to multiple colonies and the 24 x 24 meter world; measure chunk-size assumptions, near/far behavior and performance. Gate: SCH-13-15/24/28-30 with multiple seeds, matched simulation durations, identity/spatial continuity and statistical comparison.

## Boundaries and reports

Do not replace mechanism validation with graphics. Do not mix the complete map, tens of thousands of ants or voice into S0. Preserve C++/Unity, true 3D parametric authority and persistent GM identity. Uncalibrated values stay ENGINEERING_FIXTURE. Design gaps use explicit ADRs and bounded reversible choices.

Each batch reports file/interface changes, exact build/test commands and raw summaries, test IDs/results, limitations and next dependencies. Unrun tests are NOT RUN. Algorithm/model changes identify relevant design sections and schema/physics implications.
