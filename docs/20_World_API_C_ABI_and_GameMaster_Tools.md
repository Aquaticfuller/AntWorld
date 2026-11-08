# World API, C ABI and Game Master tools (v0.8)

Player and GM capability sets match; autonomous permissions depend on context. One simulation writer remains authoritative. Document 11 supplies geometry packet details.

## Layers and native contract

Unity and GM submit Query/Command/ViewControl to World Application plus authorization; validated ecological mutations enter C++. Immutable snapshots, committed events and metrics flow out. P0 can run entirely through a typed C++ headless runner. Unity later uses batched C ABI/PInvoke rather than per-ant calls; GM uses application tools, not native pointers.

Only core commit establishes success. A command accepted into the inbox is not proof that food was placed.

The ../contracts/antworld_c_api_v1.h file is a draft, not a compiled plugin. It specifies export/calling convention, fixed-width result codes, WorldId/CreateDesc, opaque world/snapshot handles, create/destroy/advance, and acquire/copy_ants/release. Structures include struct_size/api_version. Query required capacity then copy into caller-owned buffers. Changes need versioning or compatible tail extensions.

Do not pass STL, C++ exceptions, ambiguous ownership or compiler-dependent bool across the ABI. Matching library functions destroy handles; clients own copy buffers. Access after release is invalid. Actual integration begins later, not S0.

## Tool groups

| Group | Examples | World mutation / autonomous use |
|---|---|---|
| WorldQuery | GetWorldState, FindEntity, GetAnt, GetColony | Read-only, normally permitted |
| AnalyticsQuery | QueryMetrics, CompareColonies, GetHistory, GetSoilLedger | Read-only, normally permitted |
| ViewCommand | FocusCamera, FollowAnt, SetSectionPlane, ShowHeatmap | Presentation only, avoid interruption |
| ObservationCommand | WatchAnt, CreateObservationTask, GenerateReport | No ecological change; frequency/budget limits |
| WorldMutation | PlaceFood, ScheduleWeather, AddWater, permitted terrain | Explicit player request or preauthorization |
| LifecycleControl | Time scale, pause, save, world switch | Authorized operational effects |
| Destructive | DeleteWorld, OverwriteSave, MassDisaster | Explicit confirmation |

Ordinary ecology tools do not include SetAntThought, ForceBuildRoom, SetPopulation or TeleportAnt. Environmental interventions have valid material/provenance and consequences from the engine.

## Command envelope

Fields include command_id, world_id, origin (for example player_direct_via_gm), authorization_ref, operation, requested_at_sim_ms, optional expected_world_revision and typed arguments. A food request might specify kind, mass_ug and position_m. The envelope is an application protocol example, not a raw string embedded in every C ABI call.

Same command ID plus same payload returns the previous result; changed payload conflicts. Receipts identify accepted/pending/committed/rejected, command ID, optional applied revision and event IDs, and reason.

## Observation and presentation

Committed events/metric windows -> cheap observers -> ranked candidates -> permission/relevance filter -> GM -> evidence-backed queries/commentary or authorized commands. Factual statements reference existing world/event IDs or metric windows. Correlation does not establish competition or another specific cause. Persist identity independently of model/harness. Model failures never block the core or duplicate a committed mutation.

One writer publishes immutable snapshots; Unity main thread applies scene/UI/mesh changes. Background work may prepare data but cannot call main-thread-only APIs. Dirty/mesh packets carry geometry revision; discard stale packets. Interpolation/camera movement cannot modify physics or RNG.

ABI validation covers struct size/offset, UTF-8, ownership, two-phase capacity, null/invalid handles, repeated release policy and 32/64-bit boundaries. Harness selection remains open: first test typed World API using a minimal fake Agent, then compare full Python/Hermes or C# options independently.
