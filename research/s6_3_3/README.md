# S6.3.3 evidence extension

The reviewed S6.3.2.1 Evidence Atlas is AntWorld's continuing scientific reference. This release implements only authorized P10/P01. Current coefficients remain uncalibrated; broader species realism is not inferred from successful transactions.

## Index and release scope

- `docs/52_S6_3_3_Queen_Care_Protocol.md`: pre-implementation freeze plus declared source-denominator clarification.
- `docs/53_S6_3_3_Care_and_Observation_Contract.md`: actual decision/observation semantics and limitations.
- Root `STATE_MACHINE_EVIDENCE_AUDIT.md`: current16 P01/P10 rule groups, function locators and evidence distinctions.
- Root `PARAMETER_PROVENANCE.csv`: historical2559 records retained with explicit release namespace, plus current typed/default/fixture and implicit-expression inventory.
- `CURRENT_RULES.csv`, `CURRENT_IMPLICIT.csv`, `CURRENT_CONFIGURATION_USES.csv`, `summary.json`: reproducible source audit outputs.
- Root `ANT_BIOLOGY_EVIDENCE.sqlite`: unchanged historical tables plus `current_parameters`, `current_parameter_sources`, `care_rules`, `care_validation_catalog`, source endpoints/comparisons/sensitivity and all nine new `care_raw_*` tables; `release_metadata` identifies scope. Query current tables for current code. Historical `parameters` refers to the reviewed atlas, not a current source-location claim.
- `research/s6_3_2_1/baseline`: exact historical parameter/audit/database artifacts. `source_baseline.zip` is project-owned C++/scenario source from65e7875, SHA256-verified by `atlas_baseline.py`; it contains no publisher papers. Original no-change audits now read this explicit snapshot, retaining their strict claims about the old release.
- `experiments/s6_3_3/literature`: original factual data from two CC0 Dryad packages, with source/file hashes and row counts. Only delimiter/newline normalization; no selected exclusion of inconvenient observations.
- `experiments/s6_3_3/raw`: each frozen seed, configuration, original event IDs, scans, windows, run summaries and checksum receipts. Gzip event files are lossless CSV archives.
- `experiments/s6_3_3/analysis`: source endpoints, clustered numerical comparisons, paired seed contrasts, uncertainty and figure.
- `experiments/s6_3_3/performance`: controlled admission, balanced run order, native samples and hardware telemetry. Biological-matrix timing is diagnostic only, not a quiet wall-time gate.
- `S6_3_3_RESULTS.md`: final interpretation, verification, commands and review boundary.

## Primary sources actually used

**B01.** Majidifar et al. (2024), *Ontogeny of superorganisms: Social control of queen specialization in ants*, Functional Ecology38:1044-1060. [Publisher full text](https://besjournals.onlinelibrary.wiley.com/doi/full/10.1111/1365-2435.14536), DOI10.1111/1365-2435.14536. Methods2.1.3-4,2.2.4-5,2.2.12 and corresponding results/Figs1c-d,2c were read in full publisher HTML. The user also supplied a2022 preprint PDF; it is not silently substituted for the final2024 article. [Dryad](https://datadryad.org/dataset/doi:10.5061/dryad.pnvx0k6wd), version2024-02-09, downloaded by user after automated403. Source authors, geography and broader conditions remain in the49-source atlas register.

**B02.** Walsh, Signorotti, Linksvayer and d'Ettorre (2018), *Phenotypic correlation between queen and worker brood care supports the role of maternal care in the evolution of eusociality*, Ecology and Evolution8:10409-10415. [Publisher](https://onlinelibrary.wiley.com/doi/10.1002/ece3.4475), DOI10.1002/ece3.4475. User-supplied final PDF has all7 pages; Methods/Results pp10411-10413 and Figs1-3 were read, including assay duration, three-worker experimental units and paired brood-origin trials. [Dryad](https://datadryad.org/dataset/doi:10.5061/dryad.qm114cj), version2019-07-20, user-supplied complete archive. No copyrighted full text is committed.

B01 supports reversible maternal-care plasticity with worker contact conditions, not a fitted six-hour memory or universal suppression coefficient. B02 supports actual queen brood retrieval and first-generation associations, not a heritability value or identical queen/worker policy. Null own/foreign brood contrasts and lack of the same later-generation relationship remain in the historical atlas; they are not converted into positive model evidence.

## Data anomalies and analytic definitions

B01 reversibility tables use50 scans versus51 in the method text; both simulator observations are retained. The older-queen table has14 labels, three NA rows,13 measured units per hour and12 complete three-hour records. The text's12 is consistent with the complete-case cohort, but the deposited files do not establish that this was the exact original exclusion rule. Both available-case and complete12 comparisons are exported; missing measurements are not zero. Mesh files contain60 queens and unequal/partial observations; preserve actual denominators and do not present the solid wall as mesh antennation. B02 has158 queen trials (79 queens),140 first-worker trials (70 groups),100 later-worker trials (50 groups). The deposited `Lasius2.R` script explicitly joins79 queens and70 worker groups into67 matched colonies, then61 with productivity measurements. These are distinct analytic cohorts, not an unexplained count contradiction. All398 trials remain; comparisons separately report all units, matched67 and the author61 cohort. Paired trial means are clustered by queen/colony group; no individual worker pseudo-replication.

For B01, compare active-care scan fractions using original denominators. For B02, compare number retrieved by600s and contact latency capped at600s, retaining noncontacts. Original `time task` is not the simulator's time to retrieve all six; no mislabeled rate comparison is published. Partial mesh recordings are retained and their sampling limits disclosed. Bootstrap95% intervals quantify variability of the observed units/seeds, not uncertainty in all missing biological mechanisms. No data have been used to fit the candidate coefficients; B02 is a held-out endpoint, with geometric/behavioral approximations explicitly limiting validation.

B01 Methods2.2.4 assigns prior three-day worker exposure only to the removal treatment. The deposited `With_workers` group receives workers at experimental setup, so its numerical comparison uses the already-frozen **added** simulator condition, including the worker-free baseline. The continuously **present** simulator condition remains a separate mechanism control. This mapping follows actual intervention history, not whichever simulated mean is closer to the paper. Baseline glass-tube versus subsequent observation-arena transfer is still not physically reproduced by the simulator.
