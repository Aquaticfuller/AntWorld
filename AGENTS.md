# Codex Project Instructions — AntWorld

You are implementing AntWorld, a long-term ant colony ecosystem simulator. **Read `CODEX_START_HERE.md` and the referenced docs before changing code.** The design baseline is v0.8.

## Non-negotiable product intent

- AntWorld is a realistic, non-level-based, long-term ant ecosystem world; ants are independent, not centrally ordered NPCs.
- C++ Simulation Core owns all ecological facts and operates headless without Unity or LLM.
- Unity C# is a view/input/UI client. The Game Master Agent is a persistent cross-world observer, narrator, analyst and authorized game tool operator—not the ant brain.
- Individual ants preserve identity through life stages. Histories and statistics must be evidence-based.
- True 3D underground geometry: `InitialSolid + ordered parametric edits` is authoritative; local SDF, portals, collision and Unity meshes are versioned derived data.
- User's first full-world target: 24×24 meters, expandable chunks and multiple colonies. This is NOT the initial S0 implementation scope.

## Priority and scope

1. Follow direct user instructions and `docs/01_Decision_Register.md` (confirmed decisions).
2. Follow `docs/16_Implementation_Freeze_and_ADRs.md` and relevant detailed contracts.
3. Follow `docs/22_Development_Roadmap_and_Execution_Gates.md` and current batch spec.
4. Earlier suggested ideas are nonbinding if they conflict with later confirmed decisions.

**Current authorized batch: S4 3D Excavation and Connectivity only**, explicitly authorized after conditional S3 approval. Work on codex/s4-excavation-connectivity from S3 commit 288b013. Preserve all 71 S0-S3 tests and historical evidence, single-writer rollback, identity, deterministic scheduling and resource conservation. Implement authoritative InitialSolid plus ordered parametric edits, derived local SDF, actual soil carrying/deposition/fill, 3D clearance/connectivity and immediate route validation after blockage. Contact-qualified behavior must respect solid barriers. Preserve document-08 debts: SD-04 nutrition redistribution must be validated by S6, TD-01 contact scaling resolved before S6 scale tests. No global nutrition averaging or food oracle. S5-S6, Unity and Game Master remain unauthorized.

## Implementation rules

- All tracked files, filenames, code, comments, documentation, generated reports and Git commit messages must be in English. Communicate with the user in Chinese. Keep untranslated source archives local and untracked; preserve existing Git history.
- Do not invent biological calibration values or claim a numeric fixture is a real Lasius niger constant; annotate toy values `ENGINEERING_FIXTURE`.
- Every world mutation goes through a validated single-writer commit path; reads cannot mutate time/RNG.
- Record units on data; default world coordinates in meters, X east/Y up/Z north, mass micrograms, energy joules, time strong int64 milliseconds.
- Stable IDs are never reused; cross-world references include WorldId.
- A proposed action is not a committed fact event. No fabricated event history.
- C++ ABI boundaries must be stable and not expose STL/exception/owned native pointer; `contracts/antworld_c_api_v1.h` is a **draft for later**, not a task for S2.
- Build from a clean repo with reproducible commands; pin any external build dependencies. Never require machine-specific paths or secrets.
- Do not wire external model APIs, persistent shell/network tools or API keys into the C++ core.

## Development and verification

- Read `docs/23_S0_Exact_Tasks_and_Test_Cases.md` for S0 expected behavior and tests T00–T13.
- Run build and tests; report actual commands/results. If tests cannot run, mark NOT RUN with reason. Never claim a test passed without executing it.
- When an ambiguity blocks a decision, choose the smallest reversible engineering assumption; record it in an ADR and update tests. Do not silently alter confirmed user intent.
- Preserve all 71 S0-S3 tests and historical results, documenting intentional version/semantic changes. Run Debug, Release, sanitizer, CI, geometry boundaries, restore and relevant performance checks for S4.
- Follow document 32 and produce S4_RESULTS.md, geometry/material evidence, performance data and reproducible commands.
- Finish **only S4**, commit the reviewable evidence and stop for review. S5-S9 are not authorized in this run.
