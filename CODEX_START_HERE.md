# AntWorld: read before implementation

This is the v0.8 design and engineering handoff. S0/S1 are reviewed; S2 sensing, exploration and trails is the current authorized implementation batch, not a complete game.

## Architecture

- C++20 standalone Simulation Core is authoritative; Windows x64 is the first engineering target, with cross-platform headless verification encouraged.
- Unity and C# provide the client, outside S0.
- The Game Master is a persistent observer across independent worlds. It can use player-equivalent game tools; autonomous environmental changes require authorization. Its harness language remains undecided.
- Persistence separates checkpoints, committed history and aggregates; SQLite is the initial application-layer candidate.
- InitialSolid plus ordered parametric edits is authoritative geometry. Local SDF, navigation and meshes are derived.
- The first complete world targets 24 x 24 meters, expandable chunks, multiple colonies and L0-L3 precision. S0 establishes only the empty headless foundation.

## Reading order

1. AGENTS.md: boundaries and repository rules.
2. docs/01_Decision_Register.md: confirmed, proposed and superseded decisions.
3. docs/16_Implementation_Freeze_and_ADRs.md: engineering defaults and invariants.
4. docs/17_Core_Data_Contracts.md: identity, units, state, events and ownership.
5. docs/18_Scheduler_Transactions_and_Determinism.md: ordering and commits.
6. docs/23_S0_Exact_Tasks_and_Test_Cases.md: first-batch behavior.
7. docs/22_Development_Roadmap_and_Execution_Gates.md: current stage boundaries.
8. docs/24_Traceability_and_Quality_Gates.md: acceptance and audit.
9. Biology, geometry and Game Master topics as required by the active stage.
10. docs/26_S1_Implementation_Decisions.md and S1_RESULTS.md for retained transaction foundations.
11. docs/27_S2_Implementation_Decisions.md and S2_RESULTS.md for local behavior, fixtures and current evidence.

## Current implementation gate

S1 passed Code Review and the user explicitly authorized S2. Preserve the S0/S1 mechanisms and regression tests; implement only local sensing, exploration, sparse surface trails, bounded memory and autonomous collection/return. Produce S2_RESULTS.md with multi-seed ablations, Debug/Release/sanitizer and performance evidence, then stop for review. S0_RESULTS.md and S1_RESULTS.md remain historical reports. S3 requires a separate user decision.

P0 is the later integrated vertical slice: foraging, nutrition, brood, excavation, statistics and history. S0 is only its foundation. Species parameters without appropriate evidence remain engineering assumptions. The complete map, 20,000 ants, finished graphics and mature GM personality are long-term targets, not S0 acceptance criteria.

## Reporting and authority

Report completed scope, changed files, exact build commands, PASS/FAIL/NOT RUN results, assumptions and ADRs, remaining issues, and the next gate.

Preserve confirmed user intent. Do not invent mechanics, evidence or approvals. Keep the design in version control and document deviations from defaults in an ADR. All tracked content and commit messages must be English; user communication is Chinese. The original source archive is retained locally, untracked.
