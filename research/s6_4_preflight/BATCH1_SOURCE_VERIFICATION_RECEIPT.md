# S6.4-S2 Batch 1-R1 source verification receipt

The local source check covers the recovered materials for the already reviewed Batch 1. The separate evidence workflow checks the tracked inventory and records with public repository inputs.

The local run started on **2026-11-10 at 19:45:02 CET (Europe/Berlin)** in Windows PowerShell. It used Python 3.12.14 with openpyxl 3.1.5. The checked-out HEAD at execution was `58d543b96cb9c1673c7ef61c847b2113135d81d9`, the independently reviewed Batch 1 commit. The working tree contained the final R1 audit tooling and evidence edits. This receipt records that run before the R1 commit was created.

The accepted S6.3.4 baseline is `b35b988ecf1b92f7bac3c00af393b88ab8330d67`. The run read Core tree `277cc8e78cc1acd1cf4a74bf39d08dfdb6a99c69` and found no changes to the baseline Core, scenarios, historical experiments, design documents or existing Core CI workflow.

## Commands and exit states

The source-bearing check ran locally from the repository root with the existing verifier.

```sh
python research/s6_4_preflight/verify_batch1.py --download-dir out/s6_4_preflight/batch1/user_downloads --b01-dryad out/s6_3_3/sources/doi_10_5061_dryad_pnvx0k6wd__v20240209.zip
```

It exited **0** and matched all seven recovered files and the B01 Dryad archive against their registered SHA-256 hashes. The separate local `python -` inspection of the supplementary documents, archived R calls and FT01 caption exited **0**. FT01 page 18 was rendered with pdfplumber at 125 dpi and visually checked.

| Command run from the repository root | Exit | Observed result |
|---|---:|---|
| `python tools/audit_s6_4_preflight.py --check` | 0 | Frozen inventory, 541 source anchors and numeric candidate ledger verified |
| `python tools/test_s6_4_preflight.py` | 0 | Seven source anchor regression tests passed |
| `python research/s6_4_preflight/verify_batch1.py` | 0 | 15 source contexts, 42 access records, 11 conflicts, 39 mechanisms, 53 transitions and 163 parameter records checked |
| `git diff --check` | 0 | Patch whitespace check passed |
| `git diff --exit-code b35b988ecf1b92f7bac3c00af393b88ab8330d67 -- cpp scenarios experiments docs .github/workflows/ci.yml` | 0 | No differences in the protected paths |

The separate [S6.4 evidence workflow](../../.github/workflows/s6_4_preflight.yml) invokes the three Python checks without local-source options. The existing [Core CI workflow](../../.github/workflows/ci.yml) continues independently.

| Executable check or workflow at the local run | SHA-256 |
|---|---|
| `tools/audit_s6_4_preflight.py` | `9a5e6dca159ddf2fe3abb4ac81ff75148c66863303bd7d19ad788f4e3df03f5d` |
| `tools/test_s6_4_preflight.py` | `7aed38830e40121d9e8a46d7317c576f53203de2cca6769121e04d9aa5a23086` |
| `research/s6_4_preflight/verify_batch1.py` | `feef203092691c986e829e51475c5e72102a512d5aa1774600fe44d492bd59a6` |
| `.github/workflows/s6_4_preflight.yml` | `52907cf000b8ab0ec0cd439471a365b7152a4d12ae00a51169951430ac6747e2` |

## Local source inputs

All listed inputs were present and readable. Paths are relative to the repository root. The previous unsuccessful access attempts remain in the [reading log](SOURCE_ACCESS_AND_READING_LOG.csv).

| Material | Local input | SHA-256 | Role in the check |
|---|---|---|---|
| B01 Dryad | `out/s6_3_3/sources/doi_10_5061_dryad_pnvx0k6wd__v20240209.zip` | `871b119b1b461f80f76bdfa83309f2b088a2ed805a403bf6f7f43949d41b1376` | Original mesh design and BORIS observations, plus founding brood counts |
| B01 Data S1 | `out/s6_4_preflight/batch1/user_downloads/fec14536-sup-0001-datas1.zip` | `465b01be83a76bd6f0a33c8a1486acaa14c2975bbdf2c1337a53ffab522d2219` | Author's Appendix S1 script, figures and model tables |
| B03 Appendix S1 | `out/s6_4_preflight/batch1/user_downloads/blad149_suppl_supplementary_information_s1.xlsx` | `333ae1dd07ce154cb8308be06061bf8632f2ab50a9274fe25b89169eafca988c` | Queen-level day-49 workbook |
| B03 Appendix S2 | `out/s6_4_preflight/batch1/user_downloads/blad149_suppl_supplementary_information_s2.pdf` | `08e9cd4771ed0c0be2556b6604bec959caf5289d008edff130f09ac4ef69c0ea` | Published ANOVA and Tukey tables |
| B04 Data S1 | `out/s6_4_preflight/batch1/user_downloads/mec70127-sup-0001-supinfo.pdf` | `ea1caab38a29d937a27403527abf250ab786d89acd586d6d34da230a5824965f` | Checksum coverage for the previously reviewed physiology supplement |
| B07 main article JATS | `out/s6_3_2/literature/nutrition_growth_2020.xml` | `1c079adaf4ab38c4729a8d091f2f0507f011cd8652ac8109657c9518d81c88b2` | Methods, Results and Table 1 |
| B07 supporting information | `out/s6_4_preflight/batch1/user_downloads/ece36520-sup-0001-supinfo.docx` | `907494eb88b51ccd851582333b0524d657e9b24abf0aeab72e2cf20397ca62d3` | Table S3 |
| B07 Dryad | `out/s6_4_preflight/batch1/user_downloads/doi_10_5061_dryad_g79cnp5n1__v20210610.zip` | `fa359ee2bfddb20d46cf9e1b1a8354c33be72b2487a4e2797679bd41e96d181e` | Growth and isotope observations and their analysis scripts |
| FT01 merged PDF | `out/s6_4_preflight/batch1/user_downloads/Matte,_A.,_Billen,_J._(2021)_Flight_muscle_histolysis_in_Lasius_niger_queens_(10.20362@am.013003).pdf` | `2f484eeb42c2d8be96f50beee0110d25956686debcb293e2a7d9eaaa458779e5` | Article DOI and supplementary Fig. S1 at PDF page 18 |

The B07 ZIP also pins the exact bytes of the four inspected members.

| B07 Dryad member | SHA-256 |
|---|---|
| `DATA_combined.txt` | `69549b0325504526d15ee23f2bbb81e4303cc73cdd3c1bc574afb8e34645911b` |
| `02_Survival_development_and_growth.R` | `20e7b59c6c21eb4a4e4010fbb09a941b2eea439e66e70ff244c9aef86b89033f` |
| `Lasius_pulseisotopedata.txt` | `0f44af6e5df0a0ad5d020ab0b54b39eae6eb2391cdf8af0c3608708ec6cb3311` |
| `Lasius_pulse_analysis.R` | `ac133c8e2570350701f90102aa8fb3517695cc4c4ee5448ad713dec182be6e77` |

## Recomputed results and source comparisons

- **B01.** The original 60 mesh design labels reduced to 55 after the callow exclusions and to 43 after the tray exclusion. In separated / worker access / absent order, the final arm sizes were 13/14/16, with 127 retained observation windows. The Dryad founding series reproduced first observed workers at 62.88 ± 2.52 days after the nuptial flight (mean ± sample SD, 17 worker-producing queens). The inherited focal care percentages still reproduced as 6.500%, 0.125% and 6.250%. The recovered Appendix S1 confirms the filtering sequence and the source of the brood counts. [Article and Data S1](https://doi.org/10.1111/1365-2435.14536), [Dryad](https://doi.org/10.5061/dryad.pnvx0k6wd).
- **B03.** The recalculation retained all 240 Appendix S1 queen endpoints, including four rows marked `queen died`. Day-49 pupae+workers means ± sample SD per queen were 18.73 ± 4.74 (unfed, undisturbed), 17.90 ± 5.20 (unfed, disturbed), 18.23 ± 3.95 (weekly sugar) and 21.77 ± 5.04 (weekly cricket), with 30 queens per arm. Appendix S2 Table S2-2 p. 3 reports weekly cricket versus never +2.99 pupae+workers, Tukey p=0.006, and weekly sugar versus never −2.10 workers, p=0.073. These are published adjusted contrasts with a separate analysis scope. [Article and Appendices S1–S2](https://doi.org/10.1093/biolinnean/blad149).
- **B07 overall growth.** Pairing each colony by species and ID yielded 80 complete *Lasius niger* and 47 complete *L. neoniger* census 2/8 pairs. The sequential diet F statistic for census 8 minus census 2 recalculated to 4.363743 and 0.596697 respectively. Table S3 reports diet p=0.00718 for *L. niger* and p=0.6213 for *L. neoniger*. In *L. niger*, the 1:16 and 1:8 diets gave mean changes of 23.57 ± 6.82 and 34.68 ± 12.01 workers (n=21 and 22). [Table S3](https://doi.org/10.1002/ece3.6520), [Dryad](https://doi.org/10.5061/dryad.g79cnp5n1).
- **B07 longitudinal development.** The Methods, primary JATS Table 1 and archived `lme` calls were cross-checked. Table 1 reports repeated-count diet p=0.0022 in *L. niger* and p=0.0196 in *L. neoniger*, with time-by-diet p<0.001 and p=0.0037 respectively. The Table S3 *L. neoniger* diet null applies to the net-growth endpoint. It leaves the longitudinal diet effects and the significant net-growth frequency effect in place. [Comparison of both estimands](EVIDENCE_CONFLICTS.md#b1-c08--dietary-composition-and-congener-tracer-evidence), [published results](https://doi.org/10.1002/ece3.6520).
- **B07 isotope pulse.** There were 32 labeled aliquots from five enriched and three control *L. neoniger* colonies, stratified by 24/96 h and worker/larva. For enriched colonies, the mean control-relative carbon/nitrogen enrichment percentages recalculated to 16.38/194.29 at 24 h in workers and 9.41/25.40 at 96 h in larvae. The archived pulse script uses `100 × C_APE2` and `100 × N_APE2` for these units. [Article Fig. 7](https://doi.org/10.1002/ece3.6520), [Dryad isotope table and script](https://doi.org/10.5061/dryad.g79cnp5n1).
- **FT01.** The local 18-page file includes the article with DOI `10.20362/am.013003` and Fig. S1 on PDF page 18. The displayed labels are 5, 15 and 165 days from collection to fixation in three pictured *Pachycondyla crassinoda* queens. The scale bar is 2 mm. The caption and visual inspection support the separate `FT01-X` classification, `CROSS_SPECIES_EXTRAPOLATION`, Atlas D. [Matte and Billen, article p. 13 and Fig. S1](https://doi.org/10.20362/am.013003), [source context and access records](SOURCE_FULLTEXT_REGISTER.csv).

## Limits of independent verification

- The B01, B03 and B07 published R workflows and inferential p-values were not independently rerun. The receipt separates the count and descriptive recalculations and the B07 net-growth diet F recalculation from statistics read from the original tables. In particular, no Table 1 `lme` was refitted. The archived growth script calls `Anova(model1a)` without defining `model1a` in that file, so the source inspection alone cannot establish a clean replay of that exact test.
- The B03 workbook gives the recorded endpoints and death annotations. The verifier does not reconstruct each author exclusion or the adjusted analysis populations from that workbook. The B04 oxygen sample-count discrepancy and the B02 marker and cohort limitations remain recorded.
- FT01 provides a figure and caption with a collection-to-fixation clock. Individual sampling dates, independent replication at each time and quantitative flux are unavailable from the figure. The image cannot calibrate *L. niger*.
- Batch 1 covers 39/75 mechanisms, 53 state transitions, 163 parameter records and 13 original papers. Zero of the 163 reviewed parameters have quantitative calibration. `ENGINEERING_FIXTURE` designations, all negative results and the remaining open biological domains stay within their documented scope. The accepted S6.3.4 Core is frozen. Batch 2 awaits independent review of this checkpoint.
