# Historical roadmap and acceptance (v0.5 with v0.7 updates)

This document preserves earlier planning. Use document 22 for current S0-S9 stage numbers and scope. The imported baseline had no implemented game or selected GM runtime.

## Behavior research first

P0-A: about 50 L. niger workers, two food sources, local senses, pheromones and limited memory, no central orders, repeated seeds. P0-B: energy, carbohydrate/protein/water, real trophallaxis, stable egg-to-adult identity, queen reproduction and hazards. P0-C: brood relocation, spatial work, cleaning, soil transport, dynamic digging and connectivity. P0-D: real data, curves, event detectors and evidence-based GM reports.

## Earlier milestones

| Stage | Scope | Gate |
|---|---|---|
| M0 | Core, identity, time, RNG, command/event basis, headless runner | Independent simulation and tests |
| M1 | Behavior, pheromones, learning, resources, basic life loop | Two-food and nutrition/reproduction experiments |
| M2 | Chunked world, true 3D spaces, Unity batches/following | Camera does not change facts |
| M3 | Digging/transport, brood movement, microclimate and spatial use | Geometry/connectivity agree; digging has negative feedback |
| M4 | SQLite, history/charts, Agent tools and text GM | Queries and authorized interventions have evidence |
| M5 | Colonies, LOD, acceleration/offline and long regression | Identity, materials and cross-precision statistics remain valid |
| M6 | Adaptive voice, cross-world personality/memory and visual refinement | One GM identity and shared voice/text context |

## First playable target

Temperate grassland/edge, 24 x 24 meters, two colonies, roughly 50-200 ants. One dynamically expanding 3D nest and another initially lower-detail nest. Foraging, care, trophallaxis, rest, mortality and limited excavation; surface/underground observation, following and core colony comparisons. GM proactively reports a real event, answers evidence-based questions, controls views, places requested food and tracks subsequent effects.

## Acceptance

Stable identities survive saves; worlds remain isolated. No passage through disconnected space. Nutrition and trophallaxis balance with explicit sinks. Speed/headless/step changes must not systematically distort distributions beyond declared tolerance. LOD preserves state/history. Population matches unique living entities, without duplicate death. Ecology runs without GM. Commands are authorized and idempotent; claims have evidence. Measure core, rendering, mesh, database and model costs separately.

## Earlier experiments

F1 exploration without pheromone: discovery time and coverage. F2 trails on/off: formation, stability and collection. F3 memory on/off: revisits, errors and return. F4 congestion: behavior/recruitment feedback. F5 food removal: trail decay and redistribution.

E1 metabolism and activity; E2 sufficient sugar versus limited protein and brood development; E3 spatial trophallaxis network/balance; E4 queen reserves, laying and first workers. Historical N1 brood movement with climate, N2 crowding/population and digging, N3 cleaning/deposition, N4 inactivity and reactivation. Qualitative direction is not quantitative species calibration.

## Geometry and integrated updates

Use a small soil column before the full map. Earlier authority comparisons were superseded by option A. X1 tests projected crossings without connection; X2/X3 overlapping removal and transport conservation; X4 incremental excavation without blueprints; X5/X6 temperature/rain and conserved water; X7 view invariance; X8/X9 speed/offline/save consistency; X10 separate cost measurements.

Document 12 defines G0 authority/materials, G1 clearance/connectivity, G2 SDF/mesh cache, G3 Unity ABI, G4 behavior-driven digging and G5 long runs. GEOM-01-GEOM-15 enforce no duplicate soil, false connection or stale-path passage, consistent versions and view isolation.

The v0.7 proposal starts with time/events/IDs/RNG/snapshots, then food/energy/trophallaxis transactions, then a 3D front with materials and statistics. Document 14 defines SCH-01-SCH-30; document 15 describes the integrated loop. Later v0.8 stages refine this order and narrow the first batch to S0.
