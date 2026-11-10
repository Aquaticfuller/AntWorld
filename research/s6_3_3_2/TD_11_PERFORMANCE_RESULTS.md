# TD-11 and protected workload performance

## TD-11 same-colony care density

[Protocol 58](../../docs/58_S6_3_3_2_Frozen_Baseline_and_Protocol.md) fixes the seed, time, one/four brood per caregiver, 1/8/32/128 caregivers and two layouts. The same ColonyId is used throughout. Each case has one warm-up and three measured repeats. The reference adds profiling to the reviewed policy. The indexed arm changes enumeration only. Dense and dispersed groups differ in placement relative to the actual experienced shelter. Each optimized case is paired to its own reference.

All 64 paired records have the same state and trace hashes, exact restore, opportunity counts, completed acts, brood moves, fact count and encoded sizes. `WorldRuntime::care_neighborhood` uses the existing living-ant contact tree in eligible geometry-free worlds. It visits only buckets intersecting the query, filters by exact distance, and keeps stable EntityId order. Worlds without that derived index and geometry worlds retain their existing neighborhood path.

| 128 caregivers / 512 brood | Dense reference | Dense indexed | Dispersed reference | Dispersed indexed |
| --- | ---: | ---: | ---: | ---: |
| Candidates examined | 164,480 | 164,480 | 281,600 | 2,419 |
| Opportunities | 164,223 | 164,223 | 1,016 | 1,016 |
| Completed handling | 122 | 122 | 312 | 312 |
| Brood moves | 44 | 44 | 310 | 310 |
| Complete journal facts | 167,463 | 167,463 | 5,944 | 5,944 |
| Journal encoding bytes | 35,047,482 | 35,047,482 | 1,070,760 | 1,070,760 |
| Checkpoint bytes | 35,208,788 | 35,208,788 | 1,233,554 | 1,233,554 |
| Neighborhood p50 (ms) | 13.162 | 7.337 | 8.882 | 0.351 |
| Opportunity generation inclusive p50 (ms) | 29.784 | 31.554 | 0.304 | 0.285 |
| Fact history exclusive p50 (ms) | 20.031 | 21.974 | 0.666 | 0.625 |
| Checkpoint history encoding p50 (ms) | 63.659 | 65.106 | 1.995 | 2.045 |
| Advance p50 (ms) | 64.583 | 59.727 | 13.479 | 4.933 |
| Checkpoint p50 (ms) | 102.778 | 103.991 | 3.658 | 3.626 |
| Restore p50 (ms) | 74.696 | 74.148 | 4.989 | 4.518 |

Opportunity generation includes its nested history writes. Those two scopes should not be summed. The profiled advance times apply to the frozen legacy care workload under the new index, with profiler overhead and three measured replicas per cell. The [full table](../../experiments/s6_3_3_2/td11/summary.csv) includes p50/p95/p99 for each phase, scale and layout. The [raw reference](../../experiments/s6_3_3_2/td11/reference), [raw indexed arm](../../experiments/s6_3_3_2/td11/indexed) and [figure](../../experiments/s6_3_3_2/figures/td11_density.svg) preserve the smaller cases and within-condition timing spread.

**TD-11 remains OPEN.** Removing unrelated candidates improves dispersed scans. In the compact case, each actual opportunity still has to be represented. Canonical fact generation and history encoding remain the principal costs. The new motion policy can produce a different event distribution. These paired data isolate the query optimization. They do not estimate long-term storage or dense timed-care throughput. Evaluate a separate representative integrated load and a lossless history encoding under replay before changing this contract.

## TD-01 and TD-08 protected requalification

The [frozen batch](../../experiments/s6_3_3_2/performance/freeze.json) identifies source commit `2ba77bb2fb5e1b87aa539f54929868de2ac65830`, both executable SHA-256 values, the six schedules, the already independently confirmed Windows per-core instrument version and the reserve-birth executable check. This is a separate Release build with profiling disabled. The instrument and admission thresholds from S6.3.3.1 were reused unchanged. The runner retained all 504 native sample rows including warm-ups, paired block order, phases, Windows thread CPU/cycle data, temperatures, package power, effective frequency, admission checks and raw English sensor exports.

| Dense advance gate | 512 p50 (ms) | 2048 p50 (ms) | p50 growth and 95% CI | Paired median and 95% CI | Outcome |
| --- | ---: | ---: | --- | --- | --- |
| Contact | 41.4502 | 225.2336 | 5.4338x [5.3529, 5.5591] | 5.3999x [5.3141, 5.4954] | PASS |
| Reserve-birth registration | 3.0647 | 12.9592 | 4.2285x [4.1479, 4.3225] | 4.2743x [4.1500, 4.3388] | PASS |

The p95/p99 advance times at 512 and 2048 are 48.465/55.111 ms and 236.872/246.576 ms for contacts, and 3.509/4.311 ms and 13.745/15.038 ms for reserve births. The [latency table](../../experiments/s6_3_3_2/performance/analysis/latency.csv) reports setup, advance, encoding and restore, including 128 and dispersed contacts. The [work table](../../experiments/s6_3_3_2/performance/analysis/work.csv) includes events and memory. All three sessions per workload qualified, with the same state/trace/workload identities as the protected baseline. The unchanged gate is at most 6x for the specified wall-clock advance ratio.

The host was an Intel Core i7-13620H with 10 physical and 16 logical CPUs, Windows build 26200, on AC. The benchmark was pinned to logical CPU 0 and the collector excluded its physical core. Admission system p95 was 11.46–15.04% across sessions and selected-core p95 was 1.56–14.16%. All native samples passed interval checks. The supplemental PDH counter still returned invalid statuses, preserved in the raw data. Its previous discrepancy and independent source are explained in [protocol 55](../../docs/55_S6_3_3_1_Performance_Instrument_Protocol.md). In-run package temperatures ranged from 50 to 74 C and power from 3.095 to 39.064 W. Thermal flags were zero. Recorded power-limit flags are retained. These are sampled conditions, with at most 2.10 s between HWiNFO readings in the qualified sessions. [Admission and telemetry analysis](../../experiments/s6_3_3_2/performance/analysis).

The result applies to these bounded protected fixtures. It does not close TD-08 for dynamic long-lived populations, TD-11, or TD-03/06. The 24.229x S6.1 anomaly, earlier failed runs and admission failures retain their original interpretation and evidence.
