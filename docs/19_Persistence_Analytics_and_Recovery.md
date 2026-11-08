# Persistence, history, analytics and recovery (v0.8)

## Distinct data spaces

Checkpoint is authoritative continuation state: entities, physiology, memory, geometry, resources, future work, RNG and command ledger. Event journal records actual committed life/material/geometry/intervention facts for history and evidence; it is not guaranteed to reconstruct every internal state. Metrics are defined aggregates over states/events with explicit sampling and retention. Cross-world GM identity/memory is a fourth separate space, never world truth.

## Checkpoint contract

| Category | Required state when that subsystem exists |
|---|---|
| Header | Magic, schema/physics version, worldId, seed, revision, program/version metadata and integrity hash |
| Time | SimTime, phase and subsystem next boundaries |
| Entities | Instantiated identities, physiology, tasks, memory, position and wakeups |
| Spatial | InitialSolid version, compact authority/tail edits, materials, geometry revision and invalidation state |
| Resources | Ingredient inventories, carried food/crop, soil parcels and sources/sinks |
| Scheduler | Future queue, stable sequence and pending external commands |
| Random | Explicit algorithm/version and every stream state/counter |
| Authority | CommandId/payload hash/receipt ledger, committed revision/cursor |
| Analytics | Accumulators, time-window boundaries and durable cursor |

Save only at a committed boundary. Missing queue/RNG is not full restoration. S0/S1 test in-memory serialize/deserialize/continue using their implemented subset; database persistence is not required in S0.

## Durable phase

Application/Persistence writes checkpoint blob, corresponding event cursor, necessary command ledger, events and aggregates in one SQLite transaction, marking durability only after commit. Large separate files plus a generation manifest/recovery protocol are a future optimization. File rename and SQLite commit are not inherently atomic together.

Crash tests cover before save, during write, before/after transaction commit, invalid recovery and duplicate command receipt after execution. Restore only the last fully committed consistent generation.

| Candidate table | Key data / constraints |
|---|---|
| world_meta | world_id, seed, time, physics version; isolated worlds |
| checkpoints | world_id/revision unique, blob/hash/cursor in one transaction |
| committed_events | world_id/event_id unique, time/type/payload/source command |
| metrics | world/owner/metric/window/value/unit, versioned definitions |
| command_receipts | world/command ID, payload hash, status, applied revision |
| tracked_trajectories | world/entity/time/position/precision; frequent samples only for selected individuals |

GM separately stores identity, relationship memory, episodes, research goals, observation tasks and audit. It queries actual birth dates and inventory from world data rather than narrative memory.

## Define metrics first

| Metric | Definition | Unit |
|---|---|---|
| colony.worker_alive | Unique living Adult/Worker identities in the colony | individuals |
| colony.queen_alive | Living adult queens | individuals |
| colony.brood_egg/larva/pupa | Living identities at the named stage | individuals |
| colony.emerged_count | Deduplicated Pupa -> Adult facts within window | events |
| colony.death_count | Unique death facts within window | events |
| colony.food_collected_carb_ug | Carbohydrate actually acquired through valid collection | ug |
| colony.food_collected_protein_ug | Corresponding protein inflow | ug |
| colony.food_collected_water_ug | Actual acquired water, excluding unconsumed environmental water | ug |
| colony.food_consumed_carb_ug | Actual consumed/metabolized carbohydrate | ug |
| colony.trophallaxis_transfer_ug | Internal worker-to-worker transfer, not additional external intake | ug |
| colony.excavated_dry_soil_ug | Committed actual dry soil removal | ug |
| nest.volume_m3 | Void volume from authoritative geometry with declared numerical error | cubic meters |
| colony.foraging_success_rate | Successful completed trips returning usable food / defined completed trips | [0,1] |

Population is a snapshot gauge; life-event counts use windows. Define trip start/end before calculating success; being near food is insufficient. Every sample includes world time, owner and precision/definition version.

## Material accounting

Separate ingredients and sources/sinks:

`InitialFood + AuthorizedSpawn + Regeneration = RemainingFood + Carrying + Crop + Consumed/Metabolized + Discarded + OtherExplicitSinks`.

Internal trophallaxis is not counted again as colony intake. Energy joules cannot be added to micrograms; conversion and metabolic efficiency are explicit. Dry soil balance is initial/imported = remaining solid + carried + deposited + exported; water has its own account. Geometry integration error has a tested upper bound.

## Evidence, branching and storage budgets

Events contain world/time/entities/source/command/location/versions/payload. GM correlation, causal hypothesis and literary narration are separate commentary with event/metric references, never committed physical facts. Cross-world references include both IDs. Forked experimental worlds get a new WorldId with parent-world/revision lineage. After reverting to an earlier timeline, GM can retain shared memories but must distinguish the branch and not report future events as present facts.

Ordinary individuals retain basic records, work aggregates and major events. Tracked trajectories record precision and observed/interpolated status. Aggregate history by windows rather than permanently recording every individual every second. Measure checkpoint size, write/restore time, journal growth, compression and correctness; optimizations cannot silently erase required facts.
