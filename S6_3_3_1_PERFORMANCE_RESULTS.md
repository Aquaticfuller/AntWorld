# S6.3.3.1 Windows performance requalification

| Frozen workload | Qualified sessions | Raw rows | Dense advance p50 growth | Paired median | Verdict |
| --- | ---: | ---: | ---: | ---: | --- |
| Stationary contacts, 512 to 2,048 workers | 3/3 | 336 | 5.4154 [5.3468, 5.4817] | 5.4578 [5.3495, 5.5176] | PASS |
| Endogenous births with the historical reserve | 3/3 | 168 | 4.2740 [4.1934, 4.3765] | 4.3149 [4.1816, 4.4111] | PASS |

The frozen threshold is 6.0 for the ratio of pooled median advance times. The intervals are 95% hierarchical session/block bootstrap intervals with 4,096 draws. Paired medians use the ABBA/BAAB blocks. The ratios exclude only the predeclared warm-ups, which stay in the original CSVs. The 128-population diagnostic and dispersed contact samples also stay in the archive. [Original freeze](experiments/s6_3_3_1/performance/freeze.json), [reserve freeze](experiments/s6_3_3_1/performance_reserve/freeze.json)

## Independent instrument check

The two version-1 probes retain their original INCONCLUSIVE status. The restricted probe could read cumulative native CPU times but could not open the PDH processor counter. In the host version-1 probe, the old formatted Processor Information counter returned `0x800007D6` on CPU 0 eight times and CPU 2 three times. Windows defines this as `PDH_CALC_NEGATIVE_DENOMINATOR`, a counter calculation error. Each observed case has positive PDH clock advance and an idle increment exceeding that advance. Both probes also recorded some stationary or decreasing native idle and kernel totals. Their changes cancelled in `KernelTime - IdleTime`. The operating-system/provider cause remains unknown. [PDH status documentation](https://learn.microsoft.com/en-us/windows/win32/perfctrs/pdh-error-codes), [native interface](https://learn.microsoft.com/en-us/windows/win32/api/winternl/nf-winternl-ntquerysysteminformation)

The frozen version 2 uses size-checked native per-logical-processor times in 100 ns units and calculates `100 * (delta(KernelTime - IdleTime) + delta(UserTime)) / delta(wall time)` with independent QPC elapsed time. Every selected interval and all raw statuses are kept. Accounting overshoots in short samples remain visible. It validates nonnegative component changes and the declared quantization tolerance. The 60-interval confirmation was complete. The pinned CPU 0 and CPU 2 pulse medians were 100.003% and 99.992%, with opposite medians of 0.781% and 0.000%. The median absolute difference from aggregate `GetSystemTimes` was 0.0629 percentage points. Valid unpulsed paired PDH values differed by medians 1.5492 and 0.0237 points. PDH still reported four and two invalid intervals. These data support the measurement path without assigning a cause to the old errors. [GetSystemTimes](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getsystemtimes), [QPC](https://learn.microsoft.com/en-us/windows/win32/sysinfo/acquiring-high-resolution-time-stamps), [instrument confirmation](experiments/s6_3_3_1/performance/instrument_v2_confirmation/receipt.json)

## Host and timing boundary

The host is a 13th-generation Intel Core i7-13620H with 10 physical cores, 16 logical processors and 16,494,648 KiB visible memory. Windows build is 26200 and the recorded power-plan GUID is `85d583c5-cf2e-4197-80fd-3789a227a72c`. Builds use LLVM/MinGW clang 23.1.5 with a single-configuration Release build. The two freeze manifests identify the exact binaries and compilation revision. The later TD-11 receipt fix rebuilt only its separate diagnostic target. The two measured hashes matched after that build.

Each session required 60 valid one-second samples. Admission requires selected CPU and system p50 at most 10% and p95 at most 20%, AC and saver off, and fresh HWiNFO temperature, power and effective clock. CPU 0 is the chosen logical benchmark processor. The collector runs off its full physical core. The timed provider and process sample cadence is approximately 100 ms. The original localized logger copies stay outside Git, with SHA-256 and exact published window in each mapped sensor receipt. All phases identify their start and end CPU. Setup, advance, encode and restore have separate wall, CPU and cycle samples. No concurrent project build, experiment or test ran during formal collection. [Contact raw sessions](experiments/s6_3_3_1/performance/contacts/), [reserve raw sessions](experiments/s6_3_3_1/performance_reserve/births/)

## Workload selection error and qualification

The first batch used the ordinary birth executable. The historical benchmark enables `ANTWORLD_ALLOCATION_BENCHMARK=1` in the reserve executable. Checkpoint lengths and state/trace hashes exposed the configuration mistake despite matching births, event counts and queue counts. All 168 ordinary-birth rows, raw telemetry, exact mismatches and descriptive statistics remain. None contributes to the reserve verdict. Document 57 froze a separate first formal reserve run after verifying exact historical identities at all three sizes. The contact batch is used once. [Workload mismatches](experiments/s6_3_3_1/performance/analysis/workload_mismatches.csv), [reserve identity receipt](experiments/s6_3_3_1/performance_reserve/reserve_identity_receipt.json), [correction protocol](docs/57_S6_3_3_1_Reserve_Birth_Benchmark_Correction.md)

| Dense advance phase | Population | p50 (ms) | p95 (ms) | p99 (ms) |
| --- | ---: | ---: | ---: | ---: |
| Contact advance | 512 | 41.563 | 46.003 | 47.268 |
| Contact advance | 2,048 | 225.080 | 239.328 | 241.748 |
| Reserve birth advance | 512 | 3.011 | 3.345 | 4.104 |
| Reserve birth advance | 2,048 | 12.869 | 13.932 | 24.475 |

In the qualified contact batch, system admission p95 spans 9.23–14.37% and selected CPU admission p95 spans 1.64–6.40%. The reserve ranges are 9.91–17.12% and 0–7.97%. All qualified admission samples were on AC with saver off. The in-run native CPU and process accounting records are complete across 1,770 contact and 126 reserve samples. The original PDH load field is invalid in 92 contact samples and one reserve sample. Mapped HWiNFO data provide 98 and 15 samples, respectively, including the declared brackets. Maximum gaps are 2.025 and 2.006 s. Package temperatures span 49–72 C and 49–66 C, and package power spans 3.102–27.665 W and 2.904–27.515 W. Selected-thread effective-clock medians across sessions span 2,212.9–2,296.4 MHz for contacts and 967.7–1,811.6 MHz for the short reserve sessions. These values include the pre/post brackets. The observed thermal and package power-limit flags are zero.

Contact event counts are 15,874 and 63,490, with 73,728 and 294,912 candidates examined, at 512 and 2,048. Reserve birth facts are 3,587 and 14,339, with 512 and 2,048 new identities. All checkpoint and continuation hashes, counts and protected-birth ledgers match the archived workload. Dense contact checkpoint sizes are 2,877,816 and 11,508,600 bytes. Reserve sizes are 1,426,479 and 5,702,703 bytes. Median dense working sets are 22,863,872 and 59,570,176 bytes for contacts and 14,845,952 and 34,973,696 for reserve births. The 2,048 reserve advance maximum was 31.011 ms, retained along with its 24.475 ms p99. [Contact telemetry and work](experiments/s6_3_3_1/performance/analysis/), [reserve telemetry and work](experiments/s6_3_3_1/performance_reserve/analysis/)

The validated time/CPU records and contact work counters are separate from the optional fine-grained profiling categories. The formal Release build has fine-grained profiling off. Category fields stay in the original samples and zeros represent disabled measurement. [All contact phase quantiles](experiments/s6_3_3_1/performance/analysis/latency.csv), [reserve phase quantiles](experiments/s6_3_3_1/performance_reserve/analysis/latency.csv), [formal result figure](experiments/s6_3_3_1/figures/performance.svg)

S6.1's 24.229x observation and unknown cause, the older S6.3.1 failures, the S6.3.3 admission failures and its 5.5074x earlier binary sample retain their original status. These Windows gates cover their fixed workloads. The TD-11 care workload, larger dynamic populations and unbounded history remain distinct.

## Reproduction

On the same class of single-processor-group Windows host, use an independent output directory and complete the instrument probe before starting an admitted batch. Use the documented HWiNFO mapping and quiet interval. Keep the official schedule and binary manifests before starting any collection. The source compiler and hashes in the committed receipts identify the measured programs. New wall timings depend on the host.

```powershell
python tools/s6_3_3_1_processor_times.py --out out/retrieval-instrument
$perf = 'out/retrieval-reserve'
$build = 'build/retrieval-release'
$compiler = 'C:/path/to/clang++.exe'
$logger = 'D:/path/to/hwinfo_log.CSV'
python tools/run_s6_3_3_1_performance.py --prepare --kind births --out $perf --build $build --compiler $compiler --confirmation out/retrieval-instrument/receipt.json
python tools/verify_s6_3_3_1_reserve_workload.py --binary "$build/antworld_s6_3_1_birth_benchmark.exe" --scratch out/retrieval-identity --receipt "$perf/reserve_identity_receipt.json"
python tools/run_s6_3_3_1_performance.py --out $perf --build $build --archive out/retrieval-sensor-archive --hwinfo-csv $logger
python tools/analyze_s6_3_3_1_performance.py --raw $perf --out "$perf/analysis"
python tools/analyze_s6_3_3_1_performance.py --check
python tools/analyze_s6_3_3_1_performance.py --raw experiments/s6_3_3_1/performance_reserve --out experiments/s6_3_3_1/performance_reserve/analysis --check
```

For an independent contact batch use a separate root with `--kind contacts`. The original ordinary-birth runner is available at `41fc8aa`. It is retained as setup evidence. [Protocol 55](docs/55_S6_3_3_1_Performance_Instrument_Protocol.md)
