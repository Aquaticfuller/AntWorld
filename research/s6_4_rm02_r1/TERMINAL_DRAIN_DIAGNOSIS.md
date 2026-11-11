# Terminal durable publication latency

The final observer candidate enqueues bounded cut payloads on the owner thread and commits through a single background SQLite writer. The benchmark calls `flush` immediately after the last advance and capture. That call closes submission, joins the writer, surfaces any writer failure and verifies that the committed cut count matches the observed cuts. The end timestamp follows those operations. This is a real wait at the close or durable handoff boundary and contributes to observed end-to-end latency.

| Quantity | Measurement | Operational boundary |
|---|---|---|
| Owner advance | `advance_ms`, summed around each `AdvanceTo` call | Forward progress while the writer may run concurrently. |
| Foreground capture and submission | `capture_ms + publish_ms` per cut, including waits for staging and queue capacity | Can stall live simulation between cuts. The 20 ms per-cut maximum applies here. Earlier synchronous candidates also incurred any writes they performed inside these calls. |
| Writer service wall time | `background_write_ms` around each append and the final SQLite commit | Includes row encoding/hash work on the writer, SQLite calls and synchronization as incurred, and preemption inside those spans. Overlaps owner activity. |
| Queue backlog | `peak_queue_bytes`, outstanding packed payload capacity including the active item | Byte high-water over the entire run. Per-item queue age, enqueue-to-start latency and depth at shutdown are unmeasured. |
| Terminal durable wait | `flush_ms` includes writer wake/drain/join, final commit and count verification | Save/export completion on this path. Writer service time overlaps it and cannot be added to it or subtracted from it to isolate I/O or scheduling. |
| Overall timed wall | `total_ms` before first cut/advance through successful terminal publication | Includes both owner stalls and terminal wait. Setup, authoritative checkpoint/restore audit and subsequent database close are outside this interval. |

The writer uses WAL mode, FULL synchronous commits and an automatic checkpoint threshold of 256 pages. SQLite can perform synchronization and an automatic WAL checkpoint during a commit. It can also checkpoint after the last connection closes. Durability was acknowledged before the end stamp. A separate post-timer database close duration is unavailable. The archive has no file-level I/O tracing, so the split among SQLite writes, synchronization, automatic checkpoint and scheduler delay remains unresolved. [Observer implementation](../../cpp/apps/rm02_observer.cpp#L371) [SQLite WAL documentation](https://sqlite.org/wal.html#performance_considerations)

## Retained long observations

| Latest cell | Drain P50, ms | P95, ms | P99, ms | Max, ms |
|---|---:|---:|---:|---:|
| Dense-512 | 1.5105 | 1.6996 | 1.9676 | 2.4382 |
| Dense-2,048 | 4.5107 | 4.8924 | 34.5766 | 106.9501 |
| Depot-32 | 2.7968 | 44.5559 | 208.8561 | 256.1484 |

| Session / sample | Cell | Terminal wait, ms | Summed writer service, ms | Peak queued bytes | Overall wall, ms |
|---|---|---:|---:|---:|---:|
| 1 / 110 | Dense-2,048 | 106.9501 | 106.9622 | 57,842 | 348.0512 |
| 1 / 163 | Depot-32 | 91.6973 | 118.0924 | 192,588 | 979.9918 |
| 3 / 160 | Depot-32 | 189.5395 | 362.9920 | 539,285 | 1,089.2553 |
| 3 / 163 | Depot-32 | 154.8684 | 342.6082 | 539,285 | 1,028.6849 |
| 3 / 165 | Depot-32 | 256.1484 | 501.5206 | 764,679 | 1,132.6614 |

The 106.9501 ms sample occurs after a single final cut and almost equals its measured writer span. This locates the wait at publication of that cut without identifying a particular storage operation. The depot sample with the longest drain also has the largest queued payload high-water and longer total writer service, consistent with a backlog in a workload with 91 cuts. Its queue size at the moment of closing is unknown. The earlier encoded candidate also retains one terminal wait over 20 ms and a separate 310.8869 ms foreground maximum.

The archive suffices to determine the metric boundary and the frozen verdict. The tail remains an operational constraint when a caller needs a durable sidecar before proceeding. Any future requirement for a hard close deadline needs its own frozen metric and instrumented evidence of queue depth/age at close, writer scheduling and individual transaction or VFS sync/checkpoint spans. Repeating an otherwise identical batch would give more tail samples with the same attribution limits.

[All six terminal samples over 20 ms across the three builds](../../experiments/s6_4_rm02_r1/performance/terminal_drains_over_20ms.csv) [Original publication report](../s6_4_rm02_sprint/RM02_ENGINEERING_ACCEPTANCE.md) [Benchmark measurement boundary](../../cpp/apps/antworld_s6_4_rm02_benchmark.cpp#L38)
