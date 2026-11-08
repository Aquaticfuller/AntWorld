# Implementation baseline and architectural defaults (v0.8)

The freeze limits the first authorized implementation, not all future world rules or scientific calibration. Confirmed/proposed/to-validate/superseded distinctions in document 01 remain binding.

## Confirmed constraints

An open autonomous world without player/LLM worker command; explainable local behavior; persistent individual identity from egg to death; observation without biological advantages; eventual expandable 24 x 24 meter multi-colony world; true 3D InitialSolid plus ordered edits; derived SDF/nav/mesh; independent authoritative C++ core; Unity presentation; cross-world persistent GM with evidence and permissioned autonomous changes; honest historical precision.

## P0 versus S0

P0 eventually combines headless time/RNG/IDs/events, verified food/transfers/development, minimal excavation, facts/metrics and recovery into a controlled causal chain. It excludes complete-map ecology, every species, full water/heat PDEs, detailed real-time collisions, finished art/voice and mature GM infrastructure.

S0 is narrower: CMake, empty world, time, IDs, RNG, event queue, diagnostics, snapshots/checkpoints and tests. No foraging, ecosystem behavior, SDF, Unity or AI code.

## Reviewable engineering defaults

| ADR | Decision | Reason / review boundary |
|---|---|---|
| ADR-001 | C++20, CMake >=3.24, CTest; Windows x64 first, headless Linux checks encouraged | Independent core; other platforms are not excluded |
| ADR-002 | Standard C++ core only; optional precisely pinned/cacheable GoogleTest | Small offline-capable build; avoid unnecessary frameworks |
| ADR-003 | Strong int64 milliseconds | Causal ordering and persistence; resolution is not update frequency; changes need schema migration |
| ADR-004 | Single-writer commits | Correctness before parallel proposal generation |
| ADR-005 | `(time, phase, priority, tie, sequence)` order; seeded stable competition shuffle later | Reproducibility without permanently favoring low IDs |
| ADR-006 | 128-bit WorldId, non-reused uint64 local IDs, world-qualified references | World isolation and persistent identity |
| ADR-007 | Dimensioned doubles for continuous quantities; integer microgram food/soil/water ledgers | Avoid negative/duplicated stock and implicit unit mixing; signedness is explicit per contract |
| ADR-008 | Complete in-memory checkpoint first; later application-layer SQLite atomic snapshot/cursor transaction | Core independent of database; high-level journal is not full replay |
| ADR-009 | C ABI v1 draft now, integration later | Stabilize internal behavior before cross-language work |
| ADR-010 | Version/source-qualified biological parameters | ENGINEERING_FIXTURE unless actually LITERATURE_CALIBRATED |
| ADR-011 | Controlled small scene before LOD/multi-colony/full map | Localize errors without abandoning full-world goals |
| ADR-012 | One implementation stage per review | Runnable tests and evidence before a new stage |

S0-specific codec, RNG, failure semantics, CLI profile and toolchain choices are recorded in 25_S0_Implementation_Decisions.md.

## Contract invariants

Never reuse identity or create a new individual on stage transition. Commit death once. All shared material changes use the same arbitration/ledger path. Digging accounts only actual remaining material intersection, with geometry/event/ledger committed together. Time cannot reverse and dead entities cannot act. Reads/cameras/GM do not consume world RNG. Identical CommandId/payload succeeds once; changed payload conflicts. Checkpoints retain all implemented authoritative continuation state; future stages add geometry/commands when those systems exist. Performance is measured rather than promised.

## Non-blocking unknowns

Task thresholds, trophallaxis rates, SDF algorithms, pheromone calibration, Unity rendering, Agent harness and long-term storage budgets do not block S0. Product changes require a proposal and impact review. Engineering changes update ADRs, version rules and tests.

References: documents 01, 13-15; https://cmake.org/cmake/help/latest/manual/ctest.1.html ; https://github.com/google/googletest/blob/main/docs/quickstart-cmake.md ; Unity native plugin documentation. These are references, not mandatory additional dependencies.
