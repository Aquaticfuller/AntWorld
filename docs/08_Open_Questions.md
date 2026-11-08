# Open questions and experiments (historical v0.5 with v0.8 updates)

## Biological research

1. Unified task thresholds or separate brood/cleaning/digging schedulers? How to prevent excessive switching?
2. Which brood movement, grooming and digging mechanisms have direct L. niger evidence, and which are cross-species hypotheses?
3. How can limited local memory/senses find better brood microclimates without global knowledge?
4. Should room-use labels be purely derived? The proposed answer is yes, for observation/UI only.
5. How does a small soil removal become a carried/deposited parcel while clearance and collision stay consistent?
6. Which studies match the initial species, temperatures, humidity and colony size closely enough for calibration?

## Engineering experiments

7. C ABI layouts, batch snapshots, ownership, threading and Unity interchange.
8. Parametric geometry plus sparse SDF, dynamic mesh and collision update performance.
9. Event-based distant motion and LOD statistical consistency.
10. Actual benchmark hardware, platform and long-term save/storage budgets.
11. Candidate 2 meter chunks versus hierarchical regions and finer local chunks.
12. Minimal trophallaxis, brood care and inactivity with credible statistics.
13. SQLite versus alternatives, aggregation, log retention and checkpoint policy.
14. Equivalent task comparison of Python/Hermes, C#/Microsoft Agent Framework and a small harness.
15. Speech recognition/synthesis, echo handling, interruption and API cost.

## Later player-experience choices

16. GM name, initial personality, voice and visual presence.
17. Detailed ecological species/predators, difficulty and observation/experimental presets.
18. Food/water/weather preauthorization quotas and confirmation for major tools.
19. Deep-tracking counts, notification frequency, history retention and archival policy.
20. Background ecology and history continuity as the world expands.

## Do not assume

Full ecology does not imply equal per-individual precision for every insect. Personality does not establish subjective consciousness. AI does not authorize LLM-directed workers. Other species' brood-induced digging does not prove L. niger physiology. Proposed numbers are not calibrated facts.

## Underground questions

The earlier question 21 comparing parametric authority with occupancy authority is resolved: option A, ordered parametric edits with local SDF cache, is selected.

Remaining questions: active-front candidate 1-2 mm precision; clearance and incremental chamber formation without blueprints or unusable fragments; evidence distinguishing deposition, removal and backfill; conservative geometry constraints versus early soil mechanics; soil heat/water versus air exchange and flooding; stale navigation prevention; obtaining restricted L. niger soil-column CT, temperature and excavation data.

Specific experiments must choose bounded excavation shapes/work quantities; robust sweep/blob primitives; overlap-volume error and recovery; body/loaded clearance at narrow curved boundaries and chunk seams; Marching Cubes versus Dual Contouring for thin walls/seams/normals; compaction and lineage; material/water behavior during fill; ABI ownership and asynchronous recovery.

## Scheduling and persistence

Fix time precision/range, phase ordering and fair tie keys. Determine which behaviors are event-based versus batch sensing and how contact is detected before precision transitions. Locate energy/development/death thresholds within long integration intervals. Quantify L0-L2 error and cross-boundary interactions. Validate atomic checkpoints, cursors, idempotency and RNG replay, including same-time resource competition without permanent low-ID advantage.

One-millisecond timestamps and a 32-worker fixture are engineering choices, not biological measurements. The older vertical-slice stage numbering is superseded by document 22.

## v0.8: S0 defaults and later gates

Reversible S0 defaults are C++20/CMake/CTest, strong int64 millisecond time, single-writer commits, 128-bit WorldId, uint64 local IDs and in-memory checkpoint round trips (document 16). S0 must implement and test RNG/versioned vectors, phase keys, checkpoint codec and zero-time protection. The C ABI draft remains later-stage work.

S1 handles conflicts; S2 local senses/trails; S3 physiology/development; S4 geometry; S5 durable persistence; S7 Unity; S8 harness comparison; S9 LOD and full-map pressure. These later research decisions do not block S0. Unknown biological numbers must remain ENGINEERING_FIXTURE until properly calibrated.

## S2 implementation review items

S0/S1 have passed review; S2 implementation/evidence is recorded in document 27 and S2_RESULTS.md. Current local behavior uses a static surface and bounded experienced routes. The 128-run feature matrix shows route-memory reuse but no standalone trail-only delivery improvement on average. Chemical directionality, realistic recruitment, memory calibration and dynamic route invalidation remain research or later-stage questions, not established biological facts. The S2 report documents these limitations without changing the fixed seeds or parameters after observing the final matrix. No S3 implementation is authorized by these findings.
