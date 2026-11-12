# WP-2 observer performance

The formal collection used the unchanged dense contact and day-90 depot workloads with the expanded WP-2 projection. The Release executable SHA-256 was `dabc157b9135085855a8ffa041dba1a5f9f3fc6af039a624d3285ef49c6d2525` at `5138717b9bd5083a5bd89e30ac4a848a4614a9f7`. Timed arms used the same executable, affinity, schedule and checkpoint/continuation audit. Every case matched the frozen work, state and trace identities. [Native freeze](../../experiments/s6_4_wp2/performance/formal/freeze.json)

Three sessions qualified on their first admission. System P95 was 4.231%, 5.302% and 3.328%, and selected logical P95 was 0.000%, 0.000% and 1.563%. All 504 samples are retained, including 36 warm-ups, 36 off/off and 432 scored observations. The largest HWiNFO gap was 2.027 s. All three sessions retain valid native and PDH series, and the mapped maximum package temperatures were 71, 69 and 73 °C. Maximum reported power was 22.15 W and maximum selected effective frequency 4,444.2 MHz. The earlier restricted launch stopped at the Win32 CPU metadata read with zero admission and timing samples. Its schedule and start evidence remain archived. [Native rows and receipts](../../experiments/s6_4_wp2/performance/formal) [Earlier launch status](../../experiments/s6_4_wp2/performance/pre_admission_status.json)

| Cell | Off/off P50 | On/off P50 (95% interval) | On/off P95 (95% interval) | On/off P99 | Foreground P95 / max, ms | Max terminal drain, ms | Max paired RSS increase, MiB |
|---|---:|---:|---:|---:|---:|---:|---:|
| Dense-512 | 1.004774 | 1.056065 (1.048520–1.064569) | 1.064802 (1.005029–1.090773) | 1.030677 | 1.18877 / 1.3152 | 3.2686 | 2.336 |
| Dense-2,048 | 1.001826 | 1.023666 (1.019474–1.029610) | 1.016575 (1.000114–1.040028) | 1.024985 | 2.375675 / 2.9166 | 5.0770 | 1.727 |
| Depot-32 | 0.999199 | 1.047762 (1.041461–1.053446) | 1.059683 (1.050567–1.068277) | 1.064237 | 0.589295 / 2.2389 | 5.5020 | 2.687 |

**PASS** within the frozen three-cell scope. All rows charge the measured terminal flush to total wall time. The 20 ms maximum applies to capture and submission at a cut. The largest closed database was 3,018,752 B and the largest live WAL 1,318,432 B. Counts, cut times, per-cut payload and staged queue caps, HWiNFO bracketing, exact off/on work and continuation, energy and mass were checked again from the archive. The accepted RM-02-R1 TD-01 5.4044213013× and TD-08 4.2867769167× retain their original ≤6× qualification. The historical durable 256.1484 ms terminal tail remains an operational risk and is outside the claim this batch supports. [Machine-readable evaluation](../../experiments/s6_4_wp2/performance/formal_analysis.json) [Original performance crosswalk](../s6_4_rm02_r1/PROTOCOL_TO_ANALYZER_CROSSWALK.md)

## Timed-care workload and engineering verification

The 80 process-isolated diagnostic samples use four cells, with 64 retained and 16 warm-up rows. For the separate eight-worker timed-care cell, 298 events are processed in each arm. P50 total wall time is 0.31265 ms off and 1.35805 ms on (4.344×). P95 total is 0.38783 ms off and 1.51824 ms on (3.915×). Foreground P95 is 0.11345 ms, with a 0.13290 ms maximum. Median terminal flush is 0.82255 ms. The max closed SQLite file is 45,056 B. The small denominator and fixed durable publication cost are material in this short trial. Its status is `DESCRIPTIVE_UNADMITTED`. The frozen three-cell result does not cover that short workload or qualify TD-11 at high density. [Diagnostic schedule and raw rows](../../experiments/s6_4_wp2/performance/diagnostic)

| Local verification on Windows | Result |
|---|---|
| Debug build and CTest | 227/227, 199.80 s |
| Release build and CTest | 227/227, 42.01 s |
| ASan/UBSan build and CTest | 227/227, 594.24 s |
| Observer analysis error and boundary tests | 4/4 |
| Independent native archive evaluation | 504 rows, PASS |
| Frozen scientific matrix and comparison tables | Check mode reproduces the accepted projection and all comparisons |

The 227 tests include all 222 inherited cases, four WP-2 application cases and the additional scope/fault/recovery test. Windows sanitizer tests prepend the LLVM runtime bin directory to PATH and use `ASAN_OPTIONS=halt_on_error=1` and `UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1`. CTest uses `ctest --test-dir build/s6_3_4-<debug|release|sanitizer> --output-on-failure` after rebuilding the corresponding configuration.

## Reproduction

```text
python tools/analyze_s6_4_wp2_performance.py experiments/s6_4_wp2/performance/formal experiments/s6_4_wp2/performance/formal_analysis.json --check
python tools/test_s6_4_wp2_observations.py
python tools/build_s6_4_wp2_evidence.py --check
python tools/run_s6_4_wp2_diagnostic_timing.py experiments/s6_4_wp2/performance/diagnostic --check
```

For new admitted measurements, build `antworld_s6_4_wp2_benchmark` with Release and the recorded compiler. Start fresh output and scratch paths and retain the accepted version-2 confirmation, matched HWiNFO mapping and admission sequence.

```text
python tools/run_s6_4_wp2_performance.py --prepare --out out/wp2-formal --binary <binary> --build <build> --compiler <compiler>
python tools/run_s6_4_wp2_performance.py --out out/wp2-formal --binary <binary> --archive out/wp2-formal-private --hwinfo-csv <live-log>
python tools/archive_s6_4_rm02_performance.py out/wp2-formal out/wp2-formal-public
```
