# RM-01 egg timing results

| Gate | Result |
| --- | --- |
| Isolated clock, original-budget negatives, priority, conservation and recovery | **ENGINEERING_PASS** |
| Original durable-storage budget and observer parity | **ENGINEERING_PASS** |
| Current TD-01 and TD-08 controlled timing qualification | **NOT_RUN**. Host admission exhausted before the first timed sample. |
| Full RM-01 engineering qualification including controlled timing | **NOT_RUN** |
| Species-level viability and independent validation | **BIOLOGICAL_NOT_VALIDATED**. BR-04 remains open. |

## Scope and provenance

The start check verified [Core CI run 42983936355](https://github.com/Aquaticfuller/AntWorld/actions/runs/42983936355) at `51436048db93da8fbcfe4ff738ff74644bfa1731` with all five jobs successful. The frozen C++ tree is `277cc8e78cc1acd1cf4a74bf39d08dfdb6a99c69`. The implementation commit `2b7ca57bbc5a887527a9cf5f69066b7df0daa5ed` contains a separate executable, app-local clock resolver, tests and build registration. The only edited C++ path that existed at the comparator is `cpp/CMakeLists.txt`. The observer evidence was collected at `151cb7f8ae54d3b96dea819ca766e89b3bfe200c` using the identical RM-01 executable hash. [Frozen protocol](RM01_PROTOCOL.md) [Raw file index](../../experiments/s6_4_rm01/README.md)

The resolver admits the two B06 Table 2 rows and the legacy control. Decimal day values are converted directly to integer milliseconds. The resolved value enters an existing `PhysiologyConfig` at setup. A committed funded egg inherits that config from the queen through the existing birth transaction. The application writes derived observations from committed facts and detached queries. Matching variants and their restores retain the frozen WorldId and stable identities within each run. Run directories and their receipts identify separate comparisons. The application changes neither the Core state machine nor stored layouts. Every assay configuration and reserve is declared as an engineering fixture. [Implementation](../../cpp/apps/antworld_s6_4_egg_timing.cpp) [Profile resolver](../../cpp/apps/rm01_egg_timing.hpp) [B06 primary source](https://doi.org/10.1023/B:JOEY.0000033808.45455.75)

## Exact egg outcomes

Thirteen short arms passed the application checks and independent review of the portable records. Times are relative to the committed entry. Seeded eggs entered at time zero and the first funded eggs entered at 172,800,000 ms.

| Arm | Observed outcome | Age at outcome | Remaining energy | Remaining water |
| --- | --- | ---: | ---: | ---: |
| Legacy original budget, seeded and funded | Hatch | 172,800,000 ms | 327,200,000 nJ | 152 µg |
| Borisovka and St. Petersburg original budget, seeded and funded | Energy death | 500,000,000 ms | 0 nJ | 62 µg |
| Legacy timing sentinel | Hatch | 172,800,000 ms | 4 nJ | 1 µg |
| Borisovka timing sentinel | Hatch | 1,442,880,000 ms | 4 nJ | 1 µg |
| St. Petersburg timing sentinel | Hatch | 1,356,480,000 ms | 4 nJ | 1 µg |
| Energy ties, both warm rows | Energy death at the supplied clock | 1,442,880,000 or 1,356,480,000 ms | 0 nJ | 1 µg |
| Legacy water tie | Dehydration at the clock | 172,800,000 ms | 4 nJ | 0 µg |
| Legacy fixture interruption | Fixture death | 172,799,999 ms | 5 nJ | 2 µg |

Original warm eggs used 500,000,000 nJ and 200 µg at entry with 1 nJ/ms and 1 µg/h expenditure and zero egg absorption. The full observation window continued through each supplied clock plus 1 ms. The four warm focal eggs had death facts and zero hatch facts. All sentinel outcomes above used separate technical reserves with active mortality. For each ordinary clock transition, the observations at the boundary minus and plus 1 ms establish the inclusive trigger. The tie cases commit a death at the boundary. [Independent verification output](../../experiments/s6_4_rm01/verification.json) [Original-budget raw runs](../../experiments/s6_4_rm01/assay)

Mid-egg full checkpoint restores, mid-egg and terminal published SQLite cuts, and one-shot versus segmented continuation agreed in state, pending work and ordered canonical facts. Raw `observations.csv` fields are the detached queries projected to observation time. The checkpoint comparison checks persisted progress and the queued boundary. Invalid condition IDs, mismatched provenance, units, malformed durations and both parsing and conversion overflow were rejected with identical state, checkpoint and queue. The current production default is checked in the profile regression.

## Frozen ecology controls

All 18 seed-1 ecology runs replayed exactly and reconciled carbohydrate, protein, water, energy and soil. Each of the six legacy controls matched the historical living population, births, queen survival, fact count, state hash and trace hash. Warm runs differed only in the transmitted egg clock. The two warm profiles had the same count results. Each final warm cohort had three censored eggs. Every warm egg old enough to reach the depletion boundary died, with no hatching in any of the twelve warm long runs.

| Original ecology arm | Days | Legacy births | Legacy hatch / death / censored as eggs | Legacy living at end | Warm births per profile | Warm hatch / death / censored | Warm living at end |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Ordinary, 8 workers | 90 | 4 | 4 / 0 / 0 | 13 | 40 | 0 / 37 / 3 | 12 |
| Scarce, 8 workers | 90 | 2 | 2 / 0 / 0 | 10 | 40 | 0 / 37 / 3 | 12 |
| Depot, 8 workers | 180 | 2 | 2 / 0 / 0 | 10 | 82 | 0 / 79 / 3 | 12 |
| Ordinary, 32 workers | 90 | 15 | 15 / 0 / 0 | 37 | 36 | 0 / 33 / 3 | 36 |
| Scarce, 32 workers | 90 | 18 | 18 / 0 / 0 | 36 | 36 | 0 / 33 / 3 | 36 |
| Depot, 32 workers | 180 | 78 | 77 / 0 / 1 | 111 | 76 | 0 / 73 / 3 | 36 |

The 8-worker legacy depot queen died and the 32-worker legacy depot queen survived with continued laying through the 180-day arm. The warm depot-32 lineage retained the founding queen, 32 workers and three censored eggs at the end. Its loss of recruitment follows directly from the committed egg deaths. The legacy depot-32 event stream contained 191,461 facts and each warm counterpart contained 96,454. The different census and queen outcomes belong to these fixture trajectories. Egg outcomes and colony counts do not identify a biological allocation or survival mechanism. [Historical S6.3.1 controls](../../S6_3_1_RESULTS.md) [All ecology runs and identities](../../experiments/s6_4_rm01/verification.json)

The unchanged S6.3.4 workload reproduced eight 21-day R1 cases and six 180-day depot cases with 1,623,444 exact canonical facts. The test suites retain physical care, custody, underground access and segmented history recovery. [Retained ecological comparison](../../experiments/s6_4_rm01/durability/retained_ecology.csv) [Durability performance](RM01_PERFORMANCE_RESULTS.md)

## Verification and review boundary

Windows LLVM-MinGW Clang 23.1.5, CMake 3.31.10 and Ninja were used for the local suites. The existing Release, Debug and Debug ASan/UBSan build directories were rebuilt at the implementation revision. All suites passed 216/216 tests, including four new CTest entries. The local Windows sanitizer used `ASAN_OPTIONS=detect_leaks=0:halt_on_error=1` and `UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1`. The [implementation Core CI](https://github.com/Aquaticfuller/AntWorld/actions/runs/42989586118) passed its five Windows, Ubuntu and sanitizer jobs at the implementation commit. The accepted [Evidence CI](https://github.com/Aquaticfuller/AntWorld/actions/runs/42983936207) remains on the scientific audit branch. The new branch runs the existing Core workflow. [CTest logs](../../experiments/s6_4_rm01/ctest) [Reproduction](../../experiments/s6_4_rm01/README.md)

The [append-only intake](RM01_DATA_INTAKE.md) records 16 verified files alongside the original frozen register. The six candidate packages remain unscreened for independent eligibility. The egg cohorts, embryo energy and water budgets, and independent hatch and mortality observations required by BR-04 remain outstanding. Review the measured technical behavior and the unqualified TD timing separately before any further authorization.
