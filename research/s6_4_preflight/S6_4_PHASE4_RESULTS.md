# S6.4 Phase 4 results

## Review decision

**Phase 4 planning delivered for independent review. Scientific readiness remains blocked.** The frozen literature and source audit is complete. No root blocker was closed, no current parameter was calibrated and no full independent validation set was acquired. All nine BR records retain their original evidence and negative outcomes. The accepted Phase 3 commit is `80fa974689fc15b6deef404e64bf7721c28fe57f`. The C++ tree, model, defaults, state transitions, engineering fixtures, accepted Batch 1–3 and Phase 1–3 evidence and archived observations are unchanged. [Scientific gate](S6_4_SCIENTIFIC_GATE_ASSESSMENT.md)

## What can start after approval

- **RM-01 Egg Timing Technical Assay** is the single recommendation for `GO_FOR_ISOLATED_ENGINEERING_EXPERIMENT`. It uses an opt-in application profile, existing persisted config and committed facts. It requires an old-clock comparator, both warm clocks under the original budget, separately labeled engineering sentinels and controlled durability, conservation and performance checks. There is no approval to change production defaults.
- **RM-05 Biologically Viable Egg Development** remains blocked. Current fixture arithmetic gives 5.79 d of energy and 8.33 d of water. Both are shorter than the B06 reported warm durations of 16.7 d and 15.7 d. Adult and larval absorption does not apply to the egg. These are source-derived implications. The warm-clock experiment with the original budget remains `NOT_RUN` and must retain every result, including deaths. A sentinel hatch can verify timing. Embryo viability requires independent budgets, exposure and full-cohort hatch and competing loss observations.
- **RM-02–RM-10 biological adoption** remains blocked. Required mechanism changes are grouped under BR-01, BR-02, BR-04, BR-05 and BR-07. BR-03, BR-06, BR-08 and BR-09 first test whether bounded simplification and measured inputs predict the required contrasts. Residual error or a failed causal control can require a specific model change. The backlog lists calibration, new-data needs, technical precursors and clearance for each root. [Roadmap](MODEL_REMEDIATION_ROADMAP.md) [Backlog](S6_4_PHASE4_REMEDIATION_BACKLOG.csv) [Authorization matrix](S6_4_PHASE4_IMPLEMENTATION_AUTHORIZATION_MATRIX.csv) [First implementation gate](S6_4_PHASE4_FIRST_IMPLEMENTATION_GATE.md)

## Data acquisition

The targeted search found six partial candidates and no complete matched `VAL-BR-xx` dataset. The public listings and specified file endpoints were screened. New outcome rows were left uninspected. Eligibility still depends on matching the experimental conditions and documenting independent biological lineage. The acquisition plan records the minimum endpoints, grouping and fallback claims for all nine protocols. It consolidates the Fecundity supplement download, DataSuds permission route and B06 and Leckie author-only enquiries. None delays RM-01 after approval. [Acquisition plan and handoff](S6_4_PHASE4_DATA_ACQUISITION_PLAN.md) [Availability register](S6_4_PHASE4_DATA_ACQUISITION_REGISTER.csv)

## Reproduction and CI

Run the ten Evidence commands from the repository root. All ten returned exit status 0 on Windows PowerShell with Python 3.12.14. The Phase 4 verifier checks the approved C++ tree, the nine SHA-256 values in the implementation gate, accepted references, causal prerequisites, package authorization boundaries, acquisition status and parameter status. The Evidence workflow adds the last two commands and preserves its prior steps. The unchanged Core workflow runs its own repository audit, builds, tests and archived comparisons. [Evidence workflow](../../.github/workflows/s6_4_preflight.yml) [Core workflow](../../.github/workflows/ci.yml) [Commit workflow runs](https://github.com/Aquaticfuller/AntWorld/actions?query=branch%3Acodex%2Fs6.4-scientific-evidence-audit)

```powershell
python tools/audit_s6_4_preflight.py --check
python tools/test_s6_4_preflight.py
python research/s6_4_preflight/verify_batch1.py
python research/s6_4_preflight/verify_batch2.py
python research/s6_4_preflight/verify_batch3.py
python research/s6_4_preflight/verify_scientific_integration.py
python research/s6_4_preflight/verify_scientific_priorities.py
python research/s6_4_preflight/verify_scientific_validation_plan.py
python research/s6_4_preflight/test_phase3_validation_plan.py
python research/s6_4_preflight/verify_scientific_gate.py
```

Phase 3 used an inline Python process to apply six in-memory mutations to copies of the accepted records. The committed [test program](test_phase3_validation_plan.py) reruns those mutations, checks the verifier's specific diagnostic and leaves the tracked inputs untouched. The local run reported six tests and `OK`.

| Mutation | Expected rejection |
| --- | --- |
| Remove BR-09's protocol | `exactly one protocol` |
| Substitute B01 for the BR-03 holdout | `BR-03: holdout or execution status overstated` |
| Invent an executed `PASS` for BR-04 | `BR-04: holdout or execution status overstated` |
| Replace a BR-02 accepted source locator | `BR-02: changed accepted source link` |
| Add the egg duration to a second evaluation rule | `PhysiologyConfig.egg_duration: duplicate or incompatible` |
| Split B2-F03 from the shared B2-F01 track lineage | `unexpected fields SplitGroupId` |

Use the workflow runs attached to the Phase 4 commit for remote engineering checks. This phase implemented no C++ assay, performed no new model experiment and made no independent biological comparison. The next action is independent review of the isolated implementation authorization.
