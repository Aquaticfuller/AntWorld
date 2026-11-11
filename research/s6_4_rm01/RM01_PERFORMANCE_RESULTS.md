# RM-01 performance results

The C++ workload and storage rules are inherited from the reviewed comparator. Release measurements used uninstrumented Clang 23.1.5 on Windows 11, Intel Core i7-13620H with 16 logical processors. The same executable produced the assay and observer results. All wall-time comparisons below retain their actual work counts, configuration, host admission and recorded warm-ups. [Assay identity](../../experiments/s6_4_rm01/assay/build.json) [Observer identity](../../experiments/s6_4_rm01/observer/build.json)

## Frozen 512 to 2,048 gates

Current TD-01 and TD-08 measurements are **NOT_RUN**. The frozen analyzer reports **INCONCLUSIVE** with zero qualified sessions and zero timed rows. The first launch stopped before admission because the sandboxed Windows CIM query failed. Native read access resolved that setup failure. The newly frozen native batch then exhausted the allowed three attempts on contact session 1. Birth session collection did not start. The reserve executable's three-population diagnostic matched the protected workload before admission. [Interrupted setup](../../experiments/s6_4_rm01/controlled-setup-interrupted/process_result.json) [Protected identity](../../experiments/s6_4_rm01/controlled/reserve_identity_receipt.json)

| Contact session 1 attempt | System P50 / P95 | Selected logical CPU P50 / P95 | Result |
| --- | ---: | ---: | --- |
| 1 | 17.09% / 27.65% | 4.69% / 18.74% | Rejected |
| 2 | 10.53% / 17.20% | 0.00% / 0.08% | Rejected |
| 3 | 10.23% / 16.73% | 1.56% / 9.53% | Rejected |

The frozen limits are P50 at most 10% and P95 at most 20% for both load measurements. All 180 admission intervals had valid native timing, power and HWiNFO sensor readings under the protocol. The separate PDH diagnostic recorded one invalid sample in each of the first two attempts. Preserve the unchanged `<=6x` threshold, all admission records and the historical results. There is no current ratio or confidence interval from this batch. [Admission data](../../experiments/s6_4_rm01/controlled/contacts/session1) [Analyzer status](../../experiments/s6_4_rm01/controlled/analysis/status.csv) [Frozen instrument](../../docs/55_S6_3_3_1_Performance_Instrument_Protocol.md)

## Frozen durable-storage workloads

**ENGINEERING_PASS.** The two admission windows were 10.45% and 9.07% system busy. Forty-two measurements comprise one warm-up and five retained samples for each of seven cases. Fourteen retained ecology comparisons also replayed. The executable SHA-256 matches the archived S6.3.4 portable executable. The independent archive audit confirmed identical canonical facts, block and frame identities across both batches.

| Frozen limit | Measured worst applicable result |
| --- | ---: |
| Foreground capture/submission P95 at most 25 ms, maximum at most 100 ms | 1.363 ms P95, 1.3713 ms maximum |
| Dense timed publication P95 at most 12 s | 0.619 s |
| Dense timed restore P95 at most 8 s | 2.949 s |
| One-million-fact restore P95 at most 15 s | 9.689 s |
| Dense and million-fact online peak at most 512 and 768 MiB | 134.48 MiB dense, 59.52 MiB at one million |
| Dense timed durable store at most 128 MiB | 4.973 MiB |
| Indexed and scoped query P95 at most 2 s | 1.591 ms indexed, 17.058 ms scoped |

The complete phase and resource percentiles, budgets, operating conditions and raw samples are retained. Temperature, frequency and package power were not measured in this separate storage batch. [Qualification](../../experiments/s6_4_rm01/durability/analysis/qualification.json) [Phase data](../../experiments/s6_4_rm01/durability/analysis/performance_summary.csv) [Byte parity](../../experiments/s6_4_rm01/durability/analysis/portability_parity.json) [Frozen budgets](../../docs/64_S6_3_4_Frozen_Durable_History_Protocol.md)

## Application observer and warm workloads

The first observer host check rejected both windows at 27.85% and 26.53% system busy before timing. The later isolated batch admitted at 14.88% and 15.85%. One warm-up and five retained legacy off/off pairs completed before the off/on pairs. The retained off/off ratio envelope was 0.989884 to 1.004474. Each off/on pair processed exactly 191,461 facts with identical canonical SHA-256 and final frame SHA-256. The measured on/off ratios of advance plus observer work ranged from 0.988653 to 1.007144, with median 0.991739. Small variations cross the baseline envelope in both directions. The per-run observer timer measures a median 4.709 ms and P95 5.028 ms. These data characterize the cost without establishing an acceleration claim. [First admission](../../experiments/s6_4_rm01/observer-rejected/admission.json) [Second admission](../../experiments/s6_4_rm01/observer/admission.json) [Paired data](../../experiments/s6_4_rm01/observer/observer_pairs.csv)

| Retained legacy metric | Off P50 / P95 | On P50 / P95 |
| --- | ---: | ---: |
| Advance per 180 d run, ms | 2404.905 / 2414.785 | 2384.611 / 2395.846 |
| Checkpoint frame per cut, ms | 0.314 / 0.518 | 0.284 / 0.552 |
| Capture/submission per cut, ms | 0.380 / 0.585 | 0.356 / 0.622 |
| Background publication per cut, ms | 25.582 / 38.507 | 26.123 / 35.760 |
| Validated restore per restore cut, ms | 1134.712 / 1693.829 | 1125.059 / 1710.351 |
| Indexed / scoped query P95, ms | 0.647 / 43.817 | 0.802 / 35.818 |
| Online peak RSS P95, MiB | 21.81 | 21.67 |
| Durable store bytes | 9,134,080 | 9,134,080 |
| Egg CSV bytes | 0 | 12,584 |

The independent observer check retains P50/P95/P99 and the complete per-cut records. Both warm depot-32 observations used the same 180-day horizon and original reserves. Each processed 96,454 facts. Advance was 1,155.001 ms for Borisovka and 1,155.851 ms for St. Petersburg, about 11.98 µs per fact. Legacy observed advance P50 was about 12.45 µs per fact. The warm work excludes the later-stage outcomes of a legacy brood cohort. Per-event cost and calendar-horizon cost are descriptive under these different workloads. Each warm run wrote a 12,020-byte egg sidecar and a 5,427,200-byte durable store. [Full observer verification and horizon rows](../../experiments/s6_4_rm01/verification.json)

Online peak excludes the separate direct-reference audit, which can retain another world and inspect the full history. The total process peak is available in each summary. Data for the original gated loads, work counts and unchanged Core identity are separate from the application observer comparison.
