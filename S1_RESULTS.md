# S1 results

Date: 2026-11-08. Branch: `codex/s1-transactions`. Reviewed S0 baseline: `548df2d2d76a0c3c505669f11af0199fec02ae83`. Final code under test: **`49cda7c25ee3b476e6b165e9e774e5a2245ba243`**. Initial implementation: `3ab300e`; CI diagnostics follow-up: `6638a8f`; MSVC allocation-failure correction: `49cda7c`. This is a subsequent documentation-only report.

## Scope and S0 review response

Implemented S1 only: Ant, Colony and FoodSource stores with typed world-qualified references; stable lifetime identity; explicit engineering lifecycle fixtures; Move and CollectFood proposals; validation, deterministic arbitration, committed outcomes and ingredient-level conservation; detached queries, paged facts and full continuation checkpoints. The C++20 core still depends only on the standard library and runs without Unity, Game Master, network APIs or model services.

1. **Whole-State copy cost:** State is now noncopyable. Single-writer transactions retain only metadata, touched row before-images, append lengths and queue edits. Removed map nodes support allocation-free rollback. Cancellation has an ID index. Allocation-failure sweeps verify rollback at each allocation point for creation, growth, scheduling, cancellation, advance and load.
2. **Cross-AdvanceTo ordering:** checkpoints retain a full EventKey watermark and cumulative event count for the current timestamp. Scheduling before the watermark is rejected, including earlier priority/tie within a phase. A resolved action batch closes phases 0-4 at that timestamp. Reloading cannot reopen phases or reset the same-time guard.
3. **Engineering completeness:** RuntimeLimits makes S0 record/save bounds configurable host budgets. A regression successfully restores 150,000 pending events in a 17,250,325-byte checkpoint with raised limits; defaults reject it atomically. CI includes Linux and Windows Debug/Release plus Linux ASan/UBSan, with pinned action code. S0 tests are retained.

Exact decisions and binary layout are in [document 26](docs/26_S1_Implementation_Decisions.md). Schema/physics versions increase to **2**; S0 v1 saves are explicitly rejected with no migration. The historical [S0 results](S0_RESULTS.md) remain unchanged.

## Files and interfaces changed

| Area | Files / behavior |
|---|---|
| Public core | `types.hpp`, new `entities.hpp`, `event.hpp`, `world_runtime.hpp`: typed references, seed/configuration/limit data, proposals/outcomes, entity/material summaries and paged events |
| Transactions | `cpp/src/state.hpp`, `world_runtime.cpp`: grouped ant SoA, indexed dense stores, undo journal, persistent phase boundary, lifecycle/movement/collection |
| Persistence | `cpp/src/checkpoint.cpp`: v2 canonical codec, atomic replacement, entity/ledger/phase/history checks |
| Regression tests | `cpp/tests/test_s1.cpp`, `test_allocation_failure.cpp`, existing `test_core.cpp` |
| Build/performance | `cpp/CMakeLists.txt`, `antworld_scheduler_benchmark.cpp`, `antworld_s1_benchmark.cpp`, `tools/benchmark_s1_windows.ps1` |
| CI | `.github/workflows/ci.yml`, `tools/ci_test.py` |
| Design/documentation | `AGENTS.md`, `CODEX_START_HERE.md`, README files, documents 00/18/24/25/26, changelog and regenerated handoff manifest |

New runtime operations: seed_colony, seed_ant, seed_food, submit, schedule_lifecycle, query_ant/colony/food, summary, config and events_after. Existing diagnostic APIs remain. C++ interfaces are internal application APIs; the future C ABI draft is unchanged and unimplemented.

## Local environment and commands

Windows x64, LLVM-MinGW 20261104 / Clang 23.1.5, CMake 3.31.10, Ninja 1.13.2. This is the same i7-13620H machine recorded in S0_RESULTS.md. C++20 with warnings treated as errors (`-Wall -Wextra -Wpedantic -Wconversion -Wsign-conversion -Werror`). Portable compiler/download versions and hashes remain in the bootstrap script. No global tool installation or PATH change is required.

Executed from the repository root:

```powershell
./tools/build_windows.ps1 -Configuration Debug
./tools/build_windows.ps1 -Configuration Release
$env:ASAN_OPTIONS = 'halt_on_error=1'
$env:UBSAN_OPTIONS = 'halt_on_error=1:print_stacktrace=1'
./tools/build_windows.ps1 -Configuration Debug -BuildDirectory build/sanitized -Sanitizers
./tools/benchmark_s1_windows.ps1
./build/release/antworld_allocation_tests.exe
./build/release/antworld_s1_tests.exe FAIRNESS
./build/release/antworld_s1_tests.exe BUDGETS
python tools/update_handoff_manifest.py
python tools/verify_handoff.py
python tools/check_repository.py
git diff --check
```

Python maintenance commands used the available Python 3 runtime; the core does not require Python. Local build and CTest logs are under ignored `out/s1-debug.txt`, `out/s1-release.txt`, `out/s1-sanitized.txt`; raw benchmark outputs are in `out/s1-performance/`.

A separate clean-source Release build exported committed files with `git archive --format=tar --output=out/s1-clean-final.tar 49cda7c cpp scenarios`, extracted into `out/s1-clean-final`, then configured with `cmake -S out/s1-clean-final/cpp -B out/s1-clean-final/build -G Ninja -DCMAKE_BUILD_TYPE=Release` and the same explicit portable C++ compiler/Ninja paths used by the build script. Executed `cmake --build out/s1-clean-final/build --parallel 4` and `ctest --test-dir out/s1-clean-final/build --output-on-failure`. No untracked source files were available to that build. Full local output is in `out/s1-clean-final.txt`.

## Executed local validation

| Configuration | Result | CTest elapsed |
|---|---|---:|
| Debug | PASS, 28/28 | 7.20 s |
| Release | PASS, 28/28 | 2.19 s |
| Debug ASan + UBSan, halt on first finding | PASS, 28/28, no reported findings | 17.64 s |
| Clean exported source, Release | PASS, 28/28 | 2.30 s |
| Handoff manifest | PASS, 39 files | n/a |
| English tracked-file/commit scan | PASS, 73 UTF-8 files, zero binaries | n/a |

Elapsed times are observations, not performance acceptance thresholds. Local sanitizer coverage is address/undefined behavior; Linux CI additionally enables LeakSanitizer. No ThreadSanitizer claim is made for the single-threaded runtime.

| Test | Main coverage | Local Debug / Release / sanitizer |
|---|---|---|
| S1_ENTITIES | Stable IDs, species fixture label, counts, cross-world rejection, detached/query invariance, event paging | PASS / PASS / PASS |
| S1_MOVEMENT | Pending vs arrival, duration/speed/bounds, NaN rejection, stale position, closed boundary | PASS / PASS / PASS |
| S1_COMPETITION | 3000 + 3000 ug requests from 4000 ug, partial result, input-order independence, deterministic replay | PASS / PASS / PASS |
| S1_FAILURES | Capacity, distance, brood/caste rejection and one action per actor/boundary | PASS / PASS / PASS |
| S1_FAIRNESS | 256 seeds and 256 timestamp fixtures; neither actor has permanent ID priority | PASS / PASS / PASS |
| S1_LIFECYCLE | Continuous Egg-to-Adult ID, invalid skips, one death fact, death before same-time action, retained cargo | PASS / PASS / PASS |
| S1_PHASES | Earlier phase/priority/tie rejection across calls/reloads, action-group closure, cumulative runaway budget | PASS / PASS / PASS |
| S1_ROLLBACK | Late failure after RNG/food changes, failed seeding, rollback across earlier timestamps | PASS / PASS / PASS |
| S1_PERSISTENCE | Pending proposals and lifecycle, chunked loaded continuation, corruption/missing actors/forged material/version rejection | PASS / PASS / PASS |
| S1_ARITHMETIC | Per-ingredient conservation, 256 independent bounded-product references, uint64 maximum and overflow, remainder ties | PASS / PASS / PASS |
| S1_BUDGETS | 150,000 pending records, >16 MiB checkpoint, raised/default policy behavior and ID-index restoration | PASS / PASS / PASS |
| S1_ALLOCATION_FAILURE | Every allocation point until success for nine mutation/load scenarios; exact checkpoint rollback | PASS / PASS / PASS |
| T00-T13, CLI_VALIDATION, CORE_EDGE_CASES | All 16 existing S0 CTest registrations retained | PASS / PASS / PASS |

The intentional S0 regression update is CORE_EDGE_CASES: scheduling priority zero after priority nine at the same timestamp now must fail; a legal later full key must still execute. No S0 test was removed or disabled.

Fairness counts: seed sweep **141 / 115**, timestamp sweep **130 / 126**. These deterministic distribution guards establish variation, not ecological calibration or proof of statistical uniformity.

Allocation-failure points exercised locally: seed_ant 2, seed_colony 2, seed_food 2, SoA column growth 5, schedule 3, submit 3, cancel 1, multi-event advance 17, restore 95. Allocator counts can differ by standard library/build mode; acceptance is successful rollback at every tested failure, followed by an uninjected success.

## GitHub Actions

The [final code verification run](https://github.com/Aquaticfuller/AntWorld/actions/runs/42444978977) completed successfully on commit `49cda7c`. All five jobs passed:

| Hosted job | Result |
|---|---|
| Windows Server 2022 / MSVC Debug | PASS, all 28 CTest cases |
| Windows Server 2022 / MSVC Release | PASS, all 28 CTest cases |
| Ubuntu 24.04 / default C++ compiler Debug | PASS, all 28 CTest cases |
| Ubuntu 24.04 / default C++ compiler Release | PASS, all 28 CTest cases and all three benchmark programs |
| Ubuntu 24.04 / Clang ASan + UBSan, leak detection enabled | PASS, all 28 CTest cases |

Hosted compiler patch versions are supplied by the runner image and were not captured in this local report. The workflow pins external checkout code, not the hosted image's entire toolchain. Local portable tools are separately pinned with hashes.

The [initial run](https://github.com/Aquaticfuller/AntWorld/actions/runs/42443710542) and [diagnostic follow-up](https://github.com/Aquaticfuller/AntWorld/actions/runs/42444442628) are retained as failed evidence. Windows Debug timed out in S1_ALLOCATION_FAILURE; its other 27 tests passed. MSVC iterator debugging allocates proxies even in an empty vector's noexcept default constructor. Injecting failure there terminated instead of unwinding and waited on a CRT dialog. Core vectors now use the potentially throwing zero-count constructor; iterator checks remain enabled. The failure harness exits with a scenario/allocation diagnostic on unexpected termination. The full failing test then passed in Windows Debug; no test was skipped and the timeout was not relaxed. Checkout was also updated to a pinned Node.js 24 release to remove the runner's Node.js 20 deprecation warning.

## Release performance observations

All workloads are ENGINEERING_FIXTURE, measured locally without parallel builds. The scheduler harness is identical for S0 and S1 and uses only common APIs. The script exports the reviewed S0 commit and compiles it with the same Clang, C++20, `-O3 -DNDEBUG` and static runtime settings. Setup is excluded from timed operations. Each population uses 21 trials of 100 schedule/cancel pairs; no hard timing test is imposed.

| Existing pending events | S0 pair p50 / p95 (us) | S1 pair p50 / p95 (us) |
|---:|---:|---:|
| 128 | 8.657 / 9.623 | 0.236 / 0.386 |
| 1024 | 97.441 / 131.008 | 0.281 / 0.283 |
| 4096 | 331.551 / 374.199 | 0.314 / 0.315 |

The removal of whole-State copies and linear cancellation is visible in this workload. These numbers are not a universal speedup estimate.

S1 entity workload: 32 active workers collect 1 ug each at each of 256 boundaries (256 simulated seconds); additional ants remain idle. Every resulting checkpoint is restored and compared; total carried mass must be 8192 ug. This isolates costs of unrelated stored population from active work.

| Stored ants | Advance p50 / p95 (us) | Submit + advance p50 (us) | Sim s / advance wall s | Save bytes | Save / restore (ms) |
|---:|---:|---:|---:|---:|---:|
| 32 | 22.4 / 32.1 | 26.9 | 39218.1 | 1221054 | 3.7593 / 3.9900 |
| 2000 | 17.3 / 23.4 | 21.8 | 48419.7 | 1705182 | 5.1692 / 5.7966 |
| 20000 | 17.2 / 23.4 | 21.8 | 54439.1 | 6133182 | 18.7933 / 28.9695 |

The first row is affected by warmup/host timing variation and should not be interpreted as smaller populations being intrinsically slower. Save/load still scale with stored state/history. Simulated/wall ratios include only sparse advance work and exclude submission/setup, observation hashing and I/O; they do not predict a fully active colony.

The retained 64-trial diagnostic benchmark (128 diagnostic events/trial, 60 artificial simulated seconds) reports advance p50/p95 0.0286/0.0347 ms, save p50 0.0563 ms, restore p50 0.0361 ms, and 19,269 bytes. Its simulated/wall ratio is 2.03638e6, a diagnostic-only clock result.

Sampled process peak working sets (5 ms sampling of the OS high-water value): S0 scheduler 5,533,696 bytes; S1 scheduler 2,756,608 bytes; S1 entity benchmark 36,323,328 bytes; diagnostic benchmark 2,756,608 bytes. These include the process/runtime and can miss activity after the last sample. Process launch/wait time is not used as inner-operation throughput. No per-entity memory or full-world capacity claim is made.

## Limitations and next gate

- Movement is duration/speed/boundary-checked endpoint motion in an obstacle-free fixture AABB. There is no interpolation, contact sweep, obstacle navigation or autonomous choice.
- Lifecycle events are explicit fixtures for identity/death ordering, not biological timing or mortality. Only adult workers act. No calibrated Lasius niger values are supplied.
- Material remains in dead ants' inventories; corpse/drop/decay handling and crop/body-energy/physiology are deferred. There is no freely credited colony food pool.
- History/queues remain in memory under configurable host budgets. A long AdvanceTo retains an undo journal until it commits. Durable database saves, pruning, command authorization/idempotency and full event-sourcing are not implemented.
- S0 v1 checkpoint migration is NOT IMPLEMENTED. Invalid/incompatible files are rejected atomically. Cross-platform floating-point bit identity is NOT CLAIMED.
- The original diagnostic CLI still accepts only empty S0 JSON scenarios; S1 is exercised through its C++ API and test/benchmark fixtures. No expanded scenario importer is claimed.
- Unity, GM, SDF/geometry, pheromones, sensing, foraging, metabolism and later-stage tests are NOT RUN because those modules are out of S1 scope.

S1 is ready for the next Code Review: implemented mechanism gates SCH-03/06/07/08, query invariance, material accounting, rollback, continuation and the requested S0 follow-up checks pass. No known failing tests remain in the implemented scope. This establishes engineering mechanism validity, not biological plausibility or species calibration. S2 remains unauthorized in this run and will not be started automatically.
