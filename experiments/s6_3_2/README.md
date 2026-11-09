# S6.3.2 reproducible audit evidence

The source baseline is S6.3.1 `accdb4c7037c792ac55e45277c9a16379828b09c`. Protocol 48 was frozen in `55e6871`; the evidence matrix, parameter inventory and concrete comparison/proposal freeze (document 49) were committed in `15e5c40` before new probes. Core headers/sources and inherited tests are unchanged. No numeric biological default is calibrated or changed.

## Data layout

- `inventory`: all 119 config/seed/control fields, source expressions, indirect-use anchors, fixture/JSON contexts, coverage and source hashes. See PARAMETER_AUDIT_COVERAGE.md.
- `literature_access.json`: successful/failed host access metadata. It is not a reading-status substitute; BIOLOGY_REFERENCES.md specifies what was read. Full texts and page images remain ignored/local.
- `literature_measurements.csv`: 34 visually checked B06 stage/population/temperature means and six explicitly unavailable cold-treatment endpoints; published error is not relabeled CI.
- `probes`: 18 eligibility worlds; 30 trajectories over seeds 1–6; daily/half-day queries, exact continuation checks and full canonical fact payloads in hex. `archive.json` records hashes. Stage codes Egg=0, Larva=1, Pupa=2, Adult=3, Dead=4. Event kinds and binary payload codec are unchanged public Core contracts.
- `analysis`: independently checked probe outputs and all 18 prespecified historical queen contrasts (six ordinary32, six adequate-access8, six adequate-access32). Original 432-run S6.3.1 files remain untouched; source paths identify provenance.
- `performance`: all preplanned schedules, admissions, raw timings, phase CPU/cycles, OS load, host snapshots and normalized HWiNFO samples. Missing birth sessions have no invented rows. Raw localized HWiNFO prefixes remain private with hashes.
- `performance_analysis`: percentiles, paired ratios, fixed bootstrap intervals, work/memory, telemetry and explicit completion status.
- `figures`: standalone PNG and SVG generated from the above evidence; no article figures are republished.
- `verification`: executed local test logs; verification.json records versions, counts, hashes and CI status.

## Build and tests

Windows uses the existing pinned bootstrap/toolchain:

```powershell
./tools/bootstrap_windows.ps1
./tools/build_windows.ps1 -Configuration Debug -BuildDirectory build/s6_3_2-debug
./tools/build_windows.ps1 -Configuration Release -BuildDirectory build/s6_3_2-release
$env:ASAN_OPTIONS='detect_leaks=0:halt_on_error=1'
$env:UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'
./tools/build_windows.ps1 -Configuration Debug -BuildDirectory build/s6_3_2-sanitized -Sanitizers
```

Linux/CI uses CMake with the same pinned SQLite source, and ASan/UBSan with leak detection enabled:

```sh
cmake -S cpp -B build/review -DCMAKE_BUILD_TYPE=Release
cmake --build build/review --parallel 4
ctest --test-dir build/review --output-on-failure
./build/review/antworld_s6_3_2_audit out/s6_3_2/probes 6
python tools/analyze_s6_3_2_biology.py --probes out/s6_3_2/probes --verify-only
```

On Windows the equivalent executable is `build/s6_3_2-release/antworld_s6_3_2_audit.exe`. Each probe starts a new world; no manually successful action substitutes for missing queen care. Reproduction of the frozen results is not a biological PASS. The additional CTest is `S6_3_2_AUDIT_SMOKE`; all 161 old tests remain.

## Source, data and figure verification

```sh
python tools/inventory_s6_3_2.py --check
python tools/provenance_s6_3_2.py --check
python tools/literature_measurements_s6_3_2.py --check
python tools/analyze_s6_3_2_biology.py --check
python tools/analyze_s6_3_2_performance.py --check
python tools/ci_verify.py
```

Analysis uses only Python's standard library. Optional plotting dependencies are pinned in `tools/s2_1_plot_requirements.txt`. Install them into a local environment or `.tools/s2_1-python`; set PYTHONPATH to that target and MPLCONFIGDIR to an ignored writable `out/s6_3_2/mplconfig` directory when required. Then run `python tools/plot_s6_3_2.py`. Plots have been visually checked. Empirical endpoints, model fixtures, censoring and noncomparability are labelled separately.

## Frozen performance reproduction

Acceptance uses the exact previously verified binaries whose hashes are listed in protocol 48; do not rebuild them in place or edit the expected hashes to disguise a different binary. A new machine/toolchain/binary needs an explicitly identified replication, not the identity claim of this run. Keep the original <=6 criterion.

For each session number 1,2,3, use the separately preplanned workload:

```sh
python tools/run_s6_3_2_performance.py --binary build/s6_3_1-release/antworld_s6_2_benchmark.exe --out out/s6_3_2/performance/contacts --kind contacts --session 1 --hwinfo-csv PATH_TO_HWINFO_CSV
python tools/run_s6_3_2_performance.py --binary build/s6_3_1-release/antworld_s6_3_1_birth_benchmark.exe --out out/s6_3_2/performance/births --kind births --session 1 --hwinfo-csv PATH_TO_HWINFO_CSV
python tools/archive_s6_3_2_performance.py out/s6_3_2/performance
python tools/analyze_s6_3_2_performance.py --check
```

The runner refuses started-session repeats, premature retries, changed binaries and more than three failed admissions. Do not remove receipts to bypass these guards. A failed birth admission is not a timing result. The final performance report explains missing qualification and the reviewable measurement follow-up. Retain old 24.229x, 6.315x and 8.154x batches and their uncertainties.

## Literature access and publication

Use DOI/publisher/institutional links in BIOLOGY_REFERENCES.md and the URL receipts; `tools/fetch_s6_3_2_literature.py` can cache an explicit request JSON locally. Network entitlements and publisher availability vary, so a 403/500 or certificate failure must be recorded and another legitimate accessible source used. Never disable TLS checks or publish licensed article bodies. The source register includes one explicit NIST compilation use where the original chemistry full text was not accessed; it is not labelled direct ant calibration.

Stop after this audit and independent review. P01-P10 are proposals only; no S6.4, Unity or later-stage development is authorized.
