# S6.4 WP-4 results

Approved base `562cd6a65d075e1f3f9de2c5184975d41f104dd6`. Experiment source `24c1ee892a4910bed172a35da0919c6bef4fefde`, Windows Release executable SHA-256 `0e93ebef7f3e0cf42d70e130244a3e09f84ffeed2a9233bd97bd41655ba51066`. The authoritative `cpp/src`, `cpp/include` and `cpp/storage` trees match the approved base. Existing biology, default configurations and historical evidence keep their prior review status.

| Gate | Result |
|---|---|
| Read-only maternal/brood observation and lifecycle reconciliation | 104/104 frozen cases. 8,868,731 canonical facts, 9,524 cuts and 196,238 per-individual budget comparisons. All paired observer-off and SQLite continuation checks pass. |
| Local engineering regression | **PASS**. Debug, Release and standalone ASan/UBSan each pass 243/243. Six independent Python checks pass. The initial sanitizer timeouts remain archived. |
| Controlled performance | Observer **PASS** on 504 admitted rows. Core TD-01 **PASS** at 5.3907× and TD-08 **PASS** at 4.2586×, each on its original workload. |
| RM-04 mechanism diagnosis | **COMPLETE** for frozen conditions. Material export, actual maternal uptake, reserve depletion, reproductive outcome and worker-access coupling are visible. |
| RM-05 mechanism diagnosis | **COMPLETE** for frozen conditions. Original-budget warm egg death, exact technical clocks, and larval nutrition versus stage/terminal survival are distinct results. |
| Biological validation | **BR-01 BLOCKED**, **BR-04 BLOCKED**. Nine BR root issues remain open. |
| Next formal model change | **NOT AUTHORIZED**. The candidate and independent dataset requirements are submitted for review. |

## Observed results

No worker-free ecology world produces an adult. At the original maternal reserve, all 24 worker-free mothers fund two eggs and die of energy depletion at about day 7.87. In the depot assay, 1/6 mothers with eight initial workers and 6/6 with 32 live to day 180. At 32, 451 offspring emerge. The original fixture changes absolute depot stock with worker count. Under ordinary supply, all six 32-worker queens deplete by day 90 despite producing 88 emergences. The first cuts after death have no nest or crop carbohydrate and retain externally available stock. Lower reserves alter both the budget and provision, which prevents identifying reserve effects from colony size alone.

The original warm egg budget runs out of energy at approximately day 5.79, before either published condition-specific clock boundary. The engineered sentinels reach both boundaries and the same-tick depletion controls die. In the known-dose brood assay, the first full-dose larva reaches adulthood on world day 9.25, then dies. Low-protein and no-gift larvae die before pupation. Earlier worker-to-queen receipt leads to a different scheduled uptake pulse under unchanged phase order. These intermediate results are more discriminating than hatch counts or final colony size. [Diagnosis and complete denominators](MATERNAL_AND_BROOD_DIAGNOSIS.md)

## Scientific decision

B06 source verification establishes the daily-census origin and stage-specific conditional means. No public original founder-day sheets were found. Even recovered daily counts would leave unidentified embryo fates and component budgets unless linked observations exist. B01, B03, B07 and FT01 add behavioral, diet, developmental-count and tissue constraints. The observed maternal and larval simulation bottlenecks leave usable initial reserves, actual uptake and allocation, age-specific costs and competing death unidentified in real founding queens and their offspring.

The next candidate is a matched warm-regime study of finite maternal reserves and independently measured egg energy/water budgets. Determine feasibility before changing a biological default. Separate offspring survival from timing among survivors, retain all deaths and censoring, and hold out distinct source colonies for validation. No quantitative target is assigned from an unmeasured flux. [Evidence and gaps](SOURCE_AND_EVIDENCE_AUDIT.md) [Candidate mechanisms](MODEL_CANDIDATES_AND_VALIDATION.md) [Nine-root status](SCIENTIFIC_CLOSURE.csv) [Unsent data requests](DATA_REQUEST_DRAFTS.md)

## Review evidence

[Frozen protocol](FROZEN_PROTOCOL.md), [engineering and native performance](ENGINEERING_AND_PERFORMANCE.md), [source receipt](SOURCE_VERIFICATION_RECEIPT.md), and [reproduction commands and artifact index](../../experiments/s6_4_wp4/README.md). The raw archive retains both negative biological outcomes and the 11 first-pass host observation failures. Eight matched RM-02-R1 controls reproduce their accepted initial and final checkpoint hashes. The first-pass comparison separately confirms all 93 completed raw histories.
