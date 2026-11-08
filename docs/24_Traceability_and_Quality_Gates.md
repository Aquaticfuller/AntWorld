# Traceability, quality gates and delivery audit (v0.8)

Current gate: S4 received CONDITIONAL PASS with explicit S5 authorization. Documents 33/34 and S5_RESULTS.md map durable generation recovery, identity/evidence, command idempotency and analytics to SCH-10/17/19/20/21/25/27. All 89 inherited tests and historical archives remain; 19 added registrations bring the suite to 108. Physics remains 7; schema 6 adds receipts. S5 does not authorize S6.

## Requirement -> design -> verification

| Requirement | Design documents | Gate |
|---|---|---|
| G-06: full map, colonies and expansion | 02,03,16,21 | S9 map/LOD performance and consistency |
| G-07/T-11: true 3D observation/following | 09,10,11,20 | S4 geometry, S7 Unity |
| T-12: ordered-edit authority and derived SDF | 09,10,17,18 | S4 SCH-04/09/16/26, G1/G2 |
| B-02/B-03: local emergent behavior | 04,21 | S2 F1/F2/F3, multiple seeds |
| B-04: nutrition, transfers, continuous life | 04,17,19,21 | S3 SCH-05/07/23, document-21 N1/N2 |
| G-10: basic and deep histories | 02,05,19 | S5 identity/window/trajectory checks |
| G-12: complete statistics and comparisons | 02,19 | S5 SCH-27, reconciliation |
| G-11: speed and offline policy | 13,18,19 | S0 foundations, S9 SCH-13/24/30 |
| AI-01: no LLM worker control | 05,20 | S8 SCH-11/18, core runs without GM |
| AI-02/03: persistent cross-world identity | 05,19,20 | S8 memory migration and world isolation |
| AI-05/06: player-equivalent tools and authorization | 05,20 | S8 SCH-10/17, permissions/audit |
| T-02: independent core/read-only presentation | 03,17,20,23 | S0 headless, S7 ABI/view invariance |
| T-20/23: scheduling/recovery/idempotency | 13,18,19,23 | S0/S1/S5 SCH-01/02/19/20/22/25 |

Numbers identify document prefixes. Product requirement changes update document 01 and this mapping. Historical experiment labels require source context.

## Quality levels

- Mechanism Valid: automated state, sequence, conservation, identity and geometry tests pass for implemented scope.
- Biologically Plausible: multi-seed statistics agree with qualitative phenomena; parameters may remain uncalibrated.
- Species Calibrated: species/condition/unit-qualified evidence, fitting and cross-validation support parameters.
- Visual Prototype: observable graphics, not automatic mechanism validity.
- Gameplay Ready: stable saves, input, analytics and experience; not S0.

Never equate mechanism tests with species calibration or replace records with attractive LLM narration.

## Per-stage gate

Debug and available Release builds have no unexplained failures; keep meaningful compiler diagnostics enabled. Preserve exact commands, result summaries and environment versions. Do not silently remove/skip existing checks. Prioritize invariants, rollback, event uniqueness and world isolation. Biological constants carry units/provenance. Update relevant ADRs, changelog, open questions and next dependencies.

Failures retain a minimal reproducer/seed and remain FAIL. Unsupported/unexecuted checks are NOT RUN, not PASS. Resolve conflicts by current user instruction > confirmed document-01 intent > document-16 defaults > detailed v0.8 contracts > earlier suggestions, recording the decision. Unknown biology uses labeled fixtures, never fabricated species thresholds.

## Performance reporting

Measure simulated/wall seconds, AdvanceTo p50/p95, resident/peak memory when available, events, checkpoint size/save/restore cost and geometry/nav costs for implemented modules. Mark unavailable or inapplicable metrics explicitly. Unity frame/native/mesh timing and GM latency/frequency/cost are separate. Small P0 measurements do not establish 500-2,000 or 20,000+ ant capability.

## Audit record

Report batch, branch/commit, changed files, environment, commands, test ID/results, evidence, schema/physics changes, remaining issues and next-stage prerequisites. Distinguish local verification from configured or actually executed CI; do not claim untested platforms. See S0_RESULTS.md for actual S0 evidence.

S1 evidence belongs in S1_RESULTS.md; document 26 maps its mechanism tests to SCH-03/06/07/08 and records the S0 review corrections. S0_RESULTS.md is retained as historical evidence, not rewritten to imply v2 was present in S0.

S2 evidence belongs in S2_RESULTS.md and experiments/s2/. Document 27 maps local behavior and the complete feature-ablation matrix to F1/F2/F3. Its mechanism tests preserve the S0/S1 suite and add locality/no-oracle, input-order independence, bounded memory, sparse field decay, conservation, semantic corruption and allocation-failure rollback. Interpret negative trail-only results as measured limitations, not grounds to filter seeds or claim calibration.

S2.1 adds document 28, S2_1_RESULTS.md and S2_1_EXPERIMENTS.csv. Distinguish tested choice/field correctness from a demonstrated social recruitment benefit. Matched naive-worker trials retain non-discoverers, control training state and decay age, and estimate paired uncertainty with seed clusters. Numerical fixes or visible trails alone do not establish biological recruitment or authorize S3.

S2.2 adds documents 29/30 and S2_2_RESULTS.md. Five new registrations cover local recovery eligibility, priority/visibility, mirrored junction geometry, deterministic continuous policy trajectories, blind controls, integrated resource/checkpoint continuation, and the new experiment runner. Its local assays use controlled detached substrates, not fabricated world deposits. Retain and compare the original real-deposit social experiment and broad ablations. Local following, initial departure, correction, movement costs and colony recruitment are separate endpoints; no positive local result authorizes S3.

S3 and S4 evidence remains in their original reports and archives. S5 reruns the entire 1,536-run S3 and 160-run S4 matrices; every semantic result agrees, including seed 43. Only the declared schema-size delta (+8 empty receipt-count bytes) and the already recorded S3 physics-version label differ. All geometry edits and trajectories remain identical.

S5's test-to-contract mapping is in S5_RESULTS.md. SCH-25 tests actual process crashes and SQLite write/sync failures with an application-owned synchronous store; asynchronous worker orchestration and physical power loss are not claimed. SCH-19 applies to implemented future work, not unimplemented laying/weather. SCH-10 exercises a typed durable command without a Game Master. The 365-day diagnostic storage clock is not SCH-30 ecological validation. Metric definitions distinguish seeded identities, life events, sampled gauges, covered event flows and undefined trip success.
