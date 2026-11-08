# C++ Simulation Core data contracts (v0.8)

Normative conceptual draft: units, identities, ownership and minimum semantics. These are contracts, not evidence that all P0 types are implemented. Except confirmed product requirements, details are reference defaults changeable through ADRs.

## Units and identity

| Object | Type / rule |
|---|---|
| SimTime | Strong int64 milliseconds; timestamp resolution, not traversal frequency |
| WorldId | Two uint64 words; globally unique across worlds |
| EntityId | Typed uint64, monotonically allocated and never reused; brood/worker share lifetime identity |
| ColonyId/ResourceId/RegionId | Typed world-local uint64; serialized references carry WorldId |
| EventId | Monotonic local fact identity, assigned only to committed events |
| CommandId | External 128-bit identity for idempotency/audit, distinct from event ID |
| Coordinates/length | Double meters; X east, Y up, Z north; underground usually Y < 0 |
| Conserved mass | Explicit integer micrograms, normally int64 ledgers with nonnegative stocks/flows and checked overflow |
| Body energy | Double joules; explicit mass-to-energy conversion |
| Temperature | Celsius; convert to kelvin when absolute temperature is required |
| Duration | int64 ms, converted to seconds for power integration |
| Probability | Double in [0,1], reject invalid input |

EntityRef contains WorldId, EntityId and EntityKind. A display label such as A-017 is not a primary key. Internal dense storage slots may move; persistent IDs do not.

## Sole world owner

WorldRuntime exclusively owns WorldState: identity/seed/schema/physics version; clock/revision/phase/sequence; entity stores; InitialSolid/ordered edits/derived cache revisions; actual resources and fields; future events, proposals, command inbox and idempotency ledger; RNG; metric accumulators and journal cursor.

Only the validated commit path mutates state. Queries neither advance time nor consume RNG or schedule biology. S0 implements only its own authoritative subset; later stores are introduced by their stage.

## Ant components

Use SoA where useful with stable-ID to dense-slot mapping. Brood may share AntStore with specialized components, never duplicate its identity in two stores.

| Component | Candidate fields | Constraint |
|---|---|---|
| Identity | entityId, colonyId, speciesId, caste, birthTick | Lifetime identity; seeded=true for creation-time individuals |
| Life | stage, stageProgress, alive, developmentVersion, deathCause | Ordered development; Dead terminal and idempotent |
| Physiology | bodyEnergyJ, hydrationUg, health, injury, cropCarbUg, cropWaterUg, carriedResourceId | Dimensioned values; energy differs from food mass |
| Spatial | positionM, orientation, regionId, currentPortal, pathRef | Reachable authoritative space; stationary brood still occupies legal positions |
| Behavior | highLevelTask, actionState, targetEntity, taskEnteredTick, cooldownUntil, responseThresholdsRef | Tasks compose actions |
| Perception | localCues, sampleTick, sensoryBudget | Local information only, no global food oracle |
| Memory | Limited route/cue associations, strength, reinforcement time | Bounded model memory, separate from historical database |
| Scheduler | simLod, nextWakeupTick, plannedEventIds | Precision changes retain biological identity |

Lifecycle is Egg -> Larva -> Pupa -> Adult -> Dead. Queen/Worker/Male caste is separate. Death can occur at any stage; emergence never creates a replacement AntId. P0 may initially seed worker/queen/brood and defer mating flights or multi-queen rules without changing the identity contract.

## Colony and resources

ColonyStore holds colony/species IDs, founding time, queen IDs, nest IDs, recognition cues, physical storage references and derived brood demand. Population/task ratios/reserves are aggregated facts, not freely settable counters. No AssignWorkersToTask(n) central-command API.

FoodSource contains resourceId, positionM, totalMassUg, carbsUg, proteinUg, waterUg, otherMassUg, decayState, foodKind and optional owner. Components sum to total mass; transferring food updates the same underlying material once. Crop contents are individual-owned inventory, not simultaneously a second colony pool. Carried solid food is a separate parcel.

SoilParcel contains parcelId, sourceEditId, dryMassUg, waterMassUg, optional carrier, location and transport/deposition state. Its provenance is an actual removed material intersection. Food and soil cannot silently convert into each other.

## Geometry

InitialSolid + ordered GeometryEditLog is authoritative. A committed GeometryEdit carries editId/worldId, Excavate/Fill kind, primitive/parameters, actor, SimTime, expected/committed revision, affected AABB and dry/water deltas. An uncommitted DigProposal does not modify geometry.

SDF, navigation, collision proxies and meshes carry source revision and invalidation state. Projected crossings need an actual clearance-qualified opening. Backfill can delete connectivity. See documents 10 and 11.

## Proposals and facts

ActionProposal carries proposalId, actorId, actionKind, optional target, proposedAt, requested quantities, prerequisite revision, local evidence and region. Candidate actions include Move, Explore, FollowTrail, CollectFood, ReturnNest, Trophallaxis, FeedBrood, Rest, Excavate, PickUpSoil and DropSoil. Add them only in the authorized stage.

WorldEvent carries eventId, worldId, SimTime, type, actor/related entities, optional target resource/position, world and optional geometry revision, origin (Natural/Player/GameMaster/ScenarioSeed), optional commandId, payload and evidence references. Only actual commits produce facts. GM interpretation remains separate commentary, never authoritative ecology.

## Runtime and ownership

Conceptual operations: advance_to(target) returns reached time/revision; enqueue_command returns accepted/pending/rejected; acquire_snapshot returns an immutable owned view or detached copy; read_committed_events takes a cursor and limit. Reject backwards time. An accepted command becomes a success claim only after its fact commit.

No mutable internal store pointer escapes. Snapshot lifetimes are explicit through owned copies, reference-counted handles or caller buffers. Unity consumes published state; GM accepts only typed queries/commands, never injected code. Cross-world resolution always includes WorldId. GM real-time metadata is separate from simulation time.

## Version changes

Schema changes require migration or explicit rejection. Biological parameters carry modelVersion and a source label (ENGINEERING_FIXTURE or genuinely LITERATURE_CALIBRATED). Behavior changes cannot silently reinterpret old saves; physicsVersion identifies them. Define byte order, integer width and field order. No STL or C++ exceptions across the C ABI. The S0 concrete encoding and diagnostic-event subset are documented separately in 25.
