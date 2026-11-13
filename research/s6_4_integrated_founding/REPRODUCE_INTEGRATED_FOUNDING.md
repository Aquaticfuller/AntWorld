# Reproduce and inspect the integrated founding experiments

Use a clean checkout of the independent integration branch. The reference is R2 `f1d1fe238e95a84f6b2894e2c4143836ef35d03d`. The prerequisites and network-pinned build dependencies are the existing [Core build instructions](../../README.md) and [Core CI](../../.github/workflows/ci.yml). Run with Python 3.12 or later, CMake and a C++20 compiler. Use `.exe` on Windows. Give each collection and audit a new output directory. The commands below use PowerShell for Windows examples and unmodified relative paths under the repository.

```powershell
cmake -S cpp -B build/founding-release -DCMAKE_BUILD_TYPE=Release
cmake --build build/founding-release --parallel 4
ctest --test-dir build/founding-release --output-on-failure
$bin = 'build/founding-release/antworld_s6_4_wp6b.exe'
$compiler = 'clang++'
python tools/run_integrated_founding.py --binary $bin --compiler (Get-Command $compiler).Source --model resupply --matrix nominal --out out/repro/resupply-nominal --scratch out/repro/work
python tools/analyze_integrated_founding.py out/repro/resupply-nominal out/repro/analysis/analysis-resupply-nominal
python tools/verify_integrated_founding_replay.py $bin out/repro/exact --model r2 --model diet --model uptake --model resupply
```

In that command substitute the actual compiler path from `CMAKE_CXX_COMPILER` when it differs. Run identical commands with `--matrix factorial` and `--matrix closed` for the frozen supplied corners and the original closed-stock cases. The four work environments in `factorial` and seven in `nominal` are determined by the freeze. The `closed` matrix admits no case filter for a formal qualification. Use `--case` for individual raw archive diagnostics and declare the resulting subset. To resume a prior model on its original executable, supply `--source-receipt` with that executable's recorded nominal run and use the correct `--model`. The runner validates the binary hash, C++ tree and compatible switches.

| Matrix | Options |
|---|---|
| Nominal, 84 cases per model | `r2`, `provision`, `sugar`, `both`, `nest`, `eggs`, `diet`, `uptake`, `resupply` |
| Nominal yield sensitivities, 12 cases per model | `low-yield`, `high-yield`, `diet-low`, `diet-high`, `uptake-low`, `uptake-high`, `resupply-low`, `resupply-high` |
| Factorial, 192 cases per model | `r2`, `both`, `diet`, `uptake`, `resupply` |
| Closed original WP-6A ordinary and additional cases, 960 per model | `diet`, `uptake`, `resupply`; use the original R2 archives as the same-input reference |

```powershell
python tools/compare_integrated_founding.py out/repro/analysis out/repro/comparison --pair r2:provision --pair r2:sugar --pair r2:both --pair both:nest --pair both:eggs --pair both:diet --pair diet:uptake --pair uptake:resupply
python tools/package_integrated_founding_archives.py out/repro out/repro/public-receipts --audits out/repro/analysis
```

`facts.bin` contains length-prefixed canonical events. `initial.chk` and `final.frame` retain exact authority. `cuts.csv`, `individuals.csv`, `timings.csv` and the application receipt accompany each world. Analyses preserve every failed, dead, stalled or censored trajectory and zero ingredient. The archive package checks the SHA-256 of each full ZIP and emits each world's input and output digests. Selected archives retain the original member bytes and case names. Outer ZIP byte hashes of independent reruns can differ because ZIP metadata and performance receipts differ. Canonical authority is compared via the actual member digests and matching world IDs. SQLite evidence includes a database and its corresponding WAL when present. Keep them together when reopening. The archived durability receipt reports both file digests and the byte comparison against a continuous run.

To regenerate the complete per-batch analysis from all full archives in `out/repro`, use the batch driver. Existing verified tables can be passed as `--existing-audits` to reuse them. Omit this argument to recompute every batch from canonical events and cut snapshots. The publication step emits the smaller per-world analysis and hash index. The public checker reconciles this analysis against original case receipts and opens all sixteen canonical witnesses. Git contains these verification inputs. The full 391 ZIP archive files are retained separately on the experiment host.

```powershell
python tools/run_integrated_founding_audits.py out/repro out/repro/analysis --publish out/repro/published-analysis
python tools/verify_integrated_founding_public.py experiments/s6_4_integrated_founding/raw_index --analysis experiments/s6_4_integrated_founding/analysis
```

## Controlled Windows qualification

Use the original [native instrument](../../docs/55_S6_3_3_1_Performance_Instrument_Protocol.md), [reserve workload correction](../../docs/57_S6_3_3_1_Reserve_Birth_Benchmark_Correction.md) and [integrated performance protocol](INTEGRATED_PERFORMANCE_PROTOCOL.md). The following example assumes the previously approved host topology and the exact current HWiNFO append layout. Set `$hw` to an available local CSV. Each preparation freezes the actual source and executable SHA-256 before timing.

```powershell
$build = 'build/founding-release'
$confirmation = 'experiments/s6_3_3_1/performance/instrument_v2_confirmation/receipt.json'
$cxx = (Get-Command clang++).Source
python tools/verify_s6_3_3_1_reserve_workload.py --binary "$build/antworld_s6_3_1_birth_benchmark.exe" --scratch out/reserve-work --receipt out/reserve-receipt.json
python tools/run_s6_4_wp6b_r2_performance.py native --append-layout --hwinfo-csv $hw --prepare --kind contacts --out out/perf-contacts --build $build --compiler $cxx --confirmation $confirmation
python tools/run_s6_4_wp6b_r2_performance.py native --append-layout --hwinfo-csv $hw --kind contacts --out out/perf-contacts --build $build --confirmation $confirmation --archive out/perf-contacts-local
python tools/analyze_s6_3_3_1_performance.py --raw out/perf-contacts --out out/perf-contacts-analysis
```

Run the same commands with `births` and a fresh path, storing the workload verification receipt as `reserve_identity_receipt.json` in that batch directory. The `protected` subcommand of the same wrapper takes `--binary "$build/antworld_s6_4_wp5_benchmark.exe"`, `--build`, `--compiler`, `--out`, `--prepare` and the same log during freeze. Omit `--prepare` and use `--archive` for the collection. First generate the public manifest with `python tools/archive_s6_4_rm02_performance.py RAW PUBLIC`, then run `python tools/s6_4_wp6b_r2_protected_observer.py --analyze PUBLIC REPORT`. The inherited and integrated F1 application workloads use `python tools/profile_integrated_founding.py inherited` or `integrated` with `--out`, `--binary`, `--build`, `--compiler`, `--hwinfo-csv` and `--prepare`. Collect with `--archive` and without `--prepare`. Analyze with the same scope, `--out RAW --analysis OUTPUT`. Use `python tools/summarize_integrated_founding_performance.py RAW PHASE_OUTPUT` to separate observed storage and capture phases from process-level tails. The private local hardware snapshots supply only the exact approved CPU channels to the public archive. Admission and sample counts distinguish valid complete results from ineligible and incomplete runs.

Recompute both public application results and their timing tails with `python tools/verify_integrated_founding_application.py experiments/s6_4_integrated_founding/performance`. This also verifies the file manifests, approved sensor columns and unchanged qualification protocol. The checker expects the measured results, including failed cells.
