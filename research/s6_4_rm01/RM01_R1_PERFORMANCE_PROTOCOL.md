# RM-01-R1 frozen performance protocol

RM-01's functional engineering was independently accepted at `84decb6dc23bd03af2562214ab92c8b6847ec668`. R1 qualifies only TD-01 dense contact and TD-08 reserve birth performance. The C++ tree is `2b9d475fdb0d657dc87e46755d6511779da0c8b4`. Preserve the accepted assay, tests, observers, workload sources and earlier records byte for byte.

The original contact admissions had system P50/P95 of 17.09%/27.65%, 10.53%/17.20% and 10.23%/16.73%. Each exceeded at least one system-load limit. All 180 native, sensor and power intervals qualified. A separate restricted launch ended at the host CIM query before admission. The old batch retains all three admissions, 336 planned contact rows, 168 planned birth rows, zero timed rows and its INCONCLUSIVE analyzer status. [Original results](RM01_PERFORMANCE_RESULTS.md) [Original freeze](../../experiments/s6_4_rm01/controlled/freeze.json) [Original analysis](../../experiments/s6_4_rm01/controlled/analysis/status.csv)

## Workload and executable identity

Use the original Windows x86-64 uninstrumented Release executables, with profiling and sanitizers disabled. The compiler is LLVM-MinGW Clang 23.1.5, revision `392dfff97d29b59d77e5cac6d4b6ef2585fe7117`, target `x86_64-w64-windows-gnu`. Match both executable and all six schedule SHA-256 values to the original freeze before admission. Freeze the unchanged version-2 runner dependencies, HWiNFO mapping, compiler identity and batch order in a new manifest. Use the existing same-host version-2 confirmation with SHA-256 `ae98ebc30aa513a2e10b8b3b04004e62ef8d3450082564b0a857c3ca2ecc449f`. [Instrument protocol](../../docs/55_S6_3_3_1_Performance_Instrument_Protocol.md) [Reserve birth correction](../../docs/57_S6_3_3_1_Reserve_Birth_Benchmark_Correction.md) [Instrument confirmation](../../experiments/s6_3_3_1/performance/instrument_v2_confirmation/receipt.json)

| Workload | Frozen executable and SHA-256 | Planned rows |
| --- | --- | ---: |
| TD-01 bounded dense and dispersed nursing contact, seed 42, 10 s advance and exact continuation at 11 s | `antworld_s6_2_benchmark.exe` · `bf859f935958b93991024172470659d447b47efc8eb10f72a577106d7516b492` | 336 |
| TD-08 actual reserve-backed egg registrations, seed 42, 10 ms advance and pending worker moves | `antworld_s6_3_1_birth_benchmark.exe` · `e22ba6f43a39011afdf3922da3ecd2cc0a39650b438c9e6d82c9a5ceb2131de3` | 168 |

Run one new batch, with contact sessions 1–3 followed by birth sessions 1–3. Keep all three ABBA/BAAB schedules per workload, twelve 512/2,048 blocks per layout and session, warm-ups and 128-population diagnostic rows. For births, each 512/2,048 workload registers that many eggs alongside the original queen, worker and pending-move workload. Run the frozen three-population reserve workload identity diagnostic outside formal timing. Require the historical exact event, queue, checkpoint, state and trace identities, restore and continuation checks, birth counts and balances, and contact work counters.

## Admission and stopping rule

Use the approved version-2 Windows CPU time sampler and frozen first performance-core logical CPU. Keep the collector off its physical core. Require AC and saver off, the matching HWiNFO header, timestamps with age from −2 to 10 s, and finite package temperature, package power and effective clock. Each session needs 60 valid one-second intervals of 0.8–1.2 s and complete load samples. Require both system and selected logical CPU load P50 at most 10% and P95 at most 20%. Retain native counters and PDH diagnostics. Begin formal timing only after admission.

Allow at most three admissions per session, at least 300 s from the end of a rejection to the start of the next admission. Stop on exhaustion, a started session that fails, or completion of the six sessions. Never repeat a started session. Leave admission pending if live telemetry is unavailable before launch. Record any setup obstruction and report missing measurements as NOT_RUN. Keep builds, tests, other experiments and local analysis outside collection. Preserve every attempted admission and all timing samples, including slow and incomplete rows. Check thermal telemetry brackets and a maximum 10 s sensor gap. Keep localized HWiNFO source files local and publish the mapped sensor records and provenance.

## Analysis and qualification

Use `tools/analyze_s6_3_3_1_performance.py` unchanged. Report P50/P95/P99 of setup, advance, encode and restore along with CPU/cycles, memory, checkpoint bytes and exact workload counts. The gate for each dense workload is the pooled 2,048/512 median advance ratio at most 6. The numerator and denominator use retained samples for that workload, excluding recorded warm-ups and 128 diagnostics. Use contact `advance_ms` and birth `birth_advance_ms`. Report per-session ratios and paired block medians. For both pooled and paired ratios, use the original 4,096-draw hierarchical session/block bootstrap with seed 63201 and 2.5%/97.5% quantiles. The intervals describe measurement uncertainty. The unchanged point estimate determines the gate.

Require all three fully qualified sessions and historical identity per workload for PASS or FAIL. Preserve any INCONCLUSIVE or WORKLOAD_MISMATCH analysis. Mark unmeasured gates NOT_RUN. The original rejected attempts and all historical performance results remain in their existing paths and never substitute for R1 measurements.

Recheck the accepted assay and observer evidence with `python tools/verify_s6_4_rm01_results.py experiments/s6_4_rm01/assay --observer experiments/s6_4_rm01/observer` outside collection. Report functional acceptance, controlled performance, complete RM-01 engineering acceptance and BIOLOGICAL_NOT_VALIDATED separately. BR-04 remains open.
