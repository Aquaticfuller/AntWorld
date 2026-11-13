# Reproduce and audit S6.4 final qualification

Use the checked-in CMake project and the same single-configuration Release and Debug commands used in Core CI. The experiment receipts identify the exact source commit, C++ tree, compiler, executable SHA-256, protocol SHA-256, command arguments and cases. The authoritative `cpp/src`, `cpp/include` and `cpp/storage` are identical to the reviewed closure reference. Local experiments used Windows 11 build 26200, Clang 23.1.5 from llvm-mingw, CMake 3.31.10 and Python 3.12.14. No extra library is required to read the archives and reconstruct gates. The offline Monte Carlo uses NumPy 2.3.5. Use a fresh output path for each command.

## Capture, replay and original authorities

```powershell
cmake -S cpp -B build/final-release -DCMAKE_BUILD_TYPE=Release
cmake --build build/final-release --parallel 4
ctest --test-dir build/final-release -C Release --output-on-failure
$exe = 'build/final-release/antworld_s6_4_wp6b.exe'
$compiler = (Get-Command clang++).Source
$data = 'experiments/s6_4_final_core_readiness'
python tools/final_core_integration.py --binary $exe --compiler $compiler out/final-matrix
python tools/final_core_integration.py --shaft --binary $exe --compiler $compiler out/final-shaft
python tools/final_core_integration.py --clock --binary $exe --compiler $compiler out/final-clock
python tools/verify_final_core_integration.py out/final-matrix out/final-matrix-audit
python tools/verify_final_core_integration.py --shaft out/final-shaft out/final-shaft-audit
python tools/verify_final_core_integration.py --clock out/final-clock out/final-clock-audit --replay $exe
python tools/summarize_final_core_integration.py out/final-matrix-audit out/final-shaft-audit out/final-clock-audit out/final-comparison
python tools/verify_final_core_integration.py "$data/matrix" out/public-matrix --witness-only
python tools/verify_final_core_integration.py --shaft "$data/shaft" out/public-shaft --witness-only
python tools/verify_final_core_integration.py --clock "$data/clock" out/public-clock --witness-only --replay $exe
python tools/verify_final_core_evidence.py out/final-evidence
```

Use the extensionless executable on a single-configuration Linux build. For exact collector source provenance the original panel used `08557a5`, the shaft diagnostic used `50794b3`, and the connector-clock test used `77cc30f`. The final runner can reproduce all the scenarios with the same bytes on compatible builds. Time and RSS receipts can differ by host. The verification commands compare content authority, event identities and reported endpoints separately from host measurements.

The complete original new archive is `out/s6_4_final_core_readiness/{matrix,shaft,clock}` on the experiment host. It contains 156 complete ZIP files totaling 802,730,679 bytes. Existing full historical archives remain at their original locations. The new public manifests carry SHA-256 for every local ZIP and every original member. The fixed public witnesses cover marked compact and shaft colonies, a fast-shaft successful colony with its durable publication, blocked paths, absent supply and a protein-free ration. They include original bytes and readable derived life-stage, worker, trip and nutrition summaries. The full-matrix verifier uses all raw ZIP files and independently recomputes budgets, milestone outcomes and equalities. The public mode checks all manifest identities and rebuilds the fixed published witnesses from their raw facts. Full bytes for the other cases are accessible on the experiment host.

Each original case includes `parameters.txt`, `case.json`, `initial.chk`, `final.frame`, `facts.bin`, and its run receipt. Observed worlds include daily `cuts.csv`, `individuals.csv`, `space_cuts.csv` and ordered `geometry_edits.csv`. Saved worlds additionally include `midpoint.sqlite`. `facts.bin` is the Core length-prefixed canonical event stream. `FactKind` and payload layouts are in `cpp/include/antworld/core/event.hpp` and `cpp/src/checkpoint.cpp`. Derived counters never replace the original facts. The ledger checks reconcile both actual source and on-actor inventories. Soil facts have the edit/parcel link in their payload. A separate integer geometry reader replays every edit against its starting material and checks loaded clearance of the existing shaft. The read-only SQLite audit validates `AWFACT08` block digests and the frame anchor, then compares the whole published canonical prefix byte-for-byte with the uninterrupted authority. Geometry and surface observation use read-only probes at the declared cuts. Program residence is reconstructed from actual change/death facts. Work without a known interval has an unobserved duration.

```powershell
python tools/founding_qualification_witnesses.py experiments/s6_4_founding_qualification/witnesses --binary $exe --scratch out/final-crash
python tools/replay_founding_qualification_legacy.py $exe out/final-legacy out/final-legacy-scratch
python tools/check_s6_4_wp6b_r2_recovery.py --archive experiments/s6_4_wp6b_r2 --binary $exe --scratch out/final-r2 --out out/final-r2.json
```

The interrupted witness performs a real process exit during SQLite publication, restores the previous generation and compares the full continued authority. The exact legacy audit checks all 1,092 original worlds per v1 and R1, plus sixteen R2 midpoint/observation-disabled replays in the R2 test. Original regression tests remain in `cpp/tests` and in the Core CI Windows/Linux build matrix.

## Timing and biology

```powershell
python tools/verify_founding_qualification.py experiments/s6_4_founding_qualification --native
python tools/verify_integrated_founding_application.py experiments/s6_4_founding_qualification/performance
python tools/final_core_performance_study.py --historical-only out/final-performance-recompute
python tools/final_core_performance_study.py out/final-timing-study
python tools/final_core_performance_study.py --falsifiers out/final-timing-falsifiers
python tools/final_core_b06_cohorts.py out/final-b06
```

Native, protected observer and application analyzers recompute the archived telemetry, admission and original final classifications. The synthetic study never issues real qualification samples. The first B06 cohort reader uses the published original stage-event tables and custody/nutrition evidence, reproduces both daily count algorithms and joins each first-census larva to its terminal observation. [Original raw B06 reproduction](../s6_4_founding_qualification/REPRODUCE_QUALIFICATION.md#source-exhaustion-and-b06) provides the full independent daily-state check against the local original v7 archive. The primary article is cited in the scientific report and remains outside Git.

## Build and fault receipts

```powershell
cmake -S cpp -B build/final-debug -DCMAKE_BUILD_TYPE=Debug
cmake --build build/final-debug --parallel 4
ctest --test-dir build/final-debug -C Debug --output-on-failure
cmake -S cpp -B build/final-sanitized -DCMAKE_BUILD_TYPE=Debug -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ -DANTWORLD_SANITIZERS=ON
cmake --build build/final-sanitized --parallel 4
ctest --test-dir build/final-sanitized -C Debug --output-on-failure
```

On the Windows LLVM build, put the pinned toolchain `bin` directory on `PATH` so the instrumented executables can load the ASan DLL. Windows uses `ASAN_OPTIONS=detect_leaks=0:halt_on_error=1` and `UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1`. The existing Linux sanitizer workflow enables leak detection. Initial Windows sanitizer setup and host timeout results are documented in the run receipts. None serves as an alternative acceptance threshold. The qualified native workloads retain their ≤6× performance gates and earlier hardware receipts.
