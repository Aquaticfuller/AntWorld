# S6.3.4 raw evidence and reproduction

| Path | Contents |
|---|---|
| `portable/primary/` | Final host and schedule, 42 raw sample folders, each publication, per-process CPU counters and independent archive checks |
| `portable/ecology/` | Eight R1 21-day runs, three primary 180-day runs and three supplemental mortality controls |
| `*/[run]/attempt.json`, `integrity.json` | Original raw file hashes, exit status and independently decoded canonical and frame checksums |
| `portable/summary/` | Final phase quantiles, ecology identities, frozen acceptance and archive parity against the first build |
| `portable/migration/`, `portable/verification/` | Final dense shadow migration, three local test suites, fault injection and the test-name manifest |
| `primary/`, `ecology/`, `summary/`, `migration/` | The complete first-build measurements, all early migration receipts and derived outputs |
| `verification/` | First-build verification and CI failure, plus exact identities for the protected contact and birth workloads |
| `pilot/` | Prequalification single dense legacy case, excluded from the frozen sample set |

This directory contains CSVs, JSON and logs. Recreate the SQLite files using the recorded fixture commands. Results use fixed inputs and bytewise history comparisons. Wall-clock and memory measurements are machine-dependent. The verification tools require Python 3.11 or later.

## Build and correctness

```sh
cmake -S cpp -B build/s634-release -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build/s634-release --parallel 5
ctest --test-dir build/s634-release --output-on-failure -j 5
ctest --test-dir build/s634-release -V -L '^S6[.]3[.]4$'
cmake -S cpp -B build/s634-debug -G Ninja -DCMAKE_BUILD_TYPE=Debug
cmake --build build/s634-debug --parallel 5
ctest --test-dir build/s634-debug --output-on-failure -j 5
cmake -S cpp -B build/s634-sanitizer -G Ninja -DCMAKE_BUILD_TYPE=Debug -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ -DANTWORLD_SANITIZERS=ON
cmake --build build/s634-sanitizer --parallel 5
ctest --test-dir build/s634-sanitizer --output-on-failure -j 5
```

The recorded Windows builds used LLVM-MinGW Clang 23.1.5, CMake 3.31.10 and Ninja. Local sanitizer execution used `ASAN_OPTIONS=detect_leaks=0:halt_on_error=1` and `UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1`. The Linux GitHub sanitizer job also runs leak detection. CMake pins the SQLite and zlib sources and accepts verified local source archives for offline builds. See [CMake dependency files](../../cpp/cmake).

## Exact work and performance evidence

Use new scratch and evidence paths. The performance admission is implemented for Windows and requires two five-second load windows. Run alone on the host. After the two batches, run the independent Python verifier through the analyzer.

```powershell
python tools/run_s6_3_4.py build/s634-release/antworld_s6_3_4_experiment.exe out/s634/performance out/s634/evidence/primary --mode performance --compiler (Get-Command clang++.exe).Source
python tools/run_s6_3_4.py build/s634-release/antworld_s6_3_4_experiment.exe out/s634/ecology out/s634/evidence/ecology --mode science --compiler (Get-Command clang++.exe).Source
python tools/analyze_s6_3_4.py out/s634/evidence out/s634/summary --performance-scratch out/s634/performance --ecology-scratch out/s634/ecology
python tools/analyze_s6_3_4.py experiments/s6_3_4/portable experiments/s6_3_4/portable/summary --compare-baseline experiments/s6_3_4 --check
python tools/verify_s6_3_3_3_contact_workload.py --binary build/s634-release/antworld_s6_2_benchmark.exe --scratch out/s634/contact --receipt out/s634/contact.json
python tools/verify_s6_3_1_reserve_workload.py --binary build/s634-release/antworld_s6_3_1_birth_benchmark.exe --scratch out/s634/births --receipt out/s634/births.json
```

On Linux the executable names omit `.exe`. The science runner and offline analyzer can also run there. A single trace is independently checkable with the following commands.

```sh
build/s634-release/antworld_s6_3_4_experiment out/s634/million facts-1000000 7
python tools/verify_s6_3_4_archive.py out/s634/million/world.sqlite out/s634/million-integrity.json
```

## Legacy pressure migration

Use the retained `timed_dense_128.sqlite` from the S6.3.3 unprofiled dense persistence workload. It can be recreated from reviewed source by following the [S6.3.3 reproduction commands](../s6_3_3_3/README.md). The archived comparison includes the database and sidecars. Allow temporary disk space for the legacy-size shadow and its transaction before compaction. The source archive must remain available under its original name.

```powershell
python tools/run_s6_3_4_migration.py build/s634-release/antworld_archive.exe out/s6_3_3_3/density-persistence/timed_dense_128.sqlite out/s634/shadow.sqlite out/s634/migration-evidence
```

[Main results](../../S6_3_4_RESULTS.md) · [Frozen protocol](../../docs/64_S6_3_4_Frozen_Durable_History_Protocol.md)
