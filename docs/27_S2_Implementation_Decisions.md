# S2: local sensing, exploration and trails

Status: implemented for the user's S2 authorization after S1 Code Review. Design baseline remains v0.8. This document resolves bounded engineering choices under documents 04, 16-19, 21, 22 and 24. Every numeric behavioral parameter is `ENGINEERING_FIXTURE`, version `s2-local-v1`, without Lasius niger calibration. S3 is not authorized.

## ADR-S2-01: a static surface for local motion

S2 adds an optional immutable rectangular surface with a walkability mask. Coordinates remain meters, X east/Y up/Z north; the grid lies at a fixed Y. The origin is the center of cell (0,0). A successful surface Move traverses exactly one cardinal edge between walkable cell centers, subject to the retained speed and position-revision checks. Contact with food and the nest requires the same cell. Floating center recognition uses a numerical tolerance of 1e-9 meters, not a biological contact radius.

This is the smallest reversible local navigation fixture. There is no diagonal corner cutting, global shortest-path planner, moving obstacle, ant collision, underground graph, SDF or excavation. The S1 obstacle-free Move remains available when no surface is configured. Configuring the surface is restricted to initial setup, before entities/events. Surface and food placement are validated; one static food source per cell is supported. Initial nests are real colony positions, not implied shared coordinates.

## ADR-S2-02: bounded perception and individual decisions

`sense(AntRef)` visits only reachable cells within a configurable cardinal step radius (1-3). Its fixed storage supports at most 25 cells, four legal next steps and 25 food cues. The food-cell index avoids scanning all resources. A cue contains an actually reachable nearby source, local distance and first local step. Neighboring pheromone samples belong to the ant's own colony. Walls prevent sensing through disconnected cells. Observers may inspect global summaries; those summaries never enter the behavior model.

`choose_behavior` is a pure function of seed, stable individual identity, private state, carrying status, local cues and fixture parameters. It receives no WorldRuntime, food store, coverage map, colony controller or undiscovered target. Coordinates in its bounded paths are experienced landmarks, never a precomputed global route to food. The model can rest, explore, follow a local food cue/trail/remembered step, collect, retrace home or deliver. Empty return trips are possible.

Each individual's random stream is domain-separated in the order world seed -> identity -> decision count, using specified SplitMix64 operations and rejection sampling for integer weighted choices. Initial heading has a separate counter domain. Direct seed XOR actor mixing was rejected during development: neighboring seeds could merely permute worker streams. A regression checks this failure mode and multi-seed tests compare behavioral metrics rather than hashes containing the seed.

All same-time wake observations and choices are frozen before their proposals are committed. Canonical actor-ID order assigns internal action IDs; it does not select behavior. Resource resolution retains S1's deterministic fair arbitration. Reversing activation order produces identical per-ant state, paths, counters and fields. Setup facts and initial wake IDs can still reflect activation call order; byte-identical history across different input histories is not promised.

## ADR-S2-03: bounded homing and learned route memory

An ant maintains a loop-erased trace of its current trip, with capacity 2-64 cells (default 48). Reaching the route bound or 192 trip moves initiates return. A loaded ant retraces locally reachable predecessor cells. This bounded working trace is present in every treatment: disabling learned route memory does not disable the minimum ability to return.

The optional inter-trip memory retains one successfully experienced nest-to-food route. It is learned only after a committed collection, stores at most the same capacity, and expires after 300,000 simulated milliseconds by default. An ant can follow only an adjacent legal remembered step from its current landmark. An expired route, empty endpoint or locally unavailable next step is forgotten. Discovering a new source can replace the route. No list of global food positions or unlimited visit history is stored on the ant.

The observer records collection revisits to the individual's most recently collected source and counts forgotten routes. Static experimental sources rarely exhaust and successful revisits refresh memory, so the main matrix can legitimately have zero memory failures. Separate depletion and zero-lifetime tests exercise those branches. Dynamic route invalidation after excavation belongs to S4.

## ADR-S2-04: sparse colony trails and physical nest delivery

Trails are sparse `(ColonyId, Cell)` entries. Only a committed movement while carrying actual food deposits at the arrival cell. Deposit and movement share a transaction and fact; a proposal alone never leaves a trail. Default deposit is 1 abstract unit, saturation is 16 units, half-life is 60 simulated seconds, and sparse cutoff is 0.001 units. These units are engineering signal units, not measured chemical mass. Only neighboring walkable samples influence exploration weights; the field has no direction-to-food oracle. There is no diffusion in S2.

Decay is analytical between fixed 5,000 ms maintenance boundaries. Reads evaluate decay without materializing it or changing time/RNG. Maintenance applies decay and removes inactive entries, including after all foragers die. Deposited quantity records the actual addition after saturation. The observer's `evaporated_units` includes both exponential loss and the remaining quantity removed below cutoff. Recomputing exact saturated arithmetic validates deposits during restore, avoiding an incorrect strict comparison after floating-point subtraction.

DeliverFood transfers the ant's actual carried ingredients into its own colony's physically located `nest_food` only at nest contact. Inventory is not instantly shared by distant individuals. For each ingredient:

`introduced = available at sources + carried by ants + physically stored at nests`.

Dead ants retain identity and cargo. Delivery is storage, not ingestion, trophallaxis, energy integration, brood provisioning or colony physiology. Those mechanisms remain S3 work.

## ADR-S2-05: scheduler ownership and allocation-safe transactions

Autonomous workers are activated during setup at their own nest, with positive carrying capacity and no cargo or externally pending actions. Each enabled worker owns exactly one wake or action. Perception commits a proposal for completion after 1,100 ms; action completion schedules the next perception 1 ms later. These delays are engineering fixtures. They prevent perception from running before arrival at the same timestamp. Lifecycle death runs earlier and atomically cancels the owned event.

Public Submit cannot override an autonomous worker; public Cancel cannot orphan owned actions, wakes or field maintenance. S0/S1 full-key watermarks, same-time budgets and atomic action batches remain unchanged. A failed AdvanceTo rolls back the entire call, including earlier moves, food transfers, discoveries, memory updates, deposits, sparse erasures, facts, counters and schedules.

State remains noncopyable. The existing row/queue undo journal is extended with colony before-images and typed map journals. Map updates retain only touched values; erasures retain node handles for allocation-free rollback. Surface configuration is immutable and shared, and local observations/private route storage are bounded. Transaction cost depends on affected work, not copying all entities/history. A very long AdvanceTo still retains undo entries proportional to work until commit; callers may use shorter chunks with identical results.

## ADR-S2-06: checkpoint schema and evidence

Schema and physics versions are 3; magic is AWCKPT3. S0 v1 and S1 v2 saves are explicitly rejected, with no migration promised in this stage. The S0/S1 behavioral tests remain; fixture-generated saves use the current schema.

Canonical little-endian encoding retains the queue (115 bytes per record), extended committed facts (159 bytes), four-part world ledger including stored inventory, colony nest position/inventory, and the S2 tail. The tail stores the immutable surface/parameters/mask, counters, maintenance ownership, bounded private state (1,099 bytes per forager), sparse fields and observer evidence maps. The food-cell lookup is rebuilt from source positions. Limits are configurable host policies, not biological or format maxima.

Restore validates bounds, finite quantities, walkability, ownership, route adjacency and loop erasure, nest/current/food endpoints, enabled/lifecycle consistency, ingredient conservation and canonical unused storage. A focused history audit reconstructs S2 paths, learned memory, counters, coverage, traversed edges, discoveries and sparse fields from committed facts and checks the stored values. This is not a claim of general event sourcing or S5 durable persistence. Semantic corruption tests repair the checksum before forging quantities, counters, memory and owned event references. Failed restore preserves the current world.

ForagingDecision is an actual committed selection record, not evidence of a successful future Move/CollectFood. Each scheduled event still produces at most one fact; actual movement includes its deposit and actual collection/delivery includes exact transferred ingredients. A discovery records one explicitly logged local cue per decision (the chosen collection resource or first sensed local cue), not every source an omniscient observer can see. No fabricated history is inferred from aggregate success.

Same executable/configuration/input reproduces a checkpoint and its continuation across different AdvanceTo chunk sizes. Floating-point decay and movement retain the v0.8 boundary: cross-platform bit identity is not claimed. FNV checksums/hashes detect accidental corruption and are not authentication against a coordinated rewrite of a save and its evidence.

## F1/F2/F3 experiment contract

`antworld_s2_experiment` runs all seeds 1-16, both layouts, and four paired treatments (none, trails only, memory only, both), with identical initial geometry, resources, identities and worker count. Every run uses 12 workers for 1,800,000 simulated ms, sampled every 30,000 ms including zero. There are 128 final rows and 7,808 time samples. No seed is excluded.

The surface is 31 x 21 cells of 0.01 m. The nest is cell (3,10); two sources are at (25,5) and (25,15), each initially containing 1,000,000 ug of each of four ingredients. Each worker carries at most 1,000 ug. The barrier layout blocks x=15 except gaps at z=4 and z=16; its walkable count is 632 versus 651 for open. Sources are not in initial sensing range. These are mechanism fixtures, not a scaled colony or an insect calibration.

| Metric | Definition and interpretation |
|---|---|
| Coverage | Distinct physically visited cells (including start nest) / all walkable cells; not remotely perceived area |
| First discovery | First committed local cue and discovering stable ID; -1 means right-censored at run end |
| Delivery per started trip | Completed physical deliveries / departures from nest without cargo; includes unfinished and unsuccessful trips in denominator |
| Collection success | Successful collection events / collection decisions, including pending attempts in denominator |
| Revisit | Collection at the same source as that individual's previous successful collection |
| Mean outbound moves | Sum of actual trip movement counts at successful collections / collections; no optimal-path baseline is inferred |
| Edge reuse | (All traversals - distinct undirected edges) / all traversals; includes homeward movement and exploration loops |
| Trail/memory moves | Actual successful steps selected in FollowTrail/FollowMemory mode; these are mechanism-use counts, not proofs of causal optimality |
| Memory failure | An actual decision forgetting an expired, exhausted or locally invalid learned route |
| Trail amount | Read-only decayed active quantity; deposited and evaporated amounts are cumulative |

`summary.csv` and `timeseries.csv` are deterministic raw output. `tools/analyze_s2.py` audits balanced treatments, time samples, monotonic aggregates, total material and disabled features; it generates means, sample standard deviations, ranges and paired differences. It does not claim significance or biological calibration. Checkpoints additionally validate each ingredient and the evidence history for every final run. Exact trial results and negative findings belong in S2_RESULTS.md.

## Verification map and boundaries

The retained 28 S0/S1 tests run alongside 15 S2 cases: SURFACE, LOCALITY, LOOP, ORDER, MEMORY, TRAILS, REPLAY, ROLLBACK, SCHEDULING, MULTISEED, MODEL, COLONIES, CORRUPTION, ALLOCATION_FAILURE and EXPERIMENT_SMOKE. Allocation injection covers surface setup, local indexing, activation, discovery/decision, movement, learning, deposits, decay/pruning, delivery, death cancellation and restore.

The S2 benchmark measures 16/128/512 active workers, per-advance p50/p95, throughput, event count, save size/cost and restored continuation. The S1 fixed-active and S0 scheduler/diagnostic benchmarks remain. These are small static surfaces, not evidence for full-map, 20,000-active-ant, offline or LOD goals. No S3-S9 implementation or approval is implied. Stop at S2 for Code Review.
