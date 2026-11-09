# S6.3.3.1 data and reproduction

The [main report](../../S6_3_3_1_RESULTS.md) separates engineering capability, exploratory behavioral fit and formal performance. [Performance results](../../S6_3_3_1_PERFORMANCE_RESULTS.md) give the workload-specific qualification and instrument limitations. [Scientific evidence](../../research/s6_3_3_1/EVIDENCE.md) records original studies, full-text access, observation definitions and data roles.

| Path | Contents |
| --- | --- |
| `diagnosis/` | Pre-change decision reconstruction, event-level outcomes and B01 window audit from the immutable S6.3.3 archive. These tables are frozen at `bbb03b7`. |
| `raw/manifest.json` | Every new model run in 16 batches. Names identify legacy or local policy and layout/assay. Files retain both compressed SHA-256 and the SHA-256 of the native CSV. |
| `raw/{legacy,local}/{retrieval-line,holdout-*,b01}/` | Native run summaries, full exported events as losslessly compressed CSV, native scan rows and window summaries. Empty window/scan tables in retrieval assays have their original headers. |
| `analysis/runs.csv`, `actors.csv`, `acts.csv`, `decisions.csv` | Per-run and per-individual timing, action phases, current ranges and carrier path lengths. Perception is reconstructed at decision boundaries in the open arena. Empty timing fields indicate unobserved endpoints. |
| `analysis/transport_segments.csv`, `continuous_loaded_episodes.csv`, `trips.csv` | Terminal segment identity, move distance, factual outcome, end time, ordered consecutive segment groups, and caregiver–target trip follow-up. Scheduled end-to-start spacing is 2 ms. |
| `analysis/after_delivery.csv`, `first_delivery_followup.csv` | First and later deliveries with initially displaced brood still outstanding, observed retry times, and right-censoring windows. |
| `analysis/paired_retrieval.csv` | Historical and prospective simulator seed-paired means and 95% percentile intervals. Blank per-actor endpoints remain in the raw tables. Group first-contact misses contribute 600 s to capped means. |
| `analysis/b02_literature_comparison.csv` | The all-unit, paired 67 and productivity 61 B02 cohorts, paired within a published colony only when aggregating its repeated trials. Paper-versus-simulation errors resample paper units and simulation seeds independently. Revised B02 comparisons are exploratory. |
| `analysis/b01_windows.csv`, `b01_literature_comparison.csv` | Actual committed and clipped care bouts, worker opportunities and contacts, 50/51 overlap and point scores, and measured-vs-simulated signed errors. |
| `density.csv`, `analysis/density_summary.csv` | All 128 TD-11 timing rows including warmups, phase p50/p95/p99, derived exact candidate work, opportunity facts, handling, checkpoint and encoded journal bytes. TD-11 is separate from the legacy worker gate. The initial trace-placeholder export remains in `density_before_trace_receipt.csv`. |
| `independent_movement/` | All 69 derived flat worker trajectory records, by-colony and overall summaries, and original Dataset S1 checksum. The source uses inclination index 1 for its flat condition. Coordinates are in m, time in s, and speed in mm/s. |
| `historical_replay.json` | A complete independent replay of 384 inherited cases with matched exported event counts and original archive checksums. The canonical archive remains under `../s6_3_3/raw`. |
| `performance/` | Three original instrument probes, six schedules and raw telemetry, qualified contact samples, and the preserved wrong-workload ordinary-birth sample batch. |
| `performance_reserve/` | Corrected reserve-birth-only freeze, independent workload identity receipt, raw and analyzed results. No original rows are replaced or pooled. |
| `verification/` | Local test logs and cross-platform verification information. |
| `figures/` | Standalone SVG figures from the analysis tables. |

## Build and run

The local build used LLVM/MinGW clang 23.1.5, CMake 3.31.10, Ninja, C++20 and the repository-pinned SQLite 3.54.1. Replace the native build path with the actual executable location on a multi-configuration generator. The next commands show single-configuration Release on Windows. Choose a fresh local output directory for reruns.

```powershell
cmake -S cpp -B build/retrieval-release -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build/retrieval-release --parallel 4
ctest --test-dir build/retrieval-release --output-on-failure -j 4

$runRoot = 'out/retrieval-repro'
$binary = 'build/retrieval-release/antworld_s6_3_3_experiment.exe'
New-Item -ItemType Directory -Force $runRoot
python tools/run_s6_3_3_1_assays.py --binary $binary --out "$runRoot/raw"
python tools/analyze_s6_3_3_1.py --raw "$runRoot/raw" --out "$runRoot/analysis"
python tools/run_s6_3_3_1_assays.py --binary $binary --out "$runRoot/legacy" --historical-report "$runRoot/legacy.json"
python tools/diagnose_s6_3_3_1.py --out "$runRoot/frozen-diagnosis"
& 'build/retrieval-release/antworld_s6_3_3_1_density.exe' "$runRoot/density.csv"
python tools/analyze_s6_3_3_1.py --density-only --density "$runRoot/density.csv" --out "$runRoot/analysis"
```

Use a fresh build configured with `-DCMAKE_BUILD_TYPE=Debug` for the Debug suite. Use the same with `-DANTWORLD_SANITIZERS=ON` and Clang for ASan and UBSan. The Windows run used `ASAN_OPTIONS=detect_leaks=0:halt_on_error=1` and `UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1`. GitHub Actions configures Linux Clang ASan with leak detection enabled. The recorded reports exclude the application output directories from Git except for permitted evidence files.

To regenerate the movement comparison, download [Khuong et al. Dataset S1](https://doi.org/10.1371/journal.pone.0076531.s005) into an ignored local directory. The script verifies the original SHA-256 and reads the author tables from the archive without republishing it.

```powershell
python tools/analyze_s6_3_3_1_tracks.py out/Khuong_2013_Dataset_S1.zip --out out/retrieval-repro/movement
python tools/plot_s6_3_3_1.py --out out/retrieval-repro/figures
```

The plotting tool uses Matplotlib. Analysis and archive verification use Python's standard library. The default analysis source is the archived evidence in this directory. [Performance reproduction and provenance](../../S6_3_3_1_PERFORMANCE_RESULTS.md)
