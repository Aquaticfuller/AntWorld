# First integrated ecological vertical slice (historical v0.7)

This later P0 milestone validates an autonomous loop without Unity or LLM. S0 is only its infrastructure foundation. The current stage numbering is document 22.

## Goal and fixture

Demonstrate local foraging -> food brought home -> trophallaxis/brood care -> physiology/development -> physical excavation -> committed events/statistics. Include at least one validated real 3D digging transaction. The target is a small controlled experiment, not the complete map, all species, finished art or a mature general-purpose Agent.

Candidate engineering fixture: one L. niger colony with a queen, about 32 workers and 12 brood; a connected seeded chamber/entrance; two food sources for nutrient coverage; reachable soil, a transport/deposition route; stable identities and at least one tracked worker. These counts are test inputs, not field measurements. Navigation is genuinely spatial, without requiring detailed animations.

## Required causal chain

WorldClock -> local discovery of FoodSource -> pickup proposal and committed source loss -> actual reachable return -> trophallaxis with donor/receiver changes -> metabolism/brood nutrition -> stage/state change -> local spatial stimulus and digging proposal -> material removal plus parcel -> geometry/nav update -> later transport -> structured events, metrics and queries.

Random outcomes may vary. Fixed fixtures/seeds or clearly labeled test injection cover each operation; do not demand identical biological stories on a fixed timetable from every seed.

## Interface and delivery

CreateWorld, AdvanceTo, EnqueueCommand with idempotent receipt, world-scoped ant/colony queries, metric ranges, committed-event cursors, immutable snapshots and checkpoint save/load. Headless JSON/CSV is sufficient initially. Unity later follows the C ABI ownership/version contract.

The historical sequence proposed S0 time/IDs/RNG, S1 stores/proposals, S2 foraging/trails, S3 physiology/brood, S4 geometry, S5 persistence/analytics, S6 Unity and S7 GM. The v0.8 roadmap supersedes those final labels: S6 is integrated ecology, S7 Unity, S8 GM and S9 expansion. Do not silently mix stage definitions.

## Observation and acceptance

Initial diagnostics should show population and nutrient balance curves, a route/pheromone plot and a causal event list. These are debugging views, not final art. Later Unity shows actual 3D nests, sections and following; 60 FPS is not a biological correctness test.

Success: locally autonomous search/collection/return, balanced actual trophallaxis, modeled brood changes, reachable physical excavation, associated identity/time/evidence, and unchanged committed history across restore. Failure: wall passage or teleportation, duplicate resources, fabricated transfers, copied soil, repeated death/emergence, observer-induced randomness, lost future events or APIs bypassing rules.

P0 does not establish species calibration, years of stable ecology, complex insects, finished animation, mature personality growth or tens-of-thousands throughput. Open work includes precise phase/time contracts, minimal legal proposals/fairness, store/lifecycle transitions, atomic recovery and source-qualified biological parameters. Later v0.8 documents supply the first engineering defaults.
