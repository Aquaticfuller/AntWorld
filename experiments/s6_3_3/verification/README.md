# S6.3.3 verification records

Initial implementation: `35a0df49eebbffd17c97bc3d223476aa8bd92590`; exception-safe Core: `769494c18b9fe57b3b48a8ea25a54ff467edc9b3`; final experiment-layout revision: `5f4f46cf8acf7bf0d57f15b2687d9a0536709476`. All162 inherited tests remain; the18 additions bring the total to180. The old build-directory names were reused. The final Core passes all local suites; the driver-only line-break correction additionally passes the local smoke test and all final-source CI suites.

- `ctest-debug.txt`, `ctest-release.txt`, `ctest-sanitized.txt`: final review-source suites,180/180 each. Clang23.1.5, pinned LLVM-MinGW20261104, CMake3.31.10, Windows x64. Windows leak detection is unavailable; Linux CI enables it.
- `pre_guard_ctest-*.txt`: earlier successful suites, retained separately from the final custom-input speed validation.
- `review_reproduction.json`: post-speed-guard executable reproduces23 complete primary seed7 cases. `portable_reproduction.json` repeats the comparison after the MSVC constructor correction, including every exported event and all biological endpoints. Wall timings are excluded; position serialization alone permits1e-12m roundoff.
- `validation_guard.json`: mathematical implication checked for all384 frozen configurations, plus the exact pre-guard project-source archive. No coefficient or accepted experiment behavior was changed.
- `evidence_checks.log`: earlier complete policy/atlas/historical/current evidence audit.
- `final_evidence_checks.log`: complete audit after raw-file checksum validation and separate preliminary performance summaries were added, before the later constructor correction. The current source/portability checks are in `portable_source_checks.log`; CI repeats the entire audit against the final source.
- `repository_policy.log`: language-bearing tracked text/commit checks after all new files were staged. Original localized hardware snapshots and publisher papers are untracked.
- `ci_initial_failure.json`: first Linux CI failure annotations for host-dependent ZIP re-encoding equality. `portable_archive_check.txt` verifies the replacement check against the unchanged archive digest and exact source payloads; it does not regenerate or relabel historical evidence.
- `ci_initial.json` and `ci_initial_windows_debug_failure.json`: complete first-run status and the MSVC Debug allocation37 failure. `portable_allocation.json` verifies the limited empty-vector constructor correction against the frozen source hashes; no behavioral coefficient, RNG call or successful action was changed.
- `ci_gcc_build_failure.json`: GCC's experiment-driver indentation diagnostics. Only three line breaks changed; the portability checker reconstructs and hashes the retained executed driver. No warning suppression or condition/value change is used.
- `msvc_allocation_ci.json`: the constructor-corrected Windows Debug job passes, closing the original allocation37 failure.
- `ci_final_source.json`: [final-source CI42695868377](https://github.com/Aquaticfuller/AntWorld/actions/runs/42695868377), all five jobs PASS, including Linux Release reproduction through the complete new primary seed. The subsequent report commit adds only documentation/receipts; it does not modify code, tests, fixtures or analysis.

Actual local regression commands, after prepending the pinned compiler and Ninja directories to PATH:

```powershell
& .tools/cmake-3.31.10-windows-x86_64/bin/cmake.exe --build build/s6_3_2-debug --parallel 4
& .tools/cmake-3.31.10-windows-x86_64/bin/ctest.exe --test-dir build/s6_3_2-debug --output-on-failure
& .tools/cmake-3.31.10-windows-x86_64/bin/cmake.exe --build build/s6_3_2-release --parallel 4
& .tools/cmake-3.31.10-windows-x86_64/bin/ctest.exe --test-dir build/s6_3_2-release --output-on-failure
$env:ASAN_OPTIONS = 'detect_leaks=0:halt_on_error=1'
$env:UBSAN_OPTIONS = 'halt_on_error=1:print_stacktrace=1'
& .tools/cmake-3.31.10-windows-x86_64/bin/cmake.exe --build build/s6_3_2-sanitized --parallel 4
& .tools/cmake-3.31.10-windows-x86_64/bin/ctest.exe --test-dir build/s6_3_2-sanitized --output-on-failure
python tools/ci_verify.py
```

Raw experimental CSVs retain their original bytes, including CRLF where originally emitted; `.gitattributes` prevents checkout normalization from invalidating the original SHA-256 receipts. The final staged blobs matched all116 final/preliminary/source-data checksum entries. This is byte preservation, not alteration of measurement values or their hashes.

The GitHub result is reported against the exact tested implementation revision in the root results report and the archived CI receipt. Local tests do not stand in for that remote result. Neither engineering regressions nor a single preliminary performance session establish quantitative biological validity or final scale qualification.
