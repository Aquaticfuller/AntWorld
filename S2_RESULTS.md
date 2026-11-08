# S2 results

Date: 2026-11-08. Branch: `codex/s2-foraging`. Reviewed S1 baseline: `632af76de5480c62e597afd9fdadd1485a31c811`. Implementation: `9ff9b35`; conditional-metric/CI follow-up: `989a382`; final verified code: **`d273a92ec68acd19aa6bd1e6e5a6425b96b99d7e`**. This is a subsequent documentation/evidence commit. S3 is not authorized.

## Implemented scope and review response

S2 implements a minimum autonomous explore -> locally discover -> collect -> physically return -> unload loop, with optional sparse surface trails and bounded learned route memory. The C++20 Simulation Core depends only on the standard library and runs headless, independently of Unity, Game Master, LLM services and network tools.

- Preserved S1's noncopyable State, single-writer undo journal, full event-key watermarks, deterministic resource arbitration, ingredient conservation, failed-transaction rollback and all 28 S0/S1 CTest registrations.
- Added optional static walkable surface cells and bounded cardinal movement. Local sensing uses a fixed-size reachable-cell traversal and a spatial food lookup, not a scan of all sources. Workers receive only local cues and their own bounded experienced paths.
- Added a pure individual behavior model with domain-separated per-ant decision randomness. All same-time observations/choices are frozen before proposals commit. Activation order cannot choose behavior, and external proposals cannot override autonomous schedules.
- Added successful-return trail deposition, analytical evaporation, saturation and fixed-time sparse cleanup; separate fields for each colony; finite inter-trip route memory with expiry/depletion handling; a bounded current-trip return trace in every treatment.
- Added actual nest inventory and atomic delivery. Each of four ingredients remains conserved across sources, carriers (including dead ants) and physical nests. There is no nutrition, feeding or global redistribution.
- Extended detached queries, committed evidence, map undo journals and checkpoints to schema/physics **3**. S0 v1 and S1 v2 saves are explicitly rejected, with no migration. Same-build restored continuation is tested. The historical S0_RESULTS.md and S1_RESULTS.md remain unchanged.

All uncalibrated parameters and experiment output are labeled `ENGINEERING_FIXTURE`. The complete choices, parameter units, API semantics, metric definitions and limits are in [document 27](docs/27_S2_Implementation_Decisions.md). No biological calibration or S3/S4 feature is claimed.

## Files and interfaces

| Area | Files and responsibility |
|---|---|
| Public model | `behavior.hpp`, `entities.hpp`, `event.hpp`, `world_runtime.hpp`: local observations, bounded private state, surface/trail metrics, physical nests, new actions/facts |
| Individual and surface logic | `behavior.cpp`, `behavior_rng.hpp`, `foraging.cpp`, `surface_internal.hpp`: pure choices, seed/identity separation, local sensing, loop-erased paths, sparse field and managed wakes |
| Transactions | `state.hpp`, `world_runtime.cpp`: touched-map undo, nest inventory before-images, local action validation, delivery, lifecycle cancellation |
| Checkpoints | `checkpoint.cpp`, `checkpoint_codec.hpp`, `checkpoint_s2.hpp`: v3 codec, ownership/route/field validation and reconciliation against committed evidence |
| Tests | `test_s2.cpp`, extended `test_allocation_failure.cpp`, retained S0/S1 suites |
| Experiments/performance | `s2_fixture.hpp`, `antworld_s2_experiment.cpp`, `antworld_s2_benchmark.cpp`, `tools/analyze_s2.py`, `tools/benchmark_s2_windows.ps1`, `experiments/s2/` |
| Engineering | CMake, CI benchmark/data audit, `tools/ci_build.py` failure annotations, AGENTS/start/README, documents 00/18/24/26/27, changelog and manifest |

New operations: configure_surface, start_foraging, sense, query_forager, trails, visits and surface_snapshot. seed_colony accepts a nest position. DeliverFood/Rest extend the internal C++ action API. The future C ABI remains an unimplemented draft.

## Environment and executed commands

Local Windows x64 / i7-13620H; LLVM-MinGW 20261104, Clang 23.1.5; CMake 3.31.10; Ninja 1.13.2; C++20 with warnings treated as errors. No new third-party runtime dependency was introduced. Existing pinned bootstrap versions/hashes remain unchanged. Python is only a repository/analysis tool, not a core dependency.

```powershell
./tools/build_windows.ps1 -Configuration Debug
./tools/build_windows.ps1 -Configuration Release
$env:ASAN_OPTIONS = 'halt_on_error=1'
$env:UBSAN_OPTIONS = 'halt_on_error=1:print_stacktrace=1'
./tools/build_windows.ps1 -Configuration Debug -BuildDirectory build/sanitized -Sanitizers
./build/release/antworld_s2_experiment.exe experiments/s2 16 1800000
python tools/analyze_s2.py experiments/s2
python tools/analyze_s2.py experiments/s2 --check
./tools/benchmark_s2_windows.ps1
./build/release/antworld_allocation_tests.exe S2
./build/release/antworld_s2_tests.exe MULTISEED
python tools/update_handoff_manifest.py
python tools/verify_handoff.py
python tools/check_repository.py
git diff --check
```

Build scripts were invoked through `pwsh -NoProfile -File`; Python commands used the available Python 3 runtime. Full local logs are under ignored `out/s2-*.txt`. Tracked raw behavioral and performance data are under [experiments/s2](experiments/s2/README.md).

## Local validation

| Configuration | Result | CTest elapsed |
|---|---|---:|
| Debug, final code d273a92 | PASS, 43/43 | 11.54 s |
| Release, final code d273a92 | PASS, 43/43 | 4.48 s |
| Debug ASan + UBSan, final code d273a92 | PASS, 43/43, no reported findings | 36.37 s |
| Clean exported final d273a92 source, Release | PASS, 43/43 | 3.60 s |
| Final code hosted CI | PASS, all five jobs | see run link below |
| Full CSV matrix audit | PASS, 128 balanced runs and 7,808 samples | n/a |
| Clean-build experiment reproduction | PASS, all four raw/analysis CSVs match | n/a |
| Handoff SHA-256 manifest | PASS, 40 files | n/a |
| English tracked-file/commit scan and Git whitespace check | PASS, 100 UTF-8 files, zero binaries | n/a |

The clean-source check executed `git archive --format=tar --output=out/s2-clean-final.tar d273a92 cpp scenarios`, extracted into `out/s2-clean-final`, configured `cmake -S out/s2-clean-final/cpp -B out/s2-clean-final/build -G Ninja -DCMAKE_BUILD_TYPE=Release` with the same explicit portable compiler/Ninja paths as the normal build script, then ran `cmake --build out/s2-clean-final/build --parallel 4` and `ctest --test-dir out/s2-clean-final/build --output-on-failure`. No untracked source file was available. That executable reran the complete 128-run experiment into `out/s2-reproduced`; both raw CSVs and both regenerated analysis CSVs matched the committed data after normalizing CRLF/LF. Logs are `out/s2-clean-final.txt` and `out/s2-reproduced.txt`.

Local timings are observations, not acceptance thresholds; some builds/tests ran concurrently. Performance measurements below were separate. Address/undefined-behavior coverage is local; Linux CI additionally enables leak detection. ThreadSanitizer is not claimed for the single-threaded runtime.

| Test | Coverage | Local Debug / Release / ASan+UBSan |
|---|---|---|
| S0: T00-T13, CLI_VALIDATION, CORE_EDGE_CASES | All 16 original registrations retained | PASS / PASS / PASS |
| S1: ENTITIES, MOVEMENT, COMPETITION, FAILURES, FAIRNESS, LIFECYCLE | Identity, detached queries, arbitration, order and lifecycle | PASS / PASS / PASS |
| S1: PHASES, ROLLBACK, PERSISTENCE, ARITHMETIC, BUDGETS, ALLOCATION_FAILURE | Watermarks, integer conservation, atomicity, corruption, host limits | PASS / PASS / PASS |
| S2_SURFACE | Blocked/nonlocal moves, cardinal motion, invalid configuration and speed | PASS / PASS / PASS |
| S2_LOCALITY | Disconnected food invisible; moving hidden remote food cannot change behavior; bounded sensing and pure observers | PASS / PASS / PASS |
| S2_LOOP | Autonomous discovery, collection, return and physical nest delivery; ingredient conservation | PASS / PASS / PASS |
| S2_ORDER | Reversed activation order has identical per-ant/collective behavior; external override rejected | PASS / PASS / PASS |
| S2_MEMORY | Learning/reuse, disabled memory, expiry, depleted endpoint, storage bound | PASS / PASS / PASS |
| S2_TRAILS | Loaded-only deposits, saturation, disabled signals, half-life, sparse pruning after death | PASS / PASS / PASS |
| S2_REPLAY | One long advance versus 467 ms chunks and restored continuation | PASS / PASS / PASS |
| S2_ROLLBACK | Late delivery fact budget failure and trail-budget failure roll back the complete call | PASS / PASS / PASS |
| S2_SCHEDULING | Owned-event cancellation rejection, duplicate activation, same-time death before movement | PASS / PASS / PASS |
| S2_MULTISEED | Eight seeds, enabled/disabled features, distinct behavioral metrics and conservation | PASS / PASS / PASS |
| S2_MODEL | Pure repeated choices, invalid inputs, seed/actor stream separation, finite excursions and isolated-cell rest | PASS / PASS / PASS |
| S2_COLONIES | Separate colony signals and physical inventories | PASS / PASS / PASS |
| S2_CORRUPTION | Re-signed forged route, field, counter and pending ownership; host-bound restore rollback | PASS / PASS / PASS |
| S2_ALLOCATION_FAILURE | Every allocation point until success in 12 S2 mutation/load scenarios | PASS / PASS / PASS |
| S2_EXPERIMENT_SMOKE | Standalone runner, all four treatments/two layouts, conservation and final checkpoint round trips | PASS / PASS / PASS |

The eight-seed mechanism regression recorded 82 deliveries, 1,793 trail-selected moves and 2,892 memory-selected moves. This is a separate smaller experiment from the main matrix.

Local Release allocation-failure points: configuration 6; food index 4; activation 8; decision/discovery 9; local movement 13; collect/learn 10; return/deposit 13; field maintenance 5; delivery 10; rich restore 73; death/cancel 4; sparse erasure 6. Counts vary by standard library; acceptance requires exact pre-operation checkpoint equality after each injected failure, then successful uninjected execution.

## GitHub Actions

The [final code verification run](https://github.com/Aquaticfuller/AntWorld/actions/runs/42449517193) completed successfully on `d273a92`. All five jobs passed:

| Hosted job | Result |
|---|---|
| Windows Server 2022 / MSVC Debug | PASS, all 43 CTest cases |
| Windows Server 2022 / MSVC Release | PASS, all 43 CTest cases |
| Ubuntu 24.04 / GCC Debug | PASS, all 43 CTest cases |
| Ubuntu 24.04 / GCC Release | PASS, all 43 CTest cases and four benchmark programs |
| Ubuntu 24.04 / Clang ASan + UBSan, leak detection enabled | PASS, all 43 CTest cases |

The four normal-build jobs also verified the English repository policy, design manifest and committed CSV analysis. The initial GCC jobs failed on misleading indentation; `tools/ci_build.py` exposes bounded compiler diagnostics in check annotations and the loop layout was corrected. No warnings or tests were disabled. Hosted tool versions follow the named runner images; only the local portable toolchain and checkout action are explicitly pinned. Cross-platform deterministic behavior is tested within each executable, not by asserting identical floating-point traces across compilers.

## F1/F2/F3 results

The complete matrix uses fixed seeds 1-16, 12 workers, 1,800,000 simulated ms, four paired treatments and two static terrains. All 128 final checkpoints round-tripped exactly, and every sampled state passed ingredient conservation in C++ plus the independent CSV total-balance audit. The run includes no filtered seeds. The committed raw [summary](experiments/s2/summary.csv), [time series](experiments/s2/timeseries.csv), [aggregates](experiments/s2/aggregate.csv) and [paired differences](experiments/s2/paired_differences.csv) retain zero-success runs and uncertainty.

Values below are means over 16 seeds. Coverage is physically visited walkable cells. Success is deliveries / started trips, including unfinished and unsuccessful trips. Inter-trip memory is the ablated feature; the bounded current-trip home trace remains available in every treatment.

| Layout | Treatment | Coverage | Deliveries, mean +/- sample SD | Delivery per started trip | Collection revisits | Edge reuse |
|---|---|---:|---:|---:|---:|---:|
| Open | Neither | 83.18% | 7.50 +/- 2.90 | 4.17% | 1.06 | 95.05% |
| Open | Trails only | 84.37% | 7.31 +/- 3.07 | 3.88% | 0.81 | 95.00% |
| Open | Memory only | 81.34% | 61.25 +/- 26.73 | 30.81% | 58.13 | 95.18% |
| Open | Both | 81.61% | 76.13 +/- 20.43 | 34.36% | 72.19 | 95.15% |
| Barrier | Neither | 72.19% | 1.63 +/- 1.31 | 0.94% | 0.00 | 96.05% |
| Barrier | Trails only | 72.59% | 1.38 +/- 1.15 | 0.81% | 0.06 | 96.01% |
| Barrier | Memory only | 71.23% | 15.19 +/- 16.83 | 8.33% | 14.38 | 96.09% |
| Barrier | Both | 73.16% | 19.63 +/- 21.68 | 9.67% | 18.44 | 95.98% |

**F1, local discovery/exploration:** mean first discovery is 136.11 s in open terrain and 657.30 s with the barrier; all 16 seeds eventually log a local cue in each layout. For a given seed/layout, the first discovery is identical in all four treatments: no trail or successful-source memory exists before actual foraging experience. The obstacle test separately proves disconnected close food is not sensed. Four barrier seeds deliver no food within the observation window even with both features; discovery is not recorded as a completed collection or delivery.

**F2, sparse trails and collective differences:** trail-only behavior changes routes and coverage, averaging 1,697.88 trail-selected steps in open terrain and 411.81 with the barrier. It does **not** improve average delivery here: paired changes against neither feature are -0.19 and -0.25 deliveries. Open trail-only seeds improve/tie/worsen delivery in 7/1/8 cases; barrier cases are 2/8/6. Thus this minimal local scalar signal is operational, but its standalone recruitment efficiency is an explicit limitation. No claim of shortest paths, universal benefit or statistical significance is made.

With both features, open deliveries increase by 68.63 versus neither and by 14.88 versus memory only; barrier increases are 18.00 and 4.44 respectively. This is a measured interaction in these fixtures, not a biological calibration. Signal following is a selected-step label; edge reuse includes retracing and loops and should not be interpreted as foraging efficiency by itself.

| Layout / treatment | Mean loaded-return deposits | Mean active amount at 30 min | Mean cumulative evaporation/cutoff loss | Mean active cells |
|---|---:|---:|---:|---:|
| Open / trails | 292.81 | 15.45 | 277.36 | 83.44 |
| Open / both | 3,020.50 | 276.63 | 2,743.87 | 186.13 |
| Barrier / trails | 58.75 | 2.45 | 56.30 | 16.00 |
| Barrier / both | 806.75 | 77.62 | 729.13 | 65.00 |

Signal units are abstract ENGINEERING_FIXTURE units. The open/both time series starts at zero; at 5/15/30 minutes the mean active amounts are 51.47/123.99/276.63 and cumulative deposits are 123.00/782.75/3,020.50. Local saturation and half-life/pruning are also directly tested. Disabled trails remain exactly zero in all samples.

**F3, bounded route memory:** memory-only improves deliveries over neither in 16/16 open seeds and 12/16 barrier seeds (four ties, no decreases). Open mean successful outbound movement falls from 73.38 to 43.60 moves, or 41.93 with both features. In the barrier, conditional means over the 13 seeds with a collection are 73.51, 50.66 and 50.80; no-collection runs use -1 and are excluded, not counted as zero-length routes. Memory-selected steps average 2,258.06 open / 559.38 barrier for memory-only, and 2,721.00 / 724.38 for both. Memory-off runs contain no learned route and no memory-selected step.

The large static stocks and repeated reinforcement produce zero route-forgetting failures and zero rejected autonomous actions in the main matrix. Dedicated tests exercise expiry, depletion, finite return bounds, malformed inputs and rollback. A lack of failures in this static matrix is not evidence for changing underground geometry. Fixed seeds and sample SD/paired signs provide reproducible descriptive evidence; they do not establish population-level significance or species plausibility.

## Performance

Measured separately in Release with `tools/benchmark_s2_windows.ps1`. Raw outputs and provenance are [tracked here](experiments/s2/performance/README.md). The final compiler-layout correction does not change algorithms. Active-worker cases use the barrier surface and 180 simulated seconds, mostly 1,101 ms advances; setup, checkpoint and restore are excluded from advance timing.

| Active workers | Committed facts | Actual moves | Advance p50 / p95 | Simulated seconds / advance wall second | Checkpoint bytes | Save / restore |
|---:|---:|---:|---:|---:|---:|---:|
| 16 | 5,304 | 2,608 | 54.9 / 74.3 us | 20,110.83 | 885,375 | 2.60 / 3.03 ms |
| 128 | 42,152 | 20,861 | 488.6 / 653.6 us | 2,160.43 | 6,898,951 | 19.10 / 26.40 ms |
| 512 | 168,488 | 83,423 | 1,737.4 / 2,420.0 us | 611.03 | 27,500,927 | 78.07 / 131.12 ms |

Each case verified checkpoint equality and continued both the original and restored world to the same next time. The large case deliberately raises temporary record/save budgets; it does not redefine their defaults. Sampled PeakWorkingSet64 for the whole S2 benchmark process is 181,198,848 bytes (about 172.80 MiB), including the largest case, history, original/restored worlds and serialization buffers. Process wall time is 1,303.82 ms; it is different from the measured advance interval. Sampling every 5 ms can miss a brief peak.

The retained S1 fixed-active benchmark still processes only 32 active actors against 32 / 2,000 / 20,000 stored ants. Its advance p50 values are 23.4 / 19.0 / 17.7 us (p95 31.4 / 47.6 / 21.0 us), with no linear cost from copying the stored population. Sparse local sensing uses bounded cell visits with indexed lookup; observer summaries, checkpoint audits and history retention still scale with stored evidence. These observations do not prove asymptotic bounds from timing alone.

Retained scheduler p50 schedule/cancel costs are 0.269 / 0.319 / 0.379 us at 128 / 1,024 / 4,096 pending events. S0 diagnostics also passed: advance p50/p95 0.0302/0.0448 ms, 20,710-byte v3 checkpoint. These diagnostic values are not ecological throughput. Full-map, 20,000 active ants, geometry, LOD, Unity and GM performance are NOT RUN / outside S2.

## Issues resolved and limitations

Development regressions found and fixed a too-strict floating deposit check, short observation windows that had not reached return behavior, and seed/actor XOR stream permutation. Tests now cover exact saturated arithmetic, complete trips and seed-domain separation. CI found GCC misleading-indentation diagnostics in compact adjacent loops; statements were separated without disabling warnings. Conditional collection statistics now distinguish absent observations from zero-length work.

Remaining limits are explicit:

1. Static flat cardinal surface only, no dynamic obstacles, ant collision, full 3D navigation, excavation or SDF. One food source per cell; setup-only activation at the physical nest.
2. The small local scalar trail model has no direction or diffusion and did not improve standalone delivery in this matrix. This is a review item for future model/calibration work, not an excuse to change the S2 data or silently extend scope.
3. Bounded homing is always present; memory ablation only removes learned inter-trip routes. This is not a model of every real ant navigation strategy. Parameter values are uncalibrated engineering fixtures.
4. Checkpoint v3 rejects prior versions. Durable database history, save migration, history compaction and authenticated persistence remain later work. FNV is not authentication; history reconciliation is not general event sourcing.
5. History and transaction undo retention grow with executed work. Defaults are host safeguards; long runs or larger active populations need explicit budgets and appropriately sized AdvanceTo chunks. Runtime is single-writer, not thread-safe multi-writer.
6. Same-build determinism is verified; cross-platform floating-point bit identity, full-world/LOD equivalence and physiological accuracy are not claimed. No Unity, GM, network/model API or biological feeding/development module was added.

S2 implementation and evidence are prepared for Code Review. Stop here; S3 requires the user's next explicit authorization.
