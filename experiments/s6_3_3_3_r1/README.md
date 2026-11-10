# S6.3.3.3-R1 evidence and reproduction

The [frozen protocol](../../docs/62_S6_3_3_3_R1_Frozen_Protocol.md) starts at `9f85714`. Commit `f2c59a8` freezes the engineering and ecology cases. Commit `2b58aa3` freezes the empty-return control and isolation rules. The complete reviewed [72-world baseline and behavioral evidence](../s6_3_3_3) remain in place.

| Path | Data |
|---|---|
| `baseline/` | Fresh copies of the reviewed native coarse/fine probes and the original chamber control |
| `probes/` | Physical stride, custody and surface/3D controls. Each case lists its endpoint and trace. The event files give actual position, time, actor and amount |
| `diagnostic/` | Intermediate offset-route and pre-empty-return observations, including the host limit aborts. The full intermediate experiment can be rerun at source commit `57a82a0` |
| `ecology/<run>/` | Original native runs, days, individuals, timing, CSV event export, canonical event archive and per-attempt receipt. An abort row and its committed prefix remain distinct from a complete 21-day case |
| `ecology_*.csv` and `reviewed_endpoints.csv` | Reconciled complete runs, attempts, exact seed pairing and descriptive intervals derived from the archived events |
| `underground_witnesses.csv` | Actual first and post-return events keyed by run, actor and EventId |
| `density/` and `density_summary.csv` | 96 unfiltered host samples across both motors and their phase quantiles. The memory-only mode uses -1 for unmeasured SQLite time |
| `verification/` | Exact legacy replay, protected workload, CTest and CI receipts |

The canonical archive stores a four-byte little-endian length followed by the untouched Core `encode_event` bytes for each EventId in ascending order. The receipts record both compressed and raw hashes. The CSV provides the named evidence fields used by the analysis. Each completed world was also checked against the full SQLite fact bytes and durable identities before its scratch results could be discarded. Full PDFs remain in the local research folder. The tracked [provenance](../../research/s6_3_3_3_r1/MOTION_PROVENANCE.csv) links official full texts, data and paper locators.

## Build and test

```sh
cmake -S cpp -B build/r1-release -DCMAKE_BUILD_TYPE=Release
cmake --build build/r1-release --config Release --parallel
ctest --test-dir build/r1-release -C Release --output-on-failure
cmake -S cpp -B build/r1-debug -DCMAKE_BUILD_TYPE=Debug
cmake --build build/r1-debug --config Debug --parallel
ctest --test-dir build/r1-debug -C Debug --output-on-failure
cmake -S cpp -B build/r1-sanitized -DCMAKE_BUILD_TYPE=Debug -DANTWORLD_SANITIZERS=ON -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++
cmake --build build/r1-sanitized --config Debug --parallel
ctest --test-dir build/r1-sanitized -C Debug --output-on-failure
```

The native runs below use single-configuration output paths. On Windows append `.exe`. For Visual Studio, use its `Release/` executable directory. The local run used LLVM-MinGW Clang 23.1.5 with CMake 3.31.10 and Ninja. Local Windows ASan used `detect_leaks=0:halt_on_error=1` and UBSan used `halt_on_error=1:print_stacktrace=1`. Linux CI runs both with leak detection enabled.

```sh
build/r1-release/antworld_s6_3_3_3_r1 out/r1-motion motion
build/r1-release/antworld_s6_3_3_3_r1 out/r1-custody custody
build/r1-release/antworld_s6_3_3_3_r1 out/r1-connectivity connectivity
build/r1-release/antworld_s6_3_3_3_ecology out/r1-integration r1-smoke
python tools/run_s6_3_3_3_r1.py build/r1-release/antworld_s6_3_3_3_ecology out/r1-scratch out/r1-fresh/ecology --remove-verified-duplicate
build/r1-release/antworld_s6_3_3_3_density out/r1-density-legacy --legacy-memory
build/r1-release/antworld_s6_3_3_3_density out/r1-density-continuous --continuous-memory
python tools/analyze_s6_3_3_3_r1.py --check --deep
python tools/ci_verify.py
```

Fresh outputs need an unused destination. The collector can run independent spatial strata with `--spaces coarse fine` or `--spaces chamber underground` and `--workers 4` or `--workers 16`. The optional duplicate removal only affects files generated in that collector's scratch path after validation. Keep at least 9 GiB free for each heavy case. Native full-batch modes `r1-matrix` and `r1-depot` retain every test database by default. For regeneration, put the two native `samples.csv` files under `out/r1-fresh/density/{legacy,continuous}/` and run the analysis with `--raw out/r1-fresh`. Compare hashes and outcomes across equivalent environments. Rerun wall times as measurements.

For the baseline, build `antworld_s6_3_3_3_ecology` at `9f85714` in a detached checkout and run its `probes` and `smoke` modes. For exact old-model assays use `tools/run_s6_3_3_2_assays.py` with `--replay-report` and `--fidelity-report` separately, as in the [previous commands](../s6_3_3_3/README.md). For protected timings use the original admission protocols. The identity commands below only validate the work performed.

```powershell
python tools/verify_s6_3_3_3_contact_workload.py --binary build/r1-release/antworld_s6_2_benchmark.exe --scratch out/r1-contact --receipt out/r1-contact.json
python tools/verify_s6_3_3_1_reserve_workload.py --binary build/r1-release/antworld_s6_3_1_birth_benchmark.exe --scratch out/r1-birth --receipt out/r1-birth.json
```
