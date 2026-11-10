# Batch 2-R1 source verification receipt

## Execution record

The local run used the final R1 reproducer in the working tree over reviewed HEAD `f2994f4059c244258fe5dc7250f985bf8c399c6d`. The Core tree was `277cc8e78cc1acd1cf4a74bf39d08dfdb6a99c69`. The reproducer's file SHA-256 was `1d247cac97f16734db37380128270b5009ecacc67f6497330f1bb10d09497adb`.

The commands below ran from the repository root on Windows 11 x64 build 26200 with PowerShell 7.6.9. The local `$python` executable was Python 3.12.14 with openpyxl 3.1.5 and et-xmlfile 2.0.0. A separate PDF identity and page inspection used pypdf 6.10.0.

```powershell
& $python research/s6_4_preflight/reproduce_batch2_sources.py > out/s6_4_preflight/batch2/r1/reproduction.json
& $python research/s6_4_preflight/reproduce_batch2_sources.py --f01-zip out/s6_4_preflight/batch2/r1/not_present.zip --p04-workbook out/s6_4_preflight/batch2/downloads/P03_data.xlsx > out/s6_4_preflight/batch2/r1/reproduction-negative.json
& $python tools/audit_s6_4_preflight.py --check
& $python tools/test_s6_4_preflight.py
& $python research/s6_4_preflight/verify_batch1.py
& $python research/s6_4_preflight/verify_batch2.py
```

The positive run finished on 2026-11-10 at 21:15:05 UTC with exit status 0. It verified all six input digests and recomputed the descriptive statistics from five datasets. The negative run finished at 21:15:04 UTC with exit status 1. The missing F01 archive reported `NOT REPRODUCED` and the mismatched P04 file reported `FAIL` before parsing. The four other inputs were still checked. All four public evidence commands returned 0 locally on 2026-11-10. The public Batch 2 check rejected nine deliberately corrupted records.

For a new local run, install the workbook reader if needed with `python -m pip install openpyxl==3.1.5 et-xmlfile==2.0.0`. Run the reproducer with `--help` for local path overrides. Its JSON output records versions, input hashes, status and calculated results. The public check uses the standard library and tracked evidence. The source files and local JSON logs are excluded from Git.

## Inputs

| Source and access ID | Input relative to repository root | Verified SHA-256 |
| --- | --- | --- |
| [F01, B2-ACC-002](https://doi.org/10.1371/journal.pone.0076531.s005) | `out/s6_3_3_1/sources/Khuong_2013_Dataset_S1.zip` | `9990d73ea6c08ffeedfef7e332b8f1623ab71936afc62e25d5cf9f4df3520b49` |
| [P03, B2-ACC-032](https://doi.org/10.1371/journal.pone.0149720.s002) | `out/s6_4_preflight/batch2/downloads/P03_data.xlsx` | `7afa7c1bbbf3dba3106b2ff310536748f10387be6a63cd74b4d6060348dad42f` |
| [P04, B2-ACC-017](https://doi.org/10.1007/s00040-026-01106-9) | `out/s6_4_preflight/batch2/downloads/P04_data.xlsx` | `b311d5fdc89eac56724bb5195743cf4bb52a6cff4040b18704353091e1fe6318` |
| [P06 S2, B2-ACC-034](https://doi.org/10.1007/s00040-024-00995-y) | `out/s6_4_preflight/batch2/downloads/P06_S2.xlsx` | `84e03659c4c5623c850304cec7d9c63651e563f200a1e67f25ae5481456fd28f` |
| [P06 S3, B2-ACC-035](https://doi.org/10.1007/s00040-024-00995-y) | `out/s6_4_preflight/batch2/downloads/P06_S3.xlsx` | `cc02852d5de2235163574999744ac4424284c0fbe1f16dde13677492a2bfba3f` |
| [P15, B2-ACC-046](https://doi.org/10.1007/BF01201674) | `out/s6_4_preflight/batch2/user_downloads/Beckers1993.pdf` | `3cf04eb24d4cfdff659cbaa47e4dd1a8e76b32d0d1d1e838256fead33d52b0b0` |

## F01 — flat-canvas tracks

Dataset S1 yielded 69 flat-canvas files at 26 °C and 50% relative humidity, with 145,654 adjacent 0.04 s intervals. The script uses 25 successive intervals per one-second window and discards each incomplete tail. It divides both the sum of successive planar distances and the endpoint chord by the elapsed time, converting meters to millimeters with a factor of 1,000. It averages each measure within each track, then takes the median across track means. The 5,797 complete windows give **50.643 mm/s** for path length and **38.133 mm/s** for the chord.

Tracks are nested in colony labels and windows are repeated within tracks. The files carry 24 A, 26 C and 19 D labels. The published setup describes 23 ants per colony per inclination. The label discrepancy is unresolved. All 69 tracks retain equal weight in the reported pooled median. No inference treats windows as independent replicates. The other inclinations and the published inclination-effect inference were outside this rerun. [Primary article and supporting data](https://doi.org/10.1371/journal.pone.0076531)

## P03 — path learning

In the `cleaned for R` sheet, nonempty `treatment` identified 4,930 records across 260 distinct `(Colony, ant)` label pairs and eight colony labels. Across all rows there were 3,334 correct, 846 incorrect and 750 missing choices. At trip seven there were 314 correct, 252 incorrect and 74 missing among 640 recorded rows. Fractions use correct choices divided by observed binary choices. Blank cells stay missing and zeros count as incorrect.

| Training layout | Trail treatment | Test fork | Correct | Incorrect | Missing | Correct among observed |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| Confined | Allowed | First | 22 | 43 | 15 | 33.85% |
| Confined | Allowed | Second | 46 | 19 | 15 | 70.77% |
| Confined | Removed | First | 18 | 56 | 11 | 24.32% |
| Confined | Removed | Second | 57 | 17 | 11 | 77.03% |
| Open | Allowed | First | 35 | 40 | 5 | 46.67% |
| Open | Allowed | Second | 50 | 25 | 5 | 66.67% |
| Open | Removed | First | 35 | 34 | 6 | 50.72% |
| Open | Removed | Second | 51 | 18 | 6 | 73.91% |

Trips and forks repeat within workers and workers are drawn from colonies. The label count is a workbook check. These fractions do not estimate an adjusted treatment effect. The published final unmarked test reported `p = 0.65` for prior trail treatment. That GLMM and its multiple-comparison adjustment were **NOT REPRODUCED** here. [Article and author analysis supplements](https://doi.org/10.1371/journal.pone.0149720)

## P04 — trail occupancy and first choice

Exp. 1 uses the unweighted mean of each worker's `Proportion_Frames_MiddleZone` within its path-length and trail treatment group. The sheet has 102 workers and six colony labels. Video frames repeat within a worker.

| Approach | Surface | Workers | Mean per-worker strip frame fraction |
| --- | --- | ---: | ---: |
| Short | Marked | 26 | 0.53892 |
| Short | Solvent | 25 | 0.23722 |
| Long | Marked | 25 | 0.47134 |
| Long | Solvent | 26 | 0.23179 |

Exp. 2 uses the first Y-maze choice and computes success as `decision == phero_side`. All 398 such comparisons matched the workbook's `correct` column. The counts across eight colony labels were ON 88/100, OE 88/100, RE 88/99 and RN 84/99, or **348/398 (87.44%)** pooled. Each experiment has a separate endpoint. The author mixed-effects models were **NOT REPRODUCED** here. The original null effects for the tested approach length, direction and experience contrasts retain their assay-specific interpretation. [Article and source workbook](https://doi.org/10.1007/s00040-026-01106-9)

## P06 — deposition events

S2 uses the eye-scored total `Total_phero_eye` in `exp1`, grouped by prior trail and first-route outcome. There were 504 trial rows, 486 numeric totals and 18 missing values. Numeric zeros count as zero acts. Group means divide summed observed acts by numeric rows.

| Prior trail | First route | Rows | Numeric totals | Marks | Mean marks |
| --- | --- | ---: | ---: | ---: | ---: |
| Marked | Both outcomes | 252 | 241 | 1,663 | 6.9004 |
| Unmarked | Both outcomes | 252 | 245 | 1,823 | 7.4408 |
| Marked | Correct | 126 | 118 | 857 | 7.2627 |
| Marked | Incorrect | 126 | 123 | 806 | 6.5528 |
| Unmarked | Correct | 126 | 124 | 970 | 7.8226 |
| Unmarked | Incorrect | 126 | 121 | 853 | 7.0496 |

S3 uses `pheromone` in `for_analysis`, grouped by runway length. There were 1,248 segment rows with 1,243 numeric counts. There are 104 distinct worker/date/colony label combinations per treatment. A long-path label has nine segment rows and another has eleven, including two rows numbered segment 10. All row IDs are distinct. The recomputation retains both series as exported. Segment rows are repeated measurements within workers and do not provide independent worker or colony replicates.

| Runway | Segment rows | Numeric counts | Missing | Marks | Mean marks per observed segment |
| --- | ---: | ---: | ---: | ---: | ---: |
| Long | 1,040 | 1,039 | 1 | 689 | 0.66314 |
| Short | 208 | 204 | 4 | 75 | 0.36765 |

The article measures acts of deposition. The raw summaries supply no chemical mass or concentration. The author models, including the first-route error and interaction tests, were **NOT REPRODUCED** here. The published error tests were inconclusive for preferentially updating an erroneous branch in that assay. [Article and supplementary workbooks](https://doi.org/10.1007/s00040-024-00995-y)

## P15 — stable full text and the lifetime estimate

The publisher PDF request returned HTML. ETH and UZH discovery endpoints returned catalogue shells. The ULB catalogue identified a scanned copy with intranet restrictions. The directly requested CiteSeerX URL returned 404 during R1. The earlier page-rendering read remains in the access log. The user supplied a complete 490,987-byte PDF during R1. Its file type, authors, title, volume, issue and nine numbered pages (751–759) agree with the publisher record. The digest and this separate reading were added as `B2-ACC-046`. [Publisher record](https://doi.org/10.1007/BF01201674), [ULB catalogue](https://difusion.ulb.ac.be/vufind/Record/ULB-DIPOT:oai:dipot.ulb.ac.be:2013/96662/Details)

On pp. 752–753, a donor colony deprived for four days marks a 10 cm cardboard section leading to 1 M sucrose. The section joins a fresh unmarked branch in a Y leading from a different receiver colony to an empty box. A worker is removed after its choice. The experiment replaces the control, alternates the marked side and changes the receiver colony across age windows of 0–10, 15–25, 30–40, 45–55 and 60–70 min. The lifetime result summarizes six aging trials.

The separate branch-choice fit on pp. 755–756, Eqs. 1–2, uses cumulative mark counts as proxies and 118 early-recruitment time points. It reports an exponent near 2, a baseline of 6 in mark-count units and `r = 0.81`. In the aging assay, let `h` denote the marked-to-unmarked choice ratio and `L0` the initial proxy value. With the fitted exponent 2, baseline `k` and exponential loss rate `a`, Eqs. 3–5 imply `log(sqrt(h) - 1) = log(L0/k) - a*t`. The mean fitted `1/a` is approximately **47 min (SE 9.5 min)** and trial regression correlations range from **0.62 to 0.99**. It is an e-folding time of the inferred behavioral trail proxy. The corresponding half-time under the same model is `47 × ln(2) ≈ 32.6 min`, with a scaled SE of about 6.6 min. Neither quantity measures chemical half-life directly. The paper reports no chemical concentration time series, and trial-level branch counts were unavailable for refitting. The file and published estimates were verified. Both author regressions are **NOT REPRODUCED**. [Original experiment, pp. 752–756](https://doi.org/10.1007/BF01201674)

## Scientific boundary

The descriptive reruns leave all 67 reviewed parameters classified as `ENGINEERING_FIXTURE`, with zero quantitative calibrations. The idealized food sensor and precise route memory remain uncalibrated. The implemented deposition omits observed biological conditions and its field has no chemical-unit calibration or spatial diffusion. In-nest information transfer and colony-level recruitment benefits remain unverified. `FollowTrail` records a software behavior label. Identifying causal cue use requires an experimental contrast. The reviewed negative findings and their applicable experimental conditions remain in the [conflict register](BATCH2_EVIDENCE_CONFLICTS.md) and [validation gaps](BATCH2_VALIDATION_GAPS.md).
