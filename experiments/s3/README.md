# S3 reproducible nutrition and lifecycle evidence

All biological numbers are ENGINEERING_FIXTURE. Protocol: docs/31_S3_Implementation_and_Validation.md, frozen at abe846e before implementation. Approved parent: 18b0c9f5d5b5d60504a48ac193dce53c59f001d0. No S2/S2.1/S2.2 report or raw file is replaced.

## Contents and definitions

- raw/summary.csv and root S3_EXPERIMENTS.csv: the same 1,536 run-level records.
- raw/individuals.csv: 5,376 original individual records, including non-emergers. Stable IDs identify the same ant across stages.
- raw/configuration.json: compiled parameters, units, initial conditions and seed count.
- summary.csv, paired.csv, sensitivity.csv: 64-seed aggregates and 95% percentile bootstrap intervals (4096 resamples, seed 3003). Seed is the cluster; four brood are not independent replicates.
- input_hashes.json: SHA-256 of raw UTF-8 with normalized LF newlines.
- figures/: exportable PNG/SVG plots.
- performance/: S3 plus retained S0/S1/S2 performance fixtures and sampled process memory. Timings are observations, not performance guarantees.
- reproduction.json: independently rerun raw-data comparison from a clean committed source export.

The matrix is 64 seeds times 24 configurations. N1/development: two initial brood stages times two protein conditions times three pulse periods (768 runs). N2: three recipient capacities times supplied/empty donors times two submission orders (768 runs). Every run also repeats with irregular AdvanceTo partitions and checks an exact checkpoint match.

N1 starts four larvae; development starts four eggs. Each has two contacting nurses. The 180-second horizon includes non-emergers: restricted mean emergence time assigns them the full horizon. N2 observes two 200 ug requests at 500 ms; its seeded adult recipients are not classified as newly emerged. Zero protein is replaced with other mass to preserve initial mass. Initial body reserves differ by fixed seeded draws shared across treatments. Source, crop, body water, retained protein, oxidation and water loss remain separately accounted.

Positive N1 results verify the declared protein gate, not a measured Lasius niger growth rate. Development seed 43 retains one larva at 80 ug tissue protein while three adults retain a combined 420 ug crop protein. No seed or negative outcome is removed and no parameter is retuned after this finding.

## Reproduction commands

```powershell
./tools/build_windows.ps1 -Configuration Release
./build/release/antworld_s3_experiment.exe out/s3-reproduction 64
python tools/verify_s3_reproduction.py out/s3-reproduction --source-commit <tested-commit> --report out/s3-reproduction.json
python tools/analyze_s3.py --check
./tools/benchmark_s3_windows.ps1 -OutputDirectory out/s3-performance
```

Use an actual tested commit hash for `<tested-commit>`. On Linux, use CMake/CTest as in the root README and omit `.exe`. The experiment runner has no Python or network dependency.

```sh
python -m pip install --target .tools/s3-python -r tools/s2_1_plot_requirements.txt
python tools/plot_s3.py --packages .tools/s3-python
```

Plot dependencies reuse the existing fully pinned package list. Analysis/audit uses only Python's standard library. `python tools/analyze_s3.py` regenerates the derived CSVs and root mirror from the committed raw files; `--check` verifies them without writing. Changing pulse period changes the declared absorption model; changing host AdvanceTo boundaries does not.
