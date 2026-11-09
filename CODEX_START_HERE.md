# AntWorld: read before implementation

This is the v0.8 design and engineering handoff. S6 received independent CONDITIONAL PASS, with S7 withheld. S6.1 engineering passed but the complete stage failed. The current authorized batch is S6.2 Performance Validation and Scarcity Diagnosis on codex/s6.2-performance-scarcity. Read frozen document 39 before new measurements or modifications. Preserve all S6 evidence and its unresolved nutrition/task coupling and missed contact scaling target. S7 is not authorized.

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
12. docs/28_S2_1_Validation_Protocol.md for the frozen validation plan, baseline evidence and minimal fixes; S2_1_RESULTS.md for the current review gate.
13. docs/29_S2_2_Validation_Protocol.md and docs/30_S2_2_Literature_and_Model_Rationale.md for the current frozen protocol and primary research.

## Current implementation gate

The user conditionally accepted S6 but withheld S7, authorizing only S6.1 corrections. Read S6_1_RESULTS.md and documents 37/38; preserve S6_RESULTS.md and frozen documents 35/36. Retain S5_RESULTS.md and documents 19/22/33/34 for persistence, document 31 for physiology and the original seed-43 defect, and document 32 for geometry. S6.1 preserves all 124 inherited tests and adds 11. Its two opt-in nursing corrections, semantic-preserving contact links and independent evidence audits do not establish calibrated biology. TD-01's final <=6x scaling target is still failed; do not replace that result with a favorable profile or relax the target without review. Preserve TD-03/06 history/storage limits, SD-01/02/06 scientific limits and every original negative outcome. Stop for independent review; S7 requires new user authorization.

P0 is the later integrated vertical slice: foraging, nutrition, brood, excavation, statistics and history. S0 is only its foundation. Species parameters without appropriate evidence remain engineering assumptions. The complete map, 20,000 ants, finished graphics and mature GM personality are long-term targets, not S0 acceptance criteria.

## Reporting and authority

Report completed scope, changed files, exact build commands, PASS/FAIL/NOT RUN results, assumptions and ADRs, remaining issues, and the next gate.

Preserve confirmed user intent. Do not invent mechanics, evidence or approvals. Keep the design in version control and document deviations from defaults in an ADR. All tracked content and commit messages must be English; user communication is Chinese. The original source archive is retained locally, untracked.
