# AntWorld

An autonomous ant ecosystem simulation with an authoritative C++ core, a future Unity/C# client and an evidence-based Game Master. The current implementation is **S1 entities and action transactions**: stable ant/colony/food identities, fixture lifecycle, validated movement, deterministic food competition, conserved material and headless checkpoints. Autonomous behavior, calibrated biology, 3D excavation, Unity, database and Agent integrations are later stages.

## Build and test on Windows x64

The portable toolchain lives under ignored `.tools/`; no global installation or persistent PATH changes are required. Bootstrap downloads fixed official releases and verifies SHA-256. Subsequent builds work offline.

```powershell
./tools/bootstrap_windows.ps1
./tools/build_windows.ps1 -Configuration Debug
./tools/build_windows.ps1 -Configuration Release
./tools/build_windows.ps1 -Configuration Debug -BuildDirectory build/sanitized -Sanitizers
./build/release/antworld_headless.exe --scenario scenarios/p0_smoke.json --advance-ms 60000 --output out/smoke.json
./build/release/antworld_s1_tests.exe COMPETITION
./tools/benchmark_s1_windows.ps1
```

Normal LLVM-MinGW builds link their C++ runtime statically, so the executable can run without the compiler directory on PATH. `--help` lists options. `--diagnostic-events 8` optionally schedules eight explicitly synthetic infrastructure events that draw RNG values at milliseconds 1 through 8. This does not simulate ants.

The diagnostic CLI keeps the S0 empty-scenario profile; `--advance-ms` overrides its observation target. JSON stdout and files are reproducible. Nonempty biological JSON scenarios are still rejected: S1 fixtures use the C++ API/test runner, not a broader scenario importer. See [the diagnostic profile](docs/25_S0_Implementation_Decisions.md) and [S1 contracts/ADRs](docs/26_S1_Implementation_Decisions.md).

## Other C++20 environments

The core and CLI depend only on the standard library. No dependency download occurs during CMake configure/build.

```sh
cmake -S cpp -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build
ctest --test-dir build --output-on-failure
```

For multi-configuration generators, select the same configuration when building and testing, for example `--config Debug` and `ctest -C Debug`. Use `-DANTWORLD_SANITIZERS=ON` with Clang/GCC for ASan/UBSan. Actual tested platforms/compilers and CI status are recorded in [S1_RESULTS.md](S1_RESULTS.md); [S0_RESULTS.md](S0_RESULTS.md) preserves the historical baseline.

## Minimal S1 use

```cpp
#include "antworld/core/world_runtime.hpp"
using namespace antworld;
WorldRuntime world({1, 2}, 12345); // ENGINEERING_FIXTURE world and seed.
auto colony = world.seed_colony();
auto first = world.seed_ant(colony, {});
auto second = world.seed_ant(colony, {});
auto food = world.seed_food({}, {1000, 1000, 1000, 1000}); // Integer micrograms.
world.submit({first, {10}, ActionKind::CollectFood, food, {}, 3000});
world.submit({second, {10}, ActionKind::CollectFood, food, {}, 3000});
world.advance_to({10});
auto balance = world.summary().food_ledger; // 4000 ug carried, zero remaining.
auto facts = world.events_after({0}, 100);  // Actual seeds and committed outcomes.
auto checkpoint = world.checkpoint();
```

Every numeric fixture is engineering-only. A proposal is pending until advance commits it. One request receives 3000 ug and the other 1000 ug under the deterministic resource tie-break. No colony pool is credited. Use `query_ant`, `query_colony`, `query_food` for detached rows; `summary()` reads constant-size metadata, while `snapshot()` additionally computes whole-state/trace audit hashes. Same-time late actions cannot reopen an already resolved batch.

## Structure and guarantees

- `cpp/include/antworld/core/`: typed IDs/time, entities, proposals/facts, RNG and the world owner.
- `cpp/src/`: deterministic scheduling, validated mutation and versioned checkpoint codec.
- `cpp/apps/`: diagnostic CLI/parser, scheduler comparison and S1 transaction benchmarks.
- `cpp/tests/`: retained T00-T13, S1 invariants, corruption and allocation-failure regression tests.
- `docs/`: English product design, contracts, historical context and implementation decisions.
- `scenarios/`, `schemas/`: original engineering fixtures and the broader P0 schema.
- `contracts/`: future C ABI draft, not an implemented native plugin.

All runtime writes use an undo-journal single-writer transaction, with no whole-State copies. Failed writes/loads leave the prior authoritative world unchanged. Schema/physics v2 checkpoints retain entities, pending proposals, facts, material, IDs, clock/RNG and the phase watermark. S0 v1 saves are explicitly rejected. FNV hashes detect accidental corruption, not forgery. RuntimeLimits exposes temporary host budgets; the defaults of 65,536 records, 1,024 events per timestamp and 16 MiB saves are configurable, not permanent game/format constraints. Long-world history retention is later work.

## Verification and repository policy

Use Python 3.10+ for repository maintenance tools (not needed by the C++ runtime):

```sh
python tools/update_handoff_manifest.py
python tools/verify_handoff.py
python tools/check_repository.py
```

The language scan checks tracked UTF-8 files and commit messages for leftover CJK text; manual review still determines English prose quality. Stage deletions/renames before scanning. The original Chinese archive remains locally under ignored `handoff/`, with pre-policy Git history preserved. All current tracked content, code/comments, documentation and commit messages are English. User conversation is Chinese.

Run `antworld_scheduler_benchmark` for queue scaling, `antworld_s1_benchmark` for fixed active transactions against varying stored populations, and `antworld_benchmark` for the retained diagnostic timing. `tools/benchmark_s1_windows.ps1` builds the reviewed S0 sources with the identical scheduler harness and records sampled process memory. These fixtures do not establish full-colony or whole-map performance. See [the roadmap](docs/22_Development_Roadmap_and_Execution_Gates.md). Stop after S1 and obtain the next review before starting S2.

## License

The repository retains the remote baseline's [GNU GPL v3 license](LICENSE).
