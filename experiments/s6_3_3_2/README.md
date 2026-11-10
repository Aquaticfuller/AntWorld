# S6.3.3.2 experiment archive and reproduction

[Protocol 58](../../docs/58_S6_3_3_2_Frozen_Baseline_and_Protocol.md) and [design audit 59](../../docs/59_S6_3_3_2_Care_Design_Audit.md) were committed as `de9107b` before the behavior changes. The reference scope, study inputs and negative runs remain available on the review branch.

| Directory or record | Contents |
| --- | --- |
| [raw](raw) | All 484 runs with profiles, initial identities and positions, scan windows and committed fact exports. Event CSVs are lossless gzip. The manifest includes packed and original hashes. Blank tables belong to modes without those endpoints. |
| [analysis](analysis) | Derived trajectories, per-caregiver censoring, pickup/load/release episodes, post-placement search, paired source data, errors, sensitivity, and integration diagnostics. |
| [literature](literature) | Factual source table transcriptions and independent external context. B01 and B02 use the previous [source data](../s6_3_3/literature). |
| [figures](figures) | Scientific comparisons derived from the tracked data. |
| [historical replay](historical_replay.json) | Rebuilt comparisons for the 416 previous runs. |
| [td11](td11) | Same-colony indexed/reference sample and profiler files with exact trace identity checks. |
| [performance](performance) | Formal protected Release batch. Native rows, phase/cycle data, English sensor exports, checks, manifest and bootstrap analysis. The original localized HWiNFO source remains local. |
| [local verification](verification) | Per-test local CTest outcomes and build configurations. |

Use Python 3.11+ and a C++20 CMake build. The commands below show a Windows shell and the single-configuration CMake layout. On Linux, omit the `.exe` suffix. The build pins SQLite 3.54.1 and verifies its archive. These commands use unused scratch directories for new runs.

```powershell
cmake -S cpp -B build/fidelity-release -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build/fidelity-release --parallel 4
ctest --test-dir build/fidelity-release --output-on-failure
cmake -S cpp -B build/fidelity-debug -G Ninja -DCMAKE_BUILD_TYPE=Debug
cmake --build build/fidelity-debug --parallel 4
ctest --test-dir build/fidelity-debug --output-on-failure
cmake -S cpp -B build/fidelity-san -G Ninja -DCMAKE_BUILD_TYPE=Debug -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ -DANTWORLD_SANITIZERS=ON
cmake --build build/fidelity-san --parallel 4
ctest --test-dir build/fidelity-san --output-on-failure
python tools/run_s6_3_3_2_assays.py build/fidelity-release/antworld_s6_3_3_experiment.exe out/fidelity-raw
python tools/analyze_s6_3_3_2.py --raw out/fidelity-raw --out out/fidelity-analysis --deep
python tools/run_s6_3_3_2_assays.py build/fidelity-release/antworld_s6_3_3_experiment.exe out/fidelity-old --replay-report out/fidelity-old-receipt.json
python tools/analyze_s6_3_3_2.py --verify-only --deep
python tools/ci_verify.py
```

`tools/plot_s6_3_3_2.py` uses Matplotlib and the tracked analysis and TD-11 tables to regenerate the figures. Run from the repository with the same dependency family as the previous stage figures. Figure labels and error intervals describe independent measured units and paired simulator seeds. Physical facts and endpoint calculations remain independently inspectable in the CSVs.

## TD-11 isolated profiling

The reference is the profiling-only commit `aede85e`. Build the same target at that revision and the indexed commit `5a357d0`. Both must use `-DANTWORLD_PROFILE=ON` and the same compiler and Release options. The density fixture needs no source papers or machine sensor permissions.

```powershell
git worktree add --detach ../antworld-td11-reference aede85e
git worktree add --detach ../antworld-td11-indexed 5a357d0
cmake -S ../antworld-td11-reference/cpp -B build/td11-reference -G Ninja -DCMAKE_BUILD_TYPE=Release -DANTWORLD_PROFILE=ON
cmake -S ../antworld-td11-indexed/cpp -B build/td11-indexed -G Ninja -DCMAKE_BUILD_TYPE=Release -DANTWORLD_PROFILE=ON
cmake --build build/td11-reference --target antworld_s6_3_3_2_density
cmake --build build/td11-indexed --target antworld_s6_3_3_2_density
python tools/analyze_s6_3_3_2_density.py --root out/td11-replay --collect build/td11-reference/antworld_s6_3_3_2_density.exe build/td11-indexed/antworld_s6_3_3_2_density.exe
python tools/analyze_s6_3_3_2_density.py --check
```

## Protected performance

Replay the archived measurements with the first command below. To collect a new batch, use the host and instrument requirements in [protocol 55](../../docs/55_S6_3_3_1_Performance_Instrument_Protocol.md) and the reserve identity correction in [protocol 57](../../docs/57_S6_3_3_1_Reserve_Birth_Benchmark_Correction.md). `$Compiler` is the C++ compiler used for the frozen Release build. `$SensorLog` is the live HWiNFO sensor CSV. The version-2 confirmation receipt is tied to the measured processor topology. Use a newly confirmed receipt for a different host. The executable name and reserve fixture must match. Keep the protected collection separate from builds, analysis and density profiling.

```powershell
python tools/analyze_s6_3_3_1_performance.py --raw experiments/s6_3_3_2/performance --out experiments/s6_3_3_2/performance/analysis --check
cmake --build build/fidelity-release --target antworld_s6_2_benchmark antworld_s6_3_1_birth_benchmark
python tools/run_s6_3_3_1_performance.py --prepare --build build/fidelity-release --out out/fidelity-perf --compiler $Compiler --confirmation experiments/s6_3_3_1/performance/instrument_v2_confirmation/receipt.json
python tools/verify_s6_3_3_1_reserve_workload.py --binary build/fidelity-release/antworld_s6_3_1_birth_benchmark.exe --scratch out/fidelity-reserve --receipt out/fidelity-perf/reserve_identity_receipt.json
python tools/run_s6_3_3_1_performance.py --build build/fidelity-release --out out/fidelity-perf --archive out/fidelity-sensors --hwinfo-csv $SensorLog
python tools/analyze_s6_3_3_1_performance.py --raw out/fidelity-perf --out out/fidelity-perf/analysis
```
