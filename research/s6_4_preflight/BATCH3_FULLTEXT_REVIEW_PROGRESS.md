# Batch 3 full-text review

Activity, Rest, Task Allocation, Nest Construction, Environment and Colony Dynamics Scientific Evidence Audit. The accepted input was `1652d092446fff2377b988e6f1326a9cc58f77af` on `codex/s6.4-scientific-evidence-audit`. The Core tree is `277cc8e78cc1acd1cf4a74bf39d08dfdb6a99c69`. Batch 1 and Batch 2 results, original experiments and frozen source inventories are preserved.

## Coverage

| Review | Mechanisms | Transitions | Parameter rows | Previously reviewed | First reviewed here |
| --- | ---: | ---: | ---: | ---: | ---: |
| Batch 1 | 39 | 53 | 163 | — | — |
| Batch 2 | 19 | 19 | 67 | — | — |
| Batch 3 | 17 | 27 | 139 | 92 | 47 |
| Distinct records across the three batches | 75 | 99 | 249 | — | — |

The Batch 3 mechanisms are TSK-01–05, NST-01–08 and POP-01/03/05/06. The source links use the unchanged Step 1-R1 spans, source hashes and anchors. The review counts follow the exact frozen inventory. A struct-family link can record an indirect or metadata-only application. The parameter review distinguishes those links from actual consumers, for example the use of temperature/humidity as care metadata, and protein recycling outside the vacancy calculation.

There are 28 original papers and focal assay contexts in the new register. Twenty-six have a hash-pinned PDF, HTML or XML copy and two were read in publisher body views. Several papers were reread for their new applicability. Their existing Batch 1/2 records remain independent evidence. The 45 access records include failed or restricted routes as well as positive acquisitions and local data reads. The full articles are held outside the repository.

## Domain review

- **Activity, rest and allocation.** T01–T09 compare marked workers, mature bait samples, forced transfers, hunger/recruitment, aggregation under light and ground cues, brood effects, queen care manipulation and age-by-role groups. Observed behaviors vary by individual and context. There is no observed equivalent of the Core's exact depot gate, one-millisecond return wake, fixed lottery weights or shared active-role energy charge. Resting-site choice, inactivity and sleep require different measurements.
- **Construction and environment.** N01–N05, N07 and N08 cover group-size manipulation, shape transitions, substrate effects, pellet handling, thermal CT architecture, fire-ant comparison and surface texture. Local material movement in the Core is functional. Biological morphology, soil mechanics, body posture and environmental response are unvalidated. Ordered geometry, SDF and index operations have engineering endpoints. The *Solenopsis invicta* experiment is cross-species evidence.
- **Colony dynamics and mortality.** P01–P12 cover worker cohort survival, diet and founding, developmental temperature, dormancy, field flood detection, queen signaling, desiccation, founding soil challenge and winter survival. Age, nutrition, season and caste affect different endpoints. A limited reserve ledger and continuous IDs do not identify natural age- or stage-specific death hazards. Population summaries combine living stages and require restriction to match worker census data. External food pulses describe a supplied experimental condition.

Every associated parameter retains F/`ENGINEERING_FIXTURE`. The 92 shared rows record prior review and source references, current use, possible coupling and a separate applicability judgment. Paper DOI overlap is diagnostic only. No current value was calibrated or changed. The 18 conflict/boundary records preserve null results and the unresolved source statistics.

## Deliverables

| File | Review use |
| --- | --- |
| [Original sources and read sections](BATCH3_SOURCE_FULLTEXT_REGISTER.csv) | Species, colony/individual units, conditions, endpoints, measurements, statistics and reading scope |
| [Access log](BATCH3_SOURCE_ACCESS_LOG.csv) | Full-text route, local hash, successful and unsuccessful requests |
| [Mechanisms and state transitions](BATCH3_MECHANISM_EVIDENCE_REVIEW.csv) | Frozen rule, biological comparison, implementation classification and anchored gap |
| [Parameters and shared uses](BATCH3_PARAMETER_EVIDENCE_REVIEW.csv) | Frozen value and unit, old and new context, measurement and applicability |
| [Conflicts](BATCH3_EVIDENCE_CONFLICTS.md) | Empirical contrasts, source limitations and uncertain causal interpretations |
| [Validation gaps](BATCH3_VALIDATION_GAPS.md) | Measurement endpoints and prerequisites by domain |
| [Source verification receipt](BATCH3_SOURCE_VERIFICATION_RECEIPT.md) | Actual commands, pinned inputs, recomputed statistics and scope limits |
| [Public verifier](verify_batch3.py) | Independent coverage, frozen artifacts, cross-domain links, classifications and anchors |
| [Local reproducer](reproduce_batch3_sources.py) | Descriptive flood and dormancy recomputation from original deposits |

## Verification and handoff

```text
python tools/audit_s6_4_preflight.py --check
python tools/test_s6_4_preflight.py
python research/s6_4_preflight/verify_batch1.py
python research/s6_4_preflight/verify_batch2.py
python research/s6_4_preflight/verify_batch3.py
```

The Evidence CI uses tracked material only. The original input archives are local independent checks and are optional for the public workflow. Core CI continues its existing cross-platform workflow. The review endpoint is the Batch 3 domain audit. Cross-domain integration, gap prioritization, parameter-calibration design and the independent biological validation plan require a separate review decision. Core Readiness remains pending.
