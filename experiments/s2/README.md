# S2 mechanism experiments

All runs use `ENGINEERING_FIXTURE` parameters from `s2-local-v1`. This directory preserves the complete, unfiltered 16-seed x 2-layout x 4-treatment matrix: 128 runs, 12 workers per run, 30 simulated minutes, 30-second samples including zero. No parameter is asserted to be a calibrated Lasius niger constant.

Reproduce from a Release build:

```powershell
./build/release/antworld_s2_experiment.exe out/s2-reproduced 16 1800000
python tools/analyze_s2.py out/s2-reproduced
python tools/analyze_s2.py experiments/s2 --check
```

On Linux omit `.exe` and select the actual build directory. The executable takes output directory, optional seed count (1-64), and optional duration in milliseconds (positive multiple of 30,000, at most 3,600,000). Defaults reproduce this matrix. It validates per-ingredient conservation throughout and round-trips every final checkpoint before recording the final row. Time samples come from detached observers and do not consume behavioral RNG.

- `summary.csv`: one final row per run, with units in column names.
- `timeseries.csv`: all 7,808 rows, including zeros and unsuccessful runs.
- `aggregate.csv`: per-layout/treatment means, sample standard deviations, ranges and observed counts. Unseen first discoveries are censored, never treated as negative discovery durations.
- `paired_differences.csv`: same-seed differences against the no-trails/no-learned-memory baseline. Positive/negative are numerical signs, not automatic better/worse judgments.

The memory toggle controls learned inter-trip routes. A bounded current-trip homing trace remains enabled in all treatments. Coverage counts physical cell visits; route reuse includes both directions, return steps and exploration loops; delivery success divides completed deliveries by all started trips, including unfinished ones. Sparse trail quantities are abstract signal units. Full definitions and configuration are in [document 27](../../docs/27_S2_Implementation_Decisions.md).

Interpret the comparisons together: trails need actual loaded return paths before they exist; memory requires a successful prior collection. First discovery is therefore identical across the four treatments for a given seed/layout. Information only spreads locally after discovery. Signal following alone need not improve delivery, and no shortest-path or statistical-significance claim is made. See [S2_RESULTS.md](../../S2_RESULTS.md) for measured findings, limitations and build provenance. Cross-platform floating-point bit identity is outside the determinism contract.
