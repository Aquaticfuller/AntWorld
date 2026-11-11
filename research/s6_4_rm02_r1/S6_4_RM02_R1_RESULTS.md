# S6.4 RM-02 R1 results

| Gate | Result |
|---|---|
| `RM02_OBSERVER_ENGINEERING` | `PASS`. Accepted Stage A/B correctness and 72 complete case-level observer-off and durable rejoin checks. |
| `RM02_PERFORMANCE` | `PASS_UNDER_FROZEN_PROTOCOL`. The final candidate passes the written observer budgets and the independent TD-01 and TD-08 gates. |
| `RM02_BASELINE_DIAGNOSIS` | `COMPLETE`. All 48 ecology, 12 early-window and 12 dense-coverage cases executed and independently reproduced from archived data. |
| `BR02_BIOLOGICAL_VALIDATION` | `BLOCKED`. Condition-matched independent choice, measured dose and uptake data remain missing. |
| `NEXT_MODEL_CHANGE_AUTHORIZATION` | `NOT_AUTHORIZED`. |

The R1 evaluator maps the foreground maximum to capture plus submission at each cut. It includes the last durable write in overall wall time and reports terminal drain separately. All three historical `FAIL` reports and their raw archives remain part of the evidence. The first two still fail written thresholds. The final candidate qualifies with all 504 original rows and no new host timing. It retains the 106.9501 ms dense-2,048 and 256.1484 ms depot-32 drain maxima. The physical sync and scheduling shares of those tails are unmeasured. [Protocol crosswalk](PROTOCOL_TO_ANALYZER_CROSSWALK.md) [Terminal diagnosis](TERMINAL_DRAIN_DIAGNOSIS.md)

The archived baseline scans 8,383,077 events, preserves 2,359,508 scoped facts, and has zero dropped scoped records. Each of the 5,700 cuts reconciles the nutrition and energy ledger. The 37 queen energy deaths include two queens with unabsorbed crop carbohydrate. Confirmed zeros, generic rejections, pending coverage and censored follow-up remain distinct. The evidence motivates a separately testable recipient-cue hypothesis and compartment timing measurements. [Engineering diagnosis and reproduction](STAGE_C_BASELINE_RESULTS.md) [Scientific diagnosis and reuse](STAGE_D_SCIENTIFIC_DIAGNOSIS.md)

## Verification

| Check run on the reviewed C++ tree | Result |
|---|---|
| Windows Debug CTest | 222/222, 116.04 s |
| Windows Release CTest | 222/222, 22.74 s |
| Windows ASan/UBSan CTest | 222/222, 472.46 s with the LLVM runtime directory on PATH |
| Repository policy and inherited evidence suite | Exit 0, `python tools/ci_verify.py` |
| Reconciliation error-injection tests | 3/3, `python tools/test_s6_4_rm02_performance_reconciliation.py` |
| All three observer batches and legacy controlled series | Both check-mode commands in the [crosswalk](PROTOCOL_TO_ANALYZER_CROSSWALK.md#reproduction) exit 0 |
| Full Stage C archive | `python tools/verify_s6_4_rm02_r1_baseline.py` exits 0 and reproduces 11 original analysis outputs and the four R1 diagnostic files |

CTest used `ctest --test-dir build/s6_3_4-<debug|release|sanitizer> --output-on-failure` with the corresponding single-configuration builds. The first sanitizer invocation lacked the Windows ASan runtime on PATH and returned a loader error (`0xc0000135`). The successful repeat prepended the same toolchain's bin directory and set `ASAN_OPTIONS=halt_on_error=1` and `UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1`. Core CI retains its inherited Linux and Windows build and sanitizer jobs, plus the new Linux Release archive checks. [Branch CI history](https://github.com/Aquaticfuller/AntWorld/actions/workflows/ci.yml?query=branch%3Acodex%2Fs6.4-rm02-r1-gate-reconciliation)

The review base is `d5667c7c15d61f14c09480ba55a0d58fdc461a48`. Performance reconciliation is `97370d8b841f9c9f9a0798e29be486cf6862ff01`. The executed matrix is `729e3d8d5db232e989e10ee60d039897ddc9bb38`. The C++ tree is `a95539621cdf682cb1e0427e1e9f0896aa0bfbb1` across the review base and R1. The protected-path comparison covers Core, prior RM-02 applications, the accepted design and scientific records, both frozen analysis tools and the original timing archives.

[Performance machine results](../../experiments/s6_4_rm02_r1/performance) [72 raw case folders](../../experiments/s6_4_rm02_r1/baseline/raw) [Analysis tables](../../experiments/s6_4_rm02_r1/analysis) [R1 supplemental tables](../../experiments/s6_4_rm02_r1/diagnosis)
