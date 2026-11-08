# AntWorld

An autonomous ant ecosystem simulation with an authoritative C++ core, a future Unity/C# client and an evidence-based Game Master. The current implementation is **S2.1 foraging model validation and fixes**, retaining S2 local sensing, exploration, physical food collection/return, sparse colony trails and bounded route memory. Equal food ties no longer prefer ResourceId, and fractional trail responses retain numerical precision. Controlled naive-worker experiments do not establish a reliable positive recruitment benefit. See [S2.1 results](S2_1_RESULTS.md) and [raw evidence and reproduction](experiments/s2_1/README.md). S0/S1 transactions, conservation and checkpoints remain. Physiology, 3D excavation, Unity, database and Agent integrations are later stages.

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
./build/release/antworld_s2_experiment.exe out/s2-experiments 16 1800000
python tools/analyze_s2.py out/s2-experiments
./tools/benchmark_s2_windows.ps1
./build/release/antworld_s2_1_experiment.exe out/s2_1-experiments 64 s2.1
python tools/analyze_s2_1.py --check
```

Normal LLVM-MinGW builds link their C++ runtime statically, so the executable can run without the compiler directory on PATH. `--help` lists options. `--diagnostic-events 8` optionally schedules eight explicitly synthetic infrastructure events that draw RNG values at milliseconds 1 through 8. This does not simulate ants.

The diagnostic CLI keeps the S0 empty-scenario profile; `--advance-ms` overrides its observation target. JSON stdout and files are reproducible. Nonempty biological JSON scenarios are still rejected: S1 uses the C++ API/test runner, and `antworld_s2_experiment` runs the reproducible autonomous fixtures. See [S1 contracts](docs/26_S1_Implementation_Decisions.md), [S2 decisions](docs/27_S2_Implementation_Decisions.md) and [the complete experiment data](experiments/s2/README.md).

## Other C++20 environments

The core and CLI depend only on the standard library. No dependency download occurs during CMake configure/build.

```sh
cmake -S cpp -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build
ctest --test-dir build --output-on-failure
```

For multi-configuration generators, select the same configuration when building and testing, for example `--config Debug` and `ctest -C Debug`. Use `-DANTWORLD_SANITIZERS=ON` with Clang/GCC for ASan/UBSan. Current tested platforms/compilers and CI status are recorded in [S2_1_RESULTS.md](S2_1_RESULTS.md); S0_RESULTS.md, S1_RESULTS.md and S2_RESULTS.md preserve the historical baselines.

## Minimal autonomous S2 use

```cpp
WorldRuntime world({1, 2}, 12345); // ENGINEERING_FIXTURE.
world.configure_surface({{0, 0, 0}, 7, 1, 0.01}, {});
auto colony = world.seed_colony({0, 0, 0});
auto worker = world.seed_ant(colony, {{0, 0, 0}, LifeStage::Adult, Caste::Worker, 1000});
world.seed_food({0.06, 0, 0}, {100000, 0, 0, 0});
world.start_foraging(worker);
world.advance_to({60000});
auto observations = world.sense(worker); // Reachable local cues only; no writes.
auto measurements = world.surface_snapshot(); // Observer metrics, not policy input.
auto inventory = world.query_colony(colony)->nest_food;
```

Include `antworld/core/world_runtime.hpp` and use namespace `antworld`. First activation is allowed at the worker's nest during setup or later for a previously dormant worker; it cannot reset an existing forager. The individual model then owns its wake/action schedule. The memory ablation removes learned inter-trip routes while retaining a bounded current-trip homing trace. No controller assigns food destinations.

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
- `cpp/apps/`: diagnostic CLI/parser, S2 experiments and scheduler/entity/active-forager benchmarks.
- `cpp/tests/`: retained T00-T13 and S1 invariants, plus S2 local behavior, corruption and allocation-failure regression tests.
- `experiments/s2/`: complete seed/treatment CSVs and reproducible analysis.
- `experiments/s2_1/`: frozen baseline, matched recruitment/decay controls, retained ablations, uncertainty tables and figures.
- `docs/`: English product design, contracts, historical context and implementation decisions.
- `scenarios/`, `schemas/`: original engineering fixtures and the broader P0 schema.
- `contracts/`: future C ABI draft, not an implemented native plugin.

All runtime writes use an undo-journal single-writer transaction, with no whole-State copies. Failed writes/loads leave the prior authoritative world unchanged. Schema 3 / physics 4 checkpoints retain entities, nest material, pending proposals, facts, IDs, clock/RNG, the phase watermark, surface, bounded memories, sparse trails and evidence counters. Earlier physics versions, including S2 physics 3, are explicitly rejected; there is no silent migration. FNV hashes detect accidental corruption, not forgery. RuntimeLimits exposes temporary host budgets; the defaults of 65,536 records, 1,024 events per timestamp and 16 MiB saves are configurable, not permanent game/format constraints. Long-world history retention is later work.

## Verification and repository policy

Use Python 3.10+ for repository maintenance tools (not needed by the C++ runtime):

```sh
python tools/update_handoff_manifest.py
python tools/verify_handoff.py
python tools/check_repository.py
python tools/analyze_s2.py experiments/s2 --check
python tools/analyze_s2.py experiments/s2_1/ablations --check
python tools/analyze_s2_1.py --check
```

The language scan checks tracked UTF-8 files and commit messages for leftover CJK text; manual review still determines English prose quality. Stage deletions/renames before scanning. The original Chinese archive remains locally under ignored `handoff/`, with pre-policy Git history preserved. All current tracked content, code/comments, documentation and commit messages are English. User conversation is Chinese.

Run `antworld_scheduler_benchmark` for queue scaling, `antworld_s1_benchmark` for fixed active transactions against varying stored populations, `antworld_s2_benchmark` for 16/128/512 autonomous workers, and `antworld_benchmark` for retained diagnostics. `tools/benchmark_s2_windows.ps1 -OutputDirectory out/s2_1-performance` records sampled process memory. These fixtures do not establish full-colony or whole-map performance. See [the roadmap](docs/22_Development_Roadmap_and_Execution_Gates.md). Stop after S2.1 and obtain the next review before starting S3.

## License

The repository retains the remote baseline's [GNU GPL v3 license](LICENSE).
