# RM-01-R1 evidence and reproduction

The [frozen R1 protocol](../../research/s6_4_rm01/RM01_R1_PERFORMANCE_PROTOCOL.md) defines the eligible Windows host, workload identities, admissions, estimators and stop rules. The [qualification report](../../research/s6_4_rm01/RM01_R1_PERFORMANCE_QUALIFICATION.md) records the actual outcome. The [original RM-01 evidence](../s6_4_rm01/README.md) remains at its reviewed paths.

The [payload digest index](payload_sha256.json) covers the freeze, schedules, workload identity, initial preflight, six session archives and analysis. The preflight records stale telemetry before admission. The later [collection receipt](collection_receipt.json) records the completed batch and identifies the local-only process metadata. Each session directory contains the complete admission and timed records, phase intervals, compressed native telemetry and mapped HWiNFO observations. The six schedules include warm-ups and diagnostics and match the 504 actual timing rows.

## Verify the accepted evidence

```powershell
python tools/verify_s6_4_rm01_results.py experiments/s6_4_rm01/assay --observer experiments/s6_4_rm01/observer
python tools/analyze_s6_3_3_1_performance.py --raw experiments/s6_4_rm01/controlled --out experiments/s6_4_rm01/controlled/analysis --check
python tools/analyze_s6_3_3_1_performance.py --raw experiments/s6_4_rm01_r1/controlled --out experiments/s6_4_rm01_r1/analysis --check
```

## Reproduce the controlled batch

From the repository root, use a new output directory and the exact hashed Release executables in the selected build directory. Set `$Compiler` to the matching Clang executable and `$HwinfoCsv` to the live HWiNFO CSV with the approved mapping. The second command checks the protected birth workload before admission. Its incidental wall times stay local.

```powershell
$Rm01R1 = 'out/rm01-r1-reproduction'
python tools/run_s6_3_3_1_performance.py --prepare --out "$Rm01R1/controlled" --build build/s6_3_4-release --compiler $Compiler --confirmation experiments/s6_3_3_1/performance/instrument_v2_confirmation/receipt.json
python tools/verify_s6_3_3_1_reserve_workload.py --binary build/s6_3_4-release/antworld_s6_3_1_birth_benchmark.exe --scratch "$Rm01R1/reserve-identity" --receipt "$Rm01R1/controlled/reserve_identity_receipt.json"
python tools/run_s6_3_3_1_performance.py --out "$Rm01R1/controlled" --build build/s6_3_4-release --archive "$Rm01R1/sensors" --hwinfo-csv $HwinfoCsv
python tools/analyze_s6_3_3_1_performance.py --raw "$Rm01R1/controlled" --out "$Rm01R1/analysis"
```

Use native host access for the collection command. Verify that the R1 freeze matches the accepted freeze for every field except the source commit and creation timestamp. The run must use the original admission and telemetry coverage rules. Run the analyzer after collection ends. Keep the localized HWiNFO source snapshots and host process inventories in local storage. Keep all admission and timing observations, including any incomplete sessions.
