# AntWorld decision register (v0.8)

Confirmed means explicitly accepted by the user. Proposed means suggested and changeable. To validate means evidence or experiments are required. Superseded means replaced by a later decision.

## A. Game and experience

| ID | Status | Decision |
|---|---|---|
| G-01 | Confirmed | Personal long-term ecological/life simulation, without levels, instances or player-directed combat as its foundation. |
| G-02 | Confirmed | Low-operation caretaker and observer role, with occasional food, water and limited environmental interventions; ants can survive independently. |
| G-03 | Confirmed | Start by following one colony, gradually discovering a persistent open natural ecosystem. |
| G-04 | Confirmed | Choose a newly mated queen, young colony or mature colony at creation; default to a young colony with few workers. |
| G-05 | Confirmed | Select habitat at creation; initially temperate grassland and woodland edge, with other habitats later. |
| G-06 | Confirmed | First complete world is 24 x 24 physical meters, expandable by chunks, with multiple independent initial colonies. |
| G-07 | Confirmed | True 3D surface and underground space, default 2.5D mixed camera, freely switchable transparent underground views, arbitrary sections and individual following. |
| G-08 | Confirmed | Refined, natural, semi-realistic miniature ecology; biologically credible ant morphology and visible behavior. |
| G-09 | Confirmed | Layered ecological precision: ants are most detailed; plants, aphids, prey and predators evolve autonomously without equal individual detail. |
| G-10 | Confirmed | Every instantiated ant has a basic life record; selected ants have deeper histories, with manual favorites and automatic tracking. |
| G-11 | Confirmed | Configurable pause, speed, offline pause, limited catch-up or continuing evolution. |
| G-12 | Confirmed | Macro statistics, individual history, time series, heatmaps, nest/colony comparisons and historical playback. |
| G-13 | Confirmed | Allow migration, reproduction, mating flights, decline and new colonies over time; population growth is not guaranteed. |

## B. AI Game Master

| ID | Status | Decision |
|---|---|---|
| AI-01 | Confirmed | The LLM does not make daily decisions for individual ants. It observes, explains, narrates, analyzes, accompanies the player and executes game tools. |
| AI-02 | Confirmed | One persistent GM personality spans independent worlds, sharing player memories while keeping world facts isolated. |
| AI-03 | Confirmed | Stable personality core; interests, expression, research goals and relationship memories develop through shared experience. |
| AI-04 | Confirmed | Proactively observe, select meaningful events, propose and track hypotheses, and correct errors. |
| AI-05 | Confirmed | Same game capabilities and readable data as the player; autonomous use is subject to permission levels. |
| AI-06 | Confirmed | Small interventions may be preauthorized; major/destructive changes require explicit permission. The engine computes consequences and commands are audited. |
| AI-07 | Confirmed | Text and voice are both important; switch between lightweight narration and a full interaction panel, with a unified identity. |
| AI-08 | Confirmed | Quiet, standard and documentary modes adapt initiative to player interests and observation. |
| AI-09 | Confirmed | Every factual explanation can reference simulation evidence; separate facts, correlation, causal hypotheses and literary narration. |
| AI-10 | Proposed | Persist personality, research notes, goals and shared history in game-owned storage independent of the LLM/harness. |

## C. Technology and simulation

| ID | Status | Decision |
|---|---|---|
| T-01 | Confirmed | Unity and C# client. |
| T-02 | Confirmed | Independent C++ Simulation Core owns world truth and runs headless; the engine presents and requests operations. |
| T-03 | Confirmed | Multiple precision levels: near/important interactions are detailed, distant ones lower-frequency; instantiated ants retain identity, state and necessary history across LOD changes. |
| T-04 | Proposed | Candidate 2 x 2 meter chunks (144 in 24 x 24 meters), separate surface heightfield/3D objects, local sparse underground volume, parametric spaces and connectivity. |
| T-05 | Proposed | Versioned C ABI and batch snapshots for Unity; World API/command bus for GM. |
| T-06 | Proposed | SQLite for snapshots, events and aggregated time series, with separate GM memory storage. |
| T-07 | To validate | Compare Python/Hermes, C#/Microsoft Agent Framework and a small custom harness. Python is not a confirmed default. |
| T-08 | Proposed | Initially 2-4 colonies and roughly 50-200 ants in the playable prototype, then 500-2,000 stress tests; larger populations are goals, not performance promises. |
| T-09 | Confirmed | All game mutations use one validated, authorized command path with event evidence. GM cannot alter Unity models to fabricate world facts. |
| T-10 | Confirmed | Validate behavior and basic life stages before colony society, 3D, history and GM; do not rush the complete game. |
| T-11 | Confirmed | Real 3D underground space, autonomous digging, soil transport and connectivity changes. Transparency/sections only affect observation. |
| T-12 | Confirmed | Geometry option A: initial materials plus ordered parametric excavation/fill edits are authoritative; local SDF is rebuildable cache. Replaces the earlier open A/B choice. |
| T-13 | Proposed | Track dry soil and water separately; structured digging/transport/deposition events; low-frequency multi-resolution heat/moisture. |
| T-14 | To validate | Local millimeter-scale active digging fronts and coarser environmental fields; brick dimensions, mesh method and budgets remain open. |
| T-15 | Proposed | Version geometry; derive clearance, portals and shape labels. Conservatively block/rebuild stale affected routes. |
| T-16 | Proposed | Commit actual material removal, soil parcel, geometry revision, event and ledger atomically; overlapping excavation cannot duplicate soil. |
| T-17 | Proposed | Stable C ABI exposes snapshot-bound dirty geometry and mesh packages; Unity cannot overwrite simulation geometry. |
| T-18 | To validate | Parametric CSG indexing/compaction, intersection-volume error, portal clearance, local mesh quality and performance. |
| T-19 | Proposed | Persistent region identities with split/merge lineage prevent tracking and GM history discontinuities. |
| T-20 | Proposed / to validate | Integer SimTime with mixed discrete events, continuous integration and multiple update rates; timestamp resolution is not traversal frequency. |
| T-21 | Proposed / to validate | Proposals read a consistent local state; shared resources, trophallaxis and excavation use single-writer arbitration and atomic commit; external commands take effect at safe boundaries. |
| T-22 | Proposed / to validate | Real-time, accelerated, headless and offline modes share AdvanceTo semantics. LOD preserves identity and never invents unsimulated detailed history. |
| T-23 | Proposed / to validate | Checkpoints retain queues, RNG, entities, geometry, plans and idempotency ledger. High-level events alone are not a full replay save. |
| T-24 | Proposed / to validate | Unity/GM asynchronously consume committed snapshots/events without blocking the simulation or changing individual biology. |
| T-25 | Proposed / to validate | SCH-01-SCH-30 validate scheduling and transactions; build a small headless causal loop before full integration. |

## D. Biology

| ID | Status | Decision |
|---|---|---|
| B-01 | Confirmed | First focus species: Lasius niger. Different species require different physiology, social and nesting rules, not cosmetic reskins. |
| B-02 | Confirmed | Simple, explainable, bounded individual models: state machines, response thresholds, randomness, limited route memory and pheromones; avoid anthropomorphic reasoning. |
| B-03 | Confirmed | No colony-wide commander. Allocation emerges from local stimuli, individual variation, interaction and environmental feedback. |
| B-04 | Proposed / research | Separate carbohydrate, protein and water; body energy differs from crop contents; trophallaxis is a real local transfer; identity persists egg to adult. |
| B-05 | Proposed / research | Brood care, cleaning, digging, transport, movement and inactivity compose nest work; thresholds and species mechanisms need calibration. |
| B-06 | Proposed / research | Excavate reachable local interfaces and transport real material; nest shapes and functions derive from activity and geometry, not room upgrades. |
| B-07 | To validate | Calibrate L. niger digging responses, cues, moisture, crowding and brood effects. Other species cannot supply unqualified quantitative rules. |

## Superseded and unresolved ideas

Limited LLM control of workers was replaced by local biological behavior and a world-level GM. A C# core was replaced by C++ core plus Unity C#. Python GM was withdrawn as a default.

Chunk sizes, field precision, LOD rates, throughput, database tables, weather equations, geometric primitives, GM name and voice remain proposals or experiments. Option A is selected, but its numerical implementation is not. Demonstration numbers are not measurements.

## v0.8 delivery clarification and repository policy

The handoff completes pre-development contracts and task descriptions. Execute one stage at a time using document 22. C++20, CMake, 1 ms timestamps and persistence defaults are reviewable engineering choices in document 16, not independently confirmed product requirements.

On 2026-11-08 the user approved starting S0 and required English in all tracked content and commit messages, while conversation remains Chinese. This does not authorize S1-S9 in the same run and does not alter the confirmed ecological architecture.
