# F1 performance and replay verification

Protected runtime qualification uses the unchanged TD-01 and TD-08 workloads and the accepted observer workloads. The native collection holds each binary and workload identity, fixed per-core admission, ABBA/BAAB order and original limits. The contact and birth growth gate remains ≤6× at 512 to 2,048 workers. The protected observer gate includes total wall time and real durable writes, with the final drain measured separately. [Frozen protocol](FROZEN_PROTOCOL.md) [Original benchmark acceptance](../s6_4_wp5/ENGINEERING_VERIFICATION.md)

## Protected native results

The six admitted contact and birth sessions retained all 504 scheduled rows, 336 contact and 168 birth. Five sessions admitted on the first attempt. The first birth admission had selected-core background P95 of 26.73% against 20%. The controller kept all 60 samples, waited the prescribed interval and admitted the second attempt before it timed any birth rows. Every measured workload matched the frozen identity, including exact continuation and the birth/reserve control at all three populations. The receipt binds the portable implementation at `f1aca01d860c7c0c4a51607d013039c453f682b1`. [Raw native measurements](../../experiments/s6_4_wp6b/performance/core) [Admission reconciliation](../../experiments/s6_4_wp6b/performance/core_analysis/admissions.csv)

| 512 to 2,048 workload | P50 ratio | Bootstrap 95% interval | Paired median | Paired 95% interval | Gate |
|---|---:|---:|---:|---:|---|
| TD-01 dense contact advance | 5.3468× | 5.2272–5.5046× | 5.3084× | 5.2442–5.3929× | PASS |
| TD-08 dense birth advance | 4.3599× | 4.2886–4.4533× | 4.2919× | 4.2126–4.4058× | PASS |

Setup, encode, restore and dispersed workloads remain separately identified. Raw phase and CPU-cycle rows, admission failures, sensor mapping, HWiNFO extraction hashes and exact binary fingerprints are retained. The public export excludes unrelated process inventories. [Growth and confidence intervals](../../experiments/s6_4_wp6b/performance/core_analysis/growth.csv)

All three native observer sessions admitted on the first attempt, with valid telemetry. The collection retained 504 timing rows, including the fixed warmups. The accepted analysis uses 432 rows after warmup exclusion. Off/off repeatability, exact checkpoint and history identities and every unchanged budget passed. [Raw observer measurements](../../experiments/s6_4_wp6b/performance/observer) [Observer analysis](../../experiments/s6_4_wp6b/performance/observer_analysis.json)

| Workload | Total P50 on/off | Total P95 on/off | Foreground P95 / max (ms) | Peak RSS increment (MiB) | Maximum final drain (ms) |
|---|---:|---:|---:|---:|---:|
| Dense 512 | 1.0620× | 1.0678× | 1.2029 / 1.5733 | 1.6562 | 2.9650 |
| Dense 2,048 | 1.0227× | 1.0026× | 2.9831 / 5.1625 | 1.6484 | 5.0921 |
| Depot 32 | 1.0736× | 1.0220× | 1.1777 / 12.0271 | 2.8125 | 4.5189 |

## Candidate workload costs

The independent F1 profiling batch used the frozen nominal foundress case for each population and both 8/32-worker depot and empty cases for seed 1. Each case had four observed and four unobserved launches in ABBA/BAAB order, plus one observed launch with a day-45 SQLite publication and reopen. All 90 launches matched the initial checkpoint, final frame and every canonical fact byte for their respective case. Observation on/off concerns exported census data. Maternal care remained enabled in all these profiling launches. The ten profiled canonical identities also match the original formal collection across the include-only build correction. [Frozen profiling identity](../../experiments/s6_4_wp6b/profiling/freeze.json) [Paired raw samples](../../experiments/s6_4_wp6b/profiling/samples.csv) [Cross-build hashes](../../experiments/s6_4_wp6b/profiling/cross_build_identity.json)

| Observable across measured F1 cases | Minimum | Median | Maximum |
|---|---:|---:|---:|
| Committed facts | 9,857 | 97,891 | 373,503 |
| Sampled pending queue | 25 | 48 | 121 |
| Observed run advance (ms) | 12.53 | 213.17 | 890.90 |
| Final frame (bytes) | 25,886 | 43,046 | 93,950 |
| Canonical stream (bytes) | 1,806,611 | 18,910,612 | 73,145,928 |
| Observed peak process RSS (MiB) | 10.82 | 65.27 | 232.91 |
| Midpoint full checkpoint plus SQLite save (ms) | 39.94 | 282.09 | 1,193.42 |
| Midpoint reopen and exact full-checkpoint comparison (ms) | 52.22 | 715.18 | 3,787.70 |

The reserve record is 40 bytes per enrolled identity before container overhead. Its serialized entry is 48 bytes including the ID. Each refill and funded transfer is tied to an existing owner boundary. There is no separate decision queue for F1. Full export and replay costs grow with retained history. The published frame itself omits fact bytes and carries its verified prefix binding. The sampled queue peaks are measured at the fixed daily cuts, not a continuous maximum. The high-water process RSS includes full state hashing/export. These costs describe distinct work sizes and cannot serve as the native 512-to-2,048 growth ratio.

Observed foreground cut P95 stayed at or below 0.424 ms and the maximum was 0.986 ms in this collection. Paired peak RSS increments were below 0.6 MiB. The eight seed-worker cells had process-total P50 ratios from 0.997× to 1.087×. The two nominal founder cells were 1.208× and 1.178×. The first founder cell included a 693 ms observed process launch and had a 9.11× total P95 ratio. Advance, capture and final checkpoint timing in that sample were about 13.58, 12.68 and 8.88 ms. The residual cannot be assigned to a particular cause from these logs. The entire slow launch remains in the archive. This application profiling is descriptive and leaves an independent controlled F1 export budget unqualified. The native protected observer is evaluated on its own separately admitted receipts. [Cut timings](../../experiments/s6_4_wp6b/profiling/cuts.csv) [Cell summaries](../../experiments/s6_4_wp6b/profiling/summary.csv)
