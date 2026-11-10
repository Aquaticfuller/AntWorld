# S6.3.3.3-R1 spatial care correctness and integration

Reviewed baseline `9f857145ab69aae12d23b0f84045a8e064063457`. Commit `f2c59a8` freezes the spatial probes, historical evidence and 21-day matrix before the motor edits. Commit `2b58aa3` freezes the empty-return witness before its connector fix. [Protocol](docs/62_S6_3_3_3_R1_Frozen_Protocol.md) · [Addendum](docs/63_R1_Isolated_Execution_Addendum.md)

| Gate | Result | Scope |
|---|---|---|
| R1 spatial engineering | **PASS** | Shared continuous positions, true mask/solid clearance, bounded contact error, rigid custody and reversible underground access |
| R1 ecological integration | **PASS within the frozen fixtures** | Actual brood placement, food deliveries, positive nutrient exchange, egg production, development, death and exact recovery on 21-day clocks |
| Species-level quantitative validation | **FAIL retained** | B01 and B02 discrepancies, distinct observation definitions and unmatched biology remain open |
| Long-history scale | **TD-11 OPEN** | Live lossless durable storage is mandatory before S6.4. TD-01 and TD-08 preserve the prior admitted passes and the 6× threshold |

**R1 disposition is CONDITIONAL PASS for independent review.** Engineering tests and the frozen ecological scenarios verify the three corrections. The quantitative biology and durable-storage gates remain open.

## Spatial findings

- A 10 mm terrain tile can now contain many real movements. In equal geometry, 1 and 10 mm masks give the same positions, durations and committed trace at 0.5, 1 and 2 mm care strides. Ordinary movement uses the same clearance checks. A masked wall, exact corner and an overspeed proposal reject without a physical revision. [Motion contract](research/s6_3_3_3_r1/SPATIAL_MOTION_CORRECTION.md)
- A held larva maintains its acquired offset and exclusive reservation. The 2 mm mathematical boundary and points 1 nm inside are accepted at the origin and at 12 m. Points 1 nm outside reject. The diagonal, turning, contention, lifecycle, fill, rollback and held SQLite controls preserve physical custody. [Custody contract](research/s6_3_3_3_r1/CUSTODY_NUMERICAL_INVARIANTS.md)
- Workers use a bounded connector to real openings. A 2 mm shaft supports both grid widths, including a laterally offset entrance. A 1.5 mm shaft fits the empty body but fails the cargo-clearance plan. Backfill stops travel with cargo intact, and excavation resumes the same trip after exact SQLite restoration. The empty-return witness verifies a home-cell encounter reaches the true depot. [Connectivity validation](research/s6_3_3_3_r1/SURFACE_3D_CONNECTIVITY_VALIDATION.md)

The continuous motor is an explicit `WorldConfig` choice for new worlds and uses schema 14 / physics 16. Old worlds and saves retain their original motor and encoding. The connector uses a bounded geometry search and a remembered return over the walked waypoints. It assumes a flat terrain datum and cubic clearance. Long routes beyond the existing budgets, alternate routing after permanent closure, substrate-supported locomotion and rotation of the loaded body remain outside this contract.

## Ecological and performance evidence

All 72 reviewed conditions and 24 new underground-depot runs complete 21 days with byte-identical continuations. The runs reconcile 8,288,521 committed facts, and all 48 care-on worlds place the displaced brood. The original mixed chamber rises from zero to 135 food deliveries. The underground-depot arm records 138 deliveries below the ground plane. Nine workers later complete timed tactile care and positive brood feeding after their own return. Seven queens survive the horizon, all in fed worlds. The model's uncalibrated motor and physiological coefficients remain ENGINEERING_FIXTURE. [Ecological evidence and paired comparison](research/s6_3_3_3_r1/INTEGRATED_ECOLOGY_REGRESSION.md)

Integrated 128-worker dense care records 194,693 opportunities under the continuous motor versus 97,167 in the reviewed motor. The measured in-memory checkpoint median changes from 80.50 to 125.95 ms and median resident memory from 138.44 to 205.78 MB. These are exploratory host observations. The historical 1.07 GB SQLite and 51.6 s median save remain the durable pressure baseline. Both protected workloads match the original identities, and the 5.5163× contact and 4.3147× reserve-birth values remain the latest admitted ratios. [TD-11 evidence and implementation gate](research/s6_3_3_3_r1/TD_11_R1_DURABLE_HISTORY.md)

## Verification and review

- Windows LLVM-MinGW Release, Debug and ASan/UBSan pass 201 tests each. The archived name sets cover all 197 inherited tests. The strengthened ordered ecology witness also passes in all three builds. Windows sanitizer leak detection is disabled locally. The GitHub Linux sanitizer job exercises leak detection. [Local receipts](experiments/s6_3_3_3_r1/verification) · [Branch CI](https://github.com/Aquaticfuller/AntWorld/actions/workflows/ci.yml?query=branch%3Acodex%2Fs6.3.3.3-r1-spatial-care-fixes)
- The 416 legacy/local and 484 reviewed fidelity replays reproduce the archived observations and ordered exports. S6.3.3 research and experiment trees are unchanged. [Historical evidence](experiments/s6_3_3_3)
- The [raw index and commands](experiments/s6_3_3_3_r1/README.md) locate the frozen native controls, canonical facts and observations, original seeds, test commands and storage modes. [Open Questions](docs/08_Open_Questions.md) records the surviving scientific and engineering limits.

R1 ends at independent review. S6.3.4, S6.4 and Unity remain review-gated.
