# S6.3.2.1 file index and reproduction

All content is English; original bibliographic titles and proper names identify sources. Full papers, extracted full text, original workbooks and rendered source pages are local ignored acquisition material under `out/s6_3_2_1`, not public repository content. The Dryad CSV exports are factual CC0 data with explicit provenance. No credentials, authenticated browser session or copyrighted article is needed for CI.

## Requested delivery index

| File | Purpose |
|---|---|
| [ANT_BIOLOGY_EVIDENCE_ATLAS.md](../../ANT_BIOLOGY_EVIDENCE_ATLAS.md) | Scientific synthesis, grade boundaries and coverage |
| [SPECIES_DATABASE.csv](../../SPECIES_DATABASE.csv) | 15 separate species boundaries and source locators |
| [CASTE_LIFE_STAGE_MATRIX.csv](../../CASTE_LIFE_STAGE_MATRIX.csv) | 22 frozen caste/stage slots with unknowns and DOI/locators |
| [BEHAVIOR_EVIDENCE_DATABASE.csv](../../BEHAVIOR_EVIDENCE_DATABASE.csv) | Measured/qualitative behavior endpoints |
| [ENVIRONMENT_RESPONSE_DATABASE.csv](../../ENVIRONMENT_RESPONSE_DATABASE.csv) | Environmental endpoints, controls and original units |
| [PHYSIOLOGY_DATA.csv](../../PHYSIOLOGY_DATA.csv) | Physiological observations, source fits and missingness |
| [PARAMETER_PROVENANCE.csv](../../PARAMETER_PROVENANCE.csv) | Complete existing configuration inventory plus implicit source contexts |
| [STATE_MACHINE_EVIDENCE_AUDIT.md](../../STATE_MACHINE_EVIDENCE_AUDIT.md) | 70 rule groups, actual conditions/functions, evidence and proposals |
| [MODEL_VALIDATION_CATALOG.md](../../MODEL_VALIDATION_CATALOG.md) | 20 planned matched replications, capability and data separation |
| [CONTRADICTIONS_AND_GAPS.md](../../CONTRADICTIONS_AND_GAPS.md) | Source discrepancies, model conflicts, nulls and gaps |
| [MODEL_CORRECTION_ROADMAP.md](../../MODEL_CORRECTION_ROADMAP.md) | Review-only priorities and mathematical candidates |
| [BIBLIOGRAPHY.bib](../../BIBLIOGRAPHY.bib) | Complete adopted bibliographic metadata and DOI |
| [ANT_BIOLOGY_EVIDENCE.sqlite](../../ANT_BIOLOGY_EVIDENCE.sqlite) | Relational, indexed projections including licensed raw data |
| [S6_3_2_1_RESULTS.md](../../S6_3_2_1_RESULTS.md) | Actual verification, limitations and stage conclusion |

## Canonical inputs and projections

`sources.json`, `measurements.json`, `coverage.json`, `rules.json`, `validation.json`, `conversions.json`, `search_log.json`, `manual_receipts.json`, `acquisition_receipts.json` and `channel_access.json` are curated UTF-8 evidence inputs. Acquisition receipts preserve earlier access attempts, including failures; a FETCHED receipt does not establish reading. The source register is the final reading-status authority. N01–N27 extend the inherited B01–B22 namespace.

Generated `SOURCE_READING_REGISTER.csv`, `MEASUREMENTS.csv`, `COVERAGE.csv`, `RULES.csv`, `SOURCE_RULE_INVENTORY.csv`, `UNIT_CONVERSIONS.csv`, `MANUAL_ACCESS_RECEIPTS.csv` and `summary.json` are reviewable projections. `behavior_facets.json` and its `BEHAVIOR_FACETS.csv` projection explicitly track trigger/probability/duration/termination/individual-variation evidence and unknowns for all21 behavior slots. Root domain tables are subsets of MEASUREMENTS, not additional independent observations. The implicit scanner is lexical, not an AST; source expressions include engineering validation constants. Context-only records must not be treated as biological scalars.

`raw/manifest.json` maps each CSV to dataset DOI, exact source workbook SHA256, sheet, original column labels and source-row numbers. It contains five exports: N07_survival432, N10_ctmin289, N10_lte5020, N10_smr57 and N10_condition_means20 rows. The last table overlaps other endpoints. Full metabolomics/CHC/DSC data are not claimed as extracted; their workbooks remain local. No source workbooks were edited. `NOT_RECORDED` represents an empty workbook cell; literal `NA`, zeros and status codes are retained.

`figures/` contains three original plots of the structured data, not reproduced paper figures. `verification/` contains the actual local build/test receipts and logs. The old root parameter file is preserved byte-for-byte in [the S6.3.2 snapshot](../../experiments/s6_3_2/PARAMETER_PROVENANCE_S6_3_2.csv); the old builder now targets that snapshot. Historical A–D grades remain separately namespaced rather than reinterpreted as new A–F grades.

## Reproduction commands

From the repository root, with Python3.11+ (stdlib only):

```text
python tools/build_s6_3_2_1_atlas.py
python tools/build_s6_3_2_1_atlas.py --check
python tools/provenance_s6_3_2.py --check
python tools/ci_verify.py
```

The atlas check validates stable IDs, DOI/species/grade compatibility, locators, all119 declared fields, immutable Core/header/app/test hashes, raw CSV hashes, function anchors, generated files, SQLite integrity/foreign keys and logical database equality. It cannot prove a paper's biology is true. Logical SQLite comparison avoids version-dependent page-layout claims. No network or copyrighted source file is required to reproduce the committed atlas.

Optional fresh dataset acquisition: obtain the official archives for [N07](https://doi.org/10.5061/dryad.k98sf7m8n) and [N10](https://doi.org/10.5061/dryad.931zcrk1q), keep them outside tracking, install openpyxl3.1.5 in an isolated environment, then run:

```text
python tools/import_s6_3_2_1_datasets.py out/s6_3_2_1/manual_downloads
python tools/build_s6_3_2_1_atlas.py --check
```

The importer verifies exact source hashes and reads values without executing macros or modifying workbooks. Install matplotlib3.10.7 for optional illustrations, then `python tools/plot_s6_3_2_1_atlas.py`. The runtime version actually used is recorded in the stage results; figures do not supply fitted coefficients or alter canonical data. [fetch_s6_3_2_1_sources.py](../../tools/fetch_s6_3_2_1_sources.py) is an optional acquisition helper, not a bypass for unavailable institutional access.

Portable inherited Core verification (CMake3.31+, C++20 compiler and existing pinned SQLite acquisition):

```text
cmake -S cpp -B build/atlas-debug -DCMAKE_BUILD_TYPE=Debug
cmake --build build/atlas-debug --parallel 4
ctest --test-dir build/atlas-debug --output-on-failure
cmake -S cpp -B build/atlas-release -DCMAKE_BUILD_TYPE=Release
cmake --build build/atlas-release --parallel 4
ctest --test-dir build/atlas-release --output-on-failure
cmake -S cpp -B build/atlas-sanitized -DCMAKE_BUILD_TYPE=Debug -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ -DANTWORLD_SANITIZERS=ON
cmake --build build/atlas-sanitized --parallel 4
ctest --test-dir build/atlas-sanitized --output-on-failure
```

For a multi-configuration generator use `--config Debug/Release` and `ctest -C Debug/Release`. The actual Windows verification reused the unchanged, already configured `build/s6_3_2-{debug,release,sanitized}` directories; exact commands and logs are in verification/local.json. Windows ASan uses detect_leaks=0; Linux CI enables leak detection. This data-only stage does not rerun noisy wall-clock performance trials or claim fresh performance acceptance. Prior controlled qualification and all failures remain linked in S6_3_2_PERFORMANCE_RESULTS.md.
