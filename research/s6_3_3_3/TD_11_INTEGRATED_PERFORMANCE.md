# TD-11 integrated care performance

The [frozen density design](../../docs/61_S6_3_3_3_Frozen_Validation_Protocol.md) uses 8, 32 and 128 caregivers with twice as many larvae in one colony. All caregivers start at the same depot in both layouts. The dense larvae are 1 mm away. The spread larvae use 14 mm offsets in a 16-column grid. This preserves owner, initial caregiver arrangement and total population while changing brood locations. Both layouts run ordinary physical, observation and transaction rules. The timed profile runs 600 simulated seconds. The integrated profile runs two game days using the six-hour autonomy and nutrition clocks. The completed facts include manipulation and other integrated acts, with zero successful transfers or placements in these fixed-population stress cases. The companion ecology workload includes those facts.

There are 12 configurations, one warm-up and three measured replicates per configuration in each of two Release builds. Keep all 96 rows. The first build compiles the scopes out and supplies wall times. The second adds host-only clocks for attribution. The state hash, trace hash, event counts, activity counts, full checkpoint bytes, SQLite bytes and exact restore checks match between builds and repeats. Tests use Windows 11 x64 and an Intel Core i7-13620H with 16 logical processors, LLVM-MinGW Clang 23.1.5, and the bundled SQLite build. Exploratory measurements include concurrent host activity. There is no protected timing admission for TD-11. Three-sample p95/p99 values use interpolation and describe this batch.

## Native phases

Times below are milliseconds. Sizes are decimal MB. All seven timed phases, current working set and process high-water measurements are in the [raw sample](../../experiments/s6_3_3_3/density/samples.csv) and [quantile](../../experiments/s6_3_3_3/density/summary.csv) tables. Memory is sampled after journal extraction. The process peak includes earlier cases and is not a per-case allocation measurement.

| Mode | Layout | Workers | Opportunities | Completed observations | All facts | Advance p50 / p95 / p99 | Checkpoint p50 | Memory restore p50 | SQLite save / load p50 | SQLite MB |
| --- | --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| Timed | Dense | 8 | 1,840 | 52 | 2,377 | 1.15 / 1.23 / 1.24 | 1.85 | 1.32 | 132 / 17 | 5.17 |
| Timed | Spread | 8 | 640 | 42 | 1,139 | 0.71 / 0.74 / 0.74 | 1.01 | 0.80 | 66 / 8 | 2.50 |
| Timed | Dense | 32 | 30,400 | 209 | 32,508 | 14.69 / 20.06 / 20.53 | 28.22 | 27.72 | 5,272 / 490 | 69.52 |
| Timed | Spread | 32 | 10,240 | 144 | 12,095 | 6.69 / 7.95 / 8.07 | 11.92 | 9.77 | 1,568 / 138 | 25.55 |
| Timed | Dense | 128 | 490,240 | 865 | 498,598 | 142.01 / 161.87 / 163.63 | 297.50 | 212.47 | 51,626 / 4,540 | 1,074.46 |
| Timed | Spread | 128 | 163,840 | 582 | 171,191 | 52.23 / 54.29 / 54.47 | 110.45 | 79.26 | 12,993 / 1,507 | 367.57 |
| Integrated | Dense | 8 | 1,991 | 150 | 3,144 | 2.02 / 2.04 / 2.05 | 2.11 | 1.37 | 167 / 21 | 6.39 |
| Integrated | Spread | 8 | 1,000 | 150 | 2,153 | 1.80 / 2.97 / 3.07 | 2.51 | 1.15 | 118 / 13 | 4.24 |
| Integrated | Dense | 32 | 10,851 | 952 | 17,358 | 17.37 / 24.94 / 25.62 | 12.97 | 10.83 | 2,032 / 238 | 34.49 |
| Integrated | Spread | 32 | 7,962 | 736 | 13,983 | 19.63 / 21.38 / 21.54 | 14.36 | 12.32 | 1,690 / 227 | 27.23 |
| Integrated | Dense | 128 | 97,167 | 7,228 | 140,396 | 88.82 / 94.44 / 94.94 | 83.03 | 67.53 | 11,900 / 1,162 | 285.73 |
| Integrated | Spread | 128 | 114,248 | 406 | 126,199 | 50.36 / 98.88 / 103.19 | 75.99 | 64.56 | 12,211 / 1,075 | 265.40 |

The largest timed case's current resident median is 476.71 MB with 975.09 MB process peak. Its framed canonical journal is 106.46 MB and the complete checkpoint is 104.78 MB. Both appear as different representations alongside the indexed SQLite history. Standalone journal encoding is 283.73 ms median, separate from the full checkpoint. SQLite save includes preparation, writing and the explicit WAL checkpoint.

## Where time goes

| 128-worker profile | Candidate examinations | Neighborhood exclusive ms | Care opportunity exclusive ms | Fact history exclusive ms | Checkpoint history ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| Timed dense | 491,520 | 20.77 | 33.58 | 56.83 | 209.43 |
| Timed spread | 165,120 | 4.18 | 9.64 | 21.53 | 66.52 |
| Integrated dense | 234,396 | 9.21 | 5.26 | 21.48 | 49.11 |
| Integrated spread | 245,739 | 6.71 | 6.48 | 13.93 | 45.89 |

Profiler medians are independent of the native medians. The opportunity scope's inclusive time contains nested fact handling. The table shows exclusive time and keeps the two scopes separate. The native opportunities column counts all actual Opportunity facts, including those outside the dedicated care scope. Dense timed 32→128 scales by 16.13× in opportunities for 4× workers. The integrated spread case at 128 still emits more opportunities than dense. It records 887 dedicated care opportunity batches versus 226, with the adults sharing one depot. Its completed act count is lower. Changing spatial context changes actual work. The spread case is not a like-for-like faster execution of the dense one.

For independent storage attribution, the supplemental replay loads measured replica 1 and writes that exact state and history to a fresh SQLite store. The existing save-stage hook records preparation, generation write, history/identity/flow insertion, analytics and retention, commit, and WAL flush. The replay verifies the complete durable checkpoint and each original case's fact and trace identity. One sample per case is a diagnostic decomposition. In the largest timed dense case it measures 403 ms preparation, 602 ms generation, 60,112 ms history, 1.4 ms analytics, 3,841 ms commit and 88 ms WAL flush. The corresponding integrated dense case has 13,406 ms history. The dominant persistence work is inserting history rows and maintaining their associations and indexes. These spans come from a different pass than the native medians. [Full attribution](../../experiments/s6_3_3_3/density/profile_summary.csv), [SQLite replay](../../experiments/s6_3_3_3/density/persistence.csv).

## Day-scale workload with real exchanges

The supplementary replay times all 24 balanced fine-grid and chamber worlds, with and without integrated care, across the same populations and seeds. It reproduces all 24 original state/trace identities. The replay includes 631,751 facts, 2,511 positive transfers including five timed brood-feed acts, 12 placements, 141 actual food returns and 86 emergences. Summed six-hour simulation advances range from 3.79 to 87.32 ms, with a median of 19.22 ms. The median complete checkpoint encode is 10.28 ms, the median day-10 SQLite save is 787.54 ms and the median day-21 delta save with WAL flush is 305.01 ms. Each scenario contributes one exploratory timing sample.

For example, seed 43 with 16 workers on the funded fine grid and integrated care commits 82,747 facts, 286 transfers, one timed brood feed, one physical placement and 16 deliveries. It takes 60.17 ms to advance, 245.59 ms to export observations and 45.03 ms to encode the last checkpoint. Its SQLite save stages are 8.45 s and 2.43 s. The companion data distinguish simulation, observation and storage in a workload with actual exchanges. [Phase timings and matching endpoints](../../experiments/s6_3_3_3/ecology_workload.csv).

## Exact lossless block experiment

Use 4,096 contiguous canonical event records per independently compressed block. The indexed zlib level-6 archive stores the first and last EventId, packed and raw offsets and sizes, and a SHA-256 for each decoded block. Every block round-trips to the identical framed bytes, and every decoded ID is checked in order. A second pass reads the archive by indexed offset and verifies the entire original digest and the count. The supplemental LZMA preset-0 comparison uses the same input blocks. Its sizes and timings are retained alongside the zlib measurements. The repository keeps the indexed zlib files for direct extraction.

| Case | Raw canonical bytes | zlib bytes | LZMA bytes | zlib block read/decode p50 / p95 / p99 |
| --- | ---: | ---: | ---: | --- |
| Timed dense 128 | 106,456,498 | 4,648,683 | 1,381,256 | 1.70 / 2.41 / 3.74 ms |
| Integrated dense 128 | 28,969,460 | 1,563,736 | 622,428 | 1.47 / 2.05 / 2.37 ms |

Packed payload sizes exclude the block-index table. The repeated fact fields of these cases compress well. Bounded read/decode measurements use the host cache and do not include indexed world-history queries, durability or cold-device latency. Archive objects do not replace complete recovery checkpoints. The [compression table](../../experiments/s6_3_3_3/density/archive_compression.csv), [block index](../../experiments/s6_3_3_3/density/archive_index.csv) and [exact verification](../../experiments/s6_3_3_3/density/archive_seek.csv) expose those boundaries.

TD-11 remains **OPEN**. A versioned segmented history proposal could retain the complete ordered fact payload with typed secondary index summaries and an atomic generation anchor. It would need proof of prefix/hash recovery, crash atomicity, cursor stability, filtered queries, random access, bounded memory and mixed long-lived histories before a live format change. Neighborhood indexing and compressed history address different costs. TD-01 and TD-08 retain their frozen 6× gates and reviewed 5.5163×/4.3147× measured passes. Current exact workload checks do not constitute a fresh admitted timing batch.
