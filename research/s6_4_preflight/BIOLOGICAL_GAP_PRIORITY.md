# Biological gap priorities

The dispositions apply to the [proposed v1.0 scientific scope](S6_4_PHASE2_READINESS_SCOPE.md). A blocker denotes a claim that cannot yet be made within that scope. It remains open until the observations support the claim in its stated conditions. The [mechanism register](S6_4_PHASE2_MECHANISM_PRIORITY.csv) gives one decision for each accepted mechanism, its rationale and clearance observation, and exact links to all 99 transition identities and 249 parameter keys. The [blocker register](S6_4_PHASE2_BLOCKER_REGISTER.csv) records root membership, primary source context, archival comparisons, scope, existing evidence, missing measurements, permitted simplification and the conditions that would keep the blocker open.

## Decision categories

| Primary category | Count | Reason for the classification |
| --- | ---: | --- |
| `BLOCKING_FOR_BIOLOGICAL_READINESS` | 21 | A required claim has an observed discrepancy, a necessary causal or structural gap, or lacks a matched test of the proposed prediction. The row names one primary root blocker. |
| `HIGH_PRIORITY_MODEL_REMEDIATION` | 12 | A structural assumption has substantial leverage or a direct context limit. Its effect on a required endpoint should be tested. A bounded approximation can remain if that endpoint passes. |
| `CALIBRATION_REQUIRED` | 7 | The mechanism has an observable counterpart. Its current magnitude, timing or limits need matched quantitative evidence. |
| `VALIDATION_REQUIRED` | 12 | Capability or a plausible rule is present. Matched prediction is open and a code change is conditional on the results. |
| `OPTIONAL_BIOLOGICAL_EXTENSION` | 3 | The missing capability affects a broader claim. The proposed scope can state and test a narrower claim. |
| `ENGINEERING_ONLY` | 20 | This row covers representation, observability, control, ownership or invariants. When needed it carries a secondary observation validation tag. |

Secondary classifications identify work relevant to a mechanism without creating an additional root. The `SourceBasis` column describes the strongest cited comparator available in Phase 1. An Atlas A source can measure an endpoint under a particular treatment while the model rule or coefficient remains unverified. A direct observation, cross-species experiment, unmatched simulation contrast and engineering invariant each have different evidentiary force. The row-level rationale records which inference is possible. [Accepted source and evidence classes](SCIENTIFIC_INTEGRATION_REPORT.md#how-to-trace-a-record)

## Consolidated root blockers

| Root | Required prediction | First discriminating evidence |
| --- | --- | --- |
| BR-01 | Maternal allocation and viable reproductive output across founding and worker provision | Reserve use, actual intake, egg export and conditional laying measured separately |
| BR-02 | Recipient-specific delivery and uptake in early colonies | Compatible contact, selection, actual component dose and uptake timing |
| BR-03 | Active care and retrieval by relevant queen and worker groups | Scored care windows and comparable timing, placement and retrieval counts |
| BR-04 | Stage progression and timing across admitted active conditions | Stage landmarks and nonprogression by measured temperature and nutrition |
| BR-05 | Actual activity, local task responses and state-conditioned energy and water budgets | Timed acts, transitions and physiological flux by caste and cohort |
| BR-06 | Local search, discovery and loaded return in a bounded setting | Encounter-conditioned discovery, travel and delivery, including failures |
| BR-07 | One scoped scout-to-naive recruitment chain | Independent group contrast linking mark, response, discovery and return |
| BR-08 | Survival and nonprogression risk in the claimed window | Stage and cohort survival with known exposure, depletion and censoring |
| BR-09 | Local excavation response and coarse 3D outcomes | Initiation, transport, deposition and volume or connectivity trajectories in measured substrate |

Phase 1's 34 mechanism flags and 26 transition flags concern specific claims and have been retained. Of those 34 mechanisms, 18 map directly to the proposed blockers, seven are high-priority remediation, three require calibration, three require validation and three are optional under the proposed scope. Sixteen of the 26 flagged transitions belong to direct blocker mechanisms. The other transitions retain their evidence flags and contribute through the mechanism-level decisions. Phase 2 also assigns NUT-03, NUT-04 and PHY-03 directly to BR-02. These rules jointly determine delivery and uptake, even though their Phase 1 rows were supporting records. The 21 direct mechanisms map to nine causal questions. For example, SEN-06 is optional under a restricted assay envelope and PHE-02 requires a behaviorally bounded aging response without a full chemical model. [Phase 1 claim flags and cross-domain evidence](CROSS_DOMAIN_CONFLICTS.md)

## Evidence dependencies and research order

1. Establish separable observations first. BR-02 delivery and uptake, BR-03 care, BR-05 time and power, and BR-06 discovery and return can gather matched component evidence in parallel. Their archived deficits justify measurement before redesign. Current ledgers are useful for identifying what to observe.
2. Interpret compound claims with those inputs. BR-01 uses actual delivery, care context and independently constrained maintenance to interpret maternal allocations. BR-04 can isolate timing when nutrition is measured. BR-07 uses the unmarked discovery baseline and actual scout paths from BR-06. BR-09 uses real task and work times to separate construction policy from execution. The dependencies govern interpretation of claims, and do not prevent independent collection of data.
3. Evaluate BR-08 after the relevant birth, development, delivery and expenditure contributions can be distinguished. A controlled survival cohort can be observed sooner. A survival curve with unmeasured starting stores, delivered nutrition or stage change cannot attribute the loss.

Cross-domain compensation (INT-C12) applies to all integrated clearance decisions that combine those processes. It is an evidence constraint across the roots. Treating it as a separate simulator feature would duplicate the causal questions. Joint results should show which measured intermediate quantities constrain alternative explanations. A worker-count or throughput match obtained by co-varying two unmeasured processes is inadequate. This is an order for scientific investigation under the proposed scope. Specific calibration designs and implementation sequencing belong to later reviews. [Cross-domain compensation](CROSS_DOMAIN_CONFLICTS.md#int-c12--compensation-between-mechanisms)

## Parameter dispositions

The [parameter register](S6_4_PHASE2_PARAMETER_PRIORITY.csv) has one row per global key and retains 369 context decisions across the 249 keys. The priorities describe scientific treatment of the current fields. All values keep the accepted F and `ENGINEERING_FIXTURE` provenance.

| Priority class | Count | Treatment |
| --- | ---: | --- |
| `EMPIRICAL_CALIBRATION_REQUIRED` | 26 | The quantity is observable with an appropriate matched assay or separately constrained flux measurement. Examples include stage times, loaded motion, egg exports and activity-dependent power. Current values remain uncalibrated. |
| `SENSITIVITY_RANGE_REQUIRED` | 46 | A model approximation or control can be tested across defensible settings. Examples include contact reach, event cadence when it changes effective behavior, policy switches and discrete motion. |
| `EXPERIMENTAL_CONDITION_INPUT` | 48 | Use the actual exposure, measured starting state, scenario geometry, cohort or fixture treatment. Inputs can need measurement without representing a fitted biological response. |
| `ENGINEERING_OR_NUMERICAL` | 91 | Assess units, precision, limits, sampling artifacts or time integration as software. Preserve the distinction between a numerical period and the physical rate it represents. |
| `CURRENTLY_NOT_IDENTIFIABLE` | 38 | The accepted endpoints cannot isolate the current coefficient or law. Examples include effective carbohydrate yield, hard larval protein threshold, task weights, trail strength and memory expiry. Targeted measurements or a smaller model may make an identifiable quantity possible. |

The 25 Phase 1 context-dependent keys split into 16 experimental inputs or controls and nine switches requiring behavior or sensitivity comparisons. `UseDispositionsJson` preserves the accepted `NO` and `NOT_APPLICABLE` evaluations, their original explanations, batch, mechanisms and domain. It also states the Phase 2 action for each use. None of those 25 fields requires fitting a universal number as currently defined. The behavioral response to some of those conditions does require empirical calibration or independent validation through its linked mechanism.

| Shared uses with different applicability | Phase 2 treatment |
| --- | --- |
| Four `Controls.*` arms and five `IntegratedOptions.*` inputs or controls | Treat as experimental settings for reproduction, supply and task contrasts. Worker and protein amounts should match measured exposures. Gift priority, continuation and holding time select policies. Measure actual transitions or dwell before interpreting those policies biologically. |
| `FoodMass` carbohydrate, protein and water components | Supply measured content for the assay. A natural input or renewal rate would need its own data and belongs to a broader claim. |
| `EnvironmentCareProfile.arena_radius_m` | Match the published dish dimensions for B02 when appropriate. Radius does not determine brood placement or shelter cues and has no species-wide fitted value. |
| `AntSeed.position`, `AntSeed.stage`, `AntSeed.caste` | Set the actual starting placement and cohort. The field defaults cannot estimate a natural distribution of stages, castes or positions. |
| Four `LongTermConfig.*` and five `SocialConfig.*` modes | Preserve ablation control uses and the independent biological comparisons. Require measured outcome contrasts or sensitivity bounds on the selected policy, such as contact sampling, demand cues or actual nutrient delivery. |

This is a priority decision about current parameter uses. Phase 3 will determine identifiable forms, quantitative ranges, which measurements can separate coupled parameters and which observations must be held out. [Unresolved endpoints and existing comparisons](UNRESOLVED_GAPS.md)
