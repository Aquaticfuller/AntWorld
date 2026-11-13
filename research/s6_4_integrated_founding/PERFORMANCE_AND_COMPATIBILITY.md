# Performance and compatibility qualification

The acceptance budgets are unchanged. Use the [prospective qualification protocol](INTEGRATED_PERFORMANCE_PROTOCOL.md) for three-session admission, the raw protected observer gates, the F1 application process and internal totals, and the integrated 150-day application workload. The 280 local tests cover 274 inherited cases and six new founding checks. Earlier V6 engineering iterations also completed 279 Debug and Release cases. An intermediate Windows sanitizer run reported one test-only lifetime defect, with 279 other cases passing. The final affected test was rebuilt and rerun with ASan/UBSan. The native comparison measures identical 128/512/2,048-worker workloads. Simulated history size or wall time from an altered ecological trajectory does not establish a performance regression or improvement.

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
