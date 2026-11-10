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

**Current authorized batch: S6.3.3.3 Brood Care Validation Closure**, on `codex/s6.3.3.3-brood-validation-closure` from reviewed `e5ded6e`. Read document 61, the Evidence Atlas and the prior care audit. Diagnose B01 and B02, test real game-day ecology and isolate timed/integrated TD-11 costs. Preserve exact legacy outcomes, resources, geometry, rollback, and deterministic restore. P02 metabolic equations, P03 reproduction allocation, P04 thermal development, S6.3.4, S6.4, Unity and S7-S9 remain review-gated. Every uncalibrated biological assumption remains F/ENGINEERING_FIXTURE. Keep source papers local and untracked. Publish permitted factual data, citations and original summaries.

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
- Preserve all 195 inherited tests, 384 historical runs, 416 S6.3.3.1 assays, 484 S6.3.3.2 assays and their evidence. Run Debug, Release, sanitizers, CI, retrieval and rollback regressions, frozen multi-seed assays and timed/integrated density profiling. Retain the unchanged <=6x controlled performance gate and its original results. Preserve the historical Atlas and audited source snapshots and independently audit current additions.
- Keep document 35 frozen; preserve S6_RESULTS.md, all raw experimental/performance evidence, figures, definitions in document 36 and reproducible commands.
- Follow document 61. Deliver the stage report, causal diagnosis, validation and uncertainty, long ecology, integrated TD-11, updated state and parameter audits, raw samples and reproduction commands. Treat B02 as development data. Push the independent S6.3.3.3 branch and stop for Code Review.
