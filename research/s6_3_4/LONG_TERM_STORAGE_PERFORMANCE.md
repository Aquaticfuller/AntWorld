# Long-term storage performance

**PASS against all frozen S6.3.4 storage limits.** The final sample set uses all 42 attempts, including seven declared warm-ups. Each arm contributes five retained independent process runs. The four care arms preserve the R1 state hash, trace hash, opportunity count and fact count. The original legacy timed and integrated arms also match their archived length-prefixed canonical SHA-256. The full earlier batch remains available. The two builds produce identical canonical stream, block-chain and state-frame hashes across all 56 matched performance and ecology cases. [Archive parity](../../experiments/s6_3_4/portable/summary/portability_parity.json)

## Measurement conditions

Source `3162602184b943bdd08a76082ad2d3d39eb21c9e`, C++ tree `277cc8e78cc1acd1cf4a74bf39d08dfdb6a99c69`. Release with Clang 23.1.5 and a pinned zlib writer. The local Windows 11 build 26200 host is an i7-13620H with 16 logical CPUs. Two five-second prechecks measured system busy fractions of 16.457% and 16.111%, under the frozen 25% admission limit. The batch ran sequentially with builds paused. The original per-attempt system counter readings remain available. During the complete child-process windows, aggregate busy fractions were 14.7–44.7%, including the experimental process. The run order rotates by repetition. OS cache state, CPU frequency, temperature and package power were unmeasured or uncontrolled. The system counter covers both the measurement process and background activity. [Host and schedule](../../experiments/s6_3_4/portable/primary)

Advance is wall time in `advance_to` only. Fact-pressure scheduling happens outside that timer. A compact checkpoint and capture run on the foreground. Background publication measures the worker opening the store, encoding and writing it, durable COMMIT and prefix handoff. The application acknowledges separately. An explicit WAL truncate checkpoint and validation of the latest published cut are separately timed. Query page selects up to the final 256 facts by EventId. Scoped query starts halfway through the simulated time and requests a fixed kind and, for care, a real individual. The memory figure is the highest measured process resident peak before the explicit equality audit. Constructing the separate uninterrupted reference and its legacy snapshot is recorded as a separate peak. For diagnostics, per-cut phases pool the cuts within the five runs and restoration is the final restore per run. Five-sample P95/P99 are interpolated descriptive statistics.

## Phase times

Each cell contains empirical P50/P95/P99 in milliseconds. The raw tables include capture, worker readiness wait, acknowledgement and WAL flush individually.

| Workload | Advance | Compact checkpoint | Foreground submission | Durable background publication | Validated restore |
|---|---:|---:|---:|---:|---:|
| Timed legacy motor | 135.458 / 161.493 / 165.094 | 0.982 / 1.231 / 1.263 | 1.111 / 1.375 / 1.413 | 628.365 / 857.719 / 882.357 | 2,913.180 / 3,861.023 / 4,013.450 |
| Timed continuous motor | 119.851 / 130.156 / 132.198 | 1.039 / 1.135 / 1.154 | 1.171 / 1.276 / 1.294 | 626.165 / 685.744 / 695.289 | 2,843.306 / 3,275.807 / 3,330.125 |
| Integrated legacy motor | 88.018 / 104.279 / 105.301 | 1.237 / 1.488 / 1.508 | 1.366 / 1.637 / 1.659 | 213.429 / 243.988 / 244.938 | 900.053 / 1,075.368 / 1,085.806 |
| Integrated continuous motor | 98.683 / 105.952 / 106.065 | 1.192 / 1.305 / 1.313 | 1.344 / 1.456 / 1.465 | 306.000 / 345.284 / 346.274 | 1,510.538 / 1,579.741 / 1,591.835 |
| 10,000 diagnostic facts | 3.646 / 3.866 / 3.888 | 0.011 / 0.019 / 0.020 | 0.064 / 0.085 / 0.086 | 20.850 / 35.990 / 39.154 | 67.354 / 72.947 / 73.259 |
| 100,000 diagnostic facts | 33.505 / 37.429 / 37.544 | 0.006 / 0.017 / 0.018 | 0.055 / 0.075 / 0.082 | 26.941 / 35.878 / 41.994 | 1,151.989 / 1,226.535 / 1,229.004 |
| 1,000,000 diagnostic facts | 363.423 / 391.859 / 395.018 | 0.007 / 0.019 / 0.074 | 0.060 / 0.089 / 0.132 | 31.264 / 44.288 / 57.169 | 9,755.048 / 12,571.637 / 12,715.167 |

The final million-fact P95 is 12.572 s with a maximum of 12.751 s. The first admitted batch measured 14.238 s P95 and a 14.730 s maximum, with identical archive bytes. Both batches pass. Between-session variation and five retained measurements per arm limit what these empirical tails say about other machines or longer histories. [First-batch measurements](../../experiments/s6_3_4/summary/performance_summary.csv)

| Workload | Facts / opportunities | Acknowledge P95 | Page / scoped query P95 | Peak resident maximum | SQLite maximum after flush | Raw / packed fact bytes |
|---|---:|---:|---:|---:|---:|---:|
| Timed legacy | 498,598 / 490,240 | 6.348 ms | 1.755 / 15.009 ms | 133.86 MiB | 5,206,016 B | 106,456,498 / 4,404,518 |
| Timed continuous | 499,006 / 490,240 | 4.137 ms | 1.596 / 11.186 ms | 133.40 MiB | 5,214,208 B | 106,529,836 / 4,409,841 |
| Integrated legacy | 140,396 / 97,167 | 1.884 ms | 1.203 / 20.214 ms | 97.25 MiB | 2,441,216 B | 28,969,460 / 1,547,404 |
| Integrated continuous | 213,354 / 194,693 | 1.988 ms | 0.676 / 26.729 ms | 81.77 MiB | 2,805,760 B | 45,048,510 / 1,981,018 |
| 10,000 diagnostics | 10,000 / 0 | 0.191 ms | 1.234 / 2.087 ms | 12.92 MiB | 372,736 B | 1,630,000 / 200,276 |
| 100,000 diagnostics | 100,000 / 0 | 0.357 ms | 1.660 / 3.427 ms | 15.76 MiB | 2,326,528 B | 16,300,000 / 1,993,346 |
| 1,000,000 diagnostics | 1,000,000 / 0 | 0.421 ms | 1.800 / 3.203 ms | 59.29 MiB | 21,954,560 B | 163,000,000 / 19,908,144 |

The 600 s legacy timed case reaches a 24.17× fact-block compression ratio and a median publication rate of 793,484 facts/s. The reviewed historical SQL case recorded the same 498,598 facts and 490,240 opportunities in 1,074,458,624 B with a 51,625.54 ms median save. The present legacy motor records 5,206,016 B and a 628.365 ms median durable background publication. This is a descriptive cross-stage comparison with byte-identical facts and distinct host sessions. [Historical pressure evidence](../s6_3_3_3/TD_11_INTEGRATED_PERFORMANCE.md)

Diagnostic storage grows by about 21.8 MB per million facts between the 100,000- and 1,000,000-fact endpoints. The million-fact store contains 300 blocks and 101 frames, including the final empty-history cut. Its block compression is 8.19× and its nonempty publications have a median rate of 319,364 facts/s. The 32-worker ecological archives occupy 8.21–9.73 MB at day 180, or 45.6–54.0 kB per game day of final footprint. The 8-worker controls occupy 2.48–3.37 MB, or 13.8–18.7 kB per day. These are averages over variable event and checkpoint growth. All frame, WAL, memory and archive-size measurements remain available per cut. [Ecology cut data](../../experiments/s6_3_4/portable/ecology)

## Boundaries and protected workloads

The storage gate qualifies one admitted host and these fact mixes. Cold verification time still rises with history. The dense simulations make every locally eligible opportunity and can continue to scale with overlapping neighborhoods. Holding all cut frames increases disk demand, especially for worlds with longer authoritative geometry histories. Whole legacy exports and direct equality or migration audits have higher memory demand. The million-fact reference audit's peak was about 550 MiB at P95, separate from the online peak.

TD-01 and TD-08 retain their reviewed 5.5163× and 4.3147× wall-clock P50 ratios and the ≤6× threshold. The current identity smoke tests check the existing contact and birth work at 128/512/2,048. This storage measurement supplies no new admitted wall-clock ratios for those gates.

[Raw samples and cut data](../../experiments/s6_3_4/portable/primary) · [All phase quantiles](../../experiments/s6_3_4/portable/summary/performance_summary.csv) · [Frozen budget comparison](../../experiments/s6_3_4/portable/summary/qualification.json) · [Reproduction](../../experiments/s6_3_4/README.md)
