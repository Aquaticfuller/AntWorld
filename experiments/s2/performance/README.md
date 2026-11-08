# Local S2 performance evidence

Measured on Windows x64 / i7-13620H, LLVM-MinGW 20261104 (Clang 23.1.5), CMake 3.31.10 and Ninja 1.13.2, Release, using `tools/benchmark_s2_windows.ps1`. Core behavior under measurement is commit `9ff9b35`; subsequent `989a382` only changes experiment presentation/CI and `d273a92` disambiguates loop layout under GCC warnings, with no algorithm change.

All quantities are engineering fixtures. Raw outputs:

- `active_workers.csv`: 16/128/512 autonomous workers, 180 simulated seconds, mostly 1,101 ms advances; snapshot restore and continuation verified.
- `fixed_active.csv`: retained S1 harness, 32 active actors against 32/2,000/20,000 stored ants, 256 rounds.
- `scheduler.csv`: retained schedule/cancel queue scaling harness.
- `diagnostics.json`: retained empty-world S0 synthetic event harness.
- `process_metrics.json`: whole-process wall time and sampled PeakWorkingSet64 for each executable, observed every 5 ms. It includes setup, serialization, validation and the largest case; it is not per-world steady resident memory or per-worker memory. A short-lived peak can escape polling.

Timing includes no Unity, GM, physiology, geometry, persistence database or full-map work. Tests/builds were complete before timing; results are one observed local run with per-advance quantiles, not a throughput guarantee. Histories and duplicate restore states are retained during validation, contributing to the process peak. See S2_RESULTS.md for interpretation and exact table values.
