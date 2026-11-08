# Simulation runtime, mixed scheduling and transactions (v0.7)

This is the historical integrated scheduling proposal. v0.8 contracts in 17-19 and implementation ADRs refine it. Proposed step sizes and species parameters are not measured facts.

The purpose is one causally consistent timeline linking food, trophallaxis, metabolism, development, tasks, excavation, ecology, statistics and external tools. Preserve independent C++ authority, Unity presentation, persistent cross-world GM, individual identity, the complete-map target and confirmed parametric geometry.

## Invariants

Only the core writer commits physical/biological state. Events cannot act before now. Material inputs, transfers, consumption and outputs balance within declared tolerance. One individual keeps its identity; development/death cannot double-count. Movement follows current geometry and loaded clearance. LOD preserves identity/state/history and does not invent L3 individuals. Facts carry world, time, entities, origins and evidence. Commands are idempotent. View/GM operations cannot change random trajectories. Checkpoints capture all authoritative continuation state atomically.

## Three clocks

SimTime orders world facts. WallTime selects target simulation time for real-time/offline use. RenderTime interpolates presentation and never writes back. Integer millisecond timestamps are a candidate resolution, not a requirement to traverse every entity every millisecond.

Speed multipliers change how much SimTime to advance, not metabolic/reproductive equations. Pausing stops simulation progression. Offline policy computes a legal target and can process it in bounded intervals.

## Mixed discrete/continuous execution

Future events include arrivals, pickup attempts, transfers, development thresholds, excavation, resource exhaustion, laying, commands, hazards and metric boundaries. Order by `(time, phase, semantic_priority, stable_tie, sequence)`. Collect competing proposals from a consistent snapshot, arbitrate deterministically and avoid permanently favoring low IDs. Store random tie streams/counters. New same-time work must obey phase boundaries and a finite-loop/queue budget.

Continuous processes advance only over valid intervals:

| Process | Integration / boundary |
|---|---|
| Energy | Integrate unchanged rates until behavior, temperature or intake changes |
| Hydration | Local intake/loss until climate, position or water access changes |
| Brood progress | Temperature/nutrition integration with stage and starvation thresholds |
| Queen reserves/laying | Species-specific mixed events and rates |
| Pheromones | Local deposits and time-based decay; stable diffusion steps if enabled |
| Climate | Coarse low-frequency fields, interrupted by rain or geometry boundaries |
| Near motion | Bounded substeps and contact/obstacle boundaries |
| Far motion | Route/ETA events interrupted by hazards, topology or interaction |

Pure decay can use `C(t+dt)=C(t)*exp(-lambda*dt)`. Diffusion must satisfy spatial/time stability. Mortality sampled only at the end of a large step can permit actions after death; locate relevant cumulative-risk or physiological thresholds on the timeline.

AdvanceTo chooses the earliest target, discrete event, field boundary or required near substep; integrates without crossing an unhandled hard threshold; gathers due work; resolves and commits; publishes facts; schedules subsequent work. The v0.8 version also handles already-due work at the current boundary. The pseudocode is not a proven numerical solver.

## Commit boundary

Historical phases: 0 input freeze/validation; 1 environment/lifecycle; 2 local perception; 3 proposals; 4 conflict resolution/commit; 5 secondary validation; 6 publish; 7 derived work/reschedule. Document 18 refines phases 4 and 5 into arbitration and atomic commit.

Death effective at this time precedes successful behavioral proposals. Failed collection provides no nutrition; failed digging produces no soil. Environmental facts apply before subsequent perception. Initially one writer submits all changes, with resource/geometry-scoped transactions suitable for future deterministic parallel proposal generation. Cross-chunk edits are all-or-nothing.

Two workers requesting 3 mg each from 4 mg cannot receive more than 4 mg combined. Overlapping digs recompute remaining material and commit geometry/ledger/parcels together; transport still requires later physical travel. Trophallaxis validates contact, living stages, donor supply and receiver capacity and transfers actual stock without double-counting a colony pool.

## LOD and observation

L0 handles fine local interaction; L1 ordinary nearby behavior; L2 persistent distant state, routes, significant events and scheduled wakeups; L3 background populations without invented individual histories. Before contact, participating entities enter compatible precision. If sparse motion cannot resolve a contact, disclose the approximation rather than fabricate an event.

Tracking changes record precision, not intelligence, luck or biological ability. Querying an ant or disabling GM must not change its fate. If a precision policy approximates behavior, measure bias and label history precision.

## Asynchronous clients and pause

Unity consumes committed immutable snapshots/dirty geometry. GM uses authorized command envelopes queued for safe boundaries, with accepted/committed/rejected receipts. Low-cost observers filter events; LLM latency is outside the core loop. While paused, browsing/history/chat continue. Mutations normally remain pending until resumption; any future zero-time commit mode must be explicitly designed. Historical playback is independent and labels interpolation or illustrative reconstruction.

## Checkpoint and replay

A high-level journal is not full event sourcing. Preserve time and subsystem boundaries; world/entity allocators and dead identities; physiology, behavior, memory, position, carry and plans; resources, fields and environment; InitialSolid/edits/materials/versions; queue and sequence; RNG streams/counters; pending/committed command ledger; analytics and durable cursors.

Only a complete consistent generation is recoverable. Async persistence must distinguish in-memory progress from durable progress. Separate files and databases need a recovery protocol, not an assumed atomic rename/commit pair. Start with a synchronous consistent checkpoint, restore and continuation test.

Reproducibility tiers: same binary/configuration/seed/single-writer schedule and commands should reproduce exact key facts/state; different integration/LOD/parallel backends must preserve invariants and distributions within declared tolerance, not necessarily identical trajectories. Record effective authorized GM commands for deterministic replay; LLM prose itself does not alter state.

## Future responsibilities and unknowns

Modules cover clock, future events/multiple rates, barriers/proposals, stores, physiology, behavior/perception, chemistry, ecology, spatial geometry/navigation, history, commands, RNG and versioned APIs. Runtime offers advance, enqueue, immutable snapshot and committed-event reads; concrete types follow document 17.

Measure timestamp range, movement/sensing/interaction steps, environmental stability/error, far-motion/hazard sampling, threshold location, batch arbitration, chunk scheduling, history and checkpoint cost. Reference concepts: https://doc.omnetpp.org/omnetpp/manual/index.html and Unity native plugin documentation. AntWorld does not thereby depend on OMNeT++ or inherit a verified biological model.
