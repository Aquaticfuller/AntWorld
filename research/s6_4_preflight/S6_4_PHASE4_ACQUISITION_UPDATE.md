# Phase 4 acquisition update

Recorded 2026-11-11 after Phase 4 submission at `8fae83b4be5cb3a9e66921b1dfaa9c1d7573efc2`. This update records the received files and verification of newly supplied published supporting information. The [Phase 4 acquisition register](S6_4_PHASE4_DATA_ACQUISITION_REGISTER.csv) records availability at the submitted commit.

## Current intake

All six partial candidates have been received and file-verified. Verification of candidate files covered names, archive listings and hashes. The published supporting information reviewed below comes from the existing B3-N05 study. Independent eligibility review of the candidates remains pending.

| Candidate | Comparison to prepare | Admission requirement or outstanding endpoint |
| --- | --- | --- |
| CAND-01 Teggers et al. | BR-01 and BR-08. Review single-foundress brood counts and follow-up. | Match founder cohorts, exposure and censoring. Reserve, uptake and per-egg export remain separate endpoints. [Source](https://doi.org/10.1038/s41598-021-82559-9) |
| CAND-02 ALTAA | BR-05. Group motion by brood presence and group size. | Keep time points nested within groups or source colonies as appropriate. Activity-specific metabolic costs and water loss need linked measurements. [Source](https://doi.org/10.5281/zenodo.16893940) |
| CAND-03 Pasquier and Grüter | BR-06 and BR-07. Route learning and maze performance by food condition. | Keep trials nested within ant and source colony. Local discovery, loaded return and the scout-to-naive chain still need matched observations. [Source](https://doi.org/10.5061/dryad.9j1cp) |
| CAND-04 Wendt et al. | BR-06 and BR-07. Trained feeder choice and pheromone marking. | Preserve repeated trials and source-nest identities. Naive departure, discovery and completed return still need linked observations. [Source](https://doi.org/10.5061/dryad.qz612jm8x) |
| CAND-05 Leckie et al. | BR-09. Screen the cohort and measured coarse geometry tables for control comparisons. | Verify control conditions, source colonies and observation windows. Control CT volumes and linked soil-transport observations remain missing. [Source](https://doi.org/10.5281/zenodo.15353580) |
| CAND-06 Mattens et al. | BR-01. Check for an eligible unmanipulated control for a partial fecundity comparison. | Document the intervention, stage and control definition. The natural reserve and per-egg export endpoints remain open. [Source](https://doi.org/10.17632/dkf9g6prpm.2) |

Use the candidate groupings, measured conditions and sampling hierarchy to freeze the comparison before opening outcomes. [Independent validation plan](INDEPENDENT_BIOLOGICAL_VALIDATION_PLAN.md)

### File verification

The SHA-256 values below were rechecked against the intake receipt. The small archives passed CRC checks. ALTAA and the public Leckie files match the Zenodo MD5 values. The two Dryad bundles contain the expected workbooks and the Mendeley v2 bundle contains all six listed files.

| Candidate | Received artifact | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| CAND-01 | `41598_2021_82559_MOESM1_ESM.xlsx` | 118,346 | `2b428608b1b6bdc4bdab03688c2efd73a5d17ee1507e284362bd5dbe2579af30` |
| CAND-02 | `ALTAA_data.zip` | 2,586,249,758 | `7988bbb831fcd156a0c08645ca8ba480861cf0b6eeb58fe949dbf67c693dd801` |
| CAND-03 | `doi_10_5061_dryad_9j1cp__v20160504.zip` | 98,177 | `ceed6278eaa69028e5917217fb5559896a099521ad5588383cd572622baf6557` |
| CAND-04 | `doi_10_5061_dryad_qz612jm8x__v20200407.zip` | 322,457 | `5cb03929342e95062d06661ee202d41e73f5185958b96fc2ffb6ae4d587b3ab8` |
| CAND-05 | `architectural_immunity_nest_analysis.csv` | 198,164 | `849291610d8b115a83871a6ab056afd0e6b5eda97bef2a2577168db2d2977d51` |
| CAND-05 | `COLONY_INFO.csv` | 4,220 | `92585adf3572e294b127d31feaf9f98dcade5b78f901bbe3d80f19a02e7e2fa4` |
| CAND-06 | `The effect of juvenile hormone on the chemical pro.zip` | 1,258,276 | `8f52f1a2d1515a463a63dc31e477eb41f2803f108581fccfc3e44b9b966e8ff9` |

### Outstanding reference assets

- `REF-ZJTSDI`. The B3-N05 article and published supporting DOCX were received. Access to the DataSuds ODS files has been requested and remains pending. [Dataset request](https://doi.org/10.23708/ZJTSDI)
- `REF-B06-ROWS`. The received PDF's SHA-256 is `b8f897d22096c1d073a00f992ac7f6700e67c12ae1a79476632d38999a53e3de`, identical to the accepted ACC-006 PDF. The original per-egg records and embryo budgets remain outstanding. [Accepted source log](SOURCE_ACCESS_AND_READING_LOG.csv) [Paper](https://doi.org/10.1023/B:JOEY.0000033808.45455.75)
- `REF-LECKIE-CT`. The six files placed in this intake directory were byte-identical copies of the CAND-05 archive. The duplicate directory was removed after verification. Raw control-group micro-CT scans, scan times and segmentation metadata remain outstanding. [Public archive](https://zenodo.org/records/15353580)

## Published B3-N05 supplement

B3-ACC-014 previously used the main article and its references to the supplementary results. The newly supplied publisher file `jane14040-sup-0001-supinfo.docx` has SHA-256 `0cbea1bce233b8c09657db5c86cf9f4c1f0c6f64cf86813d0532219ac47d8c90`. It provides a direct check of Table S3 and the figure captions within the same study lineage. [Accepted source log](BATCH3_SOURCE_ACCESS_LOG.csv) [Paper and supporting information](https://doi.org/10.1111/1365-2656.14040)

**Worker counts.** Table S3 gives start and end counts for 17 colonies. Each printed net change equals end minus start. Mean gains are 260.8 workers in the low-temperature group (5 colonies), 513.67 in medium (6) and 492.0 in high (6). One-way ANOVA on the absolute net changes gives `F(2,14) = 10.4530255054` and `p = 0.0016695184`, reproducing the first statistic in Fig. S10. The colony is the sampling unit and net count change is the endpoint. This supplies published context for BR-09 and BR-08. Individual births, deaths and development rates require distinct observations.

**Depth and geometry.** The captions of Figs. S2–S5 distinguish reconstructed open galleries from inferred refilled regions. The first test in Fig. S9 prints `F(1,18) = 18.099` with `P > 0.05`. The conventional F right-tail probability for these inputs is approximately `0.0004771`. The printed inputs conflict, so the mixed-model time effect remains unresolved. The existing B3-C09 dry-mass and final-depth questions also remain open. [Existing conflict record](BATCH3_EVIDENCE_CONFLICTS.md#b3-c09--underground-gradients-ct-geometry-and-source-statistics)

## Reproduction

Run from the repository root with a local copy of the publisher supplement. The script checks the exact input hash, extracts the published table and caption statistics, reproduces the colony-level ANOVA and evaluates the F tail from the printed Fig. S9 inputs. The first command was verified on Windows with Python 3.12.14. The second verifies the tracked Phase 4 evidence and gate boundaries.

```powershell
python research/s6_4_preflight/verify_published_b3_n05.py out/s6_4_preflight/phase4/intake/jane14040-sup-0001-supinfo.docx
python research/s6_4_preflight/verify_scientific_gate.py
```

The nine matched `VAL-BR-xx` sets still await acquisition and eligibility review. All nine biological blockers remain open. The [RM-01 implementation gate](S6_4_PHASE4_FIRST_IMPLEMENTATION_GATE.md) still requires independent approval for the scoped technical experiment.
