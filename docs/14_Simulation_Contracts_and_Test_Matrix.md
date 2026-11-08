# Core invariants and acceptance matrix (v0.7)

These are staged acceptance contracts, not completed tests. Document 22 determines which items apply to each implementation batch.

## Verification tools

HeadlessScenarioRunner specifies seed, initial entities/materials, time, commands and outputs. WorldInvariantChecker checks population, materials, space and identity. EventTraceInspector exposes chronology, prerequisites and commits. CheckpointRoundTrip compares continuation after a safe-boundary save/load. MetricsExporter emits JSON/CSV without Unity or GM.

## Required checks

| ID | Scenario | Requirement | Priority |
|---|---|---|---|
| SCH-01 | Repeated read at one time | No time/state/RNG mutation | P0 |
| SCH-02 | Schedule into past | Reject without changing revision | P0 |
| SCH-03 | Simultaneous collection | Combined transfer <= stock; no negative/duplicated material | P0 |
| SCH-04 | Overlapping digs | No duplicate removal; geometry/material versions agree | P0 |
| SCH-05 | Trophallaxis | Donor loss equals receiver gain; crop/body accounting is distinct | P0 |
| SCH-06 | Death and behavior at same time | Dead individual cannot subsequently act successfully | P0 |
| SCH-07 | Egg develops into worker | Continuous AntId, only stage changes | P0 |
| SCH-08 | Duplicate death | Death and population decrement happen once | P0 |
| SCH-09 | Backfilled/blocked tunnel | Immediately invalidate affected routes; no wall passage | P0 |
| SCH-10 | Retried GM food command | CommandId produces food once | P0 |
| SCH-11 | LLM/API timeout | Core continues; messages cannot change the past | P0 |
| SCH-12 | Paused view/section changes | Time, state hash and RNG unchanged | P0 |
| SCH-13 | Normal versus 120x, same configuration | Same seed/command timeline yields same logical trace | P0 |
| SCH-14 | L0 -> L2 -> L0 | Identity, physiology and confirmed history continue without cloning | P0 |
| SCH-15 | L2/L0 contact | Compatible precision before interaction; no teleport/duplicate transfer | P0 |
| SCH-16 | Different-depth crossing | No connection without real clearance | P0 |
| SCH-17 | Same local ID in two worlds | WorldId isolates references and facts | P0 |
| SCH-18 | Long run without model API | Ecology, events and statistics continue | P0 |
| SCH-19 | Save/load future events | Planned arrival, laying, stages and weather preserved | P0 |
| SCH-20 | Save/load RNG/command ledger | Continuation reproduces and operations are not repeated | P0 |
| SCH-21 | Recover from high-level journal only | Reject incomplete recovery | P0 |
| SCH-22 | Many self-triggered same-time events | Finite protection and diagnostics | P0 |
| SCH-23 | Large integration crosses threshold | Locate/truncate threshold; no actions after invalid physiology | P0 |
| SCH-24 | Different integration steps | Conservation and error within stated tolerance | P1 |
| SCH-25 | Crash during async save | Recover last complete checkpoint, no mixed generations | P0 |
| SCH-26 | Cross-chunk digs | All-or-nothing geometry/material/dirty/portal update | P0 |
| SCH-27 | Charts and event history | Windows/definitions match facts and entity values | P0 |
| SCH-28 | Parallel versus serial | Invariants and statistical distributions within tolerance | P1 |
| SCH-29 | Rain/blockage in low-frequency area | Reevaluate from real current versions, no stale-path teleportation | P0 |
| SCH-30 | Months of simulation | No negative stock, unbounded queue, ID wrap or uncontrolled storage | P0 |

## Properties and tolerances

Resource stock is nonnegative and bounded by initial stock plus explicit inputs minus sinks. Living population equals unique living AntIds by colony/stage/caste. Geometry revisions increase and current portals satisfy clearance. Same command/payload returns the prior receipt; conflicting payload under an existing ID is rejected. Queries never consume RNG. Multi-seed reports include distributions/quantiles, not a selected success story.

Choose error budgets from units, spatial sampling and numerical method before tests. A visually plausible result is not a quantitative criterion.

## Measurements and stage claims

Report simulated/wall seconds, AdvanceTo p50/p95/p99, queue length and wakeups, proposal conflicts and outcomes, subsystem CPU/memory, checkpoint/log size and cost. Render/ABI and LLM latency/cost are separate.

The historical broad P0 gate included SCH-01-SCH-23, with more advanced checks later. v0.8 narrows S0 to its applicable foundation subset and defers unimplemented features explicitly. Never mark unavailable biology, LOD or client tests passed. Biological values remain proposed or uncalibrated until evidence supports them.
