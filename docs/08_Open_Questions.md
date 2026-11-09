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

**TD-02: 3D contact through solid barriers — mandatory S4 gate.** Implemented and covered by S4_CONTACT, S4_SURFACE_BARRIER, S4_CONNECTIVITY and S4_FILL_NAVIGATION, accepted in the conditional S4 review. Geometry-enabled contacts, food/nest access, sensing and motion use authoritative solid barriers; historical validation uses the geometry at the fact's time. Tests cover nearby individuals separated by a wall, actual excavation of an opening, refilling, and pending interactions invalidated before commit. The conservative contact envelope has a minimum half extent of one coordinate quantum; it may reject a physically possible narrow/diagonal contact. No point ray may silently bypass this constraint.

| ID | Status | Evidence / next review question |
|---|---|---|
| SD-04 | PARTIALLY ADDRESSED in S6; integrated redistribution remains OPEN | The original S3 seed-43 failure remains in every legacy regression and the matched S6 egg-initialized control (three adults / one larva). Commit-time ingredient deficit caps prevent concurrent protein oversupply; the new policy yields four adults in that matched case. Complete 64-seed nutrition matrices and adult/pupa-origin surplus assays validate actual local transfer with wall/range/no-response/no-protein controls. However, integrated supplied seed 7 still leaves seven brood without emergence and 1,549 ug crop protein stranded at death. Some enrolled nurses repeatedly withdraw nest stock, then switch to foraging with surplus instead of feeding contacted brood; their travel ownership delays further local exchange. Study local refill/gift priority and demand-sensitive task persistence under a new frozen comparison, without global averaging or forcing growth. Exact deficit sensing/selective liquid composition, later larval carbohydrate/water requests, inaccessible donors and biological provisioning also remain unvalidated. |
| TD-01 | BOUNDED CONTACT WORK VALIDATED in S6; empirical latency budget OPEN | Before integrated scale runs, a derived rank-select spatial index and capped encounters replaced per-nurse dense enumeration in the opt-in S6 policy. Each decision examines at most 16 candidates by default (8/32 sensitivity), with exact distance/soil qualification and deterministic rollback/restore. All 120 first timing samples remain: dense 2,048-worker p50 is about 30x faster, but 512->2,048 growth is 7.518x, missing the <=6x target. The separate final 120-sample matrix gives 28.176x speedup but 6.876x growth, again FAIL for that target. Candidate work no longer grows with bucket population; allocator, map/tree, scheduler, geometry, setup/enrollment and history costs remain. Legacy fixtures retain their exhaustive policy for regression; observer all-neighbor queries remain exhaustive. Do not claim a universal 2,048-worker real-time or S9-scale capability. |
| SD-05 | OPEN | Absorption is pulsed; development uses fixed fixture durations gated by reserves and retained protein. Temperature, measured assimilation efficiency, body growth chemistry, liquid/solid food distinctions, laying, tissue maintenance and species mortality hazards remain uncalibrated or unimplemented. Integer exactness validates this declared model, not biological accuracy. |

## S4 geometry implementation debt

S4 independent Code Review: CONDITIONAL PASS, with explicit S5 authorization. TD-02's implemented barrier checks passed this review; its conservative-envelope limitation remains. The following debts are not closed by this approval.

| ID | Status | Evidence / next review question |
|---|---|---|
| TD-03 | PARTIALLY ADDRESSED in S5; general history remains OPEN | Required 1,000/5,000/10,000-edit size/write/restore/memory matrix completed (10 repetitions, repeated and interleaved patches). A derived identical-box index reduces the matched 1,000-edit S4 restore median from 131.057 to 2.899 ms; every authoritative edit and fact remains. The new 10,000-edit fixture restores core state in 31.969/34.843 ms and validated durable state in 160.148/161.730 ms. First saves still cost 930.002/906.757 ms; exact checkpoints are 3,456,572 bytes. This is not general compaction: distinct-shape histories, full journal retention and synchronous save latency still grow. See S5_RESULTS.md and complete raw timing/size/memory evidence. |
| TD-04 | OPEN | S4 uses axis-aligned boxes on a 0.5 mm fixture quantum, cubic body/load/reach envelopes and bounded six-neighbor 3D navigation. Local portals carry source revisions, but persistent chamber/portal semantic identity and lineage are not implemented. Curved tools, orientation-dependent clearance, heterogeneous soil, compaction ratios, granular piles, collapse, climate and meshes remain future work under their respective gates. |
| SD-06 | OPEN | The excavation loop chooses local frontiers/steps and returns along experienced traces to a known depot. It establishes actual removal and transport under a declared fixture, not a calibrated Lasius niger nest-building model. No global blueprint, food coordinates, climate mechanism or pheromone retuning was introduced. S2 long-distance following/recruitment and S3 nutrition redistribution remain open. |
| TD-05 | OPEN; S7 Geometry Dirty API | Resident SDF-cache invalidation is not a complete geometry-change stream. S7 requires a separate versioned geometry notification interface with changed bounds, source versions and cursor/gap semantics, including edits where no cache brick exists. |

SD-06 closure requires separately reviewed biological validation of colony demand, brood, temperature/moisture and spatial chamber organization. TD-04's boxes and six-axis paths do not establish realistic nest morphology; complex tunnels, chambers, pile collisions and semantic region identity remain later work. TD-01's dense co-location cost remains due before S6 scale tests.

S4 evidence: S4_RESULTS.md and experiments/s4. All S0-S3 reports and raw archives remain unchanged. The S3 1,536-run matrix was rerun under physics 7 and matches every original biological metric (including seed 43), excluding the intentional version label.

## S5 storage and analytics debt

S5 independent Code Review returned CONDITIONAL PASS with explicit S6 authorization. This does not close the scientific or scale debts. Document 33 was frozen before changes. The core remains storage-independent and physics stays 7. All 89 inherited tests and earlier raw archives remain. The complete S3 matrix still retains seed 43's failed fourth emergence; the S5 seed-1..32 persistence subset does not close SD-04.

| ID | Status | Evidence / next review question |
|---|---|---|
| TD-06 | OPEN; long-term storage budgets | Two complete checkpoint generations are retained by default, but factual events, raw observations and exact flow/bucket evidence are retained without pruning and the core still holds its full journal. At 36,502 diagnostic facts the database + WAL + SHM is 69,700,800 bytes. Define evidence-preserving archival/rollup, application save cadence and measured month-scale ecological memory budgets before claiming indefinite low-memory operation. Do not delete history or silently substitute aggregates for facts. |
| TD-07 | OPEN; broader durability/platform validation | Process termination, partial WAL writes and injected write/sync failures pass. Physical power cuts, faulty device caches, network filesystems, background save orchestration and authenticated archives are not tested/implemented. SQLite FULL relies on synchronization being honored; use local same-host WAL storage. FNV hashes are accidental-corruption checks only. Older checkpoint-schema migration remains explicit future work. |

S5 indexed time queries fix the measured current-day history scan (day 365: 15.699 to 0.378 ms); both raw runs remain. This does not resolve TD-01 dense contacts, TD-04 shape/semantic-region limits or TD-05's S7 versioned geometry notification API. SD-04 remains due by S6, TD-01 before S6 scale tests, and SD-06 requires separately reviewed nesting biology. No coefficients, global information or directional chemical cues were added.

## S6 entry gate and retained debts

Document 35 is frozen before implementation. SD-04 local demand-sensitive exchange and surplus redistribution must be researched and validated first, without global averaging. TD-01 requires measured candidate/scheduling optimization before S6 scale experiments; a spatial index alone is insufficient at dense co-location. Preserve TD-03/06 synchronous ~0.9 s saves at 10,000 edits and growing full history: later non-blocking persistence, archival and memory budgets may not delete facts to manufacture speed. SD-01/02/06 remain open scientific limits on long-distance trails, social recruitment and realistic nesting. The integrated loop is an ENGINEERING_FIXTURE and may decline or die; it must not guarantee growth by changing rates or adding unsourced nutrients. All 108 tests and S5 raw data remain immutable evidence. S7-S9 remain unauthorized.

S6 mechanism evidence and definitions are in documents 35/36, S6_RESULTS.md and `experiments/s6`. The new policy is explicit and versioned; legacy behavior is preserved. Automatic individual Rest/Nurse/Forage/Excavate choices use own reserves/cargo, bounded contacts, physical depot stock and locally reachable soil. Travel must return through actual space before routine switching. Brood enrollment wakes the same identity after emergence, and death cancels its owned work. The integrated finite-resource protocol measures decline as well as development; it does not add laying, replenish nutrients or alter physiological rates to keep the colony alive. Planar foraging plus 3D excavation is a documented mixed-space approximation, not unrestricted 3D food navigation.

TD-03/06 remain open: integrated saves still serialize and synchronously validate the complete retained history; every factual record remains. Two checkpoint generations do not bound the event journal or SQLite observations. S6's 1,800 s depletion continuation is not month-scale ecological/storage validation. SD-01/02/06 are unchanged by coupling the mechanisms: approximately two initial following steps, unproven long-distance social recruitment and uncalibrated box-shaped nest organization remain explicit limitations. S7 requires a new user review decision.

S6 retains 95.1-116.0 MB of database/WAL/SHM per primary case (58,894-71,640 facts); extended cases still retain full evidence after all individuals die. SD-06 remains especially limited: paired excavated volumes are identical across the three open nutrition conditions, with no autonomous fills in the matrix. Local crowding and soil access create actual edits but do not establish colony-demand-sensitive spatial organization. All 320 cases / 960 execution replicas reconcile; their negative ecology does not become a biological pass because the ledgers balance.

## S6.1 correction review debt

S6 received CONDITIONAL PASS but S7 was explicitly withheld. Document 37 was frozen at `03ae833` before diagnostics or corrections. Complete original seed-7 replay establishes repeated nest intake before gifts and departures despite actual sampled need. Two false-by-default flags independently test gift priority and current compatible-work continuation. No behavioral weight, physiological rate, food oracle, global nutrient allocation or rescue supply is added. The source and original raw archives remain evidence; local correctness alone is not biological calibration.

**TD-01 remains OPEN / failed acceptance target.** The final frozen 120-sample matrix preserves every candidate, exact spatial check, event and transaction. Dense 2,048 matched speedup is 39.682x and maximum candidates is 16, but bounded 512->2,048 p50 growth is **24.229x**, failing <=6x. Profile-guided child-node references remove repeated map lookups without changing canonical states or work counts. All before/after samples remain, including substantial unresolved host/context variability. No frequency/thermal telemetry was recorded during those runs, so a specific external cause cannot be asserted. A separately reviewable balanced/interleaved timing protocol and telemetry are proposed in S6_1_RESULTS.md; no replacement threshold has been adopted. Do not claim TD-01 closed or S9-scale readiness.

**SD-04 improves in the reviewed supplied fixture but remains OPEN.** All 1,216 S6.1 observer cases and 272 durable cases reconcile. In 32 paired integrated seeds with both mirrors, mean unmet protein exposure falls from 55,121.41 to 15,066.69 ug*s; the paired difference is -40,054.72 [-64,890.47,-19,827.33], 95% seed-bootstrap interval. Mean emergence increases from 11.4375 to 12, and reviewed seed 7 from 5 to 12, with real additional transfers and unchanged introduced nutrients. Scarcity counterexamples prevent general closure: at 8 workers / 500 ug, emergence decreases by 0.5 [-0.8125,-0.1875] despite increased transfer; at 128 / 500 ug, unmet exposure increases by 2,374.19 [1,759.20,2,998.16] ug*s. Post-hoc endpoints support a distribution-versus-completion-threshold tradeoff in the former; the dense-scarcity interaction remains incompletely diagnosed. No corrective rule or default was fitted to those outcomes. Precise nutrient-deficit sensing, selective gift composition, local cue biology and recycling dead/inaccessible inventory remain engineering approximations. All extended cases die by 1,800 s; improved emergence is not improved survival or calibrated colony fitness.

**SD-07: activity and task-state calibration remains OPEN.** Active task ownership is currently Nurse/Forage/Excavate program residence; it is not a measured continuous locomotion/work fraction. S6.1 supplied initial adults remain 97.5901% active, spend 95.6761% of living time away from the depot, and have 96.2299% of reconsiderations blocked by travel/cargo ownership. The paired activity change from legacy is +0.0076 [-0.0313,+0.0463] percentage points. Open no-food cases remain about 97.70% active; sealed cases are 0%. Travel ownership, minimum duration, weighted choices and metabolic costs are engineering rules, with no calibrated inactivity quota, fatigue rate or biological daily schedule. A future activity-budget change needs its own hypothesis and protocol, not coefficient tuning to produce a preferred percentage.

SD-06 still distinguishes actual local excavation from biologically organized nesting. All 64 S6.1 seed/mirror pairs have identical excavation across three open resource conditions in both policies, with zero autonomous fills. First digging precedes food delivery, but last digging occurs at 37.779-321.829 s, after the 13.808 s delivery: an early common stimulus alone is insufficient explanation. Crowding, nearby soil, initial reserves and task ownership operate without chamber demand, brood microclimate or measured construction/maintenance feedback. Actual energy feasibility does not establish nutrition-sensitive architecture. TD-03/06 retain synchronous full-history saving, growing raw memory/storage and the absence of evidence-preserving background archival. TD-04/05 geometry expressiveness and the later versioned Geometry Dirty API remain open. SD-01/02 long-distance following and genuine recruitment remain unchanged. S6.1 cannot authorize S7 by itself.

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
