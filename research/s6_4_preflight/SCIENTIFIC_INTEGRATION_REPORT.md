# S6.4 scientific evidence integration

Phase 1 reconciles the three accepted scientific reviews at `4dbafd087592b45d1b29101d67d35b400e388516`. The source inventory uses Core tree `277cc8e78cc1acd1cf4a74bf39d08dfdb6a99c69`. The coverage in this report describes the audit of the current implementation. Claims about biological readiness require independent validation and a later decision.

## Coverage and identity

| Accepted review | Mechanisms | Transitions | Parameter reviews | Source context views | Access records | Conflict records |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Batch 1 | 39 | 53 | 163 | 15 | 42 | 11 |
| Batch 2 | 19 | 19 | 67 | 26 | 46 | 11 |
| Batch 3 | 17 | 27 | 139 | 28 | 45 | 18 |
| Accepted rows | 75 | 99 | 369 | 69 | 133 | 40 |
| Global identities | 75 | 99 | 249 | 61 | 133 | 40 |

The four integrated tables retain all ten biological domains and the shared execution and observation domain. The 249 keys contain 185 declared fields and 64 reviewed in-code rules. The audit verifies all 541 frozen source anchors and the source spans of the declared fields. Parameter roles comprise 97 model settings, 62 execution rules, 54 inputs or fixtures, 17 mode switches, 13 host limits, four metadata fields and two unit conversions. This is the frozen software classification. It supplies the baseline for a later review of biological identifiability.

| Parameter review membership | Distinct keys |
| --- | ---: |
| Batch 1 only | 68 |
| Batch 2 only | 35 |
| Batch 3 only | 47 |
| Batches 1 and 2 only | 7 |
| Batches 1 and 3 only | 67 |
| Batches 2 and 3 only | 4 |
| All three | 21 |

The 99 keys reviewed in multiple batches account for 141 pairwise comparisons. Sixteen pairs cite at least one shared focal source context. Each such context supplies one evidence identity regardless of how many reviews cite it. The frozen associations span multiple domains for 144 of the 249 keys, including some reviewed within a single batch. These associations document the scope of the audit. A family-level association cannot establish that a particular function directly reads every field in the family.

All shared records agree on the source expression, value, unit, role, scope and anchors. For 25 keys, the accepted reviews disagree on whether a biological calibration question applies to the particular use. In the integrated table those keys are `CONTEXT_DEPENDENT`, with both underlying evaluations preserved. Another 120 keys have insufficient evidence for the calibration question raised by their reviews. The remaining 104 were assessed in non-calibration contexts. All 249 retain the original F and `ENGINEERING_FIXTURE` classification. `NO` means the available comparison cannot calibrate the current value. `NOT_APPLICABLE` refers to the recorded use. Neither indicates a measured coefficient.

## How to trace a record

| File | Identity and use |
| --- | --- |
| [Integrated mechanisms](INTEGRATED_MECHANISM_EVIDENCE.csv) | One row per `MechanismId`. Frozen implementation scope and rules are joined to the accepted evidence assessment and linked parameter identities. |
| [Integrated transitions](INTEGRATED_TRANSITION_EVIDENCE.csv) | One row per `TransitionId`. Trigger, guard, consequence and source position are retained. Exact transition parameter keys are identified explicitly. Family and state-group references remain verbatim in `UnexpandedParameterReferences`, and owner associations are listed separately. |
| [Integrated parameters](INTEGRATED_PARAMETER_EVIDENCE.csv) | One row per `ParameterKey`. `UseAssessmentsJson` retains the original 369 reviews, the specific mechanisms in each review, its evidence, measured quantities, conflicts, uncertainty, and scope. `CrossReviewComparisonsJson` identifies shared studies and divergent calibration applicability. |
| [Unified sources](UNIFIED_SOURCE_CONTEXT_REGISTER.csv) | One row per `SourceContextId`, linked to a `GlobalPaperId`. Records contain published conditions, sample size, sample unit, original endpoints, units and uncertainty. `SourceViewsJson` preserves the original source IDs, read scopes, access record IDs and field differences. |
| [Cross-domain conflicts](CROSS_DOMAIN_CONFLICTS.md) | Twelve integrated findings link implementation or endpoint differences, empirical gaps and unresolved source discrepancies back to accepted evidence. |
| [Independent verifier](verify_scientific_integration.py) | Reconstructs the four tables from the frozen audits and checks every output row. `--write` regenerates the four derived CSVs. |

Follow `CitationsJson` or the citation array inside a parameter review from `SourceContextId` to the source register. The `OriginalSourceId` selects the accepted view and its exact article or supplement locator. Apply its `SourceFieldOverrides` to the canonical row to recover the selected metadata. The original source and access filenames also provide a direct audit path. Source records distinguish individual ants, paired trios, groups, source colonies, pooled samples and field plots. They record repeated observations within those units and retain unknown replication counts where necessary. References to the accepted [source anchor register](SOURCE_ANCHORS.csv) preserve the primary and supporting source spans. Declared parameters instead use their recorded declaration owner, exact line span and hash. `FixtureCandidateIndex` points to the [configuration index](FIXTURE_CONFIGURATION_INDEX.csv) for explicit candidate references. The declared value and the indexed fixture assignments have different scopes. Candidate rows can include ambiguous lexical associations and do not determine the effective value of every run.

The register separates **58 publications** from **61 source contexts**. Paper identity uses the DOI, or the accepted title and source URL for the DOI-less Lenoir record. Eight aliases merge repeated focal study contexts and retain their specific scope. The Carthy views share the trained navigation study while retaining the separate vagrance and two-worker timed subsets. The B07 congener tracer, the FT01 supplemental illustrations from a different genus, and the B2-P12 congener branch-choice experiment retain separate contexts under their parent publications. A data dependency also links the reused horizontal tracks in B2-F01 and B2-F03, which have distinct publications.

`MechanismEvidenceClassification` describes the biological comparison. `ImplementationBasis` and `CoreRuleClassification` describe the code. `ParameterEvidenceClass` describes the current parameter and `CitedAtlasGrades` describe source evidence. These fields retain the accepted four-class vocabulary and the separate Atlas A–F scheme. Engineering-only records can have an empty citation field. An Atlas A source can support a measured phenomenon while leaving the implemented probability or coefficient uncalibrated.

`ScientificBlockerStatus` flags specific claims affected by a model discrepancy or missing mechanism. A related record can constrain the comparison without blocking that claim by itself. The field reflects the twelve cross-domain findings and their links to the 40 accepted conflicts. It does not assign the later priority categories or clear any of the existing issues.

## Consistency findings

The three batches contain no disagreement in the frozen rule identities, source anchors, or shared parameter values. After reconciling source aliases, sample units and endpoints, no repeated source yielded a conflicting estimate of the same estimand for the same sample across batches. Printed and deposited source discrepancies remain. The significant focal diet effects and congener net-growth null, the B01 and B02 denominator differences, and the CT statistic and depth comparison issues are visible with their original conditions. [Source discrepancies and retained negative results](CROSS_DOMAIN_CONFLICTS.md#int-c09--diet-endpoints-congener-data-and-statistical-scope)

| Cross-domain question | Phase 1 finding |
| --- | --- |
| Founding, queen care and nutrition | Worker-dependent care plasticity is observed. B01's scan differences and B02's retrieval-count differences remain. Queen crop-to-body supply, founding reserve remobilization and brood-dependent egg allocation have separate missing evidence or rules. [INT-C01 and INT-C02](CROSS_DOMAIN_CONFLICTS.md#int-c01--maternal-and-worker-care-have-distinct-observation-rules) |
| Pheromone and private route experience | Immediate choice, learning after cue removal, in-nest activity, trail persistence and colony benefit have distinct endpoints. The Core records local cue use and private routes. Quantified chemistry, spatial diffusion, and causal recruitment at the colony level remain open. [INT-C04 and INT-C05](CROSS_DOMAIN_CONFLICTS.md#int-c04--local-sensing-route-learning-and-social-recruitment) |
| Work, rest and metabolic cost | Program residence, observed acts and oxygen consumption measure different quantities. The current fixed weights, age-insensitive choices and role-based energy costs lack joint biological validation. Real rest and sleep remain unresolved. [INT-C06](CROSS_DOMAIN_CONFLICTS.md#int-c06--program-choice-observed-activity-and-energy-expenditure) |
| Construction and microenvironment | Experimental nest form depends on group and substrate conditions. The material ledger and clearance verify the software representation. No matched validation establishes chamber and branching patterns, a spontaneous refill rule, or microclimate-driven construction. [INT-C07 and INT-C08](CROSS_DOMAIN_CONFLICTS.md#int-c07--material-movement-and-nest-form) |
| Life history and population outcomes | First observed workers, stage duration, laboratory survival and field bait occupancy use distinct biological units and time origins. Fixed stage clocks and depletion deaths omit seasonal states and age-related survival. [INT-C03](CROSS_DOMAIN_CONFLICTS.md#int-c03--stage-timing-dormancy-age-and-survival) |
| Coupled parameters | Food release, transfer, energy yield, expenditure, development and mortality can compensate in a worker-count curve. Shared reach, dwell and candidate controls also change opportunity and commitment. Aggregate agreement cannot resolve these contributions. [INT-C11 and INT-C12](CROSS_DOMAIN_CONFLICTS.md#int-c11--shared-parameter-interpretation-and-applicability) |

These findings preserve the open scientific issues on recruitment and experience, nutrition and queen provisioning, nest formation, activity and rest, and brood care. The B01 and B02 datasets remain model development evidence. No new biological sample or independent validation was obtained during this integration. [Open questions and scientific debts](../../docs/08_Open_Questions.md)

## Reproduction and checks

Run from the repository root with Python and the approved Git reference available. The public check needs tracked files only.

```sh
python tools/audit_s6_4_preflight.py --check
python tools/test_s6_4_preflight.py
python research/s6_4_preflight/verify_batch1.py
python research/s6_4_preflight/verify_batch2.py
python research/s6_4_preflight/verify_batch3.py
python research/s6_4_preflight/verify_scientific_integration.py
```

The frozen inventory check, seven source anchor tests, three batch checks and integration check returned exit status 0 locally. Six in-memory corruption checks rejected altered global identities, anchor IDs, cross-review inference status and evidence classifications. The Evidence workflow now runs the independent integration check after the accepted checks. It verifies the accepted files against the approved Git tree, rechecks source hashes, and rebuilds the integrated CSV rows for comparison. The Core workflow remains the engineering regression check.

The existing local source-bearing checks also returned exit status 0 on 2026-11-11 CET, using Windows 11 build 26200, Python 3.12.14 and openpyxl 3.1.5. Commands and local input requirements follow the accepted receipts.

```sh
python research/s6_4_preflight/verify_batch1.py --download-dir out/s6_4_preflight/batch1/user_downloads --b01-dryad out/s6_3_3/sources/doi_10_5061_dryad_pnvx0k6wd__v20240209.zip
python research/s6_4_preflight/reproduce_batch2_sources.py
python research/s6_4_preflight/reproduce_batch3_sources.py
```

The rechecks confirmed the B01 per-queen scan means and mesh inclusion counts, the B02 paired counts and markers, all 240 B03 endpoints, the focal and congener B07 net-growth diet F statistics (4.363743 and 0.596697), the B2-F01 trajectory summaries, the B2-P03/P04/P06 data summaries, and the B3-P07 field and B3-P06 dormancy summaries. B2-P15's full-text file matched its hash. Recomputations retain the estimands specified in the receipts. Unavailable raw files or unreproduced author inference remain labeled in the accepted records. Local source PDFs and reproduction logs are untracked. [Batch 1 receipt](BATCH1_SOURCE_VERIFICATION_RECEIPT.md) [Batch 2 receipt](BATCH2_SOURCE_VERIFICATION_RECEIPT.md) [Batch 3 receipt](BATCH3_SOURCE_VERIFICATION_RECEIPT.md)

The integration is ready for independent Phase 1 review. Priority assignment, identifiability and independent validation protocols, remediation sequencing and a scientific gate assessment await the subsequent phases.
