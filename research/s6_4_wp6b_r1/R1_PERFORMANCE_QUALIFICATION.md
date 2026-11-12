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

## Protected observer

All 504 scheduled rows were measured. The inherited analysis retained 432 post-warm-up rows and compared the original workload identities. The first session rejected its first admission with system and selected-core P95 load at 31.30% and 31.72%. Its complete rejection and accepted retry remain in the raw archive.

| Workload | Total P50 / P95 on to off | Foreground P95 / max (ms) | Paired peak RSS increase (MiB) | Max final drain (ms) | Gate |
|---|---:|---:|---:|---:|---|
| Dense-512 | 1.0602 / 1.0718 | 1.1636 / 1.8928 | 1.8867 | 6.1860 | PASS |
| Dense-2048 | 1.0268 / 1.0236 | 2.3738 / 2.4486 | 1.7383 | 24.6419 | PASS |
| Depot-32 | 1.0704 / 1.0934 | 0.9505 / 6.0201 | 2.8594 | 5.4954 | PASS |

The 24.6419 ms drain is retained and included in the durable total. The 20 ms ceiling applies to foreground capture and submission under the previously reviewed protocol. [Raw admissions, telemetry and timings](../../experiments/s6_4_wp6b_r1/performance/protected-observer) [Protected analysis](../../experiments/s6_4_wp6b_r1/performance/protected-observer-analysis.json)

## F1 application observer

**FAIL** under the preregistered application and process scopes. All 480 rows across three qualified sessions are retained. The first session rejected one admission at 24.45% system busy P95. Across all cells the largest foreground P95 and maximum were 0.3999 and 5.6169 ms. The largest paired RSS increment was 3.8145 MiB. Seventeen of twenty cells met every gate.

| Frozen cell | Model | Application P50 / P95 | Process P50 / P95 | Gate |
|---|---|---:|---:|---|
| Borisovka nominal founder | F1 v1 | 1.0861 / 1.0965 | 1.0779 / 1.0747 | PASS |
| Borisovka nominal founder | F1-R1 | 1.0985 / 1.0843 | 1.0918 / 1.0893 | PASS |
| St. Petersburg nominal founder | F1 v1 | 1.1125 / 1.0609 | 1.1139 / 1.0552 | FAIL, median total |
| St. Petersburg nominal founder | F1-R1 | 1.0945 / 1.7878 | 1.0838 / 1.7224 | FAIL, tail total |
| Borisovka depot, 8 workers | F1 v1 | 1.0227 / 0.9427 | 1.0382 / 2.1210 | FAIL, process tail |

The R1 St. Petersburg long sample is session 1, sample 95. Its application total was 272.680 ms, of which advance was 31.206 ms, daily capture 19.167 ms, midpoint save 49.275 ms, midpoint reopen 87.634 ms, and mandatory and optional file sync 25.844 and 4.757 ms. These phases record separate sources of elapsed time. The child and whole-process totals were both affected. The Borisovka depot v1 long sample is session 3, sample 23. It completed its measured application work in 628.547 ms and took 1,790.069 ms at the process boundary. The 1,161.523 ms outer residual is not attributable to a particular operation from the available trace. Both rows remain in their original positions. The earlier 693 ms result is also preserved. No sampling rule or budget was revised in response. [Raw application timing and telemetry](../../experiments/s6_4_wp6b_r1/performance/application-observer) [Cell ratios and uncertainty](../../experiments/s6_4_wp6b_r1/performance/application-observer-analysis)

All 480 measured runs match their respective uninterrupted archive's input, initial checkpoint, terminal frame and canonical fact SHA-256. This includes every observed and unobserved restart. The 10 cells in each model are traceable to the original formal inputs. [Reference equivalence](../../experiments/s6_4_wp6b_r1/performance/application-costs/reference_equivalence.json)

| Observed nominal seed 1 | Facts | Frame (B) | Advance P50 (ms) | Advance per fact (µs) | Midpoint save / reopen P50 (ms) |
|---|---:|---:|---:|---:|---:|
| Borisovka v1 | 10,004 | 25,886 | 9.74 | 0.974 | 31.55 / 41.67 |
| Borisovka R1 | 12,798 | 29,168 | 16.04 | 1.253 | 31.98 / 44.66 |
| St. Petersburg v1 | 9,857 | 25,886 | 9.56 | 0.970 | 32.31 / 40.69 |
| St. Petersburg R1 | 14,747 | 30,291 | 19.42 | 1.317 | 31.86 / 42.49 |

The fixed frame addition for the configuration and witness is 36 bytes. Different hatch, feeding, development and worker activity histories change work and frame size across versions. Per-fact normalization describes the changed workload mix and cannot isolate CPU overhead of the added draw or state. The phase summary records setup, advance, capture, encode, sync, save, reopen and peak RSS at P50, P95 and P99 for each cell and treatment. [Application phase summary](../../experiments/s6_4_wp6b_r1/performance/application-costs/phase_costs.csv)
