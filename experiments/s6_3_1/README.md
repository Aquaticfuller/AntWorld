# S6.3.1 evidence and reproduction

All biological rates and numeric mechanism defaults are ENGINEERING_FIXTURE. This archive covers queen allocation/provisioning validation only. It does not authorize S6.4, Unity or a calibrated ecological claim.

## Frozen lineage

- Reviewed S6.3 baseline: `1865a5df2351f482f4f34ae74e3ada7a27be1619`.
- Protocol 44 frozen in `f0d38b7`; pre-execution observer/inheritance clarification 45 and passive harness in `bf61ebf`.
- All 192 baseline runs (48 historical + 144 causal/positive/sensitivity controls) used the unchanged rules at `bf61ebf`.
- Evidence-led correction freeze 46: `3c5d1d1`. Optional local maintenance gate and its tests: `1add467`. Verification/performance contract 47: `5b0848b`.
- The 240 corrected runs comprise the same 192 conditions plus 48 horizon controls. No run was dropped or capacity-censored. Historical conditions duplicate 36 causal conditions within each model; do not pool those repeats as independent evidence.
- The original baseline executable was subsequently rebuilt in place, so its binary SHA-256 was not captured. Its source revision and all output hashes remain. Final-source legacy-mode reproduction independently matches all 192 baseline native journals/checkpoints and raw observations. The reviewed 48 S6.3 worlds also match their original archives.

`S6_3_1_EXPERIMENTS.csv` at repository root contains one joined row for every execution. `ecology/{baseline,corrected}/MATRIX` retains every generated CSV row, configurations, daily population/resources, individual states, actual selected lifetime events, actual perception observations, queen event accounts and descriptive timing. Large CSVs are losslessly gzip-compressed with deterministic headers. `analysis` contains condition means, 95% intervals, all paired changes and survival curves; `figures` contains standalone PNG/SVG exports.

Each matrix `archive.json` records original byte size and SHA-256 plus the archived file/hash. Full native `events.bin`, `final.aw` and SQLite duplicates remain in the local output directory with immutable hashes in the archive. The CSV is selected evidence, not the entire journal. No history is deleted from Core to obtain speed or smaller authoritative saves. Reproduction regenerates the complete native evidence and compares these hashes. No sensor-source localized text is tracked; English CPU columns and provenance retain the required measured data.

Plain archived text uses UTF-8/LF for Git portability; original source byte hashes remain separate from archived hashes. This newline normalization changes no row, numeric observation or fact. Canonical native streams are hashed in their original binary form.

The observer's `context` is 0 nutrition choice, 1 autonomy choice or 2 actual withdrawal perception. Physical reachability is host-only diagnostic evidence; worker decisions only see their original bounded local samples. Decision rows are emitted only after the AdvanceTo call commits. `queen_events.csv` is independently reconstructed from actual event records, with pre/post stores and elapsed maintenance. See document 47 for units and boundary semantics. The initial analysis exporter reused `final_alive` for both population and queen status; this derived-column collision was corrected before publication by joining the unchanged raw summary as `final_population`. The queen's `final_alive` and `queen_alive` remain distinct from colony population, and CI checks that relation. No simulated outcome or frozen hypothesis changed.

## Build and tests

The existing bootstrap pins CMake 3.31.10, LLVM-MinGW 20261104 (Clang 23.1.5), Ninja 1.13.2 and SQLite 3.54.1. Local Debug, Release and ASan/UBSan receipts use those versions. Portable review commands:

```sh
cmake -S cpp -B build/review -DCMAKE_BUILD_TYPE=Release
cmake --build build/review --parallel 4
ctest --test-dir build/review --output-on-failure
cmake -S cpp -B build/review-debug -DCMAKE_BUILD_TYPE=Debug
cmake --build build/review-debug --parallel 4
ctest --test-dir build/review-debug --output-on-failure
cmake -S cpp -B build/review-sanitized -DCMAKE_BUILD_TYPE=Debug -DANTWORLD_SANITIZERS=ON -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++
cmake --build build/review-sanitized --parallel 4
ctest --test-dir build/review-sanitized --output-on-failure
```

For an offline configure add `-DANTWORLD_SQLITE_ARCHIVE=/path/to/sqlite-amalgamation-3540100.zip`. Windows uses `.exe`; the repository bootstrap/build script supplies the pinned local compiler. Windows sanitizer execution needs the compiler `bin` on the process PATH, `ASAN_OPTIONS=detect_leaks=0:halt_on_error=1`, and `UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1`. Linux CI enables leak detection. No persistent system environment changes are required.

## Reproduce every ecological control

Use fresh directories; the runner refuses to overwrite prior worlds. MATRIX is `historical`, `causal`, `restricted`, `sensitivity` or `positive`:

```sh
./build/review/antworld_s6_3_1_experiment out/review-baseline-causal causal legacy
python tools/diagnose_s6_3_1.py out/review-baseline-causal
python tools/verify_s6_3_1_reproduction.py out/review-baseline-causal --model baseline --matrix causal --report out/baseline-causal-check.json

./build/review/antworld_s6_3_1_experiment out/review-corrected-causal causal reserve
python tools/diagnose_s6_3_1.py out/review-corrected-causal
python tools/verify_s6_3_1_reproduction.py out/review-corrected-causal --matrix causal --report out/corrected-causal-check.json

./build/review/antworld_s6_3_1_experiment out/review-horizons horizons reserve
python tools/diagnose_s6_3_1.py out/review-horizons
python tools/verify_s6_3_1_reproduction.py out/review-horizons --matrix horizons --report out/horizons-check.json

./build/review/antworld_s6_3_1_experiment out/review-positive review reserve
python tools/diagnose_s6_3_1.py out/review-positive
python tools/verify_s6_3_1_reproduction.py out/review-positive --report out/positive-check.json
python tools/analyze_s6_3_1.py --check
python tools/plot_s6_3_1.py
```

Repeat the first two command groups for every MATRIX. `review` is the frozen seed-1 positive control at 8 and 32 workers, both 180 days; it includes a negative queen outcome. `horizons` always runs both shorter and longer predeclared windows. The final optional `legacy|reserve` argument defaults to legacy. Reproduction verification on another compiler/platform uses `--cross-platform`: integer observations remain exact; coordinates use document-18 absolute tolerance 1e-12 m, while native binary hashes are explicitly excluded. Same-platform verification requires exact native bytes.

`diagnose_s6_3_1.py` requires the regenerated native `events.bin` and original CSVs, reconstructs every queen budget and compares every actual decision-time and daily queen query. It also reconstructs death-time stranded stocks from facts. Analysis/verification use only Python's standard library. Plotting additionally uses Matplotlib (the existing local plotting environment); figures do not enter Core or tests.

## Performance and limitations

Document 47 freezes the existing three-session ABBA/BAAB protocol. Use Windows read-only telemetry and the user-provided HWiNFO CSV path:

```sh
python tools/run_s6_3_performance.py --binary build/review/antworld_s6_2_benchmark.exe --out out/review-contacts --kind contacts --hwinfo-csv PATH_TO_HWINFO_CSV
python tools/run_s6_3_performance.py --binary build/review/antworld_s6_3_1_birth_benchmark.exe --out out/review-births --kind births --hwinfo-csv PATH_TO_HWINFO_CSV
python tools/extract_s6_2_hwinfo.py out/review-contacts experiments/s6_2/hwinfo_columns_v2.json
python tools/extract_s6_2_hwinfo.py out/review-births experiments/s6_2/hwinfo_columns_v2.json
python tools/analyze_s6_3_1_performance.py --check
```

The inherited runner records its original schedule protocol IDs; the new binary/source hashes and document 47 identify this regression. No builds, ecology runs or data analysis overlap acceptance timing. A first sandboxed host-metadata query failed before measurement; its English failure receipt is retained separately. Numerical output rows and their order are never filtered. Native timings separate setup, advance, checkpoint and restore; ecological-run timing includes optional observation overhead and its setup column includes observer-file initialization, so it is descriptive rather than an isolated performance gate.

This batch does **not** pass the unchanged pooled wall-time gate: dense contact growth is 6.315x and birth growth is 8.154x. Paired medians (5.375x / 4.422x) and cycle ratios cannot replace that criterion. The inherited paired bootstrap uses seed 6303 and session/block resampling. Additional pooled-p50 and cycle diagnostics were computed after the wall/paired disagreement appeared; pooled intervals resample whole sessions and matched blocks 4096 times with seed 63101. They quantify uncertainty rather than redefine acceptance. Every original per-session sample, telemetry row and phase counter remains available. A quiet-host qualification/repeat is proposed for review and was not run in this stage.

The reserve-birth stress target has N queens and N unrelated workers, then N actual births; its zero basal/water loss preserves the complete original workload. It is not a multi-queen Lasius niger claim. S6.1's 24.229x anomaly remains unknown and retained. TD-08's broader dynamic-population scaling, TD-03/06 full-history storage, SD-04/06/07, SD-01/02 and SD-08 remain open at their stated scope.
