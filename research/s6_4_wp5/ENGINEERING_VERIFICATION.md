# WP-5 engineering verification

## Correctness and recovery

The reviewed `cpp/src`, `cpp/include` and `cpp/storage` trees retain their baseline identities. WP-5 adds an application and analysis targets. It reuses the observer database schema, budgets, snapshot reads, background publishing and restart logic from RM-02 and WP-4. The local test count increases from 243 to 250. Windows Debug, Release and ASan/UBSan each completed 250/250. A strengthened compact positive assertion was subsequently rerun in all three builds. It requires a committed geometry edit from the existing 32-worker compact case. Python's five tests independently exercise event ties, censoring, material bounds, failed edit atomicity and loaded route closure. The hosted workflow runs both platform configurations and sanitizers and verifies the archived data on Linux Release. [Commands](../../experiments/s6_4_wp5/README.md) [Windows receipts](../../experiments/s6_4_wp5/tests) [Hosted CI](https://github.com/Aquaticfuller/AntWorld/actions/workflows/ci.yml?query=branch%3Acodex%2Fs6.4-wp5-survival-excavation)

All 139 new runs compare the final checkpoint and every canonical fact byte with the observation-off world advanced across a different partition. The gate witness also inserts extra advancement cuts between host interventions. A segmented SQLite snapshot restores at each run's midpoint and the Sidecar rejects duplicate cut publication. The independent reader checks SQLite integrity and the canonical prefix digest, replayed custody and edited volume, stock conservation, and cross-cut identity. The inherited storage interruption, Sidecar fault/retry and soil edit rollback tests remain part of CTest. Canonical history retains every committed fact including rejections. The bounded live observer has a narrower publication scope and independent full-history export. The field `UNOBSERVED` explicitly preserves work intervals without recorded start/stop facts. [Identity receipts](../../experiments/s6_4_wp5/analysis/run_identity.csv)

## Controlled observer performance

The frozen collector admitted three sessions and retained 504 native rows (432 measured after warmups). A session-2 attempt failed background-load admission and remains in the archive. The two dense workloads preserve the historical contact workload. The depot observer includes the existing lineage projection and a one-focal geometry/route projection. The observer and off arm retain the same authoritative checkpoint and history identity. Accepted balances and telemetry are archived for each session.

| Workload | Total P50 on/off | Total P95 on/off | Foreground P95 / maximum (ms) | Peak paired RSS increment (MiB) | Maximum final drain (ms) |
|---|---:|---:|---:|---:|---:|
| Dense 512 | 1.06 | 1.05 | 1.33 / 9.61 | 2.06 | 5.97 |
| Dense 2,048 | 1.03 | 0.99 | 2.54 / 3.33 | 1.62 | 16.52 |
| Depot 32 | 1.0733 | 1.0764 | 0.8684 / 5.9559 | 2.79 | 40.5833 |

All observer checks passed, including the original off/off controls. The final drain remains a distinct closing-time cost charged in total time. The result supplies no hard real-time guarantee for durable I/O. Real WP-5 assay timing includes full export, an independent continuation and checkpointing. Per-cut measurements and host peaks are in `assay_costs.csv`. The largest new canonical case is about 2.79 MB. The largest observed assay capture/census/probe/submission sum is 1.821 ms, a descriptive result for the fixture collection. [Native analysis with paired estimates and uncertainty](../../experiments/s6_4_wp5/performance/observer_analysis.json) [New assay costs](../../experiments/s6_4_wp5/analysis/assay_costs.csv)

## Protected Core work

Six sessions admitted on their first attempt. All 336 contact and 168 birth rows were retained, with complete native and HWiNFO provenance. The three-population birth identity check matched the accepted reserves, exact state and trace hash, event count, conservation and recovery controls before timing. The original dense 512 to 2,048 advance gates remain at 6×.

| Workload | P50 ratio | 95% bootstrap interval | Paired median (95% interval) | Result |
|---|---:|---:|---:|---|
| TD-01 dense contacts | 5.4209× | 5.3447–5.4759 | 5.3524× (5.3002–5.4245) | PASS |
| TD-08 birth registration | 4.3396× | 4.3023–4.4109 | 4.3573× (4.3050–4.4201) | PASS |

The initial schedule preparation preceded the stronger compact CTest assertion. The final formal Core schedule binds to `69c88610ea597d1660ee3931849cba3d6842b821`; the earlier preparation produced no timed rows. No performance gate, simulation workload, action rate or fact retention changed. The sanitized export removes unrelated process inventories and retains all selected telemetry, durations, phase counters, slow samples and original source hashes. [Raw Core archive](../../experiments/s6_4_wp5/performance/core) [Core growth and confidence intervals](../../experiments/s6_4_wp5/performance/core_analysis/growth.csv)
