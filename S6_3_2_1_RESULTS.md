# S6.3.2.1 — Comprehensive Ant Biology Evidence Atlas

## Conclusion and scope

**Engineering/evidence reproducibility: PASS. Evidence atlas: CONDITIONAL PASS for independent review. Biological completeness/calibration: NOT PASSED; no S6.4 readiness claim.** This stage creates the requested research foundation and maps the unchanged model, while explicitly retaining missing measurements, source discrepancies and incomplete behavioral mechanisms. It does not declare that49 papers or passing software tests establish realistic ant biology.

Branch: `codex/s6.3.2.1-biology-evidence-atlas`. Baseline: `2e1a5fa129821176954f26a88f56791635bc8cda`. Protocol: [document51](docs/51_S6_3_2_1_Evidence_Atlas_Protocol.md), frozen in `765032d`. No Core/header/application/test file, biological parameter, RNG decision, scheduler semantics, resource transfer, geometry or historical event was changed. All162 inherited tests and all S0–S6.3.2 negative experiments remain. No parameter fitting, biological correction, new weather, species simulation, Game Master or Unity work occurred.

## Delivered evidence and coverage

All13 requested atlas artifacts and this report are indexed with reproduction commands in [research/s6_3_2_1/README.md](research/s6_3_2_1/README.md). The main scientific entry is [ANT_BIOLOGY_EVIDENCE_ATLAS.md](ANT_BIOLOGY_EVIDENCE_ATLAS.md). SQLite, CSV, BibTeX and generated audit documents derive reproducibly from curated JSON and licensed factual CSV exports.

| Audit quantity | Completed scope | Important limit |
|---|---:|---|
| Adopted references |49 | Targeted broad search, not a database-exhaustive systematic review |
| Full text with relevant selected sections actually read |47 | Does not mean every supplement or entire bibliography was read |
| Abstract/first page only |1, N03 | User-supplied instar paper contains p9 only; full pp9–13 unavailable |
| Original accessed through secondary compilation |1, B22 | Original chemistry paper not falsely labelled read |
| Separately represented species |15 | Other-species records do not calibrate L. niger |
| Curated endpoints |292 | A217/B38/C21/D15/E1; includes qualitative, negative, approximate and fitted endpoints |
| Licensed repository rows |818 |432 survival,289 CTmin,20 fitted LTe50,57 pooled SMR,20 overlapping summaries; not818 independent experiments |
| Frozen coverage slots |84 |40 direct quantitative,9 additional direct qualitative/observational,35 partial/extrapolated/abstract/theoretical/unknown |
| Behavior facets |21/21 | Trigger, probability, duration, transition/termination and individual variation explicitly separate; many UNKNOWN |
| Config-field inventory |119/119 (100%) |16 structs; inventory/audit completion is not calibration completion |
| Parameter/context records |2,559 |1,209 expressions +469 supplemental contexts +881 implicit lexical lines; not independent scalar parameters |
| Reviewed mechanism groups |70/70 with verified function anchors | Includes14 implementation/helper files; lexical scan is not a C++ AST proof |
| Parameters newly fitted or adopted |0 | All current biological coefficients remain F / ENGINEERING_FIXTURE |
| Replication designs |20 | Capability PARTIAL/NOT IMPLEMENTED/NOT TESTABLE; none executed as new biological validation |

Direct-quantitative endpoint coverage is11/22 life-stage slots,14/21 behaviors,6/16 environmental variables and9/25 physiological endpoints. This measures **presence of some relevant measurement**, not completeness of all mechanisms/conditions in a slot. Full reading list, DOI, species, sample/control conditions, pages/figures/tables and extraction limitations are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv). N19 is an explicitly unreviewed preprint. All44 recorded searches, access outcomes and user-supplied document hashes remain available. WoS/Scopus returned403 through the available web interface; Scholar and authenticated browser routes were unavailable. Institutional access was not claimed merely because the machine is on a school network. User-supplied publisher PDFs and two official Dryad archives resolved the principal missing full texts/data.

## Scientific findings and boundaries

**Direct biological basis:** founding queen care and reversible worker-dependent specialization; condition/brood-dependent reproductive allocation; population/stage-specific thermal development and cold larval arrest; caste-related respiration; heterogeneous local trophallaxis; food/brood-dependent intake and marking; local trail/memory responses; and substrate-sensitive movement/construction. These are source-specific mechanisms/endpoints, not evidence for arbitrary implementation constants.

**Quantitatively usable candidates:** B06 first-brood temperature/duration tables and egg-only published fits; N14 intake/drinking-time distributions and authors' stopping-volume fits; N01 contact durations with source-statistic cautions; N25 projected kinematics; and N27 direct caste/device respiration tables. Matching observation protocols, units, sample structure and missing states must precede calibration. No per-egg nutrient cost, gut absorption coefficient, queen feeding dosage, individual within-L. niger mass exponent or long-distance recruitment probability is identified here.

**Reasonable engineering approximations:** conserved crop/body separation, funded offspring with the retained local reserve guard, finite memory, local scalar trails, bounded social encounters and explicitly finite resource sources. Their quantitative biology remains unvalidated. The two-day maternal horizon is not a measured constant.

**Conflicts/omissions:** the queen's permanent Worker-only care prohibition conflicts with direct maternal-care experiments; environment-independent seven-day supplied-tissue development does not match B06; unconditional loaded-move marking omits experimentally conditional signal production; homogeneous caste/stage physiology lacks a justified compartment/mass model. Fixed task weights, quarter-capacity urgency, half-crop intake, exact neighboring stores and perfect route replay remain unmeasured rules. See the70-group [source audit](STATE_MACHINE_EVIDENCE_AUDIT.md).

The newly supplied N27 full paper establishes that the cited allometric coefficients were fitted across three species and pooled workers. They must not be relabelled as species-specific individual constants. N27's oxygen device/temperature confounding, unreliable RQ, table/text sample differences and arithmetic conversion discrepancy remain visible. N07's raw status0/1 conflicts with the README1/2 legend; early deaths are interval-uncertain. These are retained, not silently corrected into clean-looking biological curves. N14 endpoint-specific samples and zero-intake detection limits, N25 fine-substrate caption differences, mixed-species field observations and all null results are documented in [CONTRADICTIONS_AND_GAPS.md](CONTRADICTIONS_AND_GAPS.md).

## Verification actually executed

Windows used the existing pinned LLVM-MinGW20261104 / Clang23.1.5, CMake3.31.10, Ninja1.13.2 and SQLite3.54.1 configurations. Builds completed with no source rebuild required. Actual CTest elapsed times below are from retained logs, not performance qualification samples.

| Check | Result |
|---|---|
| Windows Debug |162/162 PASS;67.32s |
| Windows Release |162/162 PASS;13.55s |
| Windows ASan + UBSan |162/162 PASS;255.48s; Windows leak detection disabled as unsupported |
| Complete inherited evidence audits, tools/ci_verify.py |PASS; all old negative/performance records preserved and reconciled |
| Final atlas builder and --check |PASS; source/grade/locator/field checks, raw hashes, generated equality and SQLite integrity/FKs |
| Immutable source identity |64 Core/header/app/test files match the inherited normalized manifest; git diff of cpp is empty |
| Old parameter reproducibility |PASS; original1,678-row matrix preserved in versioned legacy snapshot |
| Figure QA |Three original plots rendered and visually inspected; source means/errors are not invented |
| GitHub Actions |Publication workflow tracked by branch and delivery commit; final receipt is research/s6_3_2_1/verification/github_ci.json |

Local commands, stdout and hashes are in [verification/local.json](research/s6_3_2_1/verification/local.json). The full inherited evidence audit and the final smaller atlas checks are separate receipts because the latter includes the final source-extraction review. Existing SQLite recovery, single-writer rollback, stable identity, geometry/barriers, deterministic scheduling, conservation and restore regressions are preserved. Linux sanitizer CI enables leak detection. Data acquisition used read-only openpyxl3.1.5; figures used matplotlib3.10.7. CI reconstruction uses stdlib only and does not need papers or proprietary spreadsheet software.

No new noisy timing campaign was run in this data-only stage. Prior controlled contact5.418486x and funded-birth4.169260x results remain workload-specific passes under <=6x, alongside the original incomplete birth series,6.315x/8.154x failures and unexplained24.229x anomaly. Broader moving-colony/birth/history scaling and long-term storage remain open. No behavior, contact or historical record was reduced for speed.

## Remaining work and stop gate

SD-04 nutrition allocation, SD-06 nesting, SD-07 activity, SD-08 queen provisioning/allocation, SD-09 physiology/development, SD-01/02 trails and TD-01/03/04/05/06/08 remain tracked in [Open Questions](docs/08_Open_Questions.md). Key missing data include egg composition/cost, usable reserves through founding, nutrient absorption, queen-directed transfer mass, individual worker mass/age distributions, instar-specific development/mortality, water flux and occupied-chamber humidity/temperature. First-page-only N03 and ambiguous published statistics prevent stronger claims; no values are filled from intuition.

The [correction roadmap](MODEL_CORRECTION_ROADMAP.md) retains P01–P10 as independent review proposals with simple mathematical candidates and matched experiments. Founding care, physiological measurement/compartments, temperature-dependent development and calibration/validation separation block a biologically ready Core claim. Select and approve a small proposal before implementation; do not use survival to90/180days or maximal emergence as a hidden fitting target. Stop after this branch for independent review. No automatic S6.3.3, S6.4 or Unity work.
