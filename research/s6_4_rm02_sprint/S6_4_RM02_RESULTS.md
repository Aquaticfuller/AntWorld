# S6.4 RM-02 integrated engineering sprint

Baseline `6f6a69f45b0fff0ba3227039de36158b0994cbc4`. Protocol frozen at `8ca0705f3282c1de227e9b30046ae6949459fbdb`. Branch `codex/s6.4-rm02-integrated-engineering`. The C++ Core source, public headers and authoritative storage match the protected baseline.

| Status | Result | Scope |
| --- | --- | --- |
| `RM02_OBSERVER_ENGINEERING` | `ENGINEERING_PASS` | Read-only correctness, explicit observation coverage, canonical fact bytes, RNG and authoritative checkpoint identity, failure and recovery. All 222 local CTests passed in each of Debug, Release and ASan/UBSan |
| `RM02_PERFORMANCE` | `FAIL` | TD-01 5.4044× and TD-08 4.2868× passed. All final observer P50/P95 and foreground cut budgets passed. Final durable drain exceeded 20 ms in five admitted rows across dense-2,048 and depot-32 |
| `RM02_BASELINE_DIAGNOSIS` | `BLOCKED_BY_PERFORMANCE_GATE` | Frozen 72-case population and supply matrix unstarted. Reproduction and independent analysis tools retained |
| `BR02_BIOLOGICAL_VALIDATION` | `BLOCKED` | Focal literature supports observed oral interactions. A matched independent risk set, per-component positive and zero doses and crop/body uptake data are missing |
| `NEXT_MODEL_CHANGE_AUTHORIZATION` | `NOT_AUTHORIZED` | The proposed local recipient-cue contrast remains a prospective experiment for independent review |

The observer preserves scoped committed events with stable actor, recipient and schedule identities. Detached cuts include crop, body energy, water, tissue and an exact conservation ledger. The separate versioned SQLite file has a chained digest and an authoritative checkpoint anchor. Bounded background writes retain the durable prefix on failure. Successful replay preserves the event stream and the future queue, and explicit statuses distinguish failed requests, missing scope and censored observations.

Three complete observer batches each retained 504 rows. The first two expose measured long-run median and synchronous-publication issues. The final implementation addresses the median and per-cut interruption limits. Its remaining failure is the measured tail of durable completion. A new performance disposition requires review of the applicable storage path or an independently approved terminal completion criterion. The frozen analysis and its negative evidence are preserved. [Engineering results](RM02_ENGINEERING_ACCEPTANCE.md) [Raw performance and telemetry](../../experiments/s6_4_rm02_sprint/performance/)

The scientific comparison retains the differences between oral contacts, actual nutrient masses, measured compartments and colony outcomes. It includes a bounded, falsifiable recipient-choice proposal, separate data requirements for dose and uptake, and reuse of the read path for RM-03, RM-06 and RM-07. [Evidence and candidate model](SCIENTIFIC_EVIDENCE_AND_GAPS.md)

## Review index

| Stage | Commit or artifact | Review scope |
| --- | --- | --- |
| A | `5bc8defced10f7c04d43b5240b801e5195f51aac`, [implementation and format](STAGE_A_OBSERVER.md) | Host-only reader, first independent sidecar and correctness cases |
| B | `a1c326b604bed0cc7db67f46ff0b9682b4ec4cf9`, [engineering report](RM02_ENGINEERING_ACCEPTANCE.md), [reproduction](ENGINEERING_REPRODUCTION.md) | Final code identity and measured workloads, earlier failed versions retained |
| C | [Baseline status](RM02_BASELINE_DIAGNOSIS_STATUS.md), [frozen analysis method](BASELINE_ANALYSIS_METHOD.md) | Independent entry gate decision and ready-to-run tools |
| D | [Scientific evidence and next experiment](SCIENTIFIC_EVIDENCE_AND_GAPS.md) | Primary source check, measurement gap and no adoption |

The [Core CI run for the measured source](https://github.com/Aquaticfuller/AntWorld/actions/runs/43101363752) includes the unchanged inherited workflow and the independent sidecar decoding and reconciliation. The same Core tests apply to the final review branch.
