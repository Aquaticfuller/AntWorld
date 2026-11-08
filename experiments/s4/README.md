# S4 reproducible geometry evidence

All quantities and conditions are ENGINEERING_FIXTURE. The frozen protocol is document 32. The user authorized S4 only; this archive does not authorize S5.

- `raw/summary.csv`: 160 runs, all seeds 1-32, five conditions per seed.
- `raw/edits.csv`: 1,612 committed edits with actor, time, source/fact/parcel identities, exact bounds and actual removed volume.
- `raw/trajectories.csv`: 3,872 sampled individual positions, carried soil and behavior counters. These samples are not a replacement for the committed event history.
- `raw/configuration.json`: exact experimental setup; versioned world/physiology defaults remain in the source.
- `summary.csv`: 95% seed-bootstrap intervals, 4,096 resamples with analysis RNG 4004. Reversed runs are paired controls, not additional independent observations.
- `manifest.json`: normalized-LF SHA-256 hashes and coverage audit.
- `performance/`: all raw timing samples, p50/p95/p99 summaries, host/process-memory metadata and retained S0-S3 benchmark runs. Timing values are host measurements, not deterministic biological outputs.
- `regression.json`: full S4 output equality and S3 semantic equality (1,536 runs, 5,376 individual records; only physics version differs).
- `clean_reproduction.json`: archived-source S4 output equality.
- `figures/`: all-seed outcomes and predeclared seed-1 geometry sections, PNG/SVG.

## Reproduction

Build using the repository README. Windows executable examples follow; on other platforms use the same targets without `.exe`.

```powershell
./build/release/antworld_s4_experiment.exe out/s4-reproduced 32
python tools/verify_s4_reproduction.py out/s4-reproduced --source-commit SOURCE_COMMIT --report out/s4-reproduction.json
python tools/analyze_s4.py --check
./build/release/antworld_s4_benchmark.exe out/s4-performance.csv
./build/release/antworld_s3_experiment.exe out/s4-s3-regression 64
python tools/verify_s4_reproduction.py out/s4-reproduced --source-commit SOURCE_COMMIT --s3-regression out/s4-s3-regression --report out/s4-regression.json
```

Replace `SOURCE_COMMIT` with the actual checkout's `git rev-parse HEAD`. Preserve the historical S3 archive; never point the current runner at `experiments/s3/raw`.

The checked-in analysis is standard-library Python. The optional plotting dependencies use the already pinned `tools/s2_1_plot_requirements.txt`:

```sh
python -m pip install --target .tools/s2_1-python -r tools/s2_1_plot_requirements.txt
python tools/plot_s4.py
```

To reproduce from only committed source:

```powershell
git archive --format=zip --output=out/s4-source.zip SOURCE_COMMIT cpp scenarios
Expand-Archive out/s4-source.zip out/s4-source
cmake -S out/s4-source/cpp -B build/s4-source -DCMAKE_BUILD_TYPE=Release
cmake --build build/s4-source --config Release
ctest --test-dir build/s4-source -C Release --output-on-failure
# Executable location follows the chosen CMake generator.
./build/s4-source/antworld_s4_experiment.exe out/s4-clean-run 32
python tools/verify_s4_reproduction.py out/s4-clean-run --source-commit SOURCE_COMMIT --report out/s4-clean.json
```

## Interpretation

One coordinate quantum is 0.5 mm; one cubic quantum is 0.125 cubic mm. Homogeneous soil holds 100 ug dry material and 25 ug water per cubic quantum. The box kernel has exact integer volume/material balance; signed distances use floating point in a four-quantum narrow band. Cache samples do not authorize movement: every transition is checked against exact authoritative boxes.

Four workers remove more total material than one under these fixtures. This does not establish biological cooperation, realistic architecture or valid species rates. The model has no granular pile geometry; deposited parcels remain located inventories until a supplied Fill edit compacts them. Strict history replay grows expensive for repeated overlapping edits. True dense contacts still require real neighbor work. Keep SD-01/02/03/04 and TD-01/03/04 visible in document 08.
