# S6.3.4 results — Live Durable History and Long-Term Persistence

**PASS for the frozen S6.3.4 engineering and storage scope.** This branch ends at independent review. Biological calibration and Core Readiness retain their separate review gates.

| Gate | Result | Evidence |
|---|---|---|
| Online, bounded and lossless publication | **PASS** | A background writer seals the live journal into verifiable blocks. SQLite publishes the blocks, continuation and manifest atomically. The runtime can commit later facts during a publication, and acknowledgement retires only the published prefix. |
| Recovery, integrity and migration | **PASS** | Simulated crashes at six application boundaries, partial WAL write termination, VFS write/sync failures, malformed histories, duplicate saves, held brood, carried soil, pending work and blocked geometry. Legacy shadow migration preserved canonical bytes and validated the retained states. |
| Dense and long storage budgets | **PASS** | 42 final attempts, including seven declared warm-ups, with the complete first-build batch retained separately. Final million-fact restore P95 12.572 s against 15 s. |
| Ecological continuation | **PASS for the frozen cases** | 8 unchanged 21-day worlds and 6 existing 180-day arms. Exactly 1,623,444 facts across the 14 runs match each uninterrupted counterpart byte for byte. |
| Species-level quantitative validation | **FAIL carried forward** | B01/B02 discrepancies, low trail continuity and weak social recruitment, maternal provisioning, scarcity allocation, construction feedback and activity rhythms remain open. |

## Implementation and evidence

The v2 headless archive uses one local SQLite WAL database and an immutable, SHA-256-linked journal. State frames retain the same simulation authority as the old Core checkpoint and share the publication transaction with their fact blocks. The online writer admits one queued capture and limits the hot tail to 600,000 facts and the capture to 256 MiB. Failed saves keep the owner's unpublished facts. Gauge observations come from the saved world and analytical indexes can be rebuilt from retained evidence. The v1 reader and verified shadow conversion remain available. Historical recovery uses a published base, its verified fact suffix and the target's actual continuation frame. Pending state between published frames remains outside the recovery contract.

The historical 128-worker timed benchmark still has 490,240 opportunities and 498,598 facts. It recorded 1,074,458,624 B and a 51.62554 s median save. The same canonical stream in the new format occupies 5,206,016 B with sidecars after flush. Durable background publication was 628.4 ms P50 and 857.7 ms P95. Foreground submission was 1.375 ms P95, with another 6.348 ms P95 measured for acknowledgement. The validated restore was 3.861 s P95 and resident peak was 133.86 MiB. The million-fact archive used 21,954,560 B, with 59.29 MiB online resident peak. These are bounded host results. Temperature, frequency and package power were unavailable for this batch. [Performance and raw evidence](research/s6_3_4/LONG_TERM_STORAGE_PERFORMANCE.md)

The legacy pressure archive also passed shadow migration. The original main database and any durable WAL frames are checked before and after. The 498,598 length-prefixed records match the original SHA-256 `edcaad96310fb2d398ead023731838ab5ba9020ad5ce2c277f22ce4bbf54655a`. The first outer audit flagged a zero-byte SQLite WAL sidecar as a changed source. The retained retry separates empty coordination files from durable bytes and confirms an unchanged main database and a byte-identical canonical stream. [Migration and fault evidence](research/s6_3_4/RECOVERY_AND_MIGRATION_VALIDATION.md)

## Ecological comparisons

All eight 21-day cases match their previously archived R1 state, trace and canonical SHA-256, including empty-resource extinctions. The exact comparisons cover the durable day-10 cut, irregular subsequent advancement, and the day-21 restore. The original 96 cases and 8,288,521 facts remain unchanged.

| 180-day arm | Seed | Births | Emergence | Deaths | Living at day 180 | Canonical facts |
|---|---:|---:|---:|---:|---:|---:|
| Funded, 32 workers | 1 | 78 | 71 | 0 | 111 | 191,461 |
| Funded, 32 workers | 2 | 68 | 62 | 0 | 101 | 170,290 |
| Funded, 32 workers | 3 | 82 | 75 | 0 | 115 | 205,897 |
| Funded, 8-worker mortality control | 1 | 2 | 2 | 1 | 10 | 28,624 |
| Funded, 8-worker mortality control | 2 | 9 | 5 | 5 | 13 | 34,945 |
| Funded, 8-worker mortality control | 3 | 2 | 2 | 1 | 10 | 28,990 |

The 32-worker primary cases historically showed zero deaths. The supplementary 8-worker controls were frozen before they ran and reproduce the original 180-day demographic outcomes. Seed 2 verifies five distinct death days alongside nine distinct birth days. These are cohorts within the existing queen's colony. Daughter-queen reproduction remains outside this model. Each run makes 18 durable cuts and validates continuation at days 90 and 180. Population, geometry and nutrition remain governed by the existing engineering fixtures. [Ecology CSV and references](experiments/s6_3_4/portable/summary/ecology_summary.csv) · [Supplemental protocol](research/s6_3_4/SUPPLEMENTAL_MORTALITY_PROTOCOL.md)

## Verification and remaining work

The local Debug, Release and ASan/UBSan suites each passed 212 tests. The 201 reviewed test names remain present. The first Windows CI builds rejected an implicit `int` to `uint8_t` conversion in SHA-256 padding. The typed-byte correction preserved all canonical streams, block-chain hashes and state-frame hashes across both complete experiment batches. All five CI jobs passed on the corrected C++ source, including Windows and Linux Debug/Release and Linux sanitizers with leak detection. Linux Release also verifies wire bytes independently in Python. TD-01 and TD-08 preserve the old ≤6× gates and current exact work identities at all three populations. New admitted wall-clock ratios for those protected workloads are outside this stage. [Final test and fault records](experiments/s6_3_4/portable/verification) · [Source CI run](https://github.com/Aquaticfuller/AntWorld/actions/runs/42813390915) · [Initial CI evidence](experiments/s6_3_4/verification/github-ci-before-msvc-fix.json) · [Archive parity](experiments/s6_3_4/portable/summary/portability_parity.json)

The measured storage portion of TD-11 is qualified. Dense opportunity enumeration, cold verification beyond one million facts, retention of all state frames and full geometric edit growth remain open. S6.3.4 uses bounded local SQLite archives. Physical storage failure and remote filesystem qualification are separate. The R1 continuous motor remains opt-in, with a flat ground plane, cubic clearance, bounded local connectors and unmodeled body orientation and load posture. Routing inside arbitrary cavities and alternate discovery after permanent blockage remain open. [Technical debt](docs/08_Open_Questions.md) · [Biology readiness](research/s6_3_4/BIOLOGY_MODEL_READINESS_MATRIX.md)

[Frozen protocol](docs/64_S6_3_4_Frozen_Durable_History_Protocol.md) · [Architecture](research/s6_3_4/DURABLE_HISTORY_ARCHITECTURE.md) · [Canonical block format](research/s6_3_4/CANONICAL_EVENT_BLOCK_SPEC.md) · [Reproduction and file index](experiments/s6_3_4/README.md)
