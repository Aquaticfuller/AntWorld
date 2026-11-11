# RM-02 engineering acceptance

## Correctness

Local Windows Release, Debug and Clang ASan/UBSan each passed 222 of 222 CTests, including 216 inherited tests and all six RM-02 cases. The measured application revision is `2fb4179fcdaad73d50c7a7e1e2369f94eb95db11`. The local sanitizer configuration disabled leak detection on Windows. The Ubuntu sanitizer workflow enables leak detection. The exact commands, local build/test logs and independent source and archive checks are recorded below. [Commands](ENGINEERING_REPRODUCTION.md) [Raw regression evidence](../../experiments/s6_4_rm02_sprint/regression/)

| CTest case | Evidence |
| --- | --- |
| Transfers | Worker, queen and larval gifts, partial transfer, actual component credit, absorption, larval tissue and explicit protein return |
| Failures | Capacity arbitration between donors, wrong stage, reach and unusable supply. Rejected zero request and rejected actual zero committed mass have distinct meanings |
| Lifecycle | Same-tick hatch, death and resolution ordering preserved |
| Opportunities | Committed care-profile sampled opportunity and inactive choice, with separate detached geometric neighbor record |
| Recovery | Byte identity after segmented SQLite restore, observer-off replay and partitioned continuation. Full RNG, queue and canonical history equality. Duplicate cut and persisted anchor checks |
| Faults | Failed and grouped publication rollback, unchanged authority, missing and damaged sidecars, incompatible anchor, overflow accounting and a rolled-back Core advance |

The independent Python decoder also reconciled the 180-day depot-32 seed-1 smoke with 181 cuts, 191,461 examined events, 5,973 matched focal crop states and 4,352 scoped positive gifts. The closed v2 sidecar anchor matched the authoritative checkpoint, which also matched the observer-off replay. The inherited RM-01 assay and observer evidence verifier exited zero. No additional Core instrumentation was required. [Independent verifier](../../tools/verify_s6_4_rm02_sidecar.py)

The protected trees match the Phase 0 base byte for byte. Source tree `b5f20efbfcdd9baeebb8c6c43abcb12810e1c93d`, public headers `168ec1e9cb18edcb929507b8f3c8ecaf443bd0af`, storage `14d0c32d3a0738dc2198a56b1ffd0fd4cad919bd`. The exact regression and protected-diff checks provide engineering evidence for the frozen configuration and read path.

The Phase 4 audit-branch scope checker rejected the new engineering paths when tried on this branch. Its accepted inputs and outputs remain frozen. The independent protected-path diff covers the scientific audit, the Phase 0 material and the RM-01/R1 reports and experiments in addition to the Core source. The engineering branch's Core CI runs its applicable workflow and retains the new independent sidecar check.

## Original performance gates

The two accepted RM-01-R1 Release executables were retained. The birth identity precheck matched the protected reserve workload at 128, 512 and 2,048 workers. The original version-2 runner and analysis script produced three qualified sessions per gate and 504 raw timed rows including warm-ups. The unchanged acceptance rule is dense 2,048/512 advance P50 ≤6×. The intervals below are the original paired-session/block bootstrap.

| Gate | Qualified sessions | Rows | Ratio of pooled P50 | 95% interval | Paired median | Verdict |
| --- | ---: | ---: | ---: | --- | ---: | --- |
| TD-01 dense contact | 3 | 336 | 5.4044× | 5.3090–5.4872 | 5.4012× | PASS |
| TD-08 reserve-funded birth | 3 | 168 | 4.2868× | 4.1273–4.3985 | 4.2799× | PASS |

Two rejected TD-01 third-session admissions had system background P95 25.67% and 22.43%. The second also had selected-CPU P95 29.77%. The third attempt qualified after the prescribed cooldowns. All admission records and all measured rows are retained, including raw phase times, identity checks and bracketed sensor data. The analyzed archive reproduces with the unchanged analyzer in check mode. [Native raw records](../../experiments/s6_4_rm02_sprint/performance/legacy/) [Native analysis](../../experiments/s6_4_rm02_sprint/performance/legacy_analysis/)

## Observer performance

The paired assay measures advancement plus capture and actual SQLite publication through the last durable flush. It uses one child per sample and captures RSS high-water before the checkpoint audit. SQL setup, final database size, live WAL tail size, authoritative checkpoint and restore are reported separately. Warm-up and off/off control rows remain in the archive. Earlier publication variants are retained as engineering smoke evidence and excluded from the controlled ratios. [Publication design](STAGE_B_SIDECAR_PUBLICATION.md) [Frozen gates](FROZEN_ENGINEERING_PROTOCOL.md#stage-b-engineering-and-performance-acceptance)

### First qualified observer candidate

The version measured at `2fb4179fcdaad73d50c7a7e1e2369f94eb95db11` produced 504 rows across all three qualified sessions. One admission had system background P95 24.91% and chosen CPU P95 31.25%. The prescribed retry qualified. Both dense cases passed. The depot-32 case failed its median ceiling by 0.00575×, with all sampled cut and memory ceilings satisfied. Its per-run median sum of capture was 45.37–45.71 ms across sessions, and the publication sum was 38.04–39.38 ms. [First raw batch](../../experiments/s6_4_rm02_sprint/performance/observer/) [First analysis](../../experiments/s6_4_rm02_sprint/performance/observer_analysis.json)

| Workload | P50 ratio | P95 ratio | P99 ratio | Off/off P50 | Verdict |
| --- | ---: | ---: | ---: | ---: | --- |
| Dense-512 | 1.0493× | 1.0494× | 1.0120× | 1.0175× | PASS |
| Dense-2,048 | 1.0294× | 1.0032× | 1.0643× | 1.0001× | PASS |
| Depot-32, day 90 | 1.1058× | 1.0917× | 1.0860× | 1.0059× | FAIL |

### Publication correction for the next frozen batch

The second candidate bounds the 16-cut group by one MiB of encoded input and retains the one-cut memory budget and SQLite page cache. The v2 payload, digest, authoritative comparison, terminal flush, sync mode and automatic WAL checkpoint interval are identical. An uncompressed cut larger than the group limit still uses its own transaction. The observer is the only live owner and takes an exclusive SQLite lock. Closed exports use the same independently decoded database. The second run repeats all three observer cells and complete admission and analysis rules. The native executables and tested Core work are identical to the earlier qualified gates.

The second candidate produced 504 rows with three qualified sessions. The depot median was still above the frozen ceiling and the first session recorded a 310.89 ms cut, of which 310.22 ms was synchronous publication. The final flush maximum was 22.10 ms. Both dense cases again passed. All rows, including the stalls, remain in the archive. [Second raw batch](../../experiments/s6_4_rm02_sprint/performance/observer_encoded/) [Second analysis](../../experiments/s6_4_rm02_sprint/performance/observer_encoded_analysis.json)

| Workload | P50 ratio | P95 ratio | P99 ratio | Off/off P50 | Verdict |
| --- | ---: | ---: | ---: | ---: | --- |
| Dense-512 | 1.0453× | 0.9914× | 0.9035× | 1.0030× | PASS |
| Dense-2,048 | 1.0283× | 1.0261× | 1.0076× | 1.0029× | PASS |
| Depot-32, day 90 | 1.1026× | 1.1123× | 1.3714× | 0.9928× | FAIL |

### Bounded background publication and canonical encoding

The third candidate uses one sidecar writer thread that never queries the runtime. The owner thread captures at the original cuts, encodes and submits to a bounded queue. Foreground preflight waits for room before allocating a cut. At most 64 work items can be outstanding, including the current write. Packed queue capacity is limited to 2,500 KiB, with a single larger raw cut admitted alone. Capturing waits until the queue and the next raw reservation fit in 3 MiB. One further MiB covers packing scratch and bounded public-query staging. SQLite's cache and working set remain measured separately. File ownership, FULL synchronization and grouped commit remain unchanged. The writer drains before an anchor. A failure preserves the last durable prefix and wakes the producer with a retained observation error. Both worker and owner remain on the same benchmark CPU.

The capture path writes the Core's canonical event wire fields into a stack row rather than allocating a new vector per fact. The wire format is checked against `encode_event` and actual `events_after` history in CTest. The independent Python reader also decodes the bytes and reconciles them against the detached state and anchor. Raw scopes, cut locations, ordering and facts remain the same. Timing continues through real writer drain. The foreground budget includes capture and submission. Final drain, overlapping writer wall time and peak queued bytes are recorded separately.

The third measured C++ revision is `a1c326b604bed0cc7db67f46ff0b9682b4ec4cf9`. All three local builds and all 222 tests per build passed again. The tests include background continuation, exactly one durable prefix after a fault and a successful recapture from that prefix. Local full checks and every valid timing and admission attempt are archived. [Third regression logs](../../experiments/s6_4_rm02_sprint/regression_background/) [Second regression logs](../../experiments/s6_4_rm02_sprint/regression_encoded/) [Third batch](../../experiments/s6_4_rm02_sprint/performance/observer_background/) [Third analysis](../../experiments/s6_4_rm02_sprint/performance/observer_background_analysis.json) [Cross-platform Core CI for the measured revision](https://github.com/Aquaticfuller/AntWorld/actions/runs/43101363752)

| Workload | P50 ratio (95% interval) | P95 ratio | P99 ratio | Off/off P50 | Foreground P95 / max (ms) | Final drain max (ms) | Peak paired RSS increment (MiB) | Verdict |
| --- | --- | ---: | ---: | ---: | --- | ---: | ---: | --- |
| Dense-512 | 1.0476× (1.0435–1.0510) | 1.0408× | 1.0358× | 1.0082 | 1.0226 / 1.5746 | 2.4382 | 1.93 | PASS |
| Dense-2,048 | 1.0274× (1.0235–1.0319) | 1.0391× | 1.1558× | 1.0018 | 2.1523 / 2.4032 | 106.9501 | 1.77 | FAIL |
| Depot-32, day 90 | 1.0635× (1.0563–1.0707) | 1.1166× | 1.2692× | 1.0013 | 0.5786 / 3.0890 | 256.1484 | 3.17 | FAIL |

All three sessions qualified on the first admission, and the third batch kept 504 raw rows. All work identities, checkpoint comparisons and coverage checks matched. The P50 and P95 totals, foreground cut and RSS budgets passed in all cells. The analyzer in force before formal collection also applies the 20 ms stop ceiling to final synchronous drain. Five retained observer-on rows crossed it. The 2,048 terminal case's 106.95 ms drain coincided with 106.96 ms of writer wall time for its single cut. In the depot case with the 256.15 ms drain, cumulative writer wall time was 501.52 ms and peak queued payload was 764,679 B. Maximum queued payload across the batch was 764,679 B. All those delays are included in the total wall-time ratios. The raw data locate the waiting in final writer completion. They do not resolve storage synchronization time separately from thread or host scheduling stalls.

The observed failure is a retained `FAIL` under the existing analyzer and unchanged 20 ms ceiling. Tail waits remain unavoidable in the current design when the host takes longer to return from the required durable commit. Another CPU-side encoding or grouping change has no demonstrated way to bound that wait. Review can retain the same gate and qualify the storage path with independent per-write and scheduling traces, or prospectively define separate criteria for live cut interruption and terminal durable completion. Any separate qualification must keep real end-to-end durability, use the original timed work and preserve these failed attempts.

The independent 180-day depot smoke on the final executable produced the same complete authoritative checkpoint SHA-256 and the same 181 cuts, 191,461 examined facts, 5,973 matched focal crop states and 4,352 scoped gifts. All three observer analyses were regenerated from the exported raw samples and compared byte for byte. [Final codec check receipt](../../experiments/s6_4_rm02_sprint/regression_background/depot-independent-check.csv)
