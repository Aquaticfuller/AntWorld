# TD-11 spatial cost and durable history prerequisite

**OPEN and required before the S6.4 Core Readiness Gate.** The historical unprofiled timed dense 128-worker case still has 490,240 opportunities, 498,598 facts, a 1,074,458,624-byte SQLite database and a median save of 51,625.54 ms. The prior persistence phase attribution and lossless offline block experiment remain available. [S6.3.3.3 density and storage](../s6_3_3_3/TD_11_INTEGRATED_PERFORMANCE.md)

## R1 measurements

Both contracts ran the same 12 scenarios with 8, 32 or 128 caregivers, two larvae per worker and dense/spread positions within one colony. Each had one retained warm-up and three measured runs. Timed care runs 600 s and the integrated arm runs two game days. The comparison times advance, checkpoint encoding, memory restore and journal encoding separately. The density run uses memory saves. The 21-day ecology runs additionally report real SQLite save times at days 10 and 21, with raw paired input and fact IDs.

| 128-worker case | Contract | Opportunities | Committed facts | Advance p50 | Checkpoint p50 | Resident memory p50 |
|---|---|---:|---:|---:|---:|---:|
| Timed dense | Reviewed | 490,240 | 498,598 | 138.45 ms | 301.54 ms | 465.86 MB |
| Timed dense | Continuous | 490,240 | 499,006 | 128.70 ms | 300.18 ms | 466.82 MB |
| Integrated dense | Reviewed | 97,167 | 140,396 | 88.58 ms | 80.50 ms | 138.44 MB |
| Integrated dense | Continuous | 194,693 | 213,354 | 88.44 ms | 125.95 ms | 205.78 MB |

The physical affordances change the integrated candidate's actual events. Its dense opportunity count doubles and the checkpoint phase and memory grow. Report each arm's p50/p95/p99 and fact counts as observed. The two contracts ran in separate processes in legacy-first order while ecological experiments were active. This prevents attributing the small advance-time differences to the motor alone. Each replicate agrees exactly within its contract, and the legacy identities match the archived workload. [Host and raw density samples](../../experiments/s6_3_3_3_r1/density) · [Phase quantiles](../../experiments/s6_3_3_3_r1/density_summary.csv)

Protected TD-01 and TD-08 retain the admitted 5.5163× and 4.3147× advance p50 ratios and the original ≤6× gate. The R1 workload receipts verify their same event/candidate/state identities at 128, 512 and 2048. The new mixed experiments and density measurements provide no new formal wall-clock admission. [Workload receipts](../../experiments/s6_3_3_3_r1/verification)

## Required implementation and acceptance before S6.4

1. **Version and seal canonical facts.** Define a bounded contiguous block of length-prefixed canonical event bytes with WorldId, schema and codec versions, first/last EventId and time, uncompressed size and a hash tied to the preceding block. Keep each committed opportunity, participant, source, outcome and payload. Use existing S6.3.3.3 reversible blocks as a baseline. Store a validated committed cursor for each active tail and sealed prefix.
2. **Publish atomically.** A SQLite transaction advances the manifest and checkpoint anchor only after all referenced bytes are durable. Keep older generations readable. Derived event/participant/metric indexes may be rebuilt, and late read verification must detect inconsistent cursor, checksum or order. A failed seal or background save leaves the previous published world intact. A bounded write queue must surface backpressure or a failed save while preserving committed history. Establish an explicit memory budget for both pending history and decoding.
3. **Implement compatibility and query equivalence.** Migrate an existing store through an independently verified shadow copy. Require byte-identical decoded canonical facts, full EventId/clock/revision/source order, identical individual history and all existing metric definitions and evidence links. Prove exact continuation from checkpoints taken before, inside and after a seal and at a blocked loaded carrier. Compare restored RNG, queue, custody, clearance, geometry authority and ledgers. Keep a legacy reader until migration can be checked end to end.
4. **Test failure and measured scale.** Inject faults before and after block append, fsync, manifest publication, index update and WAL recovery. Include corrupt, missing and reordered block controls, duplicate delivery of a save request and replay after restart. Re-run the unchanged 128-worker timed and integrated workload, the 21-day mixed controls and a frozen long-horizon multi-generation case. Compare actual candidate counts and bytewise facts. Report p50/p95/p99 advance, foreground stall, encoding, save, restore, seek/query and peak memory by phase, plus disk growth. Freeze numerical memory and storage latency budgets on an admitted host for review before implementing the new store. Preserve the TD-01/TD-08 thresholds.

The current native writer still checkpoints complete memory state and inserts SQLite event and participant rows. The experiment archive compresses copies only. The durable-history gate requires the live, recoverable implementation and the tests above before S6.4 acceptance.
