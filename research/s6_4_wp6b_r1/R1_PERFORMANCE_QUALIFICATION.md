# F1-R1 performance qualification

## Unchanged native workloads

The measured C++ source is `0de8a9951090d2120914721e539ba82304593bf7`. The original machine-specific confirmation and Release flags were reused. The first restricted collection stopped before admission because the Windows CIM resource query was inaccessible. Its frozen schedules, identity check and terminal status remain in the archive. The qualified retry used the same source, workload, binary and counter policy. [Pre-admission record](../../experiments/s6_4_wp6b_r1/performance/pre-admission) [Qualified raw rows](../../experiments/s6_4_wp6b_r1/performance/core)

| Native dense advance, 512 → 2,048 | Raw rows | P50 ratio | Bootstrap 95% interval | Paired median and 95% interval | ≤6× |
|---|---:|---:|---:|---:|---|
| TD-01 contact | 336 | 5.3448 | [5.2572, 5.4060] | 5.3270 [5.2721, 5.3587] | PASS |
| TD-08 paid birth registration | 168 | 4.2502 | [4.0955, 4.3548] | 4.2124 [4.1125, 4.3641] | PASS |

All six sessions had qualified telemetry and matched the frozen workload and event signatures. Birth session 2 rejected its first admission with system busy P95 of 22.98%. The 60 raw one-second records, the five-minute separation and the second admission remain available. All timed rows, warm-ups, phase timings and confidence-interval inputs are included. [Native analysis](../../experiments/s6_4_wp6b_r1/performance/core-analysis)

## Observer measurement scopes

The protected workloads exercise the existing observer gate on the unchanged work identities. The application assay measures both F1 versions with identical initial input, daily cuts and authority within a model. It includes actual day-45 segmented publication and exact reopen in both arms. Mandatory output synchronization and optional synchronized cut files count in the measured application total. Capture time measures each foreground cut separately. Optional output synchronization and the SQLite save/reopen have their own measurements.

The process total encloses the child from launch to completion. Subtracting the in-process application total gives an unattributed outer residual that includes launch, command setup, result writing, teardown and OS scheduling. The prior 693.1771 ms process sample had separately measured advance, capture and checkpoint times of about 13.58, 12.68 and 8.88 ms. These fields do not identify the residual. That sample and the original 1.208× and 1.178× nominal medians remain in their original descriptive scope. The application protocol prospectively retains both in-process and process totals against the existing 1.10× and 1.20× limits. Neither profile arm changes care, budget, history or continuation. [Prior profiling](../../experiments/s6_4_wp6b/profiling) [Frozen R1 protocol](FROZEN_R1_PROTOCOL.md)
