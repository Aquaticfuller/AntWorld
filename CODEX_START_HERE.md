# AntWorld → Codex：开始实现前必读

**这是完整设计文件与开发规格交接包，不是已经完成的游戏源码。**

## 1. 当前确定的架构

- Simulation: **C++20 standalone authoritative core** (Windows x64 first engineering target; cross-platform headless tests encouraged).
- Client: **Unity + C#**; not part of S0.
- Game Master: persistent cross-world Agent with same game tool capabilities as player, but autonomous environment mutations permission-gated; Harness language undecided.
- Persistence: checkpoint + committed event history + aggregation, initial SQLite candidate.
- Geometry: InitialSolid plus ordered parametric edits is authoritative, local SDF and nav/mesh are derived.
- First complete world: 24×24m expandable, multiple ant colonies, L0-L3 multi-precision; first **S0** is only an empty headless core foundation.

## 2. Read order

1. `AGENTS.md` — implementation boundaries and current stage.
2. `docs/01_Decision_Register.md` — confirmed, proposed and superseded decisions.
3. `docs/16_Implementation_Freeze_and_ADRs.md` — default engineering decisions and invariants.
4. `docs/17_Core_Data_Contracts.md` — IDs, units, AntState, events, ownership.
5. `docs/18_Scheduler_Transactions_and_Determinism.md` — time, event ordering, commits.
6. `docs/23_S0_Exact_Tasks_and_Test_Cases.md` — precise first batch.
7. `docs/22_Development_Roadmap_and_Execution_Gates.md` — stage boundaries.
8. `docs/24_Traceability_and_Quality_Gates.md` — acceptance and audit.
9. Other biology, 3D geometry and Game Master documents as needed; do not implement them all during S0.

## 3. The FIRST task

Open `codex_tasks/S0_KICKOFF_PROMPT.md`. Execute **S0 only**, build and test, provide `S0_RESULTS.md`, then stop for review.

## 4. Do not confuse milestones

- P0 **vertical slice** is a later milestone combining foraging, nutrition, brood, 3D excavation, statistics and history.
- S0 is merely the first foundation batch enabling P0 to be built safely.
- Biological parameters not supported by species-specific studies remain explicitly tagged as engineering assumptions.
- 24×24m world, 20,000 ants, complete game graphics and fully sentient-feeling GM are long-term targets, not S0 acceptance criteria.

## 5. Codex response format

`Completed scope / Changed files / Build commands / Test results with PASS-FAIL-NOT RUN / Assumptions and ADRs / Remaining issues / Suggested next stage`.

## 6. Requirements about the source of truth

This package is a snapshot of the user's already agreed requirements. Do not ask Codex to invent game mechanics, fabricate evidence or make unapproved product decisions. The user's current confirmed decisions take precedence. Preserve the documents in version control and update an ADR whenever implementation deviates from a suggested engineering default.
