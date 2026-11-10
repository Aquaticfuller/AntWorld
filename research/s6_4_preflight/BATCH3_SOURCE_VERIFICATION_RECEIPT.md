# Batch 3 source verification receipt

## Execution

The local reproducer ran over accepted HEAD `1652d092446fff2377b988e6f1326a9cc58f77af` with Core tree `277cc8e78cc1acd1cf4a74bf39d08dfdb6a99c69`. It executed on 2026-11-10 at 22:03:49 UTC and returned exit status 0. The environment was Windows 11 x64 build 26200, Python 3.12.14 and openpyxl 3.1.5. The command was run from the repository root with the bundled Python executable.

```powershell
& $python research/s6_4_preflight/reproduce_batch3_sources.py > out/s6_4_preflight/batch3/reproduction.json
& $python research/s6_4_preflight/reproduce_batch3_sources.py --pangaea-directory out/s6_4_preflight/batch3/no-such-data-directory > out/s6_4_preflight/batch3/reproduction-negative.json
```

The missing-input control ran at 22:29:40 UTC and returned exit status 1. It marked the flood result `NOT REPRODUCED` and still verified and summarized the dormancy archive.

To reproduce locally, install the workbook reader if needed with `python -m pip install openpyxl==3.1.5 et-xmlfile==2.0.0`. Save the original three PANGAEA text exports as the filenames below and pass their parent directory with `--pangaea-directory`. Use `--dryad-archive` for the named Dryad version. The reproducer checks hashes before reading and emits a status and outputs for both source families. Local source bytes and JSON logs stay outside Git.

| Dataset | Local input name | SHA-256 |
| --- | --- | --- |
| [PANGAEA 865170, 2006](https://doi.pangaea.de/10.1594/PANGAEA.865170?format=textfile) | `flood-2006.tsv` | `67004a4344044c3bc9ac2f5dc46a4ebc9bddf48e52c695df06b5abb18c296daf` |
| [PANGAEA 865171, 2013](https://doi.pangaea.de/10.1594/PANGAEA.865171?format=textfile) | `flood-2013.tsv` | `3ae2b87ae8bdcbf8a59b36bd961f98caf6e736fd88c9f31aeaf410e751502f70` |
| [PANGAEA 865132, duration](https://doi.pangaea.de/10.1594/PANGAEA.865132?format=textfile) | `flood-duration.tsv` | `a640af9bc30519c5d93ae3946311ee74d1c82644456e21572cf94e5a807b92f7` |
| [Dryad, version 2026-04-29](https://doi.org/10.5061/dryad.931zcrk1q) | `doi_10_5061_dryad_931zcrk1q__v20260429.zip` | `0bdbc345a5347cd62c11fd6906c0360f95e97cb3112f9ff8cc5f05ffcf7975dc` |

The three PANGAEA files were obtained in `out/s6_4_preflight/batch3/downloads`. The Dryad archive was previously supplied under `out/s6_3_2_1/manual_downloads`. The script checks three exact archive members as well.

| Archive member | Sheet | Rows before focal-species filter | SHA-256 |
| --- | --- | ---: | --- |
| `data_ctmin.xlsx` | CTmin | 289 | `4f59a5b29fd71d62f7b1482e91aed62d29ad4d2dc6c467f31c909f2c07cb4c03` |
| `data_lte50.xlsx` | Lte50 | 20 | `e5fd43bc7b2ad354c64172116e88d6da205b6df90d462ba26ea3f5b1e76e1565` |
| `data_smr.xlsx` | SMR | 57 | `08c9e92603514816575ec9a8c92058f29f39565cf8a9d393c64f8d9a62b67b2e` |

## B3-P07 field detection

The original export includes the experimental plot, occurrence flag and ant count at the bait. The script skips only the PANGAEA metadata block. It checks matching keys and sums occurrences and counts separately by year. The same 80 plot IDs also match the flood-duration export. No bait count is treated as a colony census.

| Survey | Positive plots | Workers at baits, total | Mean per plot | Range |
| --- | ---: | ---: | ---: | --- |
| 2006 | 68/80 (85%) | 823 | 10.2875 | 0–67 |
| 2013 | 68/80 (85%) | 3,094 | 38.6750 | 0–212 |

Sixty plots were positive in both surveys, four in neither, eight only in 2006 and eight only in 2013. Exposure was 4–24 days with mean 14.2625 and sample SD 4.7674 days. These are descriptive plot statistics. The 30 min surveys differ in carbohydrate bait and year. Species identity is a subsample of the 2013 assay. The authors' generalized linear models and abundance test were **NOT REPRODUCED**. [Article, Results and Data Availability](https://doi.org/10.1371/journal.pone.0152777)

## B3-P06 dormancy and acclimation

The calculation retains rows with `Species == Lasius niger`. CTmin is cessation of movement under a cooling ramp. Observations are individual workers from one focal colony. The script uses ordinary within-condition mean and sample SD, with SD denominator `n - 1`. LTe50 is a reported fit for a 24 h cold exposure with survival read after 24 h of recovery. Its confidence intervals are transcribed from the archive and are not recomputed from individual deaths.

| 10-day condition | Colony state | CTmin worker n | CTmin mean (°C) | Sample SD (°C) | Archived LTe50 and 95% CI (°C) |
| --- | --- | ---: | ---: | ---: | --- |
| 26 °C | Active | 11 | 1.7091 | 0.6766 | −2.18 [−2.82, −1.46] |
| 26 °C | Dormant | 22 | −0.1991 | 0.5861 | −6.64 [−7.25, −6.05] |
| 8 °C | Active | 11 | −0.7764 | 0.3601 | −11.18 [−11.73, −10.60] |
| 8 °C | Dormant | 10 | −3.2870 | 0.4812 | −11.70 [−12.21, −11.03] |

The article prints approximately 1.7 ± 0.64 °C for warm active workers. The archived mean agrees at the displayed precision. The archive's sample SD is 0.6766 °C, so the article's exact dispersion calculation remains unresolved. The SMR unit is µL CO₂ h⁻¹ mg⁻¹ at 18 °C. The six active and five dormant batches yield 0.21967 ± 0.01513 and 0.24100 ± 0.00908, respectively, as means and sample SDs. The paper reports the focal SMR comparison as nonsignificant. Workers and pools are nested observations from a single colony, and active/dormant samples differ in age and season. Author inferential models and dose-survival curves were **NOT REPRODUCED**. [Article, Sections 2.3–2.7 and 3.1–3.3](https://doi.org/10.1111/1365-2435.70359)

## Other source boundaries

The three user-supplied articles for B3-N01, B3-T03 and B3-P12 were checked against their DOI/title and read from the local PDF or accepted manuscript. Their hashes and reading scopes are in the [access log](BATCH3_SOURCE_ACCESS_LOG.csv). B3-N05 CT and soil raw files are restricted in DataSuds and were **NOT REPRODUCED**. B3-P09's previously archived data retain the unresolved status-code and early-censoring limitations. No new survival curve was fitted. The B3-P03 and B3-P04 comparisons use the already verified Batch 1 endpoints and the original articles in the new domain context. [Batch 1 source receipt](BATCH1_SOURCE_VERIFICATION_RECEIPT.md)
