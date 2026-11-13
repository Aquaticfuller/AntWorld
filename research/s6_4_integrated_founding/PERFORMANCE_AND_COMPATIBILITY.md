# Performance and compatibility qualification

The acceptance budgets are unchanged. Use the [prospective qualification protocol](INTEGRATED_PERFORMANCE_PROTOCOL.md) for three-session admission, the raw protected observer gates, the F1 application process and internal totals, and the integrated 150-day application workload. The 280 local tests cover 274 inherited cases and six new founding checks. Local Debug and Release each passed 280/280. An intermediate Windows sanitizer batch had 275 passes, four timeouts under concurrent experimental load, and a test-only lifetime defect. Its test was rebuilt and passed a separate ASan/UBSan run. The clean hosted Linux rerun separately tracks the full matrix. An initial hosted sanitizer run timed out on the 150-day recovery case. Only this new test's sanitizer-specific timeout was extended, with its full 150 days and all verification intact. The native comparison measures identical 128/512/2,048-worker workloads. Simulated history size or wall time from an altered ecological trajectory does not establish a performance regression or improvement.

## Durable representative measurements

The first release build compared 16 world/model pairs in observed, unobserved and durable modes. All 48 executions had identical input, initial checkpoint, final frame, facts, state hash, trace hash, RNG and event count within their pair. For the two balanced seed-1 cases the old R2 trajectory has approximately 13,000 facts, while the integrated trajectories have approximately 631,000–641,000 facts. Their workload sizes differ. The following figures are illustrative wall samples from the same run receipt, collected during normal verification. They are outside controlled performance qualification.

| Configuration | Population | Canonical facts | Day-75 save (ms) | Day-75 restore (ms) | Peak RSS (MiB) |
|---|---|---:|---:|---:|---:|
| R2 | Borisovka | 13,383 | 115.4 | 196.0 | 20.1 |
| R2 | St. Petersburg | 12,917 | 129.9 | 225.2 | 19.4 |
| N+E | Borisovka | 624,279 | 441.0 | 950.8 | 258.2 |
| N+E | St. Petersburg | 614,417 | 417.7 | 826.6 | 256.7 |
| U | Borisovka | 621,646 | 459.6 | 841.4 | 258.4 |
| U | St. Petersburg | 614,417 | 378.9 | 745.4 | 256.6 |
| F | Borisovka | 641,002 | 397.0 | 832.4 | 257.1 |
| F | St. Petersburg | 631,100 | 363.7 | 820.7 | 259.3 |

The public receipt records actual units, executable identity, sample windows, all modes and original hashes. The archived midpoint set contains the database and accompanying WAL when SQLite emits one. A restore replays its saved checkpoint and fact prefix before the simulation continues. Segmented archive integrity, format mixing rejection, queue/watermark ownership and actual post-restoration state are checked. Energy, all ingredient masses, soil and lifetime identity reconcile against the authoritative facts and state cuts.

## Host telemetry

The existing HWiNFO log provided the approved CPU sensor channels with its known appended column. A first launch with restricted Windows access failed before admission because CIM hardware metadata could not be read. Preserve its failed console, frozen schedules, analysis and zero timing rows. Reattempt through a command with read access to the same system data, preserving the original admission, affinity, thresholds and schedules. The original R2 application tail, previous TD-01 gaps and previous protected-observer gaps are independent historical evidence.

TD-01 is `PASS` with 336 of 336 rows and all three qualified sessions. The first two session-one admissions were rejected at system P95 24.11% and 20.74% against the unchanged 20% threshold. The first also had selected-core P95 38.27%. The third passed with system/core P95 13.26%/7.89%. The dense advance 2,048-to-512 P50 ratio is 5.45755×, with pooled bootstrap interval 5.38356–5.49973×. The paired median is 5.42249× and its interval is 5.39024–5.46414×. All workload hashes and event counts match the frozen native assay. The separate planned birth and observer workloads retain their own result and do not inherit this pass.

TD-08 is `PASS` with 168 of 168 rows and three qualified sessions. The exact preflight confirmed the original reserve-birth workload at all three populations. The dense birth-advance 2,048-to-512 P50 ratio is 4.25270×, with pooled bootstrap interval 4.15477–4.35044×. The paired median is 4.28693×, with interval 4.20400–4.36664×. Both limits remain 6×.

The protected observer is `PASS` under the original reconciled criteria. All 504 rows and all three host sessions qualify. The observed/unobserved total P50/P95 ratios are 1.0598/1.0881 for dense 512, 1.0281/1.0313 for dense 2,048 and 1.0664/1.0711 for depot 32. Raw foreground cuts, durable flush, exact workload identity, RSS and all outliers accompany the result. The analyzer uses the original published process-list-redacted export manifest. [Protected observer result](../../experiments/s6_4_integrated_founding/performance/protected-analysis.json)

All five [Core CI jobs for code and archive revision `361d238`](https://github.com/Aquaticfuller/AntWorld/actions/runs/43358756144) passed, including Windows/Linux Debug and Release, the Linux ASan/UBSan run and the integrated witness and recovery checks. The GitHub run's hosted tests are distinct from local controlled wall-time qualification. The source-only MSVC name correction and sanitizer test timeout correction do not change the measured model. Native contact and birth source freezes remain separately identified.

## Retained F1 application tails

All 480 original R1 and 720 R2 raw samples remain reproducible. In the R2 rerun's failed R1 St. Petersburg eight-worker depot cell, the longest observed process took 1,186.626 ms. The child recorded 1,164.841 ms total, 629.683 ms through the midpoint save measurement, 217.513 ms through restore, 1.679 ms mandatory output sync and 0.159 ms optional sync. The residual outside the measured application was 21.784 ms. The corresponding cell's longest unobserved process took 659.503 ms, with 96.005 ms in the midpoint save measurement. The midpoint save measurement includes checkpoint encoding and SQLite publication, so these data do not partition the delay into disk sync, encoding or scheduling. They do localize much of this specific tail to the save boundary. Separately, the R1 1,790.069 ms process sample has a 1,161.523 ms residual that the recorded phases cannot attribute. The original prequalification 693.177 ms sample also remains in place. Its recorded advance, capture and checkpoint costs were 13.58, 12.68 and 8.88 ms. None of these samples was excluded. [R2 reanalysis](../../experiments/s6_4_integrated_founding/performance/r2-application-phase-diagnosis) [R1 admitted reanalysis](../../experiments/s6_4_integrated_founding/performance/r1-admitted-phase-diagnosis) [Original receipts](../s6_4_wp6b_r1/R1_PERFORMANCE_QUALIFICATION.md)
