# RM-01 reproducible evidence

This directory contains the portable records from the isolated egg timing experiments. The [engineering report](../../research/s6_4_rm01/RM01_RESULTS.md) and [performance report](../../research/s6_4_rm01/RM01_PERFORMANCE_RESULTS.md) give the scoped conclusions. The [file digest index](payload_sha256.json) covers the recorded payloads.

- `assay` includes every short-arm configuration, observation, event and cut plus the ecology counters and egg histories. In a short `facts.csv` the `canonical_hex` field is the complete committed event payload. The verification hashes each payload with its little-endian 32-bit length prefix.
- `observer` contains the admitted warm-up and retained pairs, pre-candidate baseline envelope, and two warm horizon cases. `observer-rejected` contains the preceding rejected admission with zero samples.
- `durability` contains the unchanged doc 64 workload timing and ecological receipts. Each run's `archive.json` records the independently checked segment, frame and canonical fact digests.
- `controlled` retains all 180 native admission rows, planned schedules and analyzer results. There were zero timed workload rows. `controlled-setup-interrupted` preserves the earlier pre-admission access failure. Host process lists and full HWiNFO captures stay in the local originals.
- `ctest` contains the local build and test logs. Run receipts record the SHA-256 values for local databases, checkpoints and other output files. Databases, checkpoints and source studies remain in the local generated directories.

## Repeat the application tests and matrix

Configure with the supported CMake toolchain and storage enabled. The local runs reused the project-pinned LLVM-MinGW Ninja build directories `build/s6_3_4-release`, `build/s6_3_4-debug` and `build/s6_3_4-sanitizer`. They used the build and CTest commands below for each respective directory. Fresh directories with the same configuration also work.

```powershell
cmake --build build/s6_3_4-release --parallel 4
ctest --test-dir build/s6_3_4-release --output-on-failure --parallel 3
cmake --build build/s6_3_4-debug --parallel 4
ctest --test-dir build/s6_3_4-debug --output-on-failure --parallel 3
$env:ASAN_OPTIONS = 'detect_leaks=0:halt_on_error=1'
$env:UBSAN_OPTIONS = 'halt_on_error=1:print_stacktrace=1'
cmake --build build/s6_3_4-sanitizer --parallel 4
ctest --test-dir build/s6_3_4-sanitizer --output-on-failure --parallel 3
python tools/run_s6_4_rm01.py build/s6_3_4-release out/rm01-new-assay
python tools/run_s6_4_rm01.py build/s6_3_4-release out/rm01-new-observer --mode observer
python tools/verify_s6_4_rm01_results.py experiments/s6_4_rm01/assay --observer experiments/s6_4_rm01/observer
```

The driver requires a committed C++ app, verifies the base tree and authorized file scope and rebuilds the selected target. Use new output directories. Run timing batches sequentially under the frozen admissions. To reproduce the exact recorded assay source use `2b7ca57bbc5a887527a9cf5f69066b7df0daa5ed`. To reproduce the observer driver and envelope sequence use `151cb7f8ae54d3b96dea819ca766e89b3bfe200c`. Both revisions have the same compiled application. The current verification script can read both archived receipts.

## Repeat the inherited performance checks

The storage reproduction uses the original [S6.3.4 commands](../s6_3_4/README.md) with a new scratch directory. Verify the recorded measurements against the earlier portable batch.

```powershell
python tools/analyze_s6_3_4.py experiments/s6_4_rm01/durability experiments/s6_4_rm01/durability/analysis --compare-baseline experiments/s6_3_4/portable --check
python tools/analyze_s6_3_3_1_performance.py --raw experiments/s6_4_rm01/controlled --out experiments/s6_4_rm01/controlled/analysis --check
```

The controlled replay uses the unmodified [instrument runner](../../tools/run_s6_3_3_1_performance.py), the existing confirmation and exact reserve executable. The first command freezes all six schedules. The second checks the three reserve-workload identities. The third collects under native host access and the unchanged HWiNFO mapping and admission rules.

```powershell
python tools/run_s6_3_3_1_performance.py --prepare --out out/rm01-new-controlled --build build/s6_3_4-release --compiler $Compiler --confirmation experiments/s6_3_3_1/performance/instrument_v2_confirmation/receipt.json
python tools/verify_s6_3_3_1_reserve_workload.py --binary build/s6_3_4-release/antworld_s6_3_1_birth_benchmark.exe --scratch out/rm01-new-identity --receipt out/rm01-new-controlled/reserve_identity_receipt.json
python tools/run_s6_3_3_1_performance.py --out out/rm01-new-controlled --build build/s6_3_4-release --archive out/rm01-new-sensors --hwinfo-csv $HwinfoCsv
```
