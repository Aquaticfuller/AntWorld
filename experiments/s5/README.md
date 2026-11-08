# S5 evidence and reproduction

The frozen protocol is [document 33](../../docs/33_S5_Persistence_History_and_Validation.md); conclusions and limitations are in [S5_RESULTS.md](../../S5_RESULTS.md). All biological fixtures remain `ENGINEERING_FIXTURE`. This stage validates storage and factual analytics, not a new integrated ecological model.

## Files and provenance

| File | Meaning |
|---|---|
| `raw/summary.csv` | All 128 comparisons: seeds 1..32, physiology/excavation, 5 s/30 s durable-save intervals. Each run asserts canonical continuation equality against an uninterrupted reference. |
| `summary.csv` | 32 independent seeds per scenario, mean and 95% percentile seed-bootstrap interval (4,096 draws, analysis seed 5005). Save-frequency controls are paired duplicates, not additional independent seeds. |
| `performance/repeated-*.csv`, `interleaved-*.csv` | All 10 iterations at 1,000/5,000/10,000 actual edits, six operation/size rows per iteration: 360 rows. |
| `performance/summary.csv` | p50/p95/p99/max timings, bytes and peak RSS; linear interpolation between order statistics. Tail quantiles from 10 repetitions are descriptive, not stable production tail guarantees. |
| `performance/s4_reference.csv` | Original approved S4 binary measured before the derived-index optimization. |
| `performance/s4_same_fixture_s5.csv` | The same S4 benchmark under S5; only measured checkpoint sizes gain eight bytes. Zero-byte placeholders remain zero. |
| `performance/long-history-before-query-index.csv` | Preserved initial diagnostic storage run exposing an increasingly slow time-window query. |
| `performance/long-history.csv` | Every day of the same 365-day workload after using the time index. Monthly/final recovery, 100 diagnostic facts per day. |
| `performance/s0.json`, `scheduler.csv`, `s1.csv`, `s2.csv`, `s3.csv` | Retained earlier performance fixtures rerun under S5. |
| `manifest.json` | Per-file producing source commit and SHA-256 of UTF-8 text normalized to LF. Historical S4 and pre-fix S5 provenance remain distinct. |
| `environment.json`, `verification.json`, `executed_tests.csv` | Hardware/toolchain, actual verification summary and all 522 individual test executions across five local builds. |
| `clean_reproduction.json`, `prior_stage_regression.json` | Clean-source S5 equality and complete S3/S4 semantic reproduction. |
| `figures/*.png`, `figures/*.svg` | Standalone figures produced from complete raw data. |

The raw 128-run matrix was produced at `8f3f5ec7caf868dd76c9704411be9134ca24dd2c` and reproduced from a clean archive of final C++ source `fe4466cb09e913f4c4fe7863a0c5fd84eecf21da`. The latter adds the archive CLI and the bounded time-index query fix without changing the simulation. Final geometry timings and the corrected long-history run use `fe4466c`. Source IDs for every measured file are explicit in the manifest. Report/analysis/CI-only delivery commits do not change the measured C++ source.

## Measurement interpretation

Geometry conditions use actual validated dig/fill actions, real soil parcels and two seeded identities. `repeated` alternates one patch; `interleaved` uses two distinct overlapping boxes and two carriers. Only the current disposable index loses overwritten identical-box entries (one/two remaining entries). All 1,000/5,000/10,000 authority edits and matching facts remain in checkpoints and SQLite. Neither condition is a general distinct-shape worst case.

`checkpoint_encode` serializes authority. `checkpoint_restore` performs the full core restore/audit. `durable_save` includes snapshot capture, metrics/history processing, inserts and FULL-synchronized COMMIT into a fresh database; connection/schema initialization is outside this timer. `durable_load_validate` includes restore, database/evidence/metric validation, a re-encoded byte-equality check and a route-equality check. `indexed_history_and_flow_query` combines a participant page and exact dry-soil flow; it is not a constant-time guarantee for every filter. `post_wal_checkpoint_size` is a size observation with a deliberately zero duration, not a latency sample.

Times are warm OS-cache wall timings; no manual cache flush, no discarded runs and no concurrent build during the timed matrices. Each condition/count runs in its own process. Peak RSS is the whole-process high-water mark across its ten iterations, including multiple live checkpoint/runtime copies and the storage audit. Current RSS and SQLite allocator bytes are separate raw columns; neither is an estimate of per-ant memory. `database_bytes` is main + WAL + SHM, including allocated reusable space; post-checkpoint size is also recorded. Bytes are exact; plots use MiB (2^20 bytes).

The 365-day fixture has one adult without physiology, 100 scheduled diagnostic RNG draws per day and daily saves. It produces 36,502 actual facts and 366 observations/generations, retaining two complete checkpoints. It is a storage clock, **not an ecological year**, a mortality experiment or an S6/S9 gate. Negative `load_validate_us` means no restore was measured that day, not zero cost. The before/after files have identical event/time/generation/checkpoint/database-size columns. Each is one serial run, so their latency differences have no replicated-run confidence interval.

## Build, tests and durable CLI

From the repository root, use the pinned Windows toolchain:

```powershell
./tools/bootstrap_windows.ps1
./tools/build_windows.ps1 -Configuration Debug
./tools/build_windows.ps1 -Configuration Release
$env:ASAN_OPTIONS = 'halt_on_error=1'
$env:UBSAN_OPTIONS = 'halt_on_error=1:print_stacktrace=1'
./tools/build_windows.ps1 -Configuration Debug -BuildDirectory build/sanitized -Sanitizers
./build/release/antworld_archive.exe create out/example.sqlite scenarios/p0_smoke.json
./build/release/antworld_archive.exe advance out/example.sqlite 381b1f47-91b8-4b2d-9d51-967a3e2b2a01 120000
./build/release/antworld_archive.exe inspect out/example.sqlite 381b1f47-91b8-4b2d-9d51-967a3e2b2a01
```

Use a new database filename for `create`; it refuses to overwrite an existing world. The existing JSON parser accepts the diagnostic empty-world profile. Populated worlds are created by the public C++ API and experiment runners.

Portable CMake commands (C and C++20 compilers required):

```sh
cmake -S cpp -B build/release -DCMAKE_BUILD_TYPE=Release
cmake --build build/release --parallel 4
ctest --test-dir build/release --output-on-failure
cmake -S cpp -B build/core-only -DCMAKE_BUILD_TYPE=Release -DANTWORLD_STORAGE=OFF
cmake --build build/core-only --parallel 4
ctest --test-dir build/core-only --output-on-failure
```

The default build fetches SQLite 3.54.1 and verifies SHA-256 `0a9c8e34352dad46006aa82836d5383bff9dc6bc9ce5a60553c05aa30e6ad1f9`. Pass `-DANTWORLD_SQLITE_ARCHIVE=/path/to/sqlite-amalgamation-3540100.zip` for offline builds. On Windows the local `.tools/sqlite/` archive is discovered automatically. The dependency-free core-only build runs 90 tests (89 inherited tests plus the core receipt allocation test). SQLite sanitizer instrumentation is enabled with `ANTWORLD_SANITIZERS=ON`.

## Reproduce all experiments

```powershell
./build/release/antworld_s5_experiment.exe out/s5-reproduction 32
python tools/verify_s5_reproduction.py out/s5-reproduction --source-commit (git rev-parse HEAD) --report out/s5-reproduction.json
./build/release/antworld_s4_experiment.exe out/s5-s4-regression 32
./build/release/antworld_s3_experiment.exe out/s5-s3-regression 64
python tools/verify_s4_reproduction.py out/s5-s4-regression --source-commit (git rev-parse HEAD) --checkpoint-byte-delta 8 --s3-regression out/s5-s3-regression --report out/s5-prior-stage-regression.json
foreach ($condition in @('repeated', 'interleaved')) {
    foreach ($count in @(1000, 5000, 10000)) {
        ./build/release/antworld_s5_benchmark.exe out/s5-performance $count $condition 10
        if ($LASTEXITCODE -ne 0) { throw 'S5 performance fixture failed' }
    }
}
./build/release/antworld_s5_history_benchmark.exe out/s5-history 365 100
./build/release/antworld_s4_benchmark.exe out/s5-s4-performance.csv
./build/release/antworld_benchmark.exe
./build/release/antworld_scheduler_benchmark.exe
./build/release/antworld_s1_benchmark.exe
./build/release/antworld_s2_benchmark.exe
./build/release/antworld_s3_benchmark.exe
```

On Linux, omit `.exe`; use shell loops for the same six geometry cases. Benchmark fixture database names are disposable under the supplied output directory. Each run removes only its own exact fixture filenames. Do not point fixture runners at a valuable archive. The semantic verifier excludes only `database_bytes`, whose allocation depends on SQLite/OS, from S5 cross-platform comparison. The runner itself asserts complete canonical state equality, including pending queues and RNG; it does not rely solely on rounded CSV metrics.

Clean-source reproduction was performed with `git archive fe4466cb09e913f4c4fe7863a0c5fd84eecf21da`, extraction to a fresh ignored directory, a fresh Release build with the pinned local SQLite archive, all 108 tests, and all 32 S5 seeds. An equivalent portable workflow is:

```sh
git archive --format=tar --output=out/s5-source.tar fe4466cb09e913f4c4fe7863a0c5fd84eecf21da
mkdir -p out/s5-source
tar -xf out/s5-source.tar -C out/s5-source
cmake -S out/s5-source/cpp -B out/s5-build -DCMAKE_BUILD_TYPE=Release
cmake --build out/s5-build --parallel 4
ctest --test-dir out/s5-build --output-on-failure
./out/s5-build/antworld_s5_experiment out/s5-clean 32
python tools/verify_s5_reproduction.py out/s5-clean --source-commit fe4466cb09e913f4c4fe7863a0c5fd84eecf21da --report out/s5-clean.json
```

For the preserved slow reference, archive/build approved S4 `214fce398a29d26507e21c75f4f78f1485527e6b` and run its `antworld_s4_benchmark`; for the pre-index history result use `8f3f5ec7caf868dd76c9704411be9134ca24dd2c` and its history benchmark. Do not overwrite the original raw files when reproducing.

## Audit and figures

```sh
python tools/analyze_s5.py --check
python tools/ci_verify.py
python -m pip install --target .tools/s2_1-python -r tools/s2_1_plot_requirements.txt
python tools/plot_s5.py
```

The audit checks the full seed/interval matrix, zero mass/energy residuals, exact paired metrics, all timing samples, original/new geometry fixture compatibility, before/after history counters, raw hashes and recomputed summaries. Plot dependencies are optional pinned rendering packages, unrelated to the C++ runtime. GitHub CI additionally reproduces all S5 seeds on Linux Release and runs all 108 tests on Linux/Windows Debug/Release and Linux Clang ASan/UBSan. Physical device power loss is NOT RUN; injected VFS failures and process termination are separate actual tests.
