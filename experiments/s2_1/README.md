# S2.1 foraging validation evidence

All parameters and scenarios are `ENGINEERING_FIXTURE`. This is a numerical and behavioral validation of the existing local model, not a biological calibration. The protocol was frozen with the baseline before model fixes in commit `8bf22a96ee504ddd3b27b2881ed62553e1c536b1`. The complete result and gate decision are in [S2_1_RESULTS.md](../../S2_1_RESULTS.md); the design and ADRs are in [document 28](../../docs/28_S2_1_Validation_Protocol.md).

## Data inventory

| Artifact | Contents |
|---|---|
| `../../S2_1_EXPERIMENTS.csv` | 51,712 raw trial rows with model, seed, configuration and metrics: 49,152 choice/response rows, 2,304 social rows and 256 original-ablation rows |
| `baseline/{choices,social,fields}.csv` | Physics 3, instrumented S2 baseline, retained without alteration |
| `fixed/{choices,social,fields}.csv` | Physics 4, identical protocol after the two minimal fixes |
| `source_audit_before.csv`, `source_audit_after.csv` | Compact 4,096-seed ID and fractional-response diagnostics |
| `social_summary.csv` | Per-model, delay and treatment rates, seed-cluster intervals, time/path/food/field means |
| `orientation_rates.csv` | Separate east/west discovery rates with Wilson 95% intervals over 64 seeds each |
| `paired_effects.csv` | Paired present-minus-absent effects, units and seed-cluster bootstrap intervals |
| `survival.csv` | Discovery survival curves at 1-second samples, retaining non-discoverers |
| `ablations/` | Rerun of the unchanged S2 16-seed x 2-layout x 4-treatment matrix, with all 7,808 time samples |
| `ablation_summary.csv` | Old/new ablation means, sample standard deviations and ranges |
| `input_hashes.json` | SHA-256 of all six social/choice/field input files, normalizing text to UTF-8 with LF |
| `reproduction.json` | Eight-file exact comparison against independent clean-build reruns of both versions and the fixed ablations |
| `figures/` | Three figures, each as standalone SVG and PNG |
| `performance/` | Release scaling fixtures and sampled process memory |

There are 1,152 social trials per model: seeds 1-64, both mirrored food placements, delays 0/180/600 seconds and present/absent/blind treatments. Each has an independently trained scout and one initially dormant novice. All 128 seed/orientation training pairs succeeded, so the unconditional pipeline and training-conditioned rates coincide. No seeds were removed or replaced. The two field files contain 260,648 sparse sample rows, including explicit empty-field markers. The combined table enriches app output with fixed configuration values from the fixture; it does not estimate missing outcomes. Blank cells mean a field does not apply to that experiment type.

## Definitions and controls

- `first_discovery_ms`: elapsed time after novice activation of the first committed decision recording a locally visible food cue. It is not the time of physical arrival, collection or delivery. `-1` means no event observed in the window; `discovery_observed` is the censoring indicator. `followup_ms` is the discovery time or the full 180,000 ms window for a trained non-discoverer. Training failure would have zero follow-up and a separate `trained=0` row; none occurred here.
- `rmst_s`: mean time to discovery restricted to 180 seconds, including non-discoverers at the window boundary. Survival is the fraction still undiscovered, with all remaining individuals censored at the common end. Raw CSVs retain exact millisecond event times; plots sample at one second. Lower restricted time indicates earlier discovery.
- `path_before_discovery_m`: actual completed movement until first discovery or censoring. `path_window_m` includes the whole observation window. Every step is 0.01 m, requires simulated time and passes the normal movement transaction.
- `route_overlap_fraction`: fraction of those pre-discovery/censoring edges also present in the scout's actual loop-erased experienced route. Edges are undirected. This measures overlap, not a shortest path, directional guidance or proof of recruitment. The observer's recorded route is never supplied to the novice.
- `trail_moves` and `trail_moves_before_discovery`: chosen moves labeled FollowTrail because the destination had a visible signal. Such a label is descriptive, even in a zero-response control; it is not causal evidence. `signal_decisions` counts decisions with some locally visible adjacent signal, whether or not memory, return or other rules override it.
- `collected_ug` and `delivered_ug`: novice transfers only, in integer micrograms. Scout training removes 1,000 ug from the initial 4,000,000 ug stock identically in paired conditions. Four ingredient balances are checked throughout. Food availability, novice cargo/state, initial memory, terrain and observation window match.
- `release_trace_coverage`: fraction of actual return arrival cells with live signal at release. A complete trace connects the nest to within local sensing range of food; no deposit is fabricated on the source cell. Cell samples record release and every 30 seconds thereafter; `cell_x=cell_z=-1, units=0` is an empty field, not a surface cell.
- **Absent** disables deposition/response. **Blind** retains deposition/decay but has response weight zero. **Present** retains unchanged S2 response weight 180. Memory is disabled in all social runs, while the bounded current-trip homing trace remains. The scout is retired through the existing explicit lifecycle fixture immediately after its first delivery. This artificial removal isolates its trace and is not a mortality model.
- At 600 seconds the initial trace is gone, and first-discovery times/paths match the absence control exactly. Later deliveries can differ because a novice that finds food subsequently deposits its own signal in the present condition. This expired-field control isolates initial recruitment, not all post-discovery behavior.

Paired intervals use 4,096 percentile-bootstrap draws with analysis RNG seed 2101, resampling the 64 seed clusters. Each cluster averages its two mirrored orientations. Main rate intervals also resample seed clusters; Wilson intervals are reported separately for each orientation, avoiding a false assumption that mirrors are independent. Intervals are descriptive and unadjusted for multiple comparisons; a sign change or an interval containing zero does not establish benefit or equivalence. The original ablation charts show sample SD, not confidence intervals. All numerical settings and the primary seed sets were retained after inspecting results.

## Reproduce current experiments

Build from the repository root with the pinned Windows bootstrap or any tested C++20 toolchain (see the root README). No Python dependency is needed by the simulation or standard-library analysis.

```powershell
./tools/bootstrap_windows.ps1
./tools/build_windows.ps1 -Configuration Release
./build/release/antworld_s2_1_audit.exe
./build/release/antworld_s2_1_experiment.exe out/s2_1-reproduced 64 s2.1
./build/release/antworld_s2_experiment.exe out/s2_1-ablations 16 1800000
python tools/analyze_s2.py out/s2_1-ablations
python tools/analyze_s2.py experiments/s2_1/ablations --check
python tools/analyze_s2_1.py --check
./tools/benchmark_s2_windows.ps1 -OutputDirectory out/s2_1-performance
```

Compare the three `out/s2_1-reproduced/*.csv` files with `fixed/`, and the two raw ablation files with `ablations/`, normalizing only CRLF/LF. `analyze_s2_1.py` without `--check` regenerates the combined table and all derived summaries from the committed inputs. The app accepts an output directory, 1-64 seeds and a model label; the fixed build rejects a baseline label. Every social final checkpoint is restored and compared; original ablations do the same. Cross-platform floating-point byte identity is outside the determinism contract, while repeated runs on the same build/platform must match.

For Linux, use `cmake -S cpp -B build/repro -DCMAKE_BUILD_TYPE=Release`, `cmake --build build/repro --parallel 4` and `ctest --test-dir build/repro --output-on-failure`; run the same executables from `build/repro/` without `.exe`.

## Reproduce the pre-fix baseline

Use a separate checkout/export of the immutable baseline commit, preserving the current worktree:

```sh
git archive --output=out/s2_1-baseline.zip 8bf22a96ee504ddd3b27b2881ed62553e1c536b1
```

Extract into an empty directory, build its `cpp/` tree using the same compiler, then run `antworld_s2_1_experiment OUTPUT_DIR 64 s2-baseline` and `antworld_s2_1_audit`. Compare against `baseline/` and `source_audit_before.csv`. The baseline adds only validated late first activation and restore validation to S2; its food selection, weights, deposit, decay and state priorities are unchanged. Historical broad-ablation evidence is retained under `../s2/` from the S2 implementation, whose autonomous behavior is identical to that instrumentation baseline.

For a complete automatic comparison after both versions have run, use:

```sh
python tools/verify_s2_1_reproduction.py --baseline out/s2_1-reproduced-baseline --fixed out/s2_1-reproduced-fixed --ablations out/s2_1-reproduced-ablations --report out/s2_1-reproduction.json
```

The directory names must point to the actual baseline, fixed social and fixed ablation outputs. The helper compares all eight raw files exactly after newline normalization and records their row counts and hashes. It does not accept a tolerance for repeated same-build runs.

## Render figures

Optional plotting dependencies are separate from the core and pinned with all transitive versions:

```sh
python -m pip install --only-binary=:all: --target .tools/s2_1-python -r tools/s2_1_plot_requirements.txt
python tools/plot_s2_1.py --packages .tools/s2_1-python
```

`recruitment` shows rates, censored discovery times and paired uncertainty; `ablations` retains broad coverage/delivery comparisons. `trail_fields` uses seed 1 from the fixed seed set, east placement, showing actual scout deposits at release on the same intensity scale. This figure is not a selected successful recruitment example; all spatial samples remain available. English labels and PNG metadata were visually/manually reviewed.
