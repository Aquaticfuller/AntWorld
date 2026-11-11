# S6.4 Phase 3 results

**Planning complete for independent review.** The accepted Phase 2 commit is `c3cb3d0c02940420fd9e0bb4028628c7a9b19a9b`. This phase assessed parameters, specified independent validation and prepared the first implementation package. No biological parameter fit, new data analysis or biological validation was executed. All nine root blockers remain open. The C++ tree and all accepted audit and historical evidence files retain their contents.

## Decisions

- **Initial scientific scope.** Use controlled, active-season *Lasius niger* founding and early worker colonies. The v1.0 claim still includes observed foraging, scoped social recruitment, nutrition, reproduction, care, development, survival, activity and autonomous limited 3D construction. The product architecture and eventual multi-colony, expandable 24 × 24 m 3D world remain in the project design. [Scope and exclusions](BIOLOGICAL_VALIDATION_PLAN.md#scientific-claim-envelope)
- **Identifiability.** All 249 keys have an assessment, including the 110 measurement, sensitivity and non-identifiability priorities. There are zero directly estimable current values, one conditional derivation, 28 requirements for additional data, 56 presently unidentified terms or rules and 164 engineering or experimental inputs. The 369 use contexts and 25 context-dependent decisions remain traceable. [Parameter plan](PARAMETER_IDENTIFIABILITY_AND_CALIBRATION_PLAN.md)
- **Independent evidence.** Nine protocols specify condition matching, biological and repeated-measurement units, primary observables, statistical comparison, censoring, frozen data partitions, error margins, diagnosis and future observation costs. The register has 61 accepted source contexts and nine prospective holdouts. Each full protocol still lacks a registered matched independent dataset. B01 and B02 stay exposed development data. Shared B2-F01/F03 tracks cannot cross a split. [Protocols](INDEPENDENT_BIOLOGICAL_VALIDATION_PLAN.md) [Availability](S6_4_PHASE3_DATA_AVAILABILITY.csv)
- **First code task.** Propose an opt-in BR-04 warm egg-stage assay using the existing persisted egg duration. B06's observed egg means are closer to the intended field than available dose, role-cost or maternal allocation proxies. The candidate uses a condition-specific cohort mean with a declared approximation. Test hatching conditional on the observed outcome and full-cohort hatching versus death separately. The old egg budget can exhaust energy before the longer clock reaches hatch. Retain that stress outcome without changing the budget. Independent acceptance awaits a new matched warm-egg cohort. [Implementation package](S6_4_PHASE3_FIRST_REMEDIATION_PACKAGE.md)

## File index

| Artifact | Use |
| --- | --- |
| [Parameter identifiability and calibration plan](PARAMETER_IDENTIFIABILITY_AND_CALIBRATION_PLAN.md) | Feasibility classes, identification, range selection and independent evidence boundary |
| [249-row identifiability table](S6_4_PHASE3_PARAMETER_IDENTIFIABILITY.csv) and [40 authored rules](S6_4_PHASE3_PARAMETER_EVALUATION_RULES.csv) | Exact source and current values with targeted endpoint, evidence, assumptions, coupling, disposition, range and holdout |
| [Independent validation plan](INDEPENDENT_BIOLOGICAL_VALIDATION_PLAN.md) and [protocol table](S6_4_PHASE3_VALIDATION_PROTOCOLS.csv) | Reproducible design for BR-01 through BR-09 with accepted original study citations |
| [Data availability](S6_4_PHASE3_DATA_AVAILABILITY.csv) | Source and sample lineage, available material or restriction, accepted access receipts and missing holdouts |
| [Biological validation execution plan](BIOLOGICAL_VALIDATION_PLAN.md) | Scope, intake, partitioning, evidence freezing, evaluation and reporting |
| [First remediation package](S6_4_PHASE3_FIRST_REMEDIATION_PACKAGE.md) | Proposed first code change, candidates for the other priority modules, scientific and engineering criteria, controls and rollback |
| [Independent verifier](verify_scientific_validation_plan.py) | Check the accepted baseline, derived tables, exact references, planned status and split boundaries |

## Verification commands

Run these commands from the repository root with the approved reference available. The new script's `--write-derived` option regenerates the identifiability and availability CSVs from accepted data and the authored assessments and protocols. The public checks use tracked inputs. Source material and prior reanalysis keep their existing receipts.

```sh
python tools/audit_s6_4_preflight.py --check
python tools/test_s6_4_preflight.py
python research/s6_4_preflight/verify_batch1.py
python research/s6_4_preflight/verify_batch2.py
python research/s6_4_preflight/verify_batch3.py
python research/s6_4_preflight/verify_scientific_integration.py
python research/s6_4_preflight/verify_scientific_priorities.py
python research/s6_4_preflight/verify_scientific_validation_plan.py
```

All eight commands returned exit status 0 locally, including the seven source-anchor tests. Six in-memory checks rejected a missing protocol, reuse of development data as holdout, an invented pass, a changed source locator, a duplicate assessment and separation of the shared trajectory lineage. The documented day-to-ms conversions and egg-budget inequalities were checked by arithmetic. Evidence CI includes the Phase 3 verifier after all previous checks. The Core workflow checks the unchanged engineering baseline. Its outcome has a separate interpretation from scientific assessment.

Phase 3 stops with these plans and the first code proposal for independent review. Adoption, implementation, final scientific gate decisions and broader readiness remain subject to later approval.
