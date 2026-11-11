# RM-01-R1 performance qualification

| Acceptance area | Result |
| --- | --- |
| Functional engineering | **ENGINEERING_PASS** at independent review of `84decb6dc23bd03af2562214ab92c8b6847ec668`. The R1 evidence verification reproduced the accepted result byte for byte. |
| Controlled performance | **ENGINEERING_PASS**. TD-01 and TD-08 each completed three qualified sessions and met the frozen 6× maximum. |
| Complete RM-01 engineering | **ENGINEERING_PASS** on the recorded criteria, submitted for independent acceptance. |
| Biological validation | **BIOLOGICAL_NOT_VALIDATED**. BR-04 remains open. |

## Qualification record

The R1 protocol was committed at `9b31879732e7bc9466b043736dd252210ab89613` before the new freeze or diagnostic. The freeze reproduces the original compiler, executable SHA-256 values, schedule SHA-256 values, dependencies, instrumentation, sensor mapping and order. The baseline C++ tree is `2b9d475fdb0d657dc87e46755d6511779da0c8b4`. The three-population reserve diagnostic reproduced the exact accepted receipt, including births, facts, pending work, checkpoint bytes, state and trace hashes, restore and mass/energy balances. [Protocol](RM01_R1_PERFORMANCE_PROTOCOL.md) [R1 manifest](../../experiments/s6_4_rm01_r1/controlled/freeze.json) [Workload identity](../../experiments/s6_4_rm01_r1/controlled/reserve_identity_receipt.json)

The first R1 preflight recorded stale HWiNFO readings before any formal admission. After the user restored logging, the approved header and fresh temperature, package power and effective clock readings were verified. Collection ran from 17:17:13 to 17:27:38 UTC on 2026-11-11. All six sessions passed their first admission, each with 60 complete native, power and sensor intervals. The largest admission system P50/P95 were 7.87%/15.02%. The selected logical CPU P50 was 0% in every window and its largest P95 was 9.37%. These measurements use the original P50 ≤10% and P95 ≤20% limits. [Retained host preflight](../../experiments/s6_4_rm01_r1/host_preflight.json) [Admission summary](../../experiments/s6_4_rm01_r1/analysis/admissions.csv) [Collection receipt](../../experiments/s6_4_rm01_r1/collection_receipt.json)

The host was Windows 11 on an Intel Core i7-13620H. All native phase records show the frozen logical CPU 0. The 1,857 timed OS records had zero invalid native samples and complete process times. All 111 mapped HWiNFO rows bracketed the sessions with a maximum gap of 2.034 s. Package readings spanned 50–66 °C and 2.989–22.487 W. The sampler recorded zero thermal or power-limit flags, saver intervals or loss of AC. It retained 8 invalid PDH diagnostics at admission and 94 during timing. The confirmed native counter determined admission. [Phase and sensor coverage](../../experiments/s6_4_rm01_r1/analysis/telemetry.csv) [Version-2 instrument protocol](../../docs/55_S6_3_3_1_Performance_Instrument_Protocol.md)

## Gate results

The original gate divides the pooled dense 2,048 advance P50 by the 512 advance P50. Each primary population contributes 72 retained observations per workload. The full timing archive keeps warm-ups, 128-population diagnostics and dispersed contacts. The paired estimate uses the median of the 36 block ratios. Intervals use the frozen 4,096-draw hierarchical session/block bootstrap and describe measurement uncertainty on this host. [Growth and intervals](../../experiments/s6_4_rm01_r1/analysis/growth.csv) [Paired ratios](../../experiments/s6_4_rm01_r1/analysis/paired_ratios.csv) [Session identity](../../experiments/s6_4_rm01_r1/analysis/sessions.csv)

| Workload | Qualified sessions | Timed / planned rows | Pooled P50 ratio (95% interval) | Paired median (95% interval) | Session P50 ratios | Gate |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| TD-01 dense contacts | 3 / 3 | 336 / 336 | 5.419× (5.348–5.480) | 5.374× (5.322–5.434) | 5.388×, 5.431×, 5.432× | PASS |
| TD-08 reserve births | 3 / 3 | 168 / 168 | 4.243× (4.172–4.320) | 4.286× (4.205–4.329) | 4.206×, 4.289×, 4.242× | PASS |

### Dense phase times in milliseconds

| Workload | Population | Setup P50 / P95 / P99 | Advance P50 / P95 / P99 | Encode P50 / P95 / P99 | Restore P50 / P95 / P99 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Contacts | 512 | 3.36 / 4.93 / 5.42 | 41.15 / 45.15 / 47.60 | 8.08 / 8.55 / 9.71 | 10.78 / 11.56 / 12.56 |
| Contacts | 2,048 | 10.39 / 12.57 / 13.94 | 223.03 / 229.83 / 238.33 | 32.32 / 33.67 / 35.32 | 51.03 / 53.38 / 56.79 |
| Reserve births | 512 | 2.90 / 3.09 / 3.46 | 2.90 / 3.17 / 3.95 | 4.08 / 4.36 / 4.75 | 7.78 / 8.38 / 9.82 |
| Reserve births | 2,048 | 12.44 / 13.09 / 13.31 | 12.29 / 12.82 / 13.15 | 15.27 / 15.90 / 16.47 | 34.25 / 35.23 / 35.92 |

The 512/2,048 dense contact cases produced 15,874/63,490 events, 73,728/294,912 candidates and 2,877,816/11,508,600 checkpoint bytes. The birth cases registered 512/2,048 eggs and produced 3,587/14,339 events and 1,426,479/5,702,703 checkpoint bytes. The analyzer matched all historical state, trace, event, pending-work and checkpoint identities. Contact continuation and birth restore and conservation checks passed. At 512/2,048, dense contact resident memory P50 was 22.18/56.42 MiB and birth RSS P50 was 14.79/35.03 MiB. Observed process peaks reached 97.99 MiB for contacts and 46.76 MiB for births. Peak values cover the process lifetime, including earlier rows in the same session. [Work and memory](../../experiments/s6_4_rm01_r1/analysis/work.csv) [Complete phase percentiles](../../experiments/s6_4_rm01_r1/analysis/latency.csv) [CPU and cycles](../../experiments/s6_4_rm01_r1/analysis/cpu_cycles.csv)

## Protected evidence and regression checks

The original verifier exited 0 for 13 short assays, 18 ecology runs and 12 observer pairs including warm-ups. Its output SHA-256 is `04557bb0b28ed057692bc832f769a9387f18b62e6f7262a91ffd65f2bf8cc68e`, identical to the accepted verification. The existing analyzer reproduced the previous batch's three rejected admissions and INCONCLUSIVE status for both workloads. The previous batch retains 180 admission intervals, zero timed rows and all 504 scheduled rows. The original functional acceptance covers the 216 CTest entries and five successful baseline Core CI jobs. [Verification receipt](../../experiments/s6_4_rm01_r1/reproduction_receipt.json) [Original admissions and results](RM01_PERFORMANCE_RESULTS.md) [Baseline Core CI](https://github.com/Aquaticfuller/AntWorld/actions/runs/42995203428)

The native collector and the analyzer each exited 0. The analyzer's `--check` replay reproduced the published analysis byte for byte. The archive includes all admission CSVs, native phases, timed workload rows, telemetry and mapped sensor observations. Local originals retain the localized logger snapshots and unrelated process inventories omitted from fourteen published metadata receipts. The collection receipt identifies those files and records both digests. [Reproduction](../../experiments/s6_4_rm01_r1/README.md) [Published payload digests](../../experiments/s6_4_rm01_r1/payload_sha256.json)

The repository policy and design check ran locally with exit code 0. The existing Core CI workflow checks the R1 branch. The two performance gates complete the engineering evidence for independent RM-01 acceptance. The egg timing technical assay retains the accepted production defaults, original budgets, mortality behavior and biological interpretation.
