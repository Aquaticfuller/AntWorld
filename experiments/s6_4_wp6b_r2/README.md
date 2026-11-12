# WP-6B-R2 experiment archive

The [prospective protocol](../../research/s6_4_wp6b_r2/FROZEN_R2_PROTOCOL.md) identifies the protected inputs and gates. `v1_tracks` and `r1_tracks` contain independent compartment reconstructions from every prior archive. They are separate from new simulations. The v1 and R1 replay receipts compare six native outputs with the reviewed archives. Each H1, H2, combined and water archive contains complete canonical facts and identity, not just success records. An archived final frame needs its corresponding canonical prefix to restore.

The case roster additionally keeps both full, inherited wider spacing families for every model. These include the five archived v1 successes and the matched failures, with all 24 identities and unchanged input bytes. The eight combined-model seed-1 early-worker performance cases have independent uninterrupted references. Supplemental cases do not contribute to the ordinary founding gates.

## Reproduction

Build `antworld_s6_4_wp6b` in Release using the compiler in the run manifest. Use fresh output directories and the same working tree for all assays. R2 version 3 uses mask 1 for H1, mask 2 for H2 and mask 3 for both. The app's positional options after the mode are the existing R1 window, repeat parts per million and processor affinity, followed by the R2 mask. Zero affinity leaves the operating system's scheduling in place. To replay an extracted paired candidate case with actual midpoint save/reopen, use `antworld_s6_4_wp6b parameters.txt <empty-output-dir> durable 172800000 750000 0 <mask>` and compare the initial, final and canonical facts SHA-256 values in its receipt.

```powershell
cmake -S cpp -B build/r2-release -DCMAKE_BUILD_TYPE=Release
cmake --build build/r2-release --config Release
ctest --test-dir build/r2-release -C Release --output-on-failure

python tools/trace_s6_4_wp6b_r2.py experiments/s6_4_wp6b/formal out/r2/v1_tracks
python tools/trace_s6_4_wp6b_r2.py experiments/s6_4_wp6b_r1/formal out/r2/r1_tracks
foreach ($arm in @('v1', 'r1', 'h1', 'h2', 'both', 'water-r1', 'water-both')) {
    python tools/run_s6_4_wp6b_r2.py --model $arm --binary $r2App --compiler $r2Compiler --out "out/r2/$arm" --scratch out/r2-scratch
    python tools/verify_s6_4_wp6b_r2.py "out/r2/$arm" --out "out/r2/$arm-analysis"
    if ($arm -in @('h1', 'h2', 'both', 'water-r1', 'water-both')) {
        python tools/trace_s6_4_wp6b_r2.py "out/r2/$arm" "out/r2/$arm-tracks"
    }
}
python tools/check_s6_4_wp6b_r2_recovery.py --archive out/r2 --binary $r2App --scratch out/r2-restore --out out/r2/recovery-saved.json --midpoints out/r2/midpoints
python tools/verify_s6_4_wp6b_r2.py out/r2 --ci
python tools/summarize_s6_4_wp6b_r2.py out/r2 out/r2/comparison
```

`$r2App` is the Release executable, and `$r2Compiler` is its compiler path. The trace reads each relevant raw member and rebuilds individual energy, material and water using committed events and declared rates. The archive verifier additionally checks all member hashes, event order, budgets and the original simulation gates. `cues.csv.gz` links the committed cue and standard care phases to the actual paid ration where one exists. Empty fields retain unavailable endpoints. `water_adults.csv` retains actual adult exposure, deaths, absorbed water and motion. A right-censored worker with less than seven days of follow-up cannot establish seven-day survival.

## Windows performance

The same instruments use the 30 original CPU channels. If the live HWiNFO layout differs, capture and commit a new mapping only after checking the original channel labels and indices. Preserve the new and old mappings and the attempted admission. A changed used channel requires independent review. Full original localized sensor files stay local. Public files contain the mapped CPU measurements and source hashes. Run the collectors serially on a quiet admitted host. All schedules and binary identities are written before timing.

```powershell
python tools/run_s6_4_wp6b_r2_performance.py native --prepare --out out/r2-native --build $r2Release --compiler $r2Compiler --confirmation experiments/s6_3_3_1/performance/instrument_v2_confirmation/receipt.json
python tools/verify_s6_3_3_1_reserve_workload.py --binary $r2Birth --scratch out/r2-birth-identity --receipt out/r2-native/reserve_identity_receipt.json
python tools/run_s6_4_wp6b_r2_performance.py native --out out/r2-native --build $r2Release --archive $r2NativePrivate --hwinfo-csv $r2Sensors

python tools/run_s6_4_wp6b_r2_performance.py protected --prepare --out out/r2-observer --build $r2Release --compiler $r2Compiler --binary $r2Observer
python tools/run_s6_4_wp6b_r2_performance.py protected --out out/r2-observer --binary $r2Observer --archive $r2ObserverPrivate --hwinfo-csv $r2Sensors

python tools/run_s6_4_wp6b_r2_performance.py application --prepare --out out/r2-application --build $r2Release --compiler $r2Compiler --binary $r2App
python tools/run_s6_4_wp6b_r2_performance.py application --out out/r2-application --binary $r2App --archive $r2ApplicationPrivate --hwinfo-csv $r2Sensors

python tools/archive_s6_4_rm02_performance.py out/r2-native out/r2-native-public
python tools/archive_s6_4_rm02_performance.py out/r2-observer out/r2-observer-public
python tools/archive_s6_4_rm02_performance.py out/r2-application out/r2-application-public
python tools/analyze_s6_3_3_1_performance.py --raw out/r2-native-public --out out/r2-native-analysis
python tools/s6_4_wp6b_r2_protected_observer.py --analyze out/r2-observer-public out/r2-observer-analysis.json
python tools/profile_s6_4_wp6b_r2.py --out out/r2-application-public --analysis out/r2-application-analysis
python tools/summarize_s6_4_wp6b_r1_costs.py --raw out/r2-application-public --v1 experiments/s6_4_wp6b/formal --r1 experiments/s6_4_wp6b_r1/formal --both out/r2/both --out out/r2-application-costs
```

`$r2Release` is the Release build, `$r2Birth` is `antworld_s6_3_1_birth_benchmark.exe`, and `$r2Observer` is `antworld_s6_4_wp5_benchmark.exe`. The three private archive paths must be fresh. `$r2Sensors` is the live HWiNFO CSV. A failed admission, partial timing session or failed gate remains part of the record. The three historical F1 failures and the 693 ms observation remain in the [R1 performance report](../../research/s6_4_wp6b_r1/R1_PERFORMANCE_QUALIFICATION.md).
