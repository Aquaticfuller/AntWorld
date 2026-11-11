# RM-01-R1 performance qualification

| Acceptance area | Result |
| --- | --- |
| Functional engineering | **ENGINEERING_PASS** at independent review of `84decb6dc23bd03af2562214ab92c8b6847ec668`. The R1 evidence verification reproduced the accepted result byte for byte. |
| Controlled performance | **NOT_RUN** for TD-01 dense contact and TD-08 reserve birth. Live HWiNFO logging was unavailable before formal admission. |
| Complete RM-01 engineering | **PENDING**. Both controlled performance gates still require qualified measurements. |
| Biological validation | **BIOLOGICAL_NOT_VALIDATED**. BR-04 remains open. |

## Qualification record

The R1 protocol was committed at `9b31879732e7bc9466b043736dd252210ab89613` before the new freeze or diagnostic. The freeze reproduces the original compiler, executable SHA-256 values, schedule SHA-256 values, dependencies, instrumentation, sensor mapping and order. The baseline C++ tree is `2b9d475fdb0d657dc87e46755d6511779da0c8b4`. The three-population reserve diagnostic reproduced the exact accepted receipt, including births, facts, pending work, checkpoint bytes, state and trace hashes, restore and mass/energy balances. [Protocol](RM01_R1_PERFORMANCE_PROTOCOL.md) [R1 manifest](../../experiments/s6_4_rm01_r1/controlled/freeze.json) [Workload identity](../../experiments/s6_4_rm01_r1/controlled/reserve_identity_receipt.json)

The HWiNFO header matched the approved mapping. Its newest reading was recorded at 11:50 local time on 2026-11-11 and the live log had stopped updating. An attempt to open the installed application did not expose a sensor window. A native launch returned a process that did not remain running or resume CSV writes. R1 stopped before formal admission under the original requirement for valid readings within the −2 to 10 s age window. Current system-load admission, timing telemetry, ratios and confidence intervals are unavailable. [Host preflight](../../experiments/s6_4_rm01_r1/host_preflight.json)

| Workload | Qualified sessions | Formal admissions attempted | Timed / planned rows | Primary growth / 95% interval |
| --- | ---: | ---: | ---: | --- |
| TD-01 contacts | 0 / 3 | 0 | 0 / 336 | NOT_RUN |
| TD-08 reserve births | 0 / 3 | 0 | 0 / 168 | NOT_RUN |

Each gate still requires three qualified sessions and an exact-work pooled dense 2,048/512 median advance ratio of at most 6. The existing version-2 runner and analyzer define the eligible observations. R1 has preflight and workload identity records. The first formal session awaits live HWiNFO logging and the frozen admission checks. [Reproduction commands](../../experiments/s6_4_rm01_r1/README.md)

## Protected evidence and regression checks

The original verifier exited 0 for 13 short assays, 18 ecology runs and 12 observer pairs including warm-ups. Its output SHA-256 is `04557bb0b28ed057692bc832f769a9387f18b62e6f7262a91ffd65f2bf8cc68e`, identical to the accepted verification. The existing analyzer reproduced the previous batch's three rejected admissions and INCONCLUSIVE status for both workloads. The previous batch retains 180 admission intervals, zero timed rows and all 504 scheduled rows. The original functional acceptance covers the 216 CTest entries and five successful baseline Core CI jobs. [Verification receipt](../../experiments/s6_4_rm01_r1/reproduction_receipt.json) [Original admissions and results](RM01_PERFORMANCE_RESULTS.md) [Baseline Core CI](https://github.com/Aquaticfuller/AntWorld/actions/runs/42995203428)

The repository policy and design check ran locally with exit code 0. The existing Core CI workflow checks the R1 branch. The R1 scope is the performance evidence supplement. The egg timing technical assay retains the accepted production defaults, original budgets, mortality behavior and biological interpretation.
