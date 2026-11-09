# S6.3.2 biological comparison and correction freeze

This document supplements protocol 48 before new model probes. BIOLOGY_EVIDENCE_MATRIX.md covers the current state/transition rules; BIOLOGY_REFERENCES.md records primary sources and access; MODEL_CORRECTION_PROPOSALS.md freezes P01-P10 as proposals only. The core remains identical to reviewed S6.3.1. No parameter is fitted and no survival outcome is an optimization objective.

## Endpoint mappings

| Comparison | Empirical protocol | Current mapping and frozen status |
|---|---|---|
| Founding queen care | B01 worker addition/removal and direct care scans; B02 isolated brood retrieval | NOT IMPLEMENTED: caste gate forbids Queen Nurse/autonomy; retrieval/grooming/feeding are different endpoints. Probe eligibility only; do not call rejection a biological success |
| Claustral founding | B03 49 days at 24.5 C with water, diet arms; B06 unfed with water at fixed temperatures | NOT TESTABLE as a matched experiment: initial fat/structural reserves, water access, temperature and queen care absent. A sealed-resource queen probe is explicitly not the wet-test-tube experiment |
| Temperature/development | B06 Table 2, population and stage-specific daily observations | Temperature NOT IMPLEMENTED. Probe the existing fully supplied tissue clock to expose its magnitude; no temperature labels attached to simulated runs and no fitted error statistic |
| Caste energy use | B04 mass-adjusted postabsorptive respiration; B05 sexual whole-individual respiration at 20 C | PARTIAL dimensional diagnostic only. Probe identical current caste configurations at rest; no empirical fit because mass, age, temperature, oxygen and compartment mapping differ |
| Local trophallaxis | B08 queenless/broodless groups, four-day deprivation, 90 min including 30 min prefood, contact >5 s | NOT TESTABLE quantitatively: current instantaneous transfer lacks duration/observed contact definition. Audit direction, locality and retained mass ledgers; do not compare transfer mass with observed event counts |
| Trail following/memory | B14 junction angle; B15/B17 trajectories; B16 learning; B18 crowded deposition | PARTIAL: reuse all S2.1/S2.2 raw positive and negative outcomes, no rerun with larger weight; geometry/dose/trajectory metrics are not matched enough for an error target |
| Task distribution | B20 individually marked workers and observed categories/windows | NOT TESTABLE quantitatively: assigned program time is not moving/feeding/resting observation time. Retain SD-07 |
| Nest construction | B12 shallow surface construction; B13 deep soil with thermal treatments | PARTIAL material/locality mechanics only; morphology and temperature response NOT IMPLEMENTED. Retain SD-06/TD-04 |

## Unchanged-core probe set

Use seeds 1,2,3,4,5,6, all retained. Inputs below are ENGINEERING_FIXTURE diagnostics, not replacements for paper conditions. Report the deterministic lack of between-seed variability rather than fabricating confidence intervals.

1. **Care eligibility:** 0/1/5 adult workers, one queen and one larva at the same depot. Queen `set_behavior(Nurse)` and `set_autonomy` must reject with byte-identical rollback. A worker control can enter Nurse. This verifies the identified model limitation and error handling, not care biology. No worker-count-driven policy is introduced.
2. **Resting caste budget:** one adult Queen or Worker, empty crop, 1.5 J usable body energy, 1600 ug hydration, identical long-term physiology (1 nJ/ms basal, 1 nJ/ms active, six-hour absorption/behavior, one ug water/hour). Remain Paused for 24 hours. Record body energy, loss, stage and events. Split at 12 hours, restore and require exact final checkpoint and trace equality.
3. **Supplied-tissue stage clock:** one Worker Egg with 100 ug incorporated tissue protein (explicit artificial diagnostic supply), 1.5 J and 1600 ug water, no crop/food, existing 2/3/2-day durations and same maintenance. Record stage each day through day 8. Preserve its EntityId; split/restore at day 4. This isolates clocks without claiming a naturally provisioned egg.
4. **Sealed-resource queen:** one adult queen, no workers/food, existing initial crop 200 ug carbohydrate/100 ug protein/200 ug water, 1.5 J and 1600 ug hydration; laying enabled or disabled. Use two-day attempt/maintenance window and existing offspring rules. Run 90 days, record daily population/queen stores/egg counts plus all committed events and exact energy/nutrition ledgers. Restore at day 45. It is NOT an empirical founding-survival comparison because water and reserves are not matched.

No new task, behavior rule, parameter default or source of food is added. Application-level fixtures and read-only analysis are permitted. All current 161 regressions remain; the diagnostic smoke check is additional. A discovered probe implementation error is corrected before archiving, with runs identified as diagnostic development rather than substituted accepted data.

## Existing S6.3.1 failure reanalysis

Use the complete unchanged 432-run archive. Extract all six corrected ordinary-access 32-worker balanced primary runs and all six corrected adequate-access eight-worker 180-day runs, with no exclusion for death. Reconcile queen initial + absorbed - maintenance - exported egg energy - reproductive dissipation = final energy from the existing ledgers. Report last-day/two-day opportunities, sampled compatible recipients, committed gifts, crop-to-body uptake and remaining external/depot/worker stores where those observables exist. Do not infer transfer from a contact opportunity or treat a missing trace field as zero.

The existing 32-worker adequate-access positive control remains evidence of bounded engineering capability, not biological validation. Retain the two-day guard and all previous negative outcomes. No new rescue run is allowed by this freeze.

## Quantitative interpretation

Publish transcribed factual Table 2 developmental endpoints with source/page, actual temperature, population, sample size and dispersion exactly as described. Do not invent confidence intervals from unspecified error bars or independent ant-level replicates when colony clustering matters. Report arithmetic dimensional ratios as diagnostics, explicitly not matched biological errors. Only a matched empirical estimand would permit an error/uncertainty claim; none of the missing-mechanism comparisons receives a fabricated score.

P01-P10 are the frozen review proposals. S6.4 remains blocked pending independent decisions on the founding, physiology, reproductive feedback, development, observational and performance gaps.
