# F1 performance and replay verification

Protected runtime qualification uses the unchanged TD-01 and TD-08 workloads and the accepted observer workloads. The native collection holds each binary and workload identity, fixed per-core admission, ABBA/BAAB order and original limits. The contact and birth growth gate remains ≤6× at 512 to 2,048 workers. The protected observer gate includes total wall time and real durable writes, with the final drain measured separately. [Frozen protocol](FROZEN_PROTOCOL.md) [Original benchmark acceptance](../s6_4_wp5/ENGINEERING_VERIFICATION.md)

## Candidate workload costs

The independent F1 profiling batch used the frozen nominal foundress case for each population and both 8/32-worker depot and empty cases for seed 1. Each case had four observed and four unobserved launches in ABBA/BAAB order, plus one observed launch with a day-45 SQLite publication and reopen. All 90 launches matched the initial checkpoint, final frame and every canonical fact byte for their respective case. Observation on/off concerns exported census data. Maternal care remained enabled in all these profiling launches. [Frozen profiling identity](../../experiments/s6_4_wp6b/profiling/freeze.json) [Paired raw samples](../../experiments/s6_4_wp6b/profiling/samples.csv)

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
