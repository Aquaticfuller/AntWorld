# WP-4 reproduction and evidence index

All runs are `ENGINEERING_FIXTURE`. See the [frozen protocol](../../research/s6_4_wp4/FROZEN_PROTOCOL.md), [source audit](../../research/s6_4_wp4/SOURCE_AND_EVIDENCE_AUDIT.md) and [results](../../research/s6_4_wp4/S6_4_WP4_RESULTS.md).

## Independent verification without rerunning the simulation

```text
python tools/build_s6_4_wp4_evidence.py --check
python tools/analyze_s6_4_wp4.py experiments/s6_4_wp4/baseline experiments/s6_4_wp4/analysis --check
python tools/summarize_s6_4_wp4.py experiments/s6_4_wp4/analysis --check
python tools/test_s6_4_wp4_observations.py experiments/s6_4_wp4/analysis
python tools/verify_s6_4_wp4_attempts.py experiments/s6_4_wp4/first_attempt experiments/s6_4_wp4/baseline --check
python tools/analyze_s6_4_wp4_performance.py experiments/s6_4_wp4/performance/formal experiments/s6_4_wp4/performance/formal_analysis.json --check
python tools/analyze_s6_3_3_1_performance.py --raw experiments/s6_4_wp4/performance/core --out experiments/s6_4_wp4/performance/core_analysis --check
```

Each `baseline/raw/CASE/` contains one compressed archive and its receipt. The archive retains full canonical facts, complete Sidecar and midpoint world SQLite, initial/mid/final checkpoints, the committed/declared input schedule, lineage initial states and per-cut states, and timings. SHA-256 and byte lengths bind every artifact. Case, WorldId and EntityId together identify a lineage across experiments. Historical control worlds retain their original WorldId across seeds and arms.

`first_attempt/` keeps the first-pass freeze, every receipt and all failed archives. Successful first-pass cases have matching authoritative histories and checkpoints in the second pass. The complete first-pass worktree archive is also retained locally under `out/s6_4_wp4/full_activity_attempt`.

`analysis/maternal_cuts.csv` contains body/crop stocks, energy/water and accumulated gifts, uptake, export and nominal program-cost integrals. `maternal_death_brackets.csv` preserves the adjacent completed cuts around death. `reproduction_attempts.csv` joins the actual attempt and child and gives prior/following cut IDs. `offspring_stages.csv` records one interval per attained stage with event or censoring. `offspring_terminal.csv`, `population_cuts.csv`, `gifts.csv`, `uptake.csv` and `fixture_inputs.csv` preserve distinct outcomes. `maternal_receipt_to_uptake.csv` is a temporal join. Per-case and paired six-seed outcomes are in `case_results.csv`, `group_summary.csv`, `common_window_outcomes.csv` and `paired_contrasts.csv`.

## Re-run locally

From the repository root in a clean checkout with Python 3.12+ and the platform compiler:

```text
cmake -S cpp -B build/wp4-release -DCMAKE_BUILD_TYPE=Release
cmake --build build/wp4-release --parallel
ctest --test-dir build/wp4-release --output-on-failure
python tools/run_s6_4_wp4.py --binary BUILD/antworld_s6_4_wp4 --cache BUILD/CMakeCache.txt --compiler COMPILER --out out/wp4-replay --scratch out/wp4-scratch
python tools/analyze_s6_4_wp4.py out/wp4-replay out/wp4-analysis
python tools/summarize_s6_4_wp4.py out/wp4-analysis
python tools/test_s6_4_wp4_observations.py out/wp4-analysis
```

Replace `BUILD` with `build/wp4-release` and `COMPILER` with the actual C++ compiler. On Windows use the executable suffix `.exe`. Supply one or more exact `--case` IDs for a smoke run into a separate new directory. CTest covers the nine WP-4 assays in every configuration. For sanitizer builds use Clang with `-DANTWORLD_SANITIZERS=ON` and halt-on-error ASan/UBSan.

## Native timing

On the admitted Windows host with a live compatible HWiNFO CSV and independently verified per-core CPU timing, freeze the same Release build and use the following commands in sequence. Preserve both collectors' original admission and telemetry. Use a fresh output directory for each collector.

```text
python tools/run_s6_4_wp4_performance.py --prepare --out out/wp4-formal --build BUILD --compiler COMPILER --binary BUILD/antworld_s6_4_wp4_benchmark.exe
python tools/run_s6_4_wp4_performance.py --out out/wp4-formal --archive out/wp4-formal-sensors --binary BUILD/antworld_s6_4_wp4_benchmark.exe --hwinfo-csv SENSOR_CSV
python tools/run_s6_3_3_1_performance.py --prepare --out out/wp4-core --build BUILD --compiler COMPILER --confirmation experiments/s6_3_3_1/performance/instrument_v2_confirmation/receipt.json
python tools/verify_s6_3_3_1_reserve_workload.py --binary BUILD/antworld_s6_3_1_birth_benchmark.exe --scratch out/wp4-reserve-identity --receipt out/wp4-core/reserve_identity_receipt.json
python tools/run_s6_3_3_1_performance.py --out out/wp4-core --archive out/wp4-core-sensors --build BUILD --hwinfo-csv SENSOR_CSV
python tools/archive_s6_4_rm02_performance.py out/wp4-formal out/wp4-formal-public
python tools/archive_s6_4_rm02_performance.py out/wp4-core out/wp4-core-public
python tools/analyze_s6_4_wp4_performance.py out/wp4-formal-public out/wp4-formal-analysis.json
python tools/analyze_s6_3_3_1_performance.py --raw out/wp4-core-public --out out/wp4-core-analysis
```

The published export preserves every sample and removes unrelated background process inventories from JSON. Raw HWiNFO copies are kept locally. The selected temperature, power and frequency columns, their provenance and native CPU intervals are archived.
