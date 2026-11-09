# AntWorld: read before implementation

This is the v0.8 design and engineering handoff. The current explicit authorization is S6.3.3 Biological Observability and Founding Queen Care (P10/P01 only), on codex/s6.3.3-queen-care-observability. Read frozen document52, implementation document53, S6_3_3_RESULTS.md and the Evidence Atlas. Preserve all162 inherited tests and every historical result. P02 metabolism, P03 reproductive allocation and P04 thermal development remain excluded. Stop for independent review after S6.3.3; S6.3.4, S6.4 and Unity are not authorized.

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

S6.3.3 adds an opt-in observation and caste-specific care contract. Current care coefficients remain F/ENGINEERING_FIXTURE; qualitative maternal capability does not validate quantitative species behavior. The historical atlas is retained under research/s6_3_2_1/baseline with a verified project-source archive. Root provenance and SQLite add current-scope records without overwriting old evidence. See document53 for actual motor acts, unknown legacy durations, finite local social cues and limitations. Historical stage statements below are not the current authorization.

S6.3.2.1 delivers an evidence atlas with source-specific reading status, original units, explicit cross-species boundaries and A-F grades. The root parameter file uses the new schema; the old A-D snapshot remains in experiments/s6_3_2/PARAMETER_PROVENANCE_S6_3_2.csv. All current biological coefficients remain F/ENGINEERING_FIXTURE;49 references and direct endpoints do not establish a calibrated state machine. Queen maternal care, caste/stage physiology, thermal development and observation contracts remain foundational gaps. Read CONTRADICTIONS_AND_GAPS.md and the review-only MODEL_CORRECTION_ROADMAP.md before proposing implementation. Historical stage summaries below preserve evidence and are not new authorization.

S6.3.2 is an audit of unchanged biological rules, not authorization to implement proposed corrections. Queen founding care/plastic specialization, physiological compartments/caste scaling, developmental temperature and observation-compatible behavioral endpoints have substantial gaps. Read BIOLOGY_EVIDENCE_MATRIX.md, PARAMETER_PROVENANCE.csv, BIOLOGICAL_VALIDATION_REPORT.md and MODEL_CORRECTION_PROPOSALS.md. The two-day maternal guard remains an uncalibrated local safety hypothesis. Performance admission failures and all measured rows must remain, without weakened thresholds or selected reruns. S6_3_2_RESULTS.md records final verification and readiness; historical stage statements below remain evidence, not the current authorization.

S6.3.1 is implemented for independent review. Read S6_3_1_RESULTS.md and protocols/contracts 44-47. Preserve all 161 current tests and the 432-run archive, including every negative queen outcome. Positive maternal-maintenance horizons explicitly use schema 10 / physics 12; zero retains old schema 9 / physics 11 and exact legacy behavior. The final source reproduces all 192 baseline controls. SD-08 remains open despite 180-day sustained reproduction in the six adequate-access 32-worker fixtures: small-colony supply and ordinary-access outcomes still fail, and all parameters remain ENGINEERING_FIXTURE. The new noisy wall-time performance batch is NOT PASSED (contact p50 growth 6.315x, birth 8.154x); paired/cycle results and historical passes do not replace its frozen gate. Stop; S6.4 and S7-S9 require new authorization. The S6.3 statement below is historical context.

S6.3 is implemented for independent review. Read S6_3_RESULTS.md, frozen protocols 41/42 and implementation/metrics document 43. Preserve S6_2_RESULTS.md and protocols 39/40, S6.1's 24.229x anomalous performance batch, and all earlier facts and negative results. The new opt-in world contract provides funded births, finite resource availability, local recovery/space feedback and actual protein recycling. Legacy worlds retain schema 8 / physics 9; the corrected long-term contract is schema 9 / physics 11. The initial 9/10 prototype and its censored/negative results remain archived and reproducible from their source revision. All 137 inherited tests remain, with 16 new regressions. Controlled stationary contacts and the proposed dynamic-birth registration fixture pass their <=6x growth targets, without extending that result to arbitrary long histories or colony sizes. SD-04/06/07 and new SD-08 reproductive allocation remain biologically open; all primary queens eventually exhaust energy. Preserve SD-01/02 and TD-03/04/05/06/08 limits in document 08. Retain document 31 for physiology, 32 for geometry and 33/34 for persistence. Stop after S6.3; S6.4 and S7-S9 require new authorization.

P0 is the later integrated vertical slice: foraging, nutrition, brood, excavation, statistics and history. S0 is only its foundation. Species parameters without appropriate evidence remain engineering assumptions. The complete map, 20,000 ants, finished graphics and mature GM personality are long-term targets, not S0 acceptance criteria.

## Reporting and authority

Report completed scope, changed files, exact build commands, PASS/FAIL/NOT RUN results, assumptions and ADRs, remaining issues, and the next gate.

Preserve confirmed user intent. Do not invent mechanics, evidence or approvals. Keep the design in version control and document deviations from defaults in an ADR. All tracked content and commit messages must be English; user communication is Chinese. The original source archive is retained locally, untracked.
