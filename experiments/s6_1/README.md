# S6.1 evidence and reproduction

All scenarios, numeric parameters and behavioral mechanisms are **ENGINEERING_FIXTURE**. Read frozen document 37 (`03ae833`), metric definitions in document 38 and `S6_1_RESULTS.md`. Preserve every existing S0-S6 archive. Use fresh output directories: native runners refuse to overwrite completed outputs. No S7 work is authorized.

## Build and regression tests

Use the pinned CMake/toolchain/bootstrap described in the repository README. SQLite 3.54.1 and its archive hash are pinned by `cpp/CMakeLists.txt`. Portable commands, with `cmake`, a C++20 compiler and `python` on PATH:

```sh
cmake -S cpp -B build/s6_1-release -DCMAKE_BUILD_TYPE=Release
cmake --build build/s6_1-release --parallel 4
ctest --test-dir build/s6_1-release --output-on-failure
cmake -S cpp -B build/s6_1-debug -DCMAKE_BUILD_TYPE=Debug
cmake --build build/s6_1-debug --parallel 4
ctest --test-dir build/s6_1-debug --output-on-failure
cmake -S cpp -B build/s6_1-sanitized -DCMAKE_BUILD_TYPE=Debug -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ -DANTWORLD_SANITIZERS=ON
cmake --build build/s6_1-sanitized --parallel 4
ctest --test-dir build/s6_1-sanitized --output-on-failure
cmake -S cpp -B build/s6_1-core-only -DCMAKE_BUILD_TYPE=Release -DANTWORLD_STORAGE=OFF
cmake --build build/s6_1-core-only --parallel 4
ctest --test-dir build/s6_1-core-only --output-on-failure
```

These commands use a single-configuration generator (for example Ninja or Unix Makefiles). With Visual Studio or another multi-configuration generator, add the matching `--config Release` / `--config Debug` to builds and `-C Release` / `-C Debug` to CTest; `CMAKE_BUILD_TYPE` alone does not select that generator's configuration.

For clean-source verification, export the measured source with `git archive`, extract to a new directory and configure a separate Release build against that exported `cpp` tree. On Windows, use the pinned `tools/bootstrap_windows.ps1` dependencies and supply the local pinned SQLite archive via `ANTWORLD_SQLITE_ARCHIVE`; append `.exe` to executables below. ASan/UBSan use `halt_on_error=1`; Linux additionally enables leak detection. Keep console and `Testing/Temporary/LastTest.log` evidence. The recorder reads executed tests; it does not manufacture passes.

## Full frozen ecology grids

```sh
build/s6_1-release/antworld_s6_1_experiment out/s6_1-matrix 16 matrix
build/s6_1-release/antworld_s6_1_experiment out/s6_1-sensitivity 16 sensitivity
build/s6_1-release/antworld_s6_1_experiment out/s6_1-observer-integrated 32 integrated
build/s6_1-release/antworld_s6_experiment out/s6_1-integrated 32 primary combined
build/s6_1-release/antworld_s6_experiment out/s6_1-long 8 long combined
build/s6_1-release/antworld_s6_experiment out/s6_1-legacy-reproduction 1 primary legacy
python tools/verify_s6_reproduction.py out/s6_1-legacy-reproduction --source-commit MEASURED_COMMIT --schema-version 8 --physics-version 9 --checkpoint-byte-delta 2 --report out/s6_1-legacy-reproduction.json
```

The observer's two flags are fixed by arm, never selected from outcomes. Main matrix: 16 seeds x 4 arms x 3 worker counts x 3 source-protein amounts = 576 cases, 180 s. Sensitivity: 128 additional cases at 180 s, plus default cases already present in the matrix. Integrated observer: 32 seeds x 2 mirrors x 4 resource/geometry conditions x 2 policies = 512 cases, 600 s. Durable primary: 256 corrected cases x 3 modes; long: 16 corrected cases x 3 modes, 1,800 s. Each observer checks accelerated/checkpoint continuation at common 30 s boundaries; durable runs independently use actual SQLite recovery every 60 s.

Each case retains every canonical fact in a local binary or SQLite history. `events.csv` is a selected factual projection, not a claim that omitted fact kinds never occurred; `event_counts.csv` counts every kind. `scheduled_kind` identifies actual resolved Trophallaxis sources, including failed resolutions. Time series export ingredient inventory components and explicit sinks for independent balance checks. `geometry.csv` contains every ordered authoritative edit. WorldId `(6,8)` is fixture-local: identify a run by its complete configuration key and archive, not WorldId alone.

The measured ecology execution uses source `fbe8852` and contiguous independent process intervals. An optional final `FIRST_SEED` argument defaults to 1; `SEEDS` remains a count. Matrix and sensitivity intervals are `(count=4, first=1/5/9/13)`; integrated observer and durable primary intervals are `(count=8, first=1/9/17/25)`; durable long intervals are `(count=2, first=1/3/5/7)`. Run every interval, then merge before archiving. For example, the full matrix can be reproduced as:

```sh
build/s6_1-release/antworld_s6_1_experiment out/parts/matrix-1 4 matrix 1
build/s6_1-release/antworld_s6_1_experiment out/parts/matrix-5 4 matrix 5
build/s6_1-release/antworld_s6_1_experiment out/parts/matrix-9 4 matrix 9
build/s6_1-release/antworld_s6_1_experiment out/parts/matrix-13 4 matrix 13
python tools/merge_s6_1.py out/merged/matrix out/parts/matrix-1 out/parts/matrix-5 out/parts/matrix-9 out/parts/matrix-13
```

These independent commands may execute concurrently. The merger requires the complete frozen grid without gaps or overlap, checks configurations and row counts, preserves ordering and records interval provenance. Complete facts and databases remain in the original interval directories. It never picks between repeated outcomes. Earlier serial attempts were interrupted solely to use this execution partitioning; `execution_prefixes` retains every completed summary and canonical fact hash. Analysis requires exact reproduction of all 102 matrix cases, 64 observer cases and 69 durable mode rows in those prefixes. They are verification duplicates, not extra independent samples. Local incomplete in-progress outputs remain recorded as unfinished, not successful cases.

Raw archiving retains all rows in original order. Files larger than 40 MB are split into CSV parts with identical headers. The manifest hashes the original normalized-LF stream, including one header, so sharding can be checked independently. Full binary facts remain in the local output; their SHA-256 and fact counts are recorded. Do not delete old SQLite histories to recover space without an explicit evidence-preserving archival decision.

For a new archive root, retain the committed `execution_prefixes`, `verification.json`, `executed_tests.csv` and `interval_ci.json` there as historical reference evidence before invoking the full analyzer below. They describe the original executed checks and are not claims about tests on a new machine. Record new local test/CI executions separately. Use merged interval directories as archive sources when partitioning instead of the serial output paths below. The complete cross-run audit requires exact original Windows-host canonical traces; cross-platform fixtures can use the `--pilot` observer audit and the explicit S6 `--cross-platform` semantic reproduction mode, without claiming binary hash equality.

```sh
python tools/archive_s6_1.py out/s6_1-matrix NEW_ARCHIVE_ROOT/matrix
python tools/archive_s6_1.py out/s6_1-sensitivity NEW_ARCHIVE_ROOT/sensitivity
python tools/archive_s6_1.py out/s6_1-observer-integrated NEW_ARCHIVE_ROOT/observer_integrated
python tools/archive_s6_1.py out/s6_1-integrated NEW_ARCHIVE_ROOT/integrated
python tools/archive_s6_1.py out/s6_1-long NEW_ARCHIVE_ROOT/long
python tools/analyze_s6_1.py --root NEW_ARCHIVE_ROOT
python tools/analyze_s6_1.py --root NEW_ARCHIVE_ROOT --check
python tools/analyze_s6_1_scarcity.py --root NEW_ARCHIVE_ROOT
```

Copy the separate performance archives to that root before the performance analysis and plots. `python tools/analyze_s6_1.py --check` validates the committed archive. Statistics use 4,096 paired-seed resamples, seed 6106; mirrors are averaged within seed. An attempt-free gift rate is undefined; conditional rate intervals show defined seed counts, while all raw cases and attempt counts remain. Reachable demand/supply integrals measure coexistence, not an omniscient allocation or a guaranteed feasible flow.

`analyze_s6_1_scarcity.py` is explicitly post-hoc diagnosis of the negative 500 ug cases at 8/128 workers, using every declared seed in both legacy/combined arms. It exports physical brood inventories relative to the unchanged 100 ug fixture threshold. Its second table records all resolved gift failures in the default 32-worker/2,000 ug four-arm cell. This diagnostic does not change the model, select replacement cases, add a new acceptance threshold or estimate a biological parameter.

## Baseline diagnosis and performance

The full original seed-7 reconstruction is in `diagnosis`. Original S6 SQLite databases are required to re-extract the entire factual trace with `tools/trace_s6_1_baseline.py`. The pure trace observer (`antworld_s6_1_trace OUTPUT_DIR`) reproduces its history without changing authority. The source chronology is frozen protocol `03ae833`, profiling/diagnosis `f6a46b9`, disposable contact-link optimization `4591160`, behavioral flags/tests `d60c8ff`, full observer source `c8dd6d0`.

Build `ANTWORLD_PROFILE=ON` in a separate directory for instrumentation. It must never be used for acceptance latency. For the before profile use `f6a46b9`, after profile `4591160`; both use identical legacy biology. Acceptance uses normal Release and the exact fixed ten-repetition benchmark. Run timing suites separately from builds and ecological workloads. Save all samples, even when the growth target fails.

```sh
build/s6_1-release/antworld_s6_contact_benchmark out/s6_1-contact-final 10
build/PROFILE_BUILD/antworld_s6_contact_benchmark out/s6_1-contact-profile 3
python tools/analyze_s6_1_performance.py --root NEW_ARCHIVE_ROOT
python tools/analyze_s6_1_performance.py --check
python -m pip install -r tools/s2_1_plot_requirements.txt
python tools/plot_s6_1.py
```

The timing archive reports p50/p95/p99/max for setup, advance, encode and restore; current/peak RSS; checkpoints; event/queue counts; candidate/bucket/tree work. Profile categories distinguish index maintenance, candidate sampling, spatial validation, scheduler, transaction/journal, history, physiology, policy and root residual. Nine exclusive categories sum exactly to each root inclusive advancement time. No fabricated performance improvement is inferred from instrumentation or host variation.

## Earlier semantic reproduction

```sh
build/s6_1-release/antworld_s3_experiment out/s6_1-s3-regression 64
build/s6_1-release/antworld_s4_experiment out/s6_1-s4-regression 32
build/s6_1-release/antworld_s5_experiment out/s6_1-s5-regression 32
python tools/verify_s4_reproduction.py out/s6_1-s4-regression --source-commit MEASURED_COMMIT --checkpoint-byte-delta 9 --physics-version 9 --s3-regression out/s6_1-s3-regression --report out/s6_1-s4-reproduction.json
python tools/verify_s5_reproduction.py out/s6_1-s5-regression --source-commit MEASURED_COMMIT --checkpoint-byte-delta 1 --report out/s6_1-s5-reproduction.json
python tools/ci_verify.py
```

Cross-platform S6 reproduction uses the existing document-18 tolerance and excludes binary hashes only when explicitly requested with `--cross-platform`. Same-host reproduction requires exact trace equality and only declared checkpoint version/flag differences. All old raw results remain unchanged.
