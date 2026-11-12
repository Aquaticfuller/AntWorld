# WP-6B-R1 experiment archive

The [prospective protocol](../../research/s6_4_wp6b_r1/FROZEN_R1_PROTOCOL.md) is the controlling record. The original [F1 v1 archive](../s6_4_wp6b) remains the paired reference. All numerical inputs are engineering fixtures or declared population-specific development anchors as in that archive. `baseline_paths` adds read-only reconstruction from the original facts and does not alter the original archives.

| Directory | Contents |
|---|---|
| `baseline_paths` | Per-wake in-contact identities, per-ration recipient and bout lineage, larval histories, and input/output hashes for F1 v1 |
| `v1_replay` | Repeated v1 runs on the candidate executable with six exact file hashes per original ordinary and matched wider case |
| `formal` | Candidate inputs, initial checkpoints, final frames, full canonical facts, daily world and individual cuts, attempts, timing and per-file SHA-256 |
| `candidate_paths` | Repeat-aware per-wake, recipient and post-feeding uptake paths reconstructed from the candidate archive |
| `analysis` | Independent ledger checks, phase occupancy, exact-count timing, unchanged robustness gates and full archive receipt |
| `ci_archive` | Fixed representative care-on and care-off archives for the independent CI check |
| `comparison` | World-paired changes, allocation and timing summaries, sensitivity arms and profile/seed bootstrap intervals |
| `limits` | Hatch energy constraint, first-dose timing, daily counts and adult competing outcomes |
| `performance` | Frozen schedules, all admissions, timed rows and analyses for native, protected observer and application workloads |
| `tests` | Local test logs, the retained timeout and retry, build identity and cross-platform CI receipts |

## Reproduction

Run from the repository root. Choose paths on the local machine for the build, compiler and fresh output folders. Build Release without sanitizers or internal phase instrumentation for measured workloads.

```powershell
cmake -S cpp -B build/r1-release -DCMAKE_BUILD_TYPE=Release
cmake --build build/r1-release --config Release
ctest --test-dir build/r1-release -C Release --output-on-failure
python tools/freeze_s6_4_wp6b.py
python tools/diagnose_s6_4_wp6b_r1.py experiments/s6_4_wp6b/formal out/r1-base-paths

$r1Binary = '<Release path to antworld_s6_4_wp6b>'
$r1Compiler = '<compiler used for that Release build>'
python tools/run_s6_4_wp6b_r1.py --model v1 --binary $r1Binary --compiler $r1Compiler --out out/r1-v1-replay --scratch out/r1-scratch
python tools/run_s6_4_wp6b_r1.py --model r1 --binary $r1Binary --compiler $r1Compiler --out out/r1-formal --scratch out/r1-scratch
python tools/verify_s6_4_wp6b_r1.py out/r1-v1-replay
python tools/verify_s6_4_wp6b_r1.py out/r1-formal --out out/r1-analysis
python tools/diagnose_s6_4_wp6b_r1.py out/r1-formal out/r1-candidate-paths
python tools/summarize_s6_4_wp6b_r1.py --v1 out/r1-base-paths --r1 out/r1-candidate-paths --candidate out/r1-analysis --out out/r1-comparison
python tools/diagnose_s6_4_wp6b_r1_limits.py experiments/s6_4_wp6b_r1 out/r1-limits
```

The formal tool compares native v1 output against the archived original bytes. Timing and machine receipts naturally differ on replay. Each candidate input preserves original world identity and seed and adds explicit R1 options in its `case.json`. The first entry of `care_memory` is the window in milliseconds. The second is the repeat probability in parts per million. A replay of one extracted case uses `antworld_s6_4_wp6b parameters.txt <empty-output-dir> observed <window-ms> <repeat-ppm>`. The observer can be disabled with the `unobserved` mode or verified across a durable midpoint with `durable`.

The approved Windows native and protected observer samplers require the mapped HWiNFO CSV, compatible instrument-v2 confirmation, pinned binaries, and an admitted host. Start with fresh output paths. Save the full private sensor capture locally and publish only the mapped CPU sensor rows, hashes and aggregate process-independent observations. Run the three collectors sequentially on a single host.

```powershell
python tools/run_s6_3_3_1_performance.py --prepare --out out/r1-core --build $r1Release --compiler $r1Compiler --confirmation experiments/s6_3_3_1/performance/instrument_v2_confirmation/receipt.json
python tools/verify_s6_3_3_1_reserve_workload.py --binary $r1BirthBinary --scratch out/r1-birth-identity --receipt out/r1-core/reserve_identity_receipt.json
python tools/run_s6_3_3_1_performance.py --out out/r1-core --build $r1Release --archive $r1PrivateCore --hwinfo-csv $r1SensorFile
python tools/run_s6_4_wp6b_r1_protected_observer.py --prepare --out out/r1-observer --build $r1Release --compiler $r1Compiler --binary $r1ObserverBinary
python tools/run_s6_4_wp6b_r1_protected_observer.py --out out/r1-observer --binary $r1ObserverBinary --archive $r1PrivateObserver --hwinfo-csv $r1SensorFile
python tools/profile_s6_4_wp6b_r1.py --prepare --out out/r1-application --build $r1Release --compiler $r1Compiler --binary $r1Binary
python tools/profile_s6_4_wp6b_r1.py --out out/r1-application --binary $r1Binary --archive $r1PrivateApplication --hwinfo-csv $r1SensorFile

python tools/analyze_s6_3_3_1_performance.py --raw out/r1-core --out out/r1-core-analysis
python tools/analyze_s6_4_wp6b_r1_protected_observer.py out/r1-observer out/r1-observer-analysis.json
python tools/profile_s6_4_wp6b_r1.py --out out/r1-application --analysis out/r1-application-analysis
python tools/summarize_s6_4_wp6b_r1_costs.py --raw out/r1-application --v1 experiments/s6_4_wp6b/formal --r1 out/r1-formal --out out/r1-application-costs
```

`$r1Release` is the Release build directory. `$r1BirthBinary` is `antworld_s6_3_1_birth_benchmark.exe`, `$r1ObserverBinary` is `antworld_s6_4_wp5_benchmark.exe`, and `$r1SensorFile` is the ongoing HWiNFO CSV. `$r1PrivateCore`, `$r1PrivateObserver` and `$r1PrivateApplication` are separate fresh scratch directories. Use `tools/archive_s6_4_rm02_performance.py` to prepare public timing receipts with process inventories removed. The original 693 ms result remains in the [v1 application profiling archive](../s6_4_wp6b/profiling).
