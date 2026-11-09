# S6.3 implementation and metric definitions

Authoritative protocols: frozen documents 41 and 42. No change to their numerical ecological inputs. All biological constants and response rules remain ENGINEERING_FIXTURE. This document explains the implementation, not a new survival target.

## Authority, provenance and versions

Long-term worlds opt in before physiology. Existing worlds retain checkpoint schema 8 / physics 9 and the original canonical bytes. S6.3 uses schema 9 / physics 11. The unreleased initial 9/10 prototype is intentionally rejected by the corrected reader; its negative data and source commit f04ef77 remain available. Numerical byte formats, fixed 159-byte facts and SplitMix64 v1 remain explicit. All configuration, maternal identities, resource reserves, owned wakes and integer remainders are checkpointed. Derived caches are rebuilt rather than serialized.

Queen reproduction checks only that queen's actual crop protein, body energy, body hydration, life state and physical clearance. One successful attempt atomically debits her, allocates an egg identity, establishes its funded physiology and enrolls its future autonomous worker program. Eggs/pupae do not feed. The existing stage integrator grants development only after actual tissue requirements, positive energy and water. Larval carbohydrate/water need remains locally signaled after its protein requirement has been met. There is no new fixed lifespan or hidden maternal input.

`PhysiologyState.initial` describes the individual's starting compartments. If `mother` is nonzero, these are an internal birth transfer, not external input. The parent's `exported_energy_nj` reconciles her individual energy balance; the child's energy is counted once in the world ledger. Parent reproductive expenditure is separately dissipated. Dead bodies, crops, tissue, water and energy remain retained inventories. Corpse nutrient recovery, structural-protein remobilization and queen-only claustral brood care are not implemented.

Food-cycle input is a finite reserve explicitly introduced at setup. Accessible stock plus remaining reserve plus all actual collection/consumption/sinks must equal this source. Release moves material from reserve to the same stable FoodSource. Its exogenous periodic productivity is an availability fixture, not measured climate or weather simulation. No environmental rule reads ant demand or population. Soil water stays in the soil-material ledger; it is not silently converted to drinkable nutrition.

Local task selection uses bounded reachable contact samples, self state, actual depot contact and bounded reachable geometry. The space proxy counts accessible quantum sites inside the existing reach radius and stops once the local sufficiency threshold is met. It is neither packing volume nor real chamber identity. A completed depot visit schedules a recovery decision for that same ant. After a successful nursing intake, one short follow-up permits a real encounter before the next coarse metabolism pulse; it does not force a recipient or repeat an unbounded intake loop. Capacity, ingredient demand, contact, barriers, mortality and transaction checks still apply at resolution. These rules are physiological/behavioral hypotheses, not Lasius niger calibration.

## Event fields and accounting

The C++ physiology numerator is named `water_loss_ug_per_period`; `water_loss_period` supplies its exact millisecond denominator (1000 ms in legacy configurations). This source-level name replaces the earlier per-second member to avoid falsely labeling a per-hour fixture rate. The legacy codec slot, value, arithmetic and old JSON experiment labels are unchanged. C ABI integration remains outside scope.

The existing fixed fact payload is extended by new kind tags. `AntBorn.actor` is the new identity; `payload` is its mother; `transferred.protein_ug` and `transferred.water_ug` are funded tissue and body water; the legacy `random_value` slot contains the funded nanojoules for this kind, not an RNG draw. `ReproductionAttempt.actor` is the queen and `payload` is the created ID or zero for a funding shortfall. A successful attempt and its auxiliary birth share one actual scheduled source; only the attempt increments the executed-event count.

`ResourceCycleConfigured.transferred` is the finite reserve input. `ResourceReleased.transferred` is the actual released quantity and `payload` is productivity in permille. `ProteinRecycled` is a real donor crop-to-depot transfer. No attempted action is counted as a successful gift. For long-term intake resolution, `NestIngested`/rejected intake may use `random_value` for an additional bounded contact sample count, matching the existing nutrition-decision work convention. Restore checks these counts and real transfer evidence. All source facts remain retained.

The analytics registry appends nine IDs; existing IDs and per-definition version 1 are unchanged:

| Metric | Kind | Unit | Definition |
|---|---|---|---|
| life.born | flow | events | Actual funded AntBorn events, excluding seeded identities |
| nutrition.recycled_protein | flow | ug | Actual worker crop protein returned at the depot |
| environment.released_carbs/protein/water | flow | ug | Finite reserve-to-source transfers, not external intake |
| environment.reserve_carbs/protein/water/other | gauge | ug | Inaccessible finite world reserve remaining |

SQLite stores both mother and child as participants in a birth. `IndividualRecord.seeded` derives from the creation fact; it is false for births. The 60 pre-existing metrics retain their original definitions and old-world observation hashes. The world energy dissipation total in long-term worlds additionally contains the explicitly recorded reproductive cost. The new metrics and raw history reconcile with the authoritative checkpoint on durable recovery.

## TD-08 mechanisms and measurement scope

Initial S6.2 registration repeatedly computed the whole nutrition snapshot and scanned all configured physiology to validate an arithmetic upper bound. S6.3 caches the conservative external-input mass, initial energy and maximum carbohydrate yield in transaction metadata. Commit updates are checked, rollback restores them, and restore derives them from validated inputs. No scientific parameter or old trace changes.

A second measured bottleneck occurs during birth when unrelated Resolution events are pending. `change_autonomy` scanned the whole future queue once per newborn. The pre-index controlled fixture uses N queens plus N pre-existing workers with real pending Move proposals at 100 ms, then N actual funded births at 10 ms. N = 128/512/2048 is the number of births/queens; initial and final ant counts are 2N and 3N. This is an ENGINEERING_FIXTURE for registration, not a biological multi-queen colony claim. At 512/2048 its fixed event counts are 3587/14339 and pending counts 2048/8192. The first recorded baseline samples show a large quadratic growth risk. Preserve all measured batches before and after optimization.

Long-term worlds now keep per-individual counts of pending forced development and Resolution events, with undo-journal updates on insertion/removal. Owned action IDs distinguish legitimate program work from external conflicts in constant-count lookups. The index is also built when opting into a world with existing pending work and rebuilt on restore. Legacy worlds keep their unchanged queue behavior, with cheap zero-count guards. This avoids imposing a new index cost on the accepted TD-01 fixture. A restored or canceled command must not disappear from conflict validation.

Report setup, actual birth advance, checkpoint encoding and restore independently. Include process CPU/cycles, affinity, telemetry, memory, raw event/state hashes, p50/p95/p99 and block-paired uncertainty. The earlier stationary 512/2048 worker contact test remains a separate <=6x gate. The proposed <=6x registration/birth target in document 41 is not permission to relax TD-01. Profiled runs attribute costs but are not acceptance timing runs.

## Raw experiment interpretation

Each run retains daily population/resource/energy/soil snapshots, individual daily states, selected readable life/transfer events and the complete fixed-record fact stream. Event IDs and trace hashes allow independent reconstruction. Daily unmet-demand exposure computed from these observations is a sampled trapezoidal estimate, not exact continuous integration; individual transfer amounts and timestamps are actual facts. Activity durations integrate committed program transitions over living adult-worker time and are not measured walking/working minutes. Child emergence is cumulative; terminal identity remains in death inventories.

Capacity-censored runs retain their last completely committed day and every preceding fact. They are not extinction observations and cannot be substituted into 90-day success denominators. Runtime/encoding/RSS columns in ecology matrices are descriptive host observations, not isolated microbenchmark acceptance data. Dedicated controlled benchmark batches provide the scaling conclusions. Scientific limitations and verdicts belong in S6_3_RESULTS.md and document 08.
