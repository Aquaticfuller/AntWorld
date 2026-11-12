# WP-4 source verification receipt

The source check ran on 2026-11-12 on Windows with Python 3.12.14. Source review and protocol freeze are recorded at `3ce6099`. Local scholarly files remain untracked.

```text
python research/s6_4_preflight/verify_batch1.py --download-dir out/s6_4_preflight/batch1/user_downloads --b01-dryad out/s6_3_3/sources/doi_10_5061_dryad_pnvx0k6wd__v20240209.zip
python tools/build_s6_4_wp4_evidence.py --check
```

The first command exited 0, verified the eight accepted archive/file hashes and recalculated the following endpoints from the original data.

| Source | Verified material or check |
|---|---|
| B01 | 43 retained queens and 127 repeated mesh observations. In the separate founder brood series the first observed worker timing is 62.88 ± 2.52 days, mean ± sample SD across the 17 queens with workers. |
| B03 | 240 original foundress outcomes including four death annotations. All registered day-49 descriptions recalculated from Appendix S1. Appendix S2 model results retain their published analysis scope. |
| B07 | 80 matched census pairs for *L. niger*, 47 for *L. neoniger*. The recomputed sequential diet F statistics were 4.363743 and 0.596697. The tracer file has 32 aliquots from *L. neoniger*. |
| FT01 | Local combined article/supplement hash `2f484eeb42c2d8be96f50beee0110d25956686debcb293e2a7d9eaaa458779e5`. Species and sampling design are reported in the source audit. |

The [original Batch 1 receipt](../s6_4_preflight/BATCH1_SOURCE_VERIFICATION_RECEIPT.md) records the exact local input names, SHA-256 values, material reuse boundaries and unrefitted inferential models.

The B06 PDF and Teggers workbook were separately verified with SHA-256. Opened B06 pp. 166–172, including Table 2 on journal p. 169. The nominal 25 °C treatments reported a realized egg temperature of 24.7 °C. Borisovka had 16.7 ± 0.07 days with range 15–18 (138 reported observations). St. Petersburg had 15.7 ± 0.08 days with range 14–19 (130 reported observations). These counts occur under the paper's within-foundress sampling scheme, and the displayed errors retain the paper's reporting conventions. Warm complete-development means were 41.1 and 39.9 days. The prepupa interval and stage-specific realized temperatures are part of those conditions. [B06 article](https://doi.org/10.1023/B:JOEY.0000033808.45455.75)

| Local input | SHA-256 and reading scope |
|---|---|
| `B_JOEY.0000033808.45455.75.pdf` | `b8f897d22096c1d073a00f992ac7f6700e67c12ae1a79476632d38999a53e3de`. Checked full methods and the phase-specific reporting above. The original census sheets remain `NOT_FOUND`. |
| `41598_2021_82559_MOESM1_ESM.xlsx` | `2b428608b1b6bdc4bdab03688c2efd73a5d17ee1507e284362bd5dbe2579af30`. Read workbook structure with Python `zipfile` and `ElementTree`. The `Benefits Pleometrosis` sheet has dimension `A1:E2593` and 2,593 XML row records. Numerical outcome cells remain sealed. The paper reports handling of excluded founders and July 2017 source dates. |

The [evidence projection](MECHANISM_TRANSITION_PARAMETER_MAP.csv) reuses the accepted integrated tables and their source hashes. BR-01 covers 15 mechanism, 15 transition and 103 parameter references. BR-04 covers 12, 12 and 63 respectively. Shared rows are evaluated in the appropriate mechanism context.
