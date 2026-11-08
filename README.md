# AntWorld

An autonomous ant ecosystem simulation with an authoritative C++ core, a future Unity/C# client and an evidence-based Game Master. The current implementation is **S4 3D excavation and connectivity**: ordered parametric box edits, exact soil inventories, conservative 3D clearance, versioned local portals, barrier-aware contact and disposable SDF caches. See [S4 results](S4_RESULTS.md), [frozen protocol](docs/32_S4_Implementation_and_Validation.md) and [reproduction](experiments/s4/README.md). All S0-S3 mechanisms, 71 inherited tests and original evidence remain. Long-distance trail following, social recruitment, nutrition redistribution and dense-contact scaling remain open in [document 08](docs/08_Open_Questions.md). S5 is not authorized.

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
./build/release/antworld_s2_1_experiment.exe out/s4-social-regression 64 s4
./build/release/antworld_s2_2_experiment.exe out/s2_2-local 512
python tools/analyze_s2_1.py --check
./build/release/antworld_s3_experiment.exe out/s3-reproduction 64
python tools/analyze_s3.py --check
./tools/benchmark_s3_windows.ps1
./build/release/antworld_s4_experiment.exe out/s4-reproduction 32
python tools/analyze_s4.py --check
./build/release/antworld_s4_benchmark.exe out/s4-performance.csv
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

For multi-configuration generators, select the same configuration when building and testing, for example `--config Debug` and `ctest -C Debug`. Use `-DANTWORLD_SANITIZERS=ON` with Clang/GCC for ASan/UBSan. Current tested platforms/compilers and CI status are recorded in [S4_RESULTS.md](S4_RESULTS.md); earlier reports preserve their historical baselines.

## Minimal S4 geometry use

```cpp
WorldRuntime world({1, 2}, 1); // ENGINEERING_FIXTURE, no calibrated excavation law.
GeometryConfig geometry;
const BoxQ room{{2, 2, 2}, {14, 22, 22}};
world.configure_geometry(geometry, std::span{&room, 1});
const PositionM depot{0.003, -0.010, 0.006};
auto colony = world.seed_colony(depot);
auto worker = world.seed_ant(colony, {depot, LifeStage::Adult, Caste::Worker, 20000});
world.enable_physiology(worker, {{500, 0, 500, 0}, 1000000000, 1000, 0});
world.set_behavior(worker, IndividualBehavior::Excavate);
world.advance_to({60000});
auto material = world.geometry_snapshot();
auto parcels = world.soil_parcels();
auto local_openings = world.query_portals(worker);
world.set_behavior(worker, IndividualBehavior::Paused); // Soil is retained.
```

Geometry must be configured before seeding entities. If a surface fixture is also present, configure it first. Geometry-world positions lie on `origin_m + PointQ * quantum_m`; boxes are half-open. Contact/movement uses exact authoritative material, never an SDF sample as an unchecked collision result. `query_route()` is a bounded observer query; the individual model uses local openings/frontiers and its experienced return trace. `submit_soil()` supports explicit Excavate/Drop/Pickup/Fill fixture proposals for paused workers, with real parcel ownership. Deposited parcels are physical inventories, not granular pile geometry. Cache rebuilding is explicit and cannot change ecological facts or canonical checkpoint bytes.

## Minimal S3 nutrition use

```cpp
WorldRuntime world({1, 2}, 43); // ENGINEERING_FIXTURE, no calibrated species rates.
auto colony = world.seed_colony();
auto nurse = world.seed_ant(colony, {});
auto egg = world.seed_ant(colony, {{}, LifeStage::Egg, Caste::Worker, 4000});
world.enable_physiology(nurse, {{100, 400, 400, 100}, 1000000000, 1000, 0});
world.enable_physiology(egg);
world.set_behavior(nurse, IndividualBehavior::Nurse);
world.advance_to({60000});
world.set_behavior(nurse, IndividualBehavior::Paused); // Metabolism continues.
auto energy_j = world.query_physiology(nurse)->body_energy_j();
auto balance = world.nutrition_snapshot();
auto checkpoint = world.checkpoint();
```

Initialize physiology at unexecuted time zero; choose runtime Paused/Rest/Nurse/Forage programs on individual adults. These are engineering experiment controls, not a colony commander or player labor-allocation UI. Pausing/switching cancels owned pending actions and preserves acquired routes and crop. First Forage activation needs an unloaded worker at its physical nest; resumption preserves its experienced path. Queries project continuous expenditure to the committed time without changing stored state, RNG or queue. In physiology-enabled worlds, the legacy `food_ledger` reports source/cargo/nest inventories; use `nutrition_snapshot()` for complete ingredient and energy balances.

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

All runtime writes use an undo-journal single-writer transaction, with no whole-State copies. Failed writes/loads leave the prior authoritative world unchanged. Schema 5 / physics 7 checkpoints retain entities, nutrition, lifecycle, clock/RNG, phase watermark, surface behavior and trails, plus initial geometry, ordered edits, material provenance/parcels, ledgers, soil requests and excavation memory/schedules. Derived indices rebuild on load; SDF warmness is not authoritative. Earlier schema/physics versions are explicitly rejected; there is no silent migration. FNV hashes detect accidental corruption, not forgery. RuntimeLimits exposes temporary host budgets, including geometry partition, index, cache and navigation limits. Record/event/save defaults are configurable, not permanent game/format constraints. Long-world history retention and geometry compaction remain later work.

## Verification and repository policy

Use Python 3.10+ for repository maintenance tools (not needed by the C++ runtime):

```sh
python tools/update_handoff_manifest.py
python tools/verify_handoff.py
python tools/check_repository.py
python tools/analyze_s2.py experiments/s2 --check
python tools/analyze_s2.py experiments/s2_1/ablations --check
python tools/analyze_s2_1.py --check
python tools/analyze_s2_2.py --check
python tools/analyze_s3.py --check
python tools/analyze_s4.py --check
```

The language scan checks tracked UTF-8 files and commit messages for leftover CJK text; manual review still determines English prose quality. Stage deletions/renames before scanning. The original Chinese archive remains locally under ignored `handoff/`, with pre-policy Git history preserved. All current tracked content, code/comments, documentation and commit messages are English. User conversation is Chinese.

Run `antworld_scheduler_benchmark` for queue scaling, `antworld_s1_benchmark` for fixed active transactions against varying stored populations, `antworld_s2_benchmark` for 16/128/512 autonomous workers, and `antworld_benchmark` for retained diagnostics. `antworld_s3_benchmark` measures active physiology/nursing; `antworld_s4_benchmark` measures geometry commits, exact queries, SDF, navigation, saves and local/dense neighborhoods. These fixtures do not establish full-colony or whole-map performance. Stop after S4 and obtain the next review before starting S5.

## License

The repository retains the remote baseline's [GNU GPL v3 license](LICENSE).
