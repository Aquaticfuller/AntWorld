# WP-6B experimental evidence

`freeze/` contains the 960 ordinary and check cases, the 972 supplemental cases and the 250 inherited CTest identities. `formal/` holds the actual frozen collection. Every compressed archive member retains its original bytes, and each case receipt has its seed, exact input, exit code, artifact sizes and SHA-256. `formal/completed.json` binds all archive files and case statuses. `analysis/` contains independently reconciled material and lineage outputs. The `tests/`, `profiling/` and `performance/` directories carry the local verification and timing receipts. The initial cross-wall pilot failure and the disk-space build failure remain under `attempts/`.

Each completed raw case has an initial full checkpoint, final versioned frame, complete length-prefixed canonical history, daily individual and ledger cuts, intervention record, timing rows and a run summary. The initial checkpoint and the input file define the launch condition. The final frame is paired with that case's verified history prefix. The raw preflight rejections retain the exact parameters and error text without manufactured daily rows. The provenance is `d7b5948fd052b5620f461808e23d1c5dcaddf761`. The later include-only portability change at `f1aca01d860c7c0c4a51607d013039c453f682b1` leaves the Core source, headers, storage and model inputs identical. The profiled repeats run with that header correction.

## Reproduction commands

Use the repository CMake dependencies and a normal Release build. Replace `BUILD`, `COMPILER` and `SCRATCH` with local paths. Windows executable names include `.exe`. Use fresh output directories. Allow room for the full evidence batch and temporary uncompressed per-case data.

```text
python tools/freeze_s6_4_wp6b.py
cmake -S cpp -B BUILD -DCMAKE_BUILD_TYPE=Release
cmake --build BUILD --parallel 4
ctest --test-dir BUILD -j2 --output-on-failure
python tools/run_s6_4_wp6b.py --binary BUILD/antworld_s6_4_wp6b.exe --compiler COMPILER --out out/wp6b-formal --scratch SCRATCH
python tools/analyze_s6_4_wp6b.py out/wp6b-formal out/wp6b-analysis
python tools/analyze_s6_4_wp6b.py experiments/s6_4_wp6b/formal out/wp6b-audit
python tools/summarize_s6_4_wp6b.py out/wp6b-audit
python tools/verify_s6_4_wp6b_legacy.py --binary BUILD/antworld_s6_4_wp5.exe --out out/wp6b-legacy.json
python tools/profile_s6_4_wp6b.py --binary BUILD/antworld_s6_4_wp6b.exe --out out/wp6b-profile --scratch SCRATCH
```

To reproduce a single input exactly, extract its archive members and run `BUILD/antworld_s6_4_wp6b.exe PARAMETERS_FILE OUTPUT observed`. `unobserved` omits the daily projection and still exports the same canonical facts and final frame. `durable` additionally publishes and reopens a segmented SQLite checkpoint at day 45. Compare the original and recovered outputs by SHA-256. Benchmark elapsed values, build hashes and absolute timings depend on the host and build environment.

On the Windows hardware used for native qualification, use the same live HWiNFO log, power state and processor-times instrument. The original approval and acceptance thresholds still apply.

```text
python tools/run_s6_3_3_1_performance.py --prepare --out out/wp6b-core --build BUILD --compiler COMPILER --confirmation experiments/s6_3_3_1/performance/instrument_v2_confirmation/receipt.json
python tools/verify_s6_3_3_1_reserve_workload.py --binary BUILD/antworld_s6_3_1_birth_benchmark.exe --scratch SCRATCH/wp6b-native-identity --receipt out/wp6b-core/reserve_identity_receipt.json
python tools/run_s6_3_3_1_performance.py --out out/wp6b-core --archive SCRATCH/wp6b-core-private --build BUILD --hwinfo-csv SENSOR_CSV
python tools/analyze_s6_3_3_1_performance.py --raw out/wp6b-core --out out/wp6b-core-analysis
python tools/run_s6_4_wp6b_observer_performance.py --prepare --out out/wp6b-observer --build BUILD --compiler COMPILER --binary BUILD/antworld_s6_4_wp5_benchmark.exe
python tools/run_s6_4_wp6b_observer_performance.py --out out/wp6b-observer --archive SCRATCH/wp6b-observer-private --binary BUILD/antworld_s6_4_wp5_benchmark.exe --hwinfo-csv SENSOR_CSV
python tools/analyze_s6_4_wp6b_observer_performance.py out/wp6b-observer out/wp6b-observer-analysis.json
```

Reference endpoints, hypothesis scope and decision rules are indexed in the [results](../../research/s6_4_wp6b/S6_4_WP6B_RESULTS.md), [freeze](../../research/s6_4_wp6b/FROZEN_PROTOCOL.md) and [scientific assessment](../../research/s6_4_wp6b/F1_SCIENTIFIC_ASSESSMENT.md). Existing experimental archives and old model controls remain in their original directories.
