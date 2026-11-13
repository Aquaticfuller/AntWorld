# Reproduce founding cohort and release qualification

Use the repository root and CPython 3.15.2 or the CI Python. Commands show PowerShell and a single-configuration native build. Add `.exe` on Windows and use the chosen compiler/runtime on `PATH`. Use fresh output locations for each invocation. Long panels and archive verification need several GiB of working storage. The public archives contain a fixed representative subset, complete attempt indexes, every reduced cohort and result table, and archive/member SHA-256. Full native case ZIPs remain on the experiment host.

```powershell
cmake -S cpp -B build/cohort-release -DCMAKE_BUILD_TYPE=Release
cmake --build build/cohort-release --parallel 4
ctest --test-dir build/cohort-release --output-on-failure
cmake -S cpp -B build/cohort-debug -DCMAKE_BUILD_TYPE=Debug
cmake --build build/cohort-debug --parallel 4
ctest --test-dir build/cohort-debug --output-on-failure
cmake -S cpp -B build/cohort-sanitized -DCMAKE_BUILD_TYPE=Debug -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ -DANTWORLD_SANITIZERS=ON
cmake --build build/cohort-sanitized --parallel 4
ctest --test-dir build/cohort-sanitized --output-on-failure
```

## Public verification

```powershell
$evidence = 'experiments/s6_4_founding_cohort_release'
$binary = 'build/cohort-release/antworld_s6_4_wp6b.exe'
$scout = 'build/cohort-release/antworld_ecological_recruitment.exe'
foreach ($panel in 'primary','hatch','extended') {
  python tools/verify_founding_cohort_release.py $panel "$evidence/$panel" "out/rebuilt-$panel" --public --packed-summary "$evidence/$panel/analysis"
}
python tools/verify_founding_cohort_release.py correction "$evidence/correction" out/rebuilt-correction --public --packed-summary "$evidence/correction/analysis" --binary $binary
python tools/summarize_founding_cohort_release.py $evidence "$evidence/decision" --check
python tools/summarize_founding_history_cost.py "$evidence/performance" "$evidence/performance/storage_diagnostics.json" --check
python tools/verify_ecological_publication.py out/rebuilt-inherited-ecology --joint-binary $binary --scout-binary $scout
python tools/verify_final_core_evidence.py out/rebuilt-frozen-b06
```

Public verification replays two fixed corrected worlds with daily observation and midpoint restore, and compares facts, frames, RNG, state and daily observations to the uninterrupted records. The archived split controls separately compare full authority with observations disabled. The independent SQLite check reconstructs and compares the canonical prefix at day 75. The complete old ecology verification includes both layouts, all seven SC-06 arms, intact historical failures and the previously accepted version 24/25 semantics. Both Release CI runners execute the native public witnesses.

## Complete collection and raw analysis

```powershell
$native = '<fresh native experiment directory>'
$scratch = '<experiment scratch directory>'
foreach ($panel in 'primary','hatch','extended','correction') {
  python tools/run_founding_cohort_release.py $panel $binary "$native/$panel" $scratch
  python tools/verify_founding_cohort_release.py $panel "$native/$panel" "$native/final-analysis-$panel"
}
python tools/publish_founding_cohort_release.py $native out/reproduced-cohort
python tools/summarize_founding_cohort_release.py out/reproduced-cohort out/reproduced-cohort/decision
```

`run.json` and `archives.jsonl` fix each source tree, executable, exact parameters, arm, mode, seed, member bytes and failure state. For byte-identical provenance use the biological binary recorded at `eb5e529a116be3cee5c3de9a9dc2ecc88f520745` for the three factor and extended panels and the protected assay recorded at `27427d18d3fd7b800652c631a2bbee34131a9d70` for the correction. The collector accepts `--binary-receipt` to associate an executable built from an ancestor without confusing the tool revision with the compiled tree. The extended run reuses a checked, ordered original archive prefix and records how many cases it retained. `--resume-from` accepts only a matching prospective roster and exact binary and preserves each retained SHA-256. ZIP container metadata can vary across runs. Compare authority/member bytes and registered hashes.

The fresh outputs should reproduce the registered deterministic outcomes. Timings, instrumentation and SQLite physical file layouts may differ by machine. The event CSV includes preceding sampled maternal and larval state, canonical identifiers, and timestamps. A missing action-time state is unknown. Full canonical facts remain the authority for transfers and outcomes.

## Performance

Build a separate Release tree with `-DANTWORLD_STORAGE_TIMING=ON` for the phase diagnostics. Use the tree before the one-block cache (`64ce37a`) and the cached tree (`27427d1`). Use the same Clang, options, inputs, output storage and access to SQLite. The history runner checks canonical and observation bytes against the reviewed fixed worlds at each repetition.

```powershell
python tools/measure_founding_cohort_history.py $before out/diag-bounded $scratch
python tools/measure_founding_cohort_history.py $after out/diag-bounded-cache $scratch
python tools/measure_founding_cohort_history.py $after out/diag-midpoint $scratch --midpoint-before $before
```

The separate approved application procedure requires the original Windows host topology, live mapped HWiNFO CSV, native per-core counters and the frozen admission rules. Use the uninstrumented Release executable and the same argument vector for prepare and run. Keep private source telemetry on the measurement host and publish the approved CPU channels, complete admission rows and samples. Preparation freezes all 720 slots and the input sources before measurement. The analyzer retains every original limit and failure.

The final work-identity check compares each available sample with its approved archived counterpart: same order, inputs, model, initial and final authority, event count, RNG, and state and trace hashes. A complete but nonidentical collection cannot qualify.

```powershell
python tools/qualify_founding_cohort_application.py --prepare --out $formal --archive $private --binary $binary --build build/cohort-release --compiler $clang --hwinfo-csv $sensors
python tools/qualify_founding_cohort_application.py --out $formal --archive $private --binary $binary --build build/cohort-release --compiler $clang --hwinfo-csv $sensors
python tools/qualify_founding_cohort_application.py --out $formal --analysis $analysis
```
