# AntWorld

An autonomous ant ecosystem simulation with an authoritative C++ core, a future Unity/C# client and an evidence-based Game Master. The current implementation is **S6.1 integrated ecology corrections**, awaiting independent review. Local gift priority and nursing continuation improve the reviewed supplied fixture, but scarcity/density counterexamples remain. Contact selection preserves exact simulation semantics; the frozen latency-growth target still fails. See [S6.1 results](S6_1_RESULTS.md), [frozen protocol](docs/37_S6_1_Corrections_Validation_Protocol.md), [implementation and metrics](docs/38_S6_1_Implementation_and_Metric_Definitions.md), [raw evidence/reproduction](experiments/s6_1/README.md) and [remaining debts](docs/08_Open_Questions.md). All 124 S0-S6 tests and original [S6 evidence](S6_RESULTS.md) remain, with 11 new tests. Engineering correctness passes; the complete frozen acceptance gates **FAIL** because TD-01 remains unmet. All biological mechanisms remain ENGINEERING_FIXTURE. Finite extended colonies die; sustainable growth and calibrated biology are not established. S7 is not authorized.

## Build and test on Windows x64

The portable toolchain lives under ignored `.tools/`; no global installation or persistent PATH changes are required. Bootstrap downloads fixed official releases and verifies SHA-256. The default S5 application build also fetches a pinned SQLite amalgamation on first configuration; see the offline option below.

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
./build/release/antworld_s5_experiment.exe out/s5-experiments 32
python tools/analyze_s5.py --check
./build/release/antworld_s6_experiment.exe out/s6-smoke 1 smoke
python tools/analyze_s6.py --check
./build/release/antworld_archive.exe create out/world.sqlite scenarios/p0_smoke.json
./build/release/antworld_archive.exe inspect out/world.sqlite 381b1f47-91b8-4b2d-9d51-967a3e2b2a01
```

Normal LLVM-MinGW builds link their C++ runtime statically, so the executable can run without the compiler directory on PATH. `--help` lists options. `--diagnostic-events 8` optionally schedules eight explicitly synthetic infrastructure events that draw RNG values at milliseconds 1 through 8. This does not simulate ants.

The diagnostic CLI keeps the S0 empty-scenario profile; `--advance-ms` overrides its observation target. JSON stdout and files are reproducible. Nonempty biological JSON scenarios are still rejected: S1 uses the C++ API/test runner, and `antworld_s2_experiment` runs the reproducible autonomous fixtures. See [S1 contracts](docs/26_S1_Implementation_Decisions.md), [S2 decisions](docs/27_S2_Implementation_Decisions.md) and [the complete experiment data](experiments/s2/README.md).

## Other C++20 environments

The core and diagnostic CLI depend only on the standard library. The independent `antworld_storage` application library uses SQLite 3.54.1, pinned by archive SHA-256. A normal first configure downloads that archive from sqlite.org. `-DANTWORLD_SQLITE_ARCHIVE=/path/to/sqlite-amalgamation-3540100.zip` uses a verified local copy; `-DANTWORLD_STORAGE=OFF` builds the core without SQLite or a dependency download.

```sh
cmake -S cpp -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build
ctest --test-dir build --output-on-failure
```

For multi-configuration generators, select the same configuration when building and testing, for example `--config Debug` and `ctest -C Debug`. Use `-DANTWORLD_SANITIZERS=ON` with Clang/GCC for ASan/UBSan. Current tested platforms/compilers and CI status are recorded in [S6_1_RESULTS.md](S6_1_RESULTS.md); earlier reports preserve their historical baselines.

## Minimal S5 persistence use

```cpp
#include "antworld/storage/store.hpp"
using namespace antworld;
WorldRuntime world({1, 2}, 1); // ENGINEERING_FIXTURE world and seed.
auto colony = world.seed_colony();
auto worker = world.seed_ant(colony, {});
storage::Store archive("world.sqlite");
auto token = archive.save(world); // Returns only after the atomic commit.
world.advance_to({1000});
token = archive.save(world, token); // Rejects stale writers or a divergent timeline.
auto recovered = archive.load(world.summary().world);
auto coverage = archive.coverage(recovered.token.world);
auto facts = archive.history({recovered.token.world});
auto individual = archive.individual(worker);
auto observations = archive.series(recovered.token.world, colony.id,
    storage::Metric::WorkerAlive, {0}, {1001});
```

Link `antworld_storage`; the core itself never opens a database. The application owns one writer and calls save only at committed boundaries. Default retention keeps two complete checkpoint generations and all factual history, observations and receipts. A COMMIT I/O error raises `RecoveryRequired`: reopen and recover before further writes because the outcome may be a complete old or complete new generation. Queries expose durable coverage; gauges are sampled states and flows use half-open windows. Units and evidence semantics are defined in document 34.

`antworld_archive create`, `advance` and `inspect` provide a durable command-line workflow. Creation uses the existing empty-world JSON scenario profile; populated experiments use the C++ API. SQLite WAL files belong to an active database; use a closed/checkpointed database or a SQLite-aware backup, not a live main-file-only copy. Storage is local to one host. Physical power-loss testing, asynchronous save orchestration and long-term evidence pruning remain future work.

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
- `cpp/storage/`: separate SQLite persistence, historical evidence and defined analytics.
- `cpp/apps/`: diagnostic CLI/parser, S2 experiments and scheduler/entity/active-forager benchmarks.
- `cpp/tests/`: retained T00-T13 and S1 invariants, plus S2 local behavior, corruption and allocation-failure regression tests.
- `experiments/s2/`: complete seed/treatment CSVs and reproducible analysis.
- `experiments/s2_1/`: frozen baseline, matched recruitment/decay controls, retained ablations, uncertainty tables and figures.
- `experiments/s5/`: all 128 durable comparisons, complete storage/performance matrices, provenance, plots and reproduction records.
- `docs/`: English product design, contracts, historical context and implementation decisions.
- `scenarios/`, `schemas/`: original engineering fixtures and the broader P0 schema.
- `contracts/`: future C ABI draft, not an implemented native plugin.

Core runtime mutations use an undo-journal single-writer transaction. Failed mutations/loads leave prior authority unchanged. Schema 6 / physics 7 checkpoints retain entities, nutrition, lifecycle, clock/RNG, phase watermark, surface behavior and trails, plus initial geometry, ordered edits, material provenance/parcels, ledgers, soil requests, excavation memory/schedules and the typed command receipt ledger. The explicit durable-command helper uses a separate application-owned checkpoint candidate and publishes it only after successful persistence. Derived indices rebuild on load; SDF warmness is not authoritative. Earlier schemas are explicitly rejected; there is no silent migration. FNV hashes detect accidental corruption, not forgery. RuntimeLimits exposes temporary host budgets, including geometry partition, index, cache and navigation limits. Record/event/save defaults are configurable, not permanent game/format constraints. Every authoritative geometry edit remains; only superseded identical boxes are omitted from a disposable query index. General history compaction and bounded long-world evidence retention remain open.

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
python tools/analyze_s5.py --check
```

The language scan checks tracked UTF-8 files and commit messages for leftover CJK text; manual review still determines English prose quality. Stage deletions/renames before scanning. The original Chinese archive remains locally under ignored `handoff/`, with pre-policy Git history preserved. All current tracked content, code/comments, documentation and commit messages are English. User conversation is Chinese.

Run `antworld_scheduler_benchmark` for queue scaling, `antworld_s1_benchmark` for fixed active transactions against varying stored populations, `antworld_s2_benchmark` for 16/128/512 autonomous workers, and `antworld_benchmark` for retained diagnostics. `antworld_s3_benchmark` measures active physiology/nursing; `antworld_s4_benchmark` measures geometry commits, exact queries, SDF, navigation, saves and local/dense neighborhoods. S5 benchmarks measure durable geometry histories and a diagnostic storage clock. These fixtures do not establish full-colony or whole-map performance. Stop after S5 and obtain independent review before starting S6.

## License

The repository retains the remote baseline's [GNU GPL v3 license](LICENSE).
