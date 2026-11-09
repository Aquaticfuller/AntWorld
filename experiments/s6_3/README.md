# S6.3 retained evidence and reproduction

All biological values/rules are ENGINEERING_FIXTURE. Protocol 41 (`5607139`) precedes initial implementation; correction protocol 42 (`0c26f42`) precedes the two behavioral fixes. See S6_3_RESULTS.md and document 43 for interpretation. Never replace an unfavorable seed or overwrite an old output directory.

## Files

- `ecology/primary-v1`: all 48 initial prototype worlds, including 18 capacity-censored negatives. Source `f04ef77`, schema 9 / physics 10. The archived local executable SHA-256 is `50b955973fd5c4554f10b8b672350eaef556e8a4213acf4ad2c0205f7565d030`; additional restore assertions were committed after that binary, without changing the experiment behavior. Rebuild the original revision to reproduce this unreleased format.
- `ecology/*-v2`: 102 corrected worlds: 48 primary, 18 controls, six timing sensitivity, 24 single-correction factorial and six compact-space cases. Behavior source `fa73289`, schema 9 / physics 11. Subsequent derived index/validation/source-name/format changes are verified by reproducing every corrected case from the final source.
- Each matrix's `archive.json` maps **every** original CSV/binary to byte length and SHA-256. Small CSVs are copied byte-for-byte; large CSVs and complete `events.bin` streams are gzip-compressed with an empty header filename and zero timestamp. No rows/events are sampled or discarded. Each fact is exactly 159 little-endian bytes using `encode_event`/`decode_event`. `tools/analyze_s6_3.py --deep` independently projects those bytes and reconciles IDs/stages/transfers with readable events and summary counts.
- `final.aw` and `world.sqlite` are duplicate materialized state/history views; their hashes remain in the manifest, while the complete canonical facts and all CSV observations are committed. Original duplicate files remain in local `out/s6_3`; reproduce the same source/configuration to regenerate them. No secret or localized sensor header is required to reproduce the simulator.
- `analysis/runs.csv`, `estimates.csv`, `paired.csv`, `diagnosis.csv`, `audit.json`: deterministic derivations, with sampled unmet-demand exposure, program residence, queen energy accounting, all seeds and censoring. Censored endpoints mean last successfully committed day, not 90-day population estimates.
- `performance`: complete ABBA/BAAB raw samples, schedules, phase clocks, work counts, receipts, Windows telemetry and English HWiNFO CPU columns. `registration-baseline-controlled` is the earlier exploratory batch; late session 3 overlapped build preparation, so it is retained separately and excluded from final ratios. `contacts-baseline-final` is a fresh isolated original-binary run including 128 workers. All four final comparison batches are unfiltered.
- `performance_analysis`: pooled/session p50/p95/p99, paired raw ratios, session/block bootstrap intervals, memory/events, phase CPU/cycles and sensor summaries. Instrumented attribution is separate from acceptance timing.
- `figures`: standalone PNG/SVG plots; `verification.json` and `verification/` retain executed checks and reproduction receipts.

## Build and ecological runs

Portable CMake commands (SQLite's pinned download is the default; provide the pinned local archive when offline):

```sh
cmake -S cpp -B build/s6_3-review -DCMAKE_BUILD_TYPE=Release
cmake --build build/s6_3-review --parallel 4
ctest --test-dir build/s6_3-review --output-on-failure
./build/s6_3-review/antworld_s6_3_experiment out/review-primary primary
./build/s6_3-review/antworld_s6_3_experiment out/review-controls controls
./build/s6_3-review/antworld_s6_3_experiment out/review-sensitivity sensitivity
./build/s6_3-review/antworld_s6_3_experiment out/review-factorial factorial
./build/s6_3-review/antworld_s6_3_experiment out/review-spatial spatial
python tools/verify_s6_3_reproduction.py out/review-primary --group primary-v2 --report out/review-primary.json
```

Use the corresponding `*-v2` group for the other four matrices. Across platforms add `--cross-platform`: this compares every integer/exported fact field, with absolute coordinate tolerance 1e-12 m, and explicitly excludes binary hashes under document 18. Same-platform reproduction also requires exact full fact-stream and checkpoint SHA-256. Mode `review` runs two already-frozen 90-day cases (seed 1 / 8 workers ample and seed 1 / 32 workers compact) for CI, not a replacement primary matrix.

Debug uses `-DCMAKE_BUILD_TYPE=Debug`. ASan+UBSan uses Clang and `-DANTWORLD_SANITIZERS=ON`; set `ASAN_OPTIONS=detect_leaks=1:halt_on_error=1` on Linux and `UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1`. Windows LLVM ASan lacks the Linux leak check; use `detect_leaks=0` and put the pinned compiler's `bin` directory on PATH. The independent core build uses `-DANTWORLD_STORAGE=OFF`.

The measured Windows builds use `.tools/cmake-3.31.10-windows-x86_64/bin/cmake.exe`, `.tools/ninja.exe`, Clang 23.1.5 from `.tools/llvm-mingw-20261104-ucrt-x86_64/bin`, and `.tools/sqlite/sqlite-amalgamation-3540100.zip`. Resolve these relative workspace paths when passing `CMAKE_C_COMPILER`, `CMAKE_CXX_COMPILER`, `CMAKE_MAKE_PROGRAM` and `ANTWORLD_SQLITE_ARCHIVE`; no repository-specific drive letter is required.

## Controlled performance and attribution

On the same Windows host with read-only HWiNFO logging enabled:

```sh
python tools/run_s6_3_performance.py --binary build/s6_3-review/antworld_s6_2_benchmark.exe --out out/contacts-review --kind contacts --hwinfo-csv PATH_TO_USER_LOG
python tools/run_s6_3_performance.py --binary build/s6_3-review/antworld_s6_3_birth_benchmark.exe --out out/births-review --kind births --hwinfo-csv PATH_TO_USER_LOG
python tools/extract_s6_2_hwinfo.py out/contacts-review experiments/s6_2/hwinfo_columns_v2.json
```

The extractor verifies the original header hash/column count before interpreting sensors. A different HWiNFO installation requires independently reviewed sensor mapping, not guessed columns. Original localized prefixes remain local/untracked; every CPU sample in the run interval plus three-second brackets is retained, including power limits and gaps. Native observations pin the benchmark to logical processor 0 and keep the observer off that physical core; the runner records topology and selected masks. No system power plan, governor, priority or thermal setting is changed.

The original stationary binary SHA-256 matches the S6.2 archived `cc9004e` binary (`e411faa88108643a90611c105e6e6356da391fe785bbda04fceef01d3d5efe6a`). The runner's `source_commit` records the working checkout used to drive measurement; it is not necessarily the separately selected binary's source. `provenance.json` distinguishes driver and binary revisions. The final acceptance binaries were built from `989c1a8`; later commits fix a GCC layout warning and legacy experiment CSV exports, without changing their core decisions. The before-index birth binary is `fa73289`. Every receipt pins the actual binary SHA-256.

For host-only cost attribution, build the selected revision with `-DANTWORLD_PROFILE=ON -DANTWORLD_STORAGE=OFF` and run:

```sh
python tools/profile_s6_3.py --binary build/profile/antworld_s6_3_birth_benchmark.exe --out out/profile-review --kind births --source REVIEWED_COMMIT
```

Profile calls/exclusive/inclusive nanoseconds cover indexing, candidate sampling, spatial validation, scheduler, transaction journal, history, physiology and policy; remaining advance time is explicitly unscoped work. Profiled timings are never merged into acceptance distributions. Both before/after birth builds scope `change_autonomy` as policy, so its pending-queue scan can be compared directly. Run `python tools/analyze_s6_3_profile.py` to reproduce the separate cost table.

## Audit, archive and plots

```sh
python tools/archive_s6_3.py out/review-primary out/archived-review-primary
python tools/analyze_s6_3.py --check --deep
python tools/analyze_s6_3_performance.py --check
python tools/diagnose_s6_3.py
python tools/plot_s6_3.py
```

The analysis uses the standard library. Plotting uses the repository's existing pinned NumPy/Matplotlib environment (`.tools/s2_1-python` locally); add it to PYTHONPATH where needed. The gzip evidence is substantial because complete negative high-event histories are retained. Do not replace it with selected positive summaries to reduce repository size. No runtime event pruning or geometric history compression was introduced in this stage.
