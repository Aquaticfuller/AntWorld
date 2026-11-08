# S2.2 trail-following mechanism evidence

All values are `ENGINEERING_FIXTURE`. [Protocol](../../docs/29_S2_2_Validation_Protocol.md) was committed as `1b9bdbd` before behavior changes. The untouched S2.1 behavior and complete local baseline are frozen in `173d372`. [Primary literature](../../docs/30_S2_2_Literature_and_Model_Rationale.md) motivates qualitative hypotheses, not calibration. See [S2_2_RESULTS.md](../../S2_2_RESULTS.md) for the acceptance decision and limitations.

## Files and measurements

- `baseline/local.csv`, `fixed/local.csv`: 55,296 raw local trials per version, with every seed, configuration and complete ordered trajectory. The root `S2_2_EXPERIMENTS.csv` concatenates these 110,592 local trials only. Social and broad-ablation trials are separate below.
- `baseline/` also retains the summaries produced before the production change. `summary.csv`, `paired.csv`, `model_effects.csv`, `mirrors.csv`, `departure_survival.csv` and `input_hashes.json` compare both versions without rewriting that record.
- `sensitivity_balanced.csv` compares all age/persistence cells on the shared, predeclared sensitivity seed set 1-128. All 512 primary seeds remain in the acceptance tables; no observed outcomes are removed.
- `social/{social,choices,fields}.csv`: exact original S2.1 social protocol under physics 5: 1,152 trials, 24,576 choice diagnostics and sparse field samples. The S2.1 baseline remains at `../s2_1/fixed/`. `social_summary.csv` and `social_effects.csv` compare versions, including non-discoverers and negative outcomes.
- `ablations/{summary,timeseries,aggregate,paired_differences}.csv`: original 128-run, 12-worker, 30-minute S2 matrix, with 7,808 time samples. Compare to `../s2_1/ablations/`; no-signal and memory-only results are unchanged.
- `figures/`: standalone SVG/PNG mechanism, sensitivity/social and trajectory charts. Trajectory illustration uses seed 1, unreflected, without selecting for success. The reference line in the absence panels is an observer annotation, not a chemical signal.
- `performance/`: active-forager, fixed-active, scheduler and diagnostic Release fixtures and 5 ms sampled peak process working sets. These are host measurements, not biological or full-world performance guarantees.

Each local context is crossed with present/absent/blind, both reflections, ages 0/60/180 seconds and persistence weights 0/20/40. The original persistence 20 and age zero use seeds 1-512; all other cells use seeds 1-128. Response weight remains 180 (zero only in blind controls), initial marked concentration 1, cutoff 0.001 and half-life 60 s, with natural decay during each 1,101 ms step. Food and learned memory are absent. A bounded, physically adjacent approach trace supplies initial heading; it is not a food route. All trajectories are retained.

The first-step assays (`y_symmetric`, `y_conflict`, `lost`, `visited`) measure one local choice. Symmetric Y arms are staircase paths embedded on the existing cardinal lattice; the first left/right steps are both lateral. The asymmetric Y competes a marked turn against a straight continuation. This is a topology/control experiment, not a numerical reproduction of real laboratory bifurcation angles. Only the open-arena `straight` and `bend` assays (24 moves) count as continuous-following evidence. Narrow corridors cannot establish that endpoint.

`selected_marked` means the chosen first cell lies on the reference chemical line; under absent/blind this is the same geometric location, not evidence of chemical response. `occupancy` and `near_occupancy` are fractions of completed moves landing on the line or within one Manhattan cell. `initial_streak` counts consecutive on-line moves until first departure; `max_streak` includes any later reacquisition, and `streak3` is `max_streak >= 3`. These are different endpoints. `first_deviation_step=-1` means no observed on-to-off transition; continuous-trial non-departures are censored at 24 moves in `restricted_first_deviation_step`. That survival endpoint applies to the two initially on-line continuous contexts, not the initially off-line lost/visited probes.

`deviations`/`reacquisitions` count on-to-off/off-to-on transitions. `uturns` counts a physical reversal to the immediately prior cell; the model's loop-erased predecessor can differ after closing a loop. Total `path_m` counts all steps, while `net_displacement_m` is Euclidean start-to-end displacement, with no preferred food direction. `mean_distance_m` is mean Manhattan distance from the reference line over completed moves. `trajectory` is a semicolon-separated sequence of `x:z` cells including start. No trajectory field is an intended path supplied to the policy.

The local runner is a detached production-policy assay with controlled input substrates and observer metrics. It never mutates a WorldRuntime field or fabricates committed history. Its private path update mirrors the existing bounded loop-erased trace. Independent integrated regressions use actual autonomous scout deposits and the real runtime's movement, transactions, ledgers, save/restore and decision scheduling. This separation avoids adding an experimental chemical-injection API to the authoritative core.

## Uncertainty and interpretation

Mirrors share seeds. Primary paired acceptance metrics use 4,096 bootstrap resamples of seed clusters, analysis RNG seed 2202: symmetric choice, straight/bend occupancy and three-step streak, and the lost-cue correction. Other tables use 95% normal-approximation intervals over seed-cluster means. Main social effects use 64 seed clusters and the same bootstrap procedure; rates are not averaged only over discovered workers. Intervals are descriptive without multiplicity adjustment. Primary local cells use 512 clusters, sensitivity cells 128. Baseline blind/absent paths, fixed blind/absent paths, and no-signal outcomes across versions match exactly. Initial departure/streak remains unchanged across versions; improvements in later maximum streak include recovery, not reduced first-departure probability.

## Reproduce

From a clean repository, use the pinned Windows bootstrap/build or standard C++20 CMake commands in the root README. Run from the repository root:

```powershell
./tools/bootstrap_windows.ps1
./tools/build_windows.ps1 -Configuration Release
./build/release/antworld_s2_2_experiment.exe out/s2_2-local 512
./build/release/antworld_s2_1_experiment.exe out/s2_2-social 64 s2.2
./build/release/antworld_s2_experiment.exe out/s2_2-ablations 16 1800000
python tools/analyze_s2.py out/s2_2-ablations
python tools/analyze_s2_2.py --check
./tools/build_windows.ps1 -Configuration Debug
./tools/build_windows.ps1 -Configuration Debug -BuildDirectory build/sanitized -Sanitizers
./tools/benchmark_s2_windows.ps1 -OutputDirectory out/s2_2-performance
```

Compare the output files with `fixed/`, `social/` and `ablations/`, normalizing CRLF/LF only on the same build/platform. `analyze_s2_2.py` without `--check` regenerates combined/derived evidence from the committed raw files. `--baseline-only` reproduces the pre-change local summaries without accessing the fixed results. Core determinism is same-build/platform, not promised floating-point byte equality across compilers.

To reproduce the baseline without touching the current worktree, run `git archive --output=out/s2_2-baseline.zip 173d372 cpp scenarios`, extract into a new empty directory, configure/build that tree and execute its `antworld_s2_2_experiment OUTPUT_DIR 512`. It still uses physics 4 and reports model `s2.1`. The original S2.1 social baseline can independently be rebuilt from `c3d24e8`; all of its original evidence is preserved.

After running both local versions and the fixed integrated experiments from clean builds, compare all seven raw files using:

```sh
python tools/verify_s2_2_reproduction.py --baseline out/s2_2-reproduced-baseline --fixed out/s2_2-reproduced-local --social out/s2_2-reproduced-social --ablations out/s2_2-reproduced-ablations --report out/s2_2-reproduction.json
```

`reproduction.json` retains the executed comparison's hashes and row counts. No numerical tolerance or selective metric comparison is used for repeated runs on the same compiler/platform.

On Linux, configure `cmake -S cpp -B build/repro -DCMAKE_BUILD_TYPE=Release`, build with `cmake --build build/repro --parallel 4`, and test with `ctest --test-dir build/repro --output-on-failure`; use executables from `build/repro/` without `.exe`. Optional plotting uses the already pinned S2.1 matplotlib requirements, outside the core:

```sh
python -m pip install --only-binary=:all: --target .tools/s2_1-python -r tools/s2_1_plot_requirements.txt
python tools/plot_s2_2.py --packages .tools/s2_1-python
```

No parameter search, seed replacement or additional production tuning followed the frozen matrix. The minimal correction permits a local stochastic response; it is not a general route direction or recruitment solution. Stop for review before S3.
