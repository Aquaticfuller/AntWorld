# S6.3.2 — Biological Evidence, Model Validation and Performance Requalification

## Review conclusion

**Engineering verification PASS. Biological readiness NOT PASSED. Dense-contact performance PASS for the frozen workload; funded-birth performance PASS in the user-authorized completion extension. S6.4 remains blocked.** The original delivery `1671737` passed all five [GitHub CI jobs](https://github.com/Aquaticfuller/AntWorld/actions/runs/42632533893). The quiet-interval extension changes only measurement/audit tools and evidence; its publication workflow is identified by the delivery commit on the same branch. Prior CI receipts remain in `experiments/s6_3_2/verification.json`.

This stage changes **no Simulation Core biological rule, parameter, RNG decision, scheduler semantics, resource flow or history retention**. It adds a source/provenance audit, unchanged-model diagnostic executable, empirical endpoint extraction, performance admission/analysis tools and evidence reports. All 161 inherited tests and all earlier negative results remain; one diagnostic smoke test brings local suites to 162.

## What the evidence establishes

The bibliography contains 22 sources: 20 original Lasius niger experimental papers (one also includes separately identified L. neoniger experiments), one fire-ant excavation paper used only as C-grade extrapolation, and one physical-chemistry reference with explicitly identified NIST compilation access. Relevant full methods/results or specified original pages were read for the ant papers, using publisher/institutional/author copies, including host-network PDFs. Access failures and species/assay limitations remain visible. This is a broad targeted audit, not a claim of exhaustive systematic-review coverage.

- **Direct qualitative support:** queen founding care and reversible worker influence; condition- and brood-dependent reproductive allocation; temperature/nutrition-dependent development; caste-related metabolic differences; local heterogeneous trophallaxis; learned routes and local trail response; context-dependent deposition; substrate/temperature-dependent construction.
- **Quantitative calibration candidates:** B06 stage/temperature/population measurements; matched respiration/mass data from B04/B05; geometry/dose-specific trail endpoints; observation-compatible contact network and nest measurements. **No current adopted biological coefficient becomes quantitatively calibrated in this stage.** Endpoint mapping and missing state must precede fitting.
- **Reasonable but uncalibrated approximations:** conserved crop/body separation, own-store egg funding and the retained maternal reserve guard, finite route memory, scalar trail decay, bounded local social demand and finite explicit resource inputs.
- **Conflicts or critical omissions:** Worker-only care eligibility excludes real queen founding care; fixed egg attempts omit demonstrated founding/established brood feedback; the supplied seven-day development clock is far from measured magnitude and lacks temperature; loaded-only invariant deposition omits observed context/outgoing marking; homogeneous caste/stage capacities/rates and undefined energy compartments lack justification.
- **Arbitrary engineering rules:** 4/8/12/4 task weights, quarter-capacity urgent threshold, half-crop intake gate, perfect one-visit route memory/priority, visited-cell penalty and heading/normalized-trail weights, six-axis outward excavation and contact-times-four vacancy demand. They remain explicit D-grade fixtures, not validated biology merely because a paper supports the topic.

The detailed matrix contains 54 rule/transition rows across every requested module and relevant helpers. The automatic provenance covers 119 fields in 16 configuration/seed/control structs, 1,209 source expressions and 469 supplementary hard-coded/fixture/JSON contexts. Units, current expressions, evidence locators, measured-condition caveats, sensitivity and proposed action are recorded. Contextual lines and unresolved runtime expressions are not falsely presented as calibrated scalar values.

## New diagnostics and retained negative evidence

Protocol 48 was frozen in `55e6871`; the evidence matrix, provenance and concrete comparison/proposal freeze were committed in `15e5c40` before new probes. Seeds 1–6 are fixed and all retained.

| Diagnostic | Actual result | Biological interpretation |
|---|---|---|
| Queen care with 0/1/5 workers | All 18 worlds reject Queen Nurse/autonomy with exact rollback; worker controls accept Nurse | Confirms a model conflict, not successful founding biology |
| Resting queen/worker, 24 h | Both retain 1.4136 J / 1576 ug water from identical inputs | Homogeneous fixture physiology; no matched respirometry fit |
| Supplied-tissue stage clock | Same ID changes at days 2/5/7 | Isolates fixed clock mismatch; temperature NOT IMPLEMENTED |
| Sealed-resource queen, 90 d | Suppressed laying death 19.675926 d; enabled laying death 7.870370 d after two births, every seed | Negative engineering result; not the water-accessible empirical founding protocol |
| Continuation and ledgers | All 30 trajectories exactly match midpoint restore and single-advance execution; all fact sequences and energy/nutrients reconcile | Engineering PASS, no added biological authority |

All 18 predeclared historical queen contrasts were reanalyzed without changing their data. Ordinary32 survival remains 0/6 at 90 days (median death 71.672 days); adequate-access8 remains 0/6 at 180 days (median death 50.648 days); adequate-access32 remains 6/6 right-censored at 180 days. The corresponding simulator-seed Wilson intervals are [0,0.3903], [0,0.3903] and [0.6097,1]; these do not represent natural-population uncertainty.

Median final-48-hour physical opportunities / compatible sampled donors / committed gifts are 798.5 / 2.5 / 0 for ordinary32, 173.5 / 15 / 1 for adequate-access8, and 1775.5 / 13 / 10.5 in the surviving adequate-access32 observation endpoints. Three of six ordinary32 deaths and all six adequate-access8 deaths retain external/depot carbohydrate. Exact queen ledgers reconcile. Thus colony stock, physical proximity, selected provision and absorption are different stages of the supply chain. The data do not identify a calibrated queen demand or justify forced delivery, more food, fixed lifespan protection or a global allocator.

## Verification and performance

Executed with pinned LLVM-MinGW 20261104 / Clang 23.1.5, CMake 3.31.10, Ninja 1.13.2 and SQLite 3.54.1:

| Configuration | Tests | CTest elapsed |
|---|---:|---:|
| Windows Debug | 162/162 PASS | 71.01 s |
| Windows Release | 162/162 PASS | 22.96 s |
| Windows ASan + UBSan | 162/162 PASS | 250.46 s |

Windows leak detection is unsupported and disabled; Linux sanitizer CI enables it. Existing geometry, material, deterministic phase order, failure rollback, identity, SQLite crash/restore and all prior biological fixture regressions remain. New probes also compare one large advance against observation-paced advances and restored continuation. Raw logs and hashes accompany verification.json; the CI workflow additionally reproduces all six new diagnostic seeds and retains prior S6.3.1 180-day controls.

The initial publication CI correctly rejected probe artifact hashes after Git normalized Windows CRLF output to LF. The archive now records original-source hashes separately from published LF hashes; no values, event payloads or Core rules changed. Both the failed run and successful corrected run remain in the verification receipts. All 64 Core/header/inherited-test files match the reviewed baseline after line-ending normalization.

The three qualified contact sessions retain all 336 samples and exact historical state/work equality. Dense advance grows **5.418486x [5.297897,5.501400]**, paired median **5.338576x [5.226317,5.426444]**, satisfying <=6. The detailed performance report separates setup, advance, checkpoint, restore, memory and CPU/cycle measurements. At the original delivery, birth session 1 had exhausted three failed admissions without starting timing; sessions 2/3 completed 112 of the planned 168 rows. Their pooled growth remains **4.250833x [4.140750,4.383082]**, conditional on those sessions, and that original incomplete series retains **no PASS verdict**. Valid-load excursions and PDH invalid-denominator readings are distinct, retained measurement limitations. Neither the earlier 24.229x anomaly nor the 6.315x/8.154x failures are erased or assigned an unproven cause.

After delivery, the user provided the requested quiet interval. Addendum 50 was frozen in `7badade` before diagnostics and the renewed admission series. The first new admission passed unchanged criteria; the original session-1 schedule completed once, with no timed reruns or missing rows. The predeclared completion extension combines it with unchanged sessions 2/3: **168/168 rows**, pooled advance growth **4.169260x [4.049359,4.335740]**, paired median **4.194797x [4.115608,4.370482]**, **PASS** against <=6. Every work/state/trace/restore/conservation check matches the historical binary. A two-invalid-sample preliminary counter diagnostic, one invalid in-run reading, all load excursions and all slow timings remain. This workload-specific completion does not resolve counter reliability, broader TD-01/08 scaling or any biological debt; see the performance report's extension section and `completion_analysis`.

## Deliverables and gate

- [Mechanism/state matrix](BIOLOGY_EVIDENCE_MATRIX.md)
- [Complete parameter provenance](PARAMETER_PROVENANCE.csv) and [coverage contract](experiments/s6_3_2/PARAMETER_AUDIT_COVERAGE.md)
- [Biological comparisons and dimensional audit](BIOLOGICAL_VALIDATION_REPORT.md)
- [Ten isolated correction proposals](MODEL_CORRECTION_PROPOSALS.md)
- [Performance requalification](S6_3_2_PERFORMANCE_RESULTS.md)
- [Primary bibliography and access distinctions](BIOLOGY_REFERENCES.md)
- [Raw evidence and exact reproduction commands](experiments/s6_3_2/README.md)
- [Frozen protocol](docs/48_S6_3_2_Frozen_Audit_and_Performance_Protocol.md) and [comparison/proposal freeze](docs/49_S6_3_2_Biological_Comparison_Freeze.md)
- [User-authorized quiet-interval addendum](docs/50_S6_3_2_Quiet_Interval_Performance_Addendum.md)

Technical debt is updated in document 08: retain SD-04/06/07/08, SD-01/02, TD-01/08 and TD-03/06; new **SD-09** explicitly tracks physiological/developmental calibration. P01–P04 and P10 expose foundational readiness gaps; the remaining proposals need separately reviewed scope and tests. No biological correction or performance-threshold change is silently authorized by this audit. Stop on `codex/s6.3.2-biology-audit` for independent review; do not enter S6.4 or Unity.
