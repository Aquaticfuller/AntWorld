# RM-02 engineering reproduction

Run at the benchmark instrumentation revision named by the batch freeze. The immutable starting point is Phase 0 `6f6a69f45b0fff0ba3227039de36158b0994cbc4`. For an exact controlled requalification, use the approved compiler, host topology, HWiNFO mapping and preserved Release binaries. The executable and schedule digests in the timing freeze identify the measured workload. An unadmitted check, a different binary or a different host constitutes a separate measurement.

## Local and independent regression

The Ninja build directories use Clang 23.1.5, CMake 3.31.10 and the existing pinned SQLite and zlib archives. Set `ANTWORLD_STORAGE=ON` for the host reader. The sanitizer build uses Debug with `ANTWORLD_SANITIZERS=ON`. On Windows, put the compiler runtime on PATH and set `ASAN_OPTIONS=detect_leaks=0:halt_on_error=1` and `UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1`. The existing Linux CI uses ASan with leak detection enabled.

```powershell
foreach ($mode in 'release','debug','sanitizer') {
    $build = "build/s6_3_4-$mode"
    cmake --build $build --parallel 4
    ctest --test-dir $build --parallel 4 --output-on-failure
}
build/s6_3_4-release/antworld_s6_4_rm02 out/rm02-depot ecology depot 32 1
python tools/verify_s6_4_rm02_sidecar.py out/rm02-depot
python tools/verify_s6_4_rm01_results.py experiments/s6_4_rm01/assay --observer experiments/s6_4_rm01/observer
```

The independent reader checks the raw and sparse codec, manifest, SHA-256 chain, event order, scope, crop flow and authoritative checkpoint anchor. Each authoritative comparison uses the complete checkpoint encoding and preserves the RNG, pending schedule and canonical history. Cross-platform Core CI runs the CTests in Windows and Ubuntu Debug and Release and Ubuntu ASan/UBSan. The Ubuntu Release workflow also exercises the independent sidecar decoder on an actual long-duration case.

## Frozen performance batches

Set `$compiler` to the approved compiler executable, `$build` to the Release build, `$legacyBuild` to the preserved RM-01-R1 Release executables and CMake cache, and `$sensorCsv` to the active HWiNFO CSV. Prepare creates a fresh frozen directory and records executable and schedule identities. Run the two batches sequentially on the host after independent build activity has ceased.

```powershell
$confirm = 'experiments/s6_3_3_1/performance/instrument_v2_confirmation/receipt.json'
$old = 'out/rm02-legacy-timing'
$new = 'out/rm02-observer-timing'
$native = "$build/antworld_s6_4_rm02_benchmark.exe"
python tools/run_s6_3_3_1_performance.py --prepare --out $old --build $legacyBuild --compiler $compiler --confirmation $confirm
python tools/verify_s6_3_3_1_reserve_workload.py --binary "$legacyBuild/antworld_s6_3_1_birth_benchmark.exe" --scratch out/rm02-birth-identity --receipt "$old/reserve_identity_receipt.json"
python tools/run_s6_4_rm02_performance.py --prepare --out $new --build $build --binary $native --compiler $compiler
python tools/run_s6_3_3_1_performance.py --out $old --build $legacyBuild --archive out/rm02-private-legacy --hwinfo-csv $sensorCsv
python tools/run_s6_4_rm02_performance.py --out $new --binary $native --archive out/rm02-private-observer --hwinfo-csv $sensorCsv
python tools/analyze_s6_3_3_1_performance.py --raw $old --out out/rm02-legacy-analysis
python tools/analyze_s6_4_rm02_performance.py $new out/rm02-observer-analysis.json
```

Use `tools/archive_s6_4_rm02_performance.py SOURCE TARGET` to export raw schedules, timing rows and the parsed telemetry to a new evidence directory. Its manifest preserves the original byte digests for receipts with unrelated process-name lists removed. Original HWiNFO captures stay local. The English sensor extraction retains every mapped in-window sample and its source line with the original archive digest. The foreground budget is tested against capture plus synchronous submission, with final flush measured separately. This includes SQLite stalls on the owner thread.

## Regression evidence boundaries

The contact and reserve-birth pass gates apply to the pooled advance P50 growth of their own admitted workloads. The observer experiment applies its separate paired wall-time, foreground and RSS gates to the same work in both arms. Trial builds, admission failures, startup, checkpoint audits, read-only reproduction and the dense observation coverage traces do not enter formal timing ratios. An existing performance result on the protected branch cannot supply a missing sample here. [Frozen protocol](FROZEN_ENGINEERING_PROTOCOL.md) [RM-01-R1 benchmark identity](../s6_4_rm01/RM01_R1_PERFORMANCE_PROTOCOL.md)
