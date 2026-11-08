# S2.2 frozen trail-following protocol

Base: `c3d24e83aebc95840dbcd96629334dd2d1212f82` on `codex/s2.1-foraging-validation`. The user accepted the engineering fixes but not a positive social recruitment claim. Only S2.2 is authorized. All numeric model/scenario values below remain `ENGINEERING_FIXTURE`. Commit this protocol before implementing or measuring any behavior change. Do not replace seeds, scenes, metrics or primary conditions after looking at outcomes.

## Questions and prior source reasoning

S2.1 already represents fractional local signal weights. Does that produce a marked-arm preference and sustained multi-step contact with a line in an open arena? At a turn, heading persistence competes with chemical attraction. A visited candidate receives base weight 1 instead of 10. An immediately previous cell is completely excluded whenever alternatives exist, even if it is the only visible signal. The last rule makes immediate correction after a lateral departure impossible. These are source-derived hypotheses to measure, not a predetermined claim about social recruitment.

Primary evidence is reviewed in document 30. In particular, Lasius niger studies separate branch choice, occupancy near a trail, straightness, memory and error correction. Trail chemistry must not contain a direction-to-food vector. A possible minimal change, only after baseline diagnostics, is to admit the predecessor to the existing weighted draw when it bears the only visible adjacent signal. Preserve the visited penalty, all coefficients, ordinary stochastic alternatives and higher-priority return/food/memory behavior. This is a qualitative engineering hypothesis; it is not a measured ant decision formula. Other movement mechanisms are measured but not retuned.

## Isolated local-policy assays

Use the production `choose_behavior()` and a detached fixture that supplies only its four adjacent legal samples, no food cues, no inter-trip memory and an actual accumulated bounded loop-erased path. The fixture steps one cardinal edge, updates heading/path/decision count, and advances 1,101 ms per move. Static controlled chemical lines are experimental substrates, explicitly distinct from in-world deposition. They are never injected into WorldRuntime or claimed as colony-made facts. The full social regression below supplies the independent integrated test with real committed deposits, movement, accounting and checkpoints.

The open arena is 81 x 81 cells at 0.01 m spacing. Start at (40,20), with one experienced predecessor (40,19), heading north. This two-cell approach history is not food-location experience. There is no target food or reward. Reflection maps x to 80-x. Adjacent concentration is a directionless scalar: initial 1 unit, half-life 60 s, cutoff 0.001, with decay during each trial. No diffusion or field lookahead is added.

| Context | Geometry / purpose | Observation |
|---|---|---|
| `y_symmetric` | One stem and two mirrored stair-step arms; initial east/west exits both turn from north | One branch decision |
| `y_conflict` | Stem, north-going arm and mirrored east/west arm; only turning arm marked | One branch decision; straightness versus concentration |
| `straight` | Open arena, line x=40 spanning the arena | 24 consecutive moves; departure, reacquisition and occupancy |
| `bend` | Open arena, line x=40 up to z=26, then z=26 towards the mirrored east/west edge | 24 moves; no wall forces the bend |
| `lost` | Current (41,24), previous (40,24), older (40,23), heading east; only previous cell has a visible line | One correction decision |
| `visited` | Current (40,24), previous (40,23), earlier (41,23),(41,24); east candidate on line x=41 is visited but not immediately previous | One decision isolating the visited penalty |

The Y topology is embedded on the existing cardinal lattice: symmetric arms alternate lateral and north steps. It is not a continuous 45-degree antenna model, and its first two choices are lateral. Do not present its results as a quantitative replication of laboratory angles. Narrow-arm continuation is not evidence of open-arena following; only `straight` and `bend` evaluate that endpoint.

Cross each context with present, absent and blind treatments (field present but response weight zero), both reflections, release ages 0/60,000/180,000 ms and persistence coefficients 0/20/40. Primary conditions use age 0 and the existing persistence 20 with all seeds 1-512. Each of the other eight age/persistence combinations uses seeds 1-128. This is 55,296 trial rows per model. Response coefficient stays 180 throughout; deposit/field level is not raised. The lower/higher persistence values are planned sensitivity controls, not candidates selected for deployment. A no-signal draw and its blind control must have identical physical paths.

Record every trajectory as ordered positions, per-trial configuration/seed/model/physics, branch choice, continuous first-on-line streak, maximum on-line streak, fraction of moves on the experimental line, fraction within one cell, first deviation or right censor, deviation/reacquisition counts, U-turns, net displacement, total path length, mean distance from line, and signal range/decay. Reference geometry is used only by the local sampling fixture and the observer, never passed as an intended route to the worker. Blind/absent geometric occupancy is measured against the same reference line.

## Predeclared inference and acceptance

Primary paired comparisons: present minus absent at age 0 / persistence 20. Mirrors share seeds: resample seed clusters, with 4,096 bootstrap draws, analysis seed 2202, for main effects. Show arm/occupancy rates by mirror and all sensitivity point estimates with seed-cluster normal-approximation 95% intervals. Keep all outcomes and all first-deviation censoring. No multiple-comparison-adjusted biological claim is made.

Local capability is supported if the primary symmetric marked-arm preference is positive and open straight-trail following has positive paired effects on both occupancy and the probability of at least three consecutive on-line moves, with 95% intervals above zero. Report bend performance independently even if poor. These finite, low-resolution criteria establish a mechanism effect in reasonable controlled conditions, not perfect following, optimal navigation or biological calibration. Recovery tests measure the hard-veto conflict separately; they cannot substitute for continuous following. If these criteria fail, retain that conclusion rather than changing them or increasing response weight.

## Integrated regression and safety of interpretation

Rerun the exact S2.1 social matrix (64 seeds, two placements, 0/180/600 s release delays, present/absent/blind, no learned memory, 180 s observation) after any production change. Preserve S2.1 inputs/results unchanged; write new data under experiments/s2_2. Also repeat the original 128-run S2 feature ablation matrix. Distinguish direction choice, route shape, signal age and window/state conditions from local detectability. No trained path enters an individual policy; original scouts remain autonomous. Include the existing negative outcomes in the comparison and all unobserved discoveries in restricted times/survival.

Keep all 51 existing tests. Add pure local constraints, mirror/control, recovery, deterministic sequence and integrated continuation regressions. Retain single-writer transactions, resource conservation, allocation rollback and checkpoint rejection/versioning. If semantics change, increment physics while retaining the binary schema if unchanged. Run Debug, Release, ASan/UBSan, hosted CI and the existing performance fixtures. Deliver S2_2_RESULTS.md, raw CSVs, uncertainty tables, plots, literature limitations and clean reproduction commands; stop before S3.

## Baseline evidence and implementation decision

Protocol freeze: `1b9bdbd`. Baseline harness, all 55,296 rows and analysis: `173d372`, with the production behavior unchanged from S2.1 and all 51 regressions passing. Primary paired effects (95% seed-cluster bootstrap): symmetric marked-arm choice +0.1768 [0.1553,0.1973]; straight occupancy +0.0589 [0.0430,0.0750]; straight three-step streak +0.1484 [0.0840,0.2109]. Bent-line occupancy and streak effects are also positive. Thus local trail influence already exists; it must not be confused with successful colony recruitment. In the isolated lost-cue context the correction rate is exactly zero because of the veto.

**ADR-S2.2-01:** implement only the frozen narrow correction candidate. When the experienced predecessor is the sole adjacent above-cutoff signal and trails/response are enabled, let it participate in the existing weighted draw. Keep the visited base weight 1, all other coefficients, higher-priority rules and the veto whenever another signal is visible. The predecessor is the bounded loop-erased trace predecessor; after a loop closure it need not be the last physical cell. Record actual physical U-turns separately in the assay. No new private state, field direction, sensory radius or production parameter is introduced. Physics advances to 5; binary schema stays 3. Previous physics is rejected atomically.

The change repairs a mechanistic exclusion supported by the local diagnostic and qualitative literature, rather than a failure of the predeclared positive local-capability criterion. Endpoint oscillation, decreased displacement, uncertain or negative social effects must remain in the results. Do not tune again after seeing the post-change matrix.
