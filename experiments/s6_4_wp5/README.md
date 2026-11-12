# WP-5 cohort survival and autonomous excavation evidence

The [frozen protocol](../../research/s6_4_wp5/FROZEN_PROTOCOL.md) and [technical notes](../../research/s6_4_wp5/PRECOLLECTION_ENGINEERING_NOTES.md) precede collection. The new raw archives use per-case receipt and artifact SHA-256. Every archive includes a lineage census, complete canonical stream, all application inputs, a segmented midpoint SQLite, Sidecar, checkpoint endpoints, geometry definition, edits, parcels and route samples. WP-4's 104 complete raw archives remain at `../s6_4_wp4/baseline`. They are read by their original artifact hashes.

## Reproduction

Use a Release build with profiling and sanitizers off. `BUILD` is the build directory, `COMPILER` is the matching compiler and `SENSOR_CSV` is a live HWiNFO file. Windows names include `.exe`; use executable names without that extension on Linux. Native timing requires Windows and the unchanged instrument-v2 admission rules. Use fresh output paths.

```text
cmake -S cpp -B BUILD -DCMAKE_BUILD_TYPE=Release
cmake --build BUILD --parallel 4
ctest --test-dir BUILD --output-on-failure
python tools/run_s6_4_wp5.py --binary BUILD/antworld_s6_4_wp5.exe --cache BUILD/CMakeCache.txt --compiler COMPILER --out out/wp5-assays --scratch out/wp5-scratch
python tools/analyze_s6_4_wp5.py experiments/s6_4_wp4/baseline out/wp5-assays out/wp5-analysis
python tools/analyze_s6_4_wp5.py experiments/s6_4_wp4/baseline experiments/s6_4_wp5/baseline experiments/s6_4_wp5/analysis --check
python tools/build_s6_4_wp5_evidence.py --check
python tools/screen_s6_4_wp5_sources.py out/s6_4_preflight/phase4/intake/CAND-05 experiments/s6_4_wp5/source_screening.json --check
```

The source screening uses legally acquired external control metadata by hash. It is a separate local step and requires no third-party data in CI.

```text
python tools/run_s6_4_wp5_performance.py --prepare --out out/wp5-observer --build BUILD --compiler COMPILER --binary BUILD/antworld_s6_4_wp5_benchmark.exe
python tools/run_s6_4_wp5_performance.py --out out/wp5-observer --archive out/wp5-observer-sensors --binary BUILD/antworld_s6_4_wp5_benchmark.exe --hwinfo-csv SENSOR_CSV
python tools/run_s6_3_3_1_performance.py --prepare --out out/wp5-core --build BUILD --compiler COMPILER --confirmation experiments/s6_3_3_1/performance/instrument_v2_confirmation/receipt.json
python tools/verify_s6_3_3_1_reserve_workload.py --binary BUILD/antworld_s6_3_1_birth_benchmark.exe --scratch out/wp5-reserve-identity --receipt out/wp5-core/reserve_identity_receipt.json
python tools/run_s6_3_3_1_performance.py --out out/wp5-core --archive out/wp5-core-sensors --build BUILD --hwinfo-csv SENSOR_CSV
python tools/archive_s6_4_rm02_performance.py out/wp5-observer out/wp5-observer-public
python tools/archive_s6_4_rm02_performance.py out/wp5-core out/wp5-core-public
python tools/analyze_s6_4_wp5_performance.py out/wp5-observer-public out/wp5-observer-analysis.json
python tools/analyze_s6_3_3_1_performance.py --raw out/wp5-core-public --out out/wp5-core-analysis
```

Process inventories are removed by the accepted exporter. All timing rows, admission intervals and selected hardware sensor measurements remain. Absolute performance, queue and storage traces describe the measured host. Signed risk intervals, selected action outcomes, and the independent occupancy reconstruction use committed fact IDs. An assay name identifies a simulation replica; within it references preserve the authoritative WorldId and entity ID.
