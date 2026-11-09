# S6.2 evidence and reproduction

All biological inputs are **ENGINEERING_FIXTURE**. Frozen protocol: [document 39](../../docs/39_S6_2_Performance_and_Scarcity_Protocol.md), committed as `3f6d1a9` before measurements. Observer/telemetry details and retained acquisition corrections: [document 40](../../docs/40_S6_2_Measurement_and_Observer_Implementation.md). Conclusions: [S6_2_RESULTS.md](../../S6_2_RESULTS.md). The complete earlier archives remain unchanged.

## Evidence map

| Path | Meaning |
|---|---|
| `performance/primary/session1..3` | 288 measured rows and 24 labeled warmups; exact balanced schedules; setup/advance/encode/restore timers and CPU cycles; Windows telemetry; HWiNFO CPU subset; native completion receipts |
| `performance/smoke` | Four 128-worker policy/layout parity cases |
| `performance/overhead` | 32 rows with the Python/PDH sampler disabled; HWiNFO still running |
| `performance/exhaustive` | 16 balanced dense 2,048-worker bounded/exhaustive comparisons |
| `performance/attribution` | 32 instrumented cases; inclusive/exclusive nanoseconds and calls for every category in each phase |
| `nutrition/summary.csv` | 192 full ordered replays, all declared seeds/densities/supplies and two policies, exact state/trace parity with S6.1 |
| `nutrition/gifts.csv` | Every actual gift resolution, recipient/donor states immediately before resolution, real outcome and transferred protein |
| `nutrition/decisions.csv` | Every nursing/rest decision; actual sampled/reachable compatible recipients; cancellation status; no observer information enters ants |
| `nutrition/individuals.csv` | Every identity, seeded stage, actual gift totals, retained crop/tissue, provisioning/tissue/development/death times; -1 means not reached by 180 s |
| `choice/choices.csv` | 262,144 inclusion/choice rows: 64 seeds, four ID/mirror permutations, 64 actual gifts, 16 recipients |
| `analysis/` | Deterministically regenerated quantiles, hierarchical/paired confidence intervals, allocations, failure classes, worker protein transitions, archived four-arm controls and hardware context |
| `figures/` | Eight PNG/SVG figures, all declared runs retained; scientific plots, not simulated trajectories invented by an illustrator |
| `provenance.json`, `verification.json`, `executed_tests.csv` | Actual compiler/binary/source hashes, unchanged Core trees, real local test executions and observed CI results |

Each raw directory has an archive manifest; performance roots additionally hash every archived file. Localized HWiNFO prefix snapshots remain local/untracked. Their raw-byte hashes, original column-label hashes and source line numbers are retained. `hwinfo.csv` and `hwinfo_columns.json` are the **superseded v1 frequency-label translation**, retained for audit. Use **`hwinfo_corrected.csv` and `hwinfo_columns_v2.json`** for analysis; the same raw prefixes are re-extracted, with temperatures/power and native timings unchanged. All complete in-window CPU samples are exported, without value-based filtering. One session-3 prefix has an incomplete trailing logger row, explicitly counted; complete samples still bracket the session. HWiNFO's approximate 2 s polling does not resolve every subsecond phase.

## Metric definitions

- Wall quantiles use linear interpolation, with no timing outlier removal. Primary estimators exclude only the prespecified warmups. A balanced block ratio is mean(2,048 advance)/mean(512 advance). The hierarchical interval resamples three sessions and twelve blocks per session, 4,096 times, seed 6206. Report both median and geometric-mean paired estimators, plus original p50 ratios. CPU-time/cycle ratios are explanatory and do not replace wall time.
- Profile scopes are actual steady-clock durations. Inclusive values contain nested scopes; exclusive values subtract them. `advance` exclusive is residual unclassified advance work. The exact sum of all nine exclusive scopes equals inclusive advance for each measured case. Zero index maintenance in a stationary advance is genuine; setup maintenance has its own rows. Instrumented values are not performance acceptance timings.
- RSS is a process measurement after restore, with both worlds/checkpoint resident. Peak RSS is process-lifetime high water across a balanced session, not a per-world peak. Allocator retention prevents interpreting the 512/2,048 peak ratio as a memory complexity measurement.
- Protein allocation means actual gifts to the ten initially unsupplied eggs/larvae. Two initially supplied pupae are excluded. After emergence an identity may ingest its own protein; this is reconciled with archived intake facts but is not counted as larval allocation. `threshold_ms` is retained crop+tissue reaching 100 ug; `tissue_threshold_ms` is actual absorbed tissue reaching 100 ug. Emergence requires another 60 s larval plus 30 s pupal development in this fixture. Failed/unfinished identities remain in denominators.
- `protein_hhi` is the sum of squared shares of protein gifts among the ten initially unsupplied brood. Zero total gives zero; this is a descriptive concentration measure, not an optimization objective. Partially provisioned means 1..99 ug, full means 100 ug. Fixed development thresholds and uniform recipient selection are uncalibrated.
- A sampled protein opportunity requires a Nurse holding protein, at least one physically reachable protein-demanding larva and actual candidate sampling. A miss has no such larva in the actual sample. Refill precedence, empty crop, urgent self-maintenance, no compatible local demand and canceled actions are distinguished. A canceled proposal is not a failed transfer. Failure classification uses state at the actual resolution, not a later timestamp snapshot.
- Worker protein exposure integrates each initial worker's actual crop protein times program residence (ug*s) from ordered intake/gift/program facts. It is not inferred from task-switch counts. Initial workers do not absorb protein in this model. Both the reconstructed terminal crop and total nutrition remain exact.
- Scarcity intervals use all sixteen paired seeds, 4,096 bootstrap resamples, seed 6206. Equal-choice intervals cluster 64 decisions within each seed and report each permutation separately; mirrors are not extra independent seeds. Rank-wise intervals are descriptive and not a multiple-testing proof of perfect uniformity.

## Reproduce local correctness

Use a clean checkout of this branch. The repository's pinned bootstrap installs LLVM-MinGW 20261104 (Clang 23.1.5), CMake 3.31.10 and Ninja 1.13.2. SQLite 3.54.1 remains pinned by the existing CMake download/hash contract. Python analysis uses its standard library; plots use the existing pinned `tools/s2_1_plot_requirements.txt` environment. In PowerShell:

```powershell
./tools/bootstrap_windows.ps1
./tools/build_windows.ps1 -Configuration Debug -BuildDirectory build/s6_2-debug
./tools/build_windows.ps1 -Configuration Release -BuildDirectory build/s6_2-release
$env:ASAN_OPTIONS = 'detect_leaks=0:halt_on_error=1'
$env:UBSAN_OPTIONS = 'halt_on_error=1:print_stacktrace=1'
./tools/build_windows.ps1 -Configuration Debug -BuildDirectory build/s6_2-sanitized -Sanitizers
python tools/ci_verify.py
```

Local execution used the same configuration with the cached SQLite archive passed as `-DANTWORLD_SQLITE_ARCHIVE=.tools/sqlite/sqlite-amalgamation-3540100.zip` resolved to an absolute path, `--parallel 2`, and separate configure/build/CTest commands. Clean-source Release exports committed `cpp` and `scenarios` using `git archive 95bbc5a cpp scenarios`; core-only adds `-DANTWORLD_STORAGE=OFF`. The test names/results and exact counts are in `executed_tests.csv`. Windows LeakSanitizer is unsupported: the first rejected invocation is retained in `windows_sanitizer_unsupported_leaks.log`; Linux CI keeps `detect_leaks=1`.

## Reproduce balanced performance

Do not overlap timing with builds, tests or ecological runs. Build both the normal and separate `-DANTWORLD_PROFILE=ON` Release binaries **before** timing. Start the existing HWiNFO sensor CSV logger and set `HWiNFO_CSV` to its actual file. The checked map is specific to the captured 472-column layout; inspect labels and freeze a new map for another layout rather than silently reuse indices. Shared memory is optional; this run used CSV. On the recorded host the selector chooses logical CPU 0 and excludes its physical core from the collector. No power policy is changed. Use new output directories to preserve every run:

```powershell
$normal = 'build/s6_2-release/antworld_s6_2_benchmark.exe'
python tools/run_s6_2_performance.py --binary $normal --out out/reproduce-smoke --mode smoke --hwinfo-csv $env:HWiNFO_CSV
python tools/run_s6_2_performance.py --binary $normal --out out/reproduce-primary --mode primary --hwinfo-csv $env:HWiNFO_CSV
python tools/run_s6_2_performance.py --binary $normal --out out/reproduce-overhead --mode overhead --hwinfo-csv $env:HWiNFO_CSV
python tools/run_s6_2_performance.py --binary $normal --out out/reproduce-exhaustive --mode exhaustive --hwinfo-csv $env:HWiNFO_CSV
python tools/run_s6_2_performance.py --binary build/s6_2-profile/antworld_s6_2_benchmark.exe --out out/reproduce-attribution --mode attribution --hwinfo-csv $env:HWiNFO_CSV
foreach ($mode in @('smoke','primary','overhead','exhaustive','attribution')) {
    python tools/extract_s6_2_hwinfo.py "out/reproduce-$mode" experiments/s6_2/hwinfo_columns_v2.json --stem hwinfo_corrected
}
python tools/analyze_s6_2_performance.py --check
```

The last command audits the committed reference evidence. To compare a new run, keep it separate and inspect its CSVs/receipts; the reference audit intentionally verifies the frozen source, host affinity and exact baseline counts. Primary measured executable/source is `cc9004e`; its Core and benchmark source are unchanged in the delivered branch. Profiles never replace primary latency. The first session includes labeled warmups; three measured sessions and all control counts are fixed in document 39. No new performance run was selected after seeing a slow result.

## Reproduce nutrition and identity evidence

```powershell
./build/s6_2-release/antworld_s6_2_nutrition.exe out/reproduce-nutrition 16 1
./build/s6_2-release/antworld_s6_2_choice.exe out/reproduce-choice 64
python tools/analyze_s6_2_nutrition.py --pilot out/reproduce-nutrition
python tools/analyze_s6_2_nutrition.py --check
python tools/analyze_s6_1.py --check
python tools/analyze_s6_1_scarcity.py --check
python tools/plot_s6_2.py
```

Actual full execution partitioned the fixed seeds into four disjoint intervals, with native arguments `4 1`, `4 5`, `4 9`, `4 13`, after all performance runs ended. `tools/merge_s6_2_nutrition.py` verifies exactly the 192-case grid and preserves every row; `nutrition/configuration.json` hashes each source part and the observer executable. `--pilot` accepts a complete subset of seeds (all density/supply/arm cells) and independently checks the original S6.1 hashes, real transfers, stages, thresholds and restoration. Ordinary and accelerated/checkpoint-restored runs are also compared byte-for-byte inside the native observer every 30 s.

The 256 equal-demand cases use the frozen document-40 assay; the 1 ug per-gift limit is an assay-only eligibility control, never a new ecological default. `choice/summary.csv` has the exact final hashes; `provenance.json` records its binary and full configuration. CTest covers small repeated observer/choice continuations in Debug/Release/sanitizers; Linux Release CI additionally runs all twelve first-seed nutrition cases and all 256 choice cases.

S6.2 stops for review. SD-04 scarcity/redistribution, SD-06 functional nesting feedback, SD-07 rest/activity calibration, SD-01/02 recruitment and TD-03/06 history budgets remain open. No S7 work is included.
