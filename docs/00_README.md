# AntWorld design baseline and handoff v0.8

Archive date: 2026-11-08. The imported baseline was specification-only; implementation evidence is recorded separately in S0_RESULTS.md, S1_RESULTS.md and S2_RESULTS.md.

Product requirements, reversible engineering defaults and scientific assumptions are distinct. v0.8 preserves the earlier design and adds executable contracts, a first-batch task, test definitions and traceability.

## Current specification map

| File | Purpose |
|---|---|
| 01 | Confirmed requirements, suggestions and superseded decisions |
| 16 | Engineering defaults and architectural invariants |
| 17 | C++ identities, units, data and ownership |
| 18 | Time, scheduling, transactions and determinism |
| 19 | Checkpoints, history, analytics and recovery |
| 20 | World API, C ABI and GM tools |
| 21 | P0 biology fixtures and evidence boundaries |
| 22 | Authoritative S0-S9 roadmap and exit gates |
| 23 | Exact S0 tasks and T00-T13 tests |
| 24 | Requirement traceability and quality gates |
| 25 | Historical S0 implementation decisions |
| 26 | S1 transactions, entities, ordering, budgets and checkpoint decisions |
| 27 | S2 local perception, autonomous foraging, sparse trails, bounded memory and ablations |

Read ../AGENTS.md and ../CODEX_START_HERE.md first.

## Historical topics retained

02 covers the game experience; 03 architecture; 04 biology and colony society; 05 the Game Master; 06 earlier milestones; 07 references; 08 open questions; 09 true 3D underground space and microclimate; 10 parametric geometry; 11 geometry interchange; 12 geometry tests; 13 mixed simulation scheduling; 14 SCH-01-SCH-30; 15 the first integrated ecological loop.

Older milestone numbers and reused experiment labels must be interpreted with their source document. The v0.8 roadmap in 22 takes precedence. Earlier geometry A/B comparisons are historical: ordered parametric edits with derived SDF have already been selected.

## Confirmed direction

Unity/C# client, independent authoritative C++ core, an expandable 24 x 24 meter first complete world, multiple colonies, Lasius niger as the first focus species, local individual behavior, an observing GM rather than an ant brain, true 3D excavation, detailed statistics and continuous individual histories, and one persistent GM identity across worlds.

The GM harness, species calibration, SDF brick dimensions, LOD update rates and full ecological performance are unresolved. All demonstration constants remain engineering fixtures unless specifically calibrated.

## Initial scope and supplied files

S0 provides C++20/CMake/CTest, time, deterministic RNG, IDs, events, a headless runner, read-only snapshots and in-memory checkpoint round trips. It excludes Unity, biological behavior, SDF, SQLite and Agent services. Proceed to later stages only after review.

The contracts/ header is an unimplemented ABI draft. schemas/ and scenarios/ contain reproducible fixtures. codex_tasks/ contains stage instructions. MANIFEST_SHA256.md records the maintained handoff hashes.

Changes to confirmed product requirements update 01 and the traceability matrix. Changes to engineering defaults update an ADR, affected contracts and tests. Keep historical design context without interpreting it as current authorization.
