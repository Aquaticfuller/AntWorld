# COPY THIS PROMPT INTO CODEX — ANTWORLD S0

You are taking over development of **AntWorld**. The repository contains a full v0.8 design baseline. Do not begin coding before reading `AGENTS.md`, `CODEX_START_HERE.md`, `docs/01_Decision_Register.md`, `docs/16_Implementation_Freeze_and_ADRs.md`, `docs/17_Core_Data_Contracts.md`, `docs/18_Scheduler_Transactions_and_Determinism.md`, `docs/23_S0_Exact_Tasks_and_Test_Cases.md` and `docs/24_Traceability_and_Quality_Gates.md`.

**Implement exactly S0. Do not implement S1 or later in this run.**

Objectives:
1. Create a C++20 CMake/CTest project with `antworld_core` library and `antworld_headless` command-line executable; no Unity, Python agent or cloud dependencies.
2. Define stable strong WorldId / EntityId / SimTime types with explicit units; deterministic WorldClock and world revision; an empty world runtime with typed read-only snapshot.
3. Implement a future event queue with `(time,phase,priority,tie,sequence)` deterministic ordering; reject events in the past and protect against same-time infinite scheduling.
4. Implement a versioned, reproducible pseudo-random algorithm with clear seed/state and fixed test vectors. Avoid relying on the cross-implementation behavior of `std::uniform_*`.
5. Create an in-memory round-trip checkpoint that retains world/time/revision, ID allocator, future event queue and RNG, and resumes to the same state. Detect invalid version/truncated data without altering the current world.
6. Provide a CLI accepting a deterministic smoke scenario and target simulation time, output a JSON summary and trace hash. You may adapt the provisional scenario schema only with a documented, reversible ADR.
7. Implement automated tests T00–T13 from `docs/23_S0_Exact_Tasks_and_Test_Cases.md`, or explicitly mark any test NOT RUN with reason. Verify no read operation advances time or consumes RNG.
8. Provide reproducible build and test instructions for the environment you actually used. Do not assert Windows/Unity have been tested if only Linux tests ran.

Strict boundaries:
- Do **not** implement ant behavior, full ECS, pheromone, dynamic geometry, nutrition, reproduction, persistence database, Game Master, Unity scene, GUI, voice or maps.
- Do **not** treat engineering fixture constants as measured Lasius niger biology.
- Do **not** change confirmed product decisions; record assumptions and conflicts in an ADR rather than silently overriding them.
- Do **not** claim tests passed unless actually run. Report PASS / FAIL / NOT RUN.
- Keep code clean and standalone; no hardcoded machine-specific absolute paths.

Deliverables: CMake C++ project, tests, headless CLI, a short usage README, `S0_RESULTS.md` with exact commands, tests and limitations; update affected docs/ADR only if needed.

**Stop after S0 and present the results for review.**
