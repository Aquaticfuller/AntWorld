# WP-3 experiment archives and reproduction

The [protocol](../../research/s6_4_wp3/FROZEN_PROTOCOL.md) freezes the inputs and comparisons. The [results index](../../research/s6_4_wp3/S6_4_WP3_RESULTS.md) links the scientific and engineering reports. Raw case archives contain the configuration, inputs, scope, canonical event stream, all host cuts, Sidecar, real midpoint SQLite save, initial/midpoint/final checkpoints, state and trace identities, actual native execution status and hashed receipts. The prepared path archives contain their detached inputs and trajectories. Use the case matrix to reproduce all 228 cases. A safe verifier reads each named tar member directly, checks its size and hash, and verifies the stored event bytes and published cut digests.

## Verify and rebuild

```text
python tools/build_s6_4_wp3_evidence.py --check
python tools/verify_s6_4_wp3.py experiments/s6_4_wp3/baseline
python tools/test_s6_4_wp3_observations.py
python tools/analyze_s6_4_wp3.py experiments/s6_4_wp3/baseline experiments/s6_4_wp3/analysis --check
python tools/analyze_s6_4_wp3_performance.py experiments/s6_4_wp3/performance/formal experiments/s6_4_wp3/performance/formal_analysis.json --check
python tools/analyze_s6_3_3_1_performance.py --raw experiments/s6_4_wp3/performance/core --out experiments/s6_4_wp3/performance/core_analysis --check
```

Use a new output directory and the matching Release executable. Set `$Build` to its CMake build directory, `$Compiler` to its compiler, and `$HwinfoCsv` to the compatible live log. On Windows, use the `.exe` executable names. Use paths without that suffix on other systems for the case runner. Native admission and performance collection require the approved Windows host and should run alone.

```powershell
cmake --build $Build --target antworld_s6_4_wp3 antworld_s6_4_wp3_benchmark antworld_s6_2_benchmark antworld_s6_3_1_birth_benchmark
python tools/run_s6_4_wp3.py --binary "$Build/antworld_s6_4_wp3.exe" --cache "$Build/CMakeCache.txt" --compiler $Compiler --out out/wp3-replay --scratch out/wp3-scratch
python tools/verify_s6_4_wp3.py out/wp3-replay
python tools/analyze_s6_4_wp3.py out/wp3-replay out/wp3-analysis

python tools/run_s6_4_wp3_performance.py --prepare --out out/wp3-formal --binary "$Build/antworld_s6_4_wp3_benchmark.exe" --build $Build --compiler $Compiler
python tools/run_s6_4_wp3_performance.py --out out/wp3-formal --binary "$Build/antworld_s6_4_wp3_benchmark.exe" --archive out/wp3-formal-sensors --hwinfo-csv $HwinfoCsv
python tools/archive_s6_4_rm02_performance.py out/wp3-formal out/wp3-formal-export
python tools/analyze_s6_4_wp3_performance.py out/wp3-formal-export out/wp3-formal-analysis.json

python tools/run_s6_3_3_1_performance.py --prepare --out out/wp3-core --build $Build --compiler $Compiler --confirmation experiments/s6_3_3_1/performance/instrument_v2_confirmation/receipt.json
python tools/verify_s6_3_3_1_reserve_workload.py --binary "$Build/antworld_s6_3_1_birth_benchmark.exe" --scratch out/wp3-core-identity --receipt out/wp3-core/reserve_identity_receipt.json
python tools/run_s6_3_3_1_performance.py --out out/wp3-core --build $Build --archive out/wp3-core-sensors --hwinfo-csv $HwinfoCsv
python tools/archive_s6_4_rm02_performance.py out/wp3-core out/wp3-core-export
python tools/analyze_s6_3_3_1_performance.py --raw out/wp3-core-export --out out/wp3-core-analysis
```

The published formal and Core archives retain all timing and admission rows. Host process inventories and unmapped localized sensor captures stay local. The manifests bind every public evidence file and record which JSON inventories were removed. Scientific source bytes stay local. The [bridge data receipt](../../research/s6_4_wp3/BRIDGE_DATA_RECEIPT.json) gives the exact workbook URL and SHA-256.

```text
python tools/verify_s6_4_wp3_bridge_data.py out/s6_4_wp3/sources/sakiyama-wada-trials.xlsx research/s6_4_wp3/BRIDGE_DATA_RECEIPT.json --check
python tools/verify_s6_4_wp3_candidate_data.py out/s6_4_preflight/phase4/intake out/s6_4_wp3/sources research/s6_4_wp3/CANDIDATE_DATA_RECEIPT.json --check
```
