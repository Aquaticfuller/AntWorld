# Open questions and experiments (historical v0.5 with v0.8 updates)

## Active scientific validation debt after S2.2 approval

Independent S2.2 Code Review passed and explicitly authorized S3. The historical stage restrictions below describe earlier gates, not the current authorization. Passing the engineering gate does not close these debts.

| ID | Status | Evidence and limitation | Closure requirement |
|---|---|---|---|
| SD-01 | OPEN | Mean initial continuous following is only 2.1035 straight / 2.0459 bend steps; every worker departs at least once within 24 moves. Local choice, occupancy and recovery effects do not establish reliable long-distance tracking. | A separately reviewed continuous-following protocol with appropriate controls, lengths, uncertainty and held-out conditions. |
| SD-02 | OPEN | Real-deposit single-scout recruitment remains unproven: fresh naive discovery difference +2.34375 percentage points, 95% paired interval [-8.59375, 12.5]. Local mechanism validity is not evidence of a significant colony recruitment benefit. | Dedicated social recruitment experiments separating route direction, geometry, trail age and encounter conditions; retain negative results. |
| SD-03 | OPEN / permanent constraint | No global food knowledge, directed chemical arrows, selected seeds or uncalibrated coefficient tuning may conceal SD-01/02. Every uncalibrated biological number remains ENGINEERING_FIXTURE. | Enforce in each future model review; evidence-based changes require a recorded hypothesis and frozen protocol. |

Evidence: S2_2_RESULTS.md, documents 29/30 and the unchanged experiments/s2_2 archive. S3 introduces no pheromone or route-choice coefficient changes. These debts remain visible for the next independent review and are not S3 blockers under the user's explicit decision.

## S3 implementation and scientific debt

S3 independent review: CONDITIONAL PASS, with explicit permission to start S4. **SD-04 must be experimentally validated no later than S6**, using local demand sensitivity and surplus recirculation, never global nutrition averaging. **TD-01 must be resolved before S6 scale testing**; S4 must provide a general neighborhood-query boundary suitable for an index rather than bake a full-population scan into each behavior.

**TD-02: 3D contact through solid barriers — mandatory S4 gate.** Euclidean distance alone cannot qualify underground trophallaxis, local sensing or material collection. Once true cavities are enabled, production actions and historical validation must use the authoritative geometry at the applicable revision/time. Test nearby individuals separated by a solid wall, real openings, refilled barriers and pending interactions invalidated before commit. A top-view crossing is not an opening. Status: OPEN pending S4 evidence.

| ID | Status | Evidence / next review question |
|---|---|---|
| SD-04 | OPEN | S3 development seed 43 at 1000 ms pulses yields three adults and one larva at 180 s despite 800 ug initial protein for four 100 ug requirements. Three recipients each retain 140 ug unused crop protein; the fourth receives only 80 ug. Concurrent local gifts can oversupply individuals; minimal programs do not redistribute surplus from emerged workers. Preserve this negative outcome. Study demand-aware portions and adult redistribution under a separately specified protocol without selecting seeds or tuning to force emergence. |
| TD-01 | OPEN | The S3 reference contact query filters actual distance/colony/stage but scans registered physiology rows. Per-individual integration is inexpensive; dense active nursing has quadratic query cost. Add a validated contact index before larger active populations, preserving local inputs and proposal-order independence. No full-world throughput claim. |
| SD-05 | OPEN | Absorption is pulsed; development uses fixed fixture durations gated by reserves and retained protein. Temperature, measured assimilation efficiency, body growth chemistry, liquid/solid food distinctions, laying, tissue maintenance and species mortality hazards remain uncalibrated or unimplemented. Integer exactness validates this declared model, not biological accuracy. |

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

## S2.1 recruitment validation

Document 28 records the protocol and evidence-led fixes: unbiased equal-food ties and fractional trail response precision. Actual loaded returns create contiguous locally visible traces, but the fixed 64-seed, two-orientation naive-worker experiment does not demonstrate a reliable discovery advantage. Fresh and three-minute-old effects have opposite signs with intervals including zero. Directionless signal, bounded/persistent exploration, decay and the single-scout short-window fixture remain distinct possible explanations; these experiments do not identify one as the sole cause. Do not tune coefficients or add recruitment rules without a separately reviewed question and protocol. S2_1_RESULTS.md retains the negative findings and the original ablations. S3 remains unauthorized.
