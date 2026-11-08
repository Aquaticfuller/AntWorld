# AntWorld technical architecture (historical v0.5 with v0.7 updates)

## Stack and dependencies

C++ Simulation Core owns world truth and runs headless for long simulations, experiments and regression. Unity/C# renders, handles cameras/input and presents charts. The GM harness remains open: compare Python/Hermes, C#/Microsoft Agent Framework and a lightweight custom runtime. SQLite is the initial persistence candidate; GM memory has a separate data space.

Unity and GM connect through Application/World API. Queries consume immutable snapshots, events and analytics. Mutations pass authorization and validation into the C++ command path. Player and GM capabilities match; autonomous high-impact use requires permission. Disabling GM must leave ecology running.

## Core module responsibilities

| Module | Responsibilities |
|---|---|
| world | WorldState, clock, random streams, scheduler |
| entities | Stable IDs, ant/other-species/colony stores |
| physiology | Energy, nutrients, hydration, development, mortality |
| perception | Local sensing and spatial index |
| behavior | Hierarchical tasks, response thresholds, actions |
| memory | Route associations, familiarity and forgetting |
| chemistry | Surface pheromones, deposits and decay |
| colony | Shared physical resources, trophallaxis and interactions |
| nest | Derived chambers/tunnels, digging, transport, microclimate |
| environment | Climate, food, plants and coarse predators/soil |
| navigation | Local 3D motion and surface/tunnel routing |
| scheduling | Mixed-rate updates, event queue and behavioral LOD |
| history | Structured events, snapshots and metrics |
| API | C ABI handles, commands, queries and batches |

These are future responsibilities, not an instruction to create every module in S0.

## Identity and state

Use typed WorldId, ColonyId, AntId, NestId, region and event/command IDs. Cross-world references always include WorldId. An ant keeps its ID from egg to death. Physiology, position, behavior, limited memory and scheduling are components suitable for SoA storage.

Colony state holds physical shared resources, recognition cues and derived statistics; it never centrally assigns worker occupations. Food stores real carbohydrate/protein/water quantities and decay. Transfers update a ledger. WorldEvent records world/time/entities/location/type/parameters/origin/evidence.

## Space

Coordinates are meters; ants operate at millimeter scale without visual magnification changing physics. The complete 24 x 24 meter world can use candidate 2 meter surface chunks. Surface heightfields are separate from plants, rocks, roots and walkable objects. Underground uses sparse local representation with ordered parametric geometry and derived topology.

Long-range navigation connects known spaces/exits; local movement checks clearance, avoidance and contact. Projected tunnel crossings are not connections. Pheromones live on reachable surfaces rather than a uniformly fine 3D gas grid. Digging changes real material, carried parcels, navigation and relevant environmental boundaries, refreshing only dirty areas.

## Precision and time

Behavior, environmental fields, history sampling and rendering have independent precision controls.

| Level | Meaning |
|---|---|
| L0 | Fine local perception, actions and contact for nearby/important interactions |
| L1 | Ordinary nearby behavior with reduced sensing/path frequency |
| L2 | Persistent distant individual identity, physiology, task, route, significant events and wakeup |
| L3 | Background populations outside the instantiated domain; no invented individual history |

Integer time resolution and update frequencies require validation. Acceleration advances the same simulation semantics, using sparse/event updates where valid. Interacting entities first reach compatible precision. Compare speed/step configurations statistically; do not promise identical floating-point trajectories across all backends.

## Native and Agent boundaries

Versioned C ABI operations cover create, advance, query batches, execute and save. Unity receives visible/tracked ant arrays in batches, with explicit ownership, capacity, layout, alignment and versions. Avoid per-ant per-frame P/Invoke. Rendering interpolation never writes back positions.

Candidate tools include QueryWorld, QueryAnt, QueryColonyMetrics, GetHistory, FocusCamera, PlaceFood, ScheduleWeather, SetTimeScale, WatchAnt and SaveWorld. Distinguish read-only queries, view controls, ecological changes and destructive lifecycle operations. Authorization, legality, idempotency, audit and receipts precede success reports. GM has no arbitrary shell or direct memory editing tools. Low-cost detectors run continuously; call LLMs for meaningful events, conversations or scheduled analysis.

## Storage and performance

Keep world checkpoints, committed events/time series and cross-world GM memories distinct. Candidate tables include snapshots, entities, life/world events, metrics, tracked trajectories, GM identity/memories/goals and tool audit. Ordinary ants retain major events and aggregates; only selected individuals have frequent position sampling. Define every statistic and its time window. Restore checks identities, population, nutrient balance, geometry and queues.

The earliest playable goal is roughly 50-200 ants in two colonies, one dynamic 3D nest and complete query/GM paths. Later stress targets are 500-2,000; 20,000+ is a long-term aspiration. A 60 FPS visual goal is separate from measured core, rendering, database, geometry and Agent costs. Dense contacts, pheromones, geometry/navigation refresh, growing logs and LOD continuity are risks to measure.

## Later authoritative refinements

v0.6 selected InitialSolid + OrderedGeometryEdits as geometry authority. SDF, mesh, collision and nest graphs are versioned derived data. A GeometryTransaction commits actual removal, soil parcels, ledgers and revision together. Use snapshot-bound mesh metadata/copy interfaces, dirty batches and clear handle lifetimes; no STL or exceptions across the ABI. Physics and clearance remain in C++, independent of Unity colliders. See 10-12.

v0.7 introduced int64 SimTime, future events, continuous integration and multi-rate wakeups. Local perception produces ActionProposals; deterministic arbitration and single-writer commits produce events/statistics. External commands enter an inbox and take effect at a safe boundary. Checkpoints preserve RNG, queue order, plans, material state and idempotency ledgers. SCH-01-SCH-30 and the P0 loop define validation; actual rates and performance remain experimental. The later v0.8 contracts and roadmap take precedence over earlier alternatives.
