# WP-3 engineering and controlled performance qualification

## Frozen observer benchmark

The Windows Release observer executable SHA-256 is `4696af5a7739752d2120f8c44754589d62ebaa04c26322ccca191c865c8cd03f` at `c08a49d95aac8f7a2909ad84da6aecd434a39081`. Three ABBA/BAAB sessions admitted on their first attempt with 60 valid one-second intervals each. Admission system P95 was 4.179%, 3.008% and 4.506%. Selected logical P95 was 0%, 0% and 3.126%. All 504 rows remain, including 36 warm-ups, 36 off/off and 432 scored rows. All sessions have native time and frequency, temperature and power coverage, with a largest HWiNFO gap of 2.040 s. The maximum package temperature and power across sessions were 73 °C and 23.81 W. Five supplementary PDH values were invalid in the first timed session and were retained. The independent native counter passed coverage. Per-row work, time, state/trace identities and restoration audits match. [Freeze and raw sessions](../../experiments/s6_4_wp3/performance/formal) [Independent evaluation](../../experiments/s6_4_wp3/performance/formal_analysis.json)

| Cell | Off/off P50 | Total P50 ratio (95% interval) | Total P95 ratio (95% interval) | Total P99 ratio | Foreground P95 / max, ms | Max terminal drain, ms | Max paired RSS increase, MiB |
|---|---:|---:|---:|---:|---:|---:|---:|
| Dense-512 | 1.0054 | 1.0535 [1.0420, 1.0636] | 1.0895 [1.0408, 7.0187] | 6.8345 | 1.1968 / 2.0573 | 305.3788 | 1.961 |
| Dense-2,048 | 1.0045 | 1.0219 [1.0156, 1.0291] | 1.0202 [1.0027, 1.0349] | 1.0293 | 2.3237 / 2.4310 | 5.2649 | 1.738 |
| Depot-32 | 1.0016 | 1.0475 [1.0358, 1.0542] | 1.0589 [0.8353, 1.0664] | 0.8417 | 0.5993 / 2.3385 | 8.2826 | 2.668 |

**PASS** under the original point-estimate gates. The large dense-512 upper interval and P99 describe a genuine durability tail. Session 1 dense-512 samples 22 and 29 spent 305.379 ms and 276.598 ms in the final drain, with total wall times of 354.526 ms and 325.333 ms. Their worker-side write measurements were 305.481 ms and 275.824 ms respectively. The measurement covers publication on the background thread and cannot resolve filesystem sync, OS scheduling and SQLite phase latency individually. Both tails are charged to total time and kept in the bootstrap. The foreground cut gate applies to capture and submission. The terminal drain remains a save/close latency risk, and the earlier RM-02-R1 records remain in scope for future storage work. [Raw long-tail rows](../../experiments/s6_4_wp3/performance/formal/session1/samples.csv) [Frozen gate crosswalk](../s6_4_rm02_r1/PROTOCOL_TO_ANALYZER_CROSSWALK.md)

## Original ≤6× Core regression

Reran the original workloads independently of the observer benchmark. The contact and endogenous-birth Release binaries are byte-identical to the accepted RM-01-R1 binaries, and the protected birth identity agrees at all three populations. All six sessions admitted on their first attempt. The archive has 336 contact and 168 birth timing rows with their phases, raw receipts, HWiNFO and native telemetry. [Core raw sessions](../../experiments/s6_4_wp3/performance/core) [Workload identity](../../experiments/s6_4_wp3/performance/core/reserve_identity_receipt.json)

| Gate | Dense 512→2,048 advance P50 ratio (95% interval) | Paired median (95% interval) | Verdict |
|---|---:|---:|---|
| TD-01 | 5.38990 [5.27376, 5.47950] | 5.35879 [5.28565, 5.41705] | PASS |
| TD-08 | 4.30374 [4.16189, 4.38492] | 4.29546 [4.20900, 4.36916] | PASS |

## Case capture and test evidence

The native observer gates cover the canonical publisher. The additional route and cue projection was measured separately on all 4,026 live-case cuts. It took 0.0347 ms P50, 0.2052 ms P95 and 0.9247 ms maximum, with a largest view of 11,222 B and largest canonical cut of 119,594 B. The largest staged byte count was 33,468 B, closed Sidecar 139,264 B and midpoint world SQLite 192,512 B. Case wall time includes the supplemental queries, midpoint publish and recovery, and terminal drain. These timings describe the fixture workload; they are not paired admission ratios. [Case receipt and cut data](../../experiments/s6_4_wp3/baseline) [Case timing and size table](../../experiments/s6_4_wp3/analysis/case_results.csv)

| Local Windows verification | Executed result |
|---|---:|
| Debug build and full CTest | 234/234, 169.79 s |
| Release build and full CTest | 234/234, 49.61 s |
| ASan/UBSan build and full CTest | 234/234, 603.70 s |
| Independent archive boundary and corruption tests | 5/5 |
| Independent full case and analysis verification | 228/228, all hashes and cut joins checked |
| Accepted evidence projection | 19 mechanisms, 19 transitions and 67 distinct parameter records |

CTest retained the 227 WP-2 tests, six WP-3 fixture cases and one WP-3 scope/fault/recovery test. The unchanged cross-platform matrix exercises C++ on Windows and Linux Debug/Release plus Linux sanitizers. The added Linux Release step regenerates and verifies the accepted evidence projection, WP-3 case statistics and both new native timing archives. [Local command receipts](../../experiments/s6_4_wp3/verification) [CI definition](../../.github/workflows/ci.yml) [Reproduction](../../experiments/s6_4_wp3/README.md)
