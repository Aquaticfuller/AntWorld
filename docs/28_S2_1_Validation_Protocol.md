# S2.1 foraging validation protocol

The user authorized S2.1 validation and minimal fixes on 2026-11-08, based on `21bc61b` from `codex/s2-foraging`. Stop for independent review before S3. All numerical fixtures below are `ENGINEERING_FIXTURE`. This protocol is recorded before running the new recruitment matrix; retain failures and all declared seeds.

## Questions and initial source audit

1. Equal-distance food cues currently prefer the smaller ResourceId (`behavior.cpp`). Identity is not a biological quality. Measure physical choices before and after swapping IDs, cue order and positions. No quality model is introduced: currently all locally available food cues have equal modeled quality.
2. Trail deposits occur at the arrival of a real loaded return step, capped at 16 units, with 1 unit per step before saturation. This covers the experienced return route except the source cell itself, which lies within the food sensor's reach. Test continuity from nest to the source sensing neighborhood instead of assuming it.
3. Sensors expose adjacent walkable same-colony trail cells. Default response is `floor(clamp(signal/16,0,1)*180)` added to exploration/persistence weights. Thus signals below 16/180 units add zero weight, although FollowTrail may label a selected trail-bearing cell above the 0.001 cutoff. Quantify this numerical dead interval and distinguish descriptive labels from causal recruitment.
4. Local food, loaded/bounded return and valid learned routes precede trail-weighted exploration. Audit state-dependent suppression rather than attributing all benefits or failures to the signal. No trail or successful-source memory exists before a scout's first collection, allowing matched training histories across trail treatments.

## Frozen experimental design

- **Bias audit:** seeds 1-4096, equal-distance food at opposite neighboring cells; swap IDs and cue order, and test east/west and north/south arrangements. Report every seed and configuration, plus aggregate balance. Runtime regressions also swap resource creation order with stable worker identity. Random selection must be invariant to renaming IDs and reordering equivalent observations.
- **Local response audit:** seeds 1-4096, four legal directions and a fixed heading. Compare no signal, fresh signal (1 unit), weak signal (0.04 units), and zero response weight. Include memory/return priority checks. These are diagnostic input fixtures, not fabricated in-world trails.
- **Social recruitment:** seeds 1-64, two mirrored food placements on a 21 x 15 open surface, cell size 0.01 m, nest (10,7), food (18,7) or (2,7), one autonomous scout and one initially dormant novice. Food is outside initial sensing range, with 4,000,000 ug total stock and 1,000 ug carrying capacity. Both ants and all resources are seeded before time advances; no food coordinates enter private ant state.
- Allow the scout at most 1,800,000 ms to complete its first autonomous delivery. Record all training failures without replacing their seeds. Immediately after first delivery, retire the scout with the existing explicit lifecycle fixture, identically in each paired treatment, so no further deposition occurs. This artificial removal is an experimental control, not a biological mortality model.
- Introduce the novice by activating its pre-existing idle identity at the nest, with zero decisions, no cargo and no learned route. Late first activation is the only new fixture capability needed; it must use a validated atomic commit and schedule strictly after a closed phase boundary. It cannot reset an existing forager.
- Compare **trail present**, **trail absent**, and **field present with response weight zero**. The last is a negative sensing control, not an optimized parameter. Retain all S2 coefficients in the primary comparison. Use release delays 0, 180,000 and 600,000 ms to measure loss of recruitment with natural decay, with the same delay in all paired treatments. Memory is disabled for both scout and novice in this experiment. Novice observation window is 180,000 ms after release.
- **Original ablations:** retain the S2 layouts, seeds 1-16, 12 workers, 1,800,000 ms and none/trails/memory/both treatments. Preserve historical S2 data and rerun the full matrix after fixes. Do not replace the broad matrix with the social fixture.

## Measurements and inference

Record one raw row per bias/response/social/ablation run with model version, seed, treatment, geometry, delays, duration and parameter values. For social trials include training completion/time, novice activation state, first local discovery and censoring time, movement before discovery/window end, actual experienced-path overlap, trail-selected steps, collection/delivery mass, trace length/continuity, and field amount/range/decay. Preserve sampled sparse cell fields separately for all social seeds/treatments, with no synthetic path injection.

Report discovery rates with Wilson 95% intervals, first-discovery survival curves including censored individuals, restricted mean discovery time (window-limited), and same-seed paired differences with deterministic bootstrap intervals. Mirror pairs share a seed: uncertainty resamples seed clusters, not artificially independent orientation rows. Separate failed training from novice non-discovery, reporting both unconditional pipeline and training-conditioned results. Never replace censored first-discovery times by the mean among successful ants alone.

Only if diagnostics establish a defect, implement a minimal fix and rerun the same matrix. Do not increase deposit, trail response, radius, memory, duration or seed count after looking at outcomes to improve recruitment. Weak or negative recruitment is a valid result and may require CONDITIONAL PASS or FAIL. No biological calibration, shortest-path, full-3D or S3 claim is permitted.

## Verification and output

Retain all 43 S0-S2 tests. Add bias, fractional response, real trail continuity, same-colony local propagation, matched novice controls, delayed activation/rollback, deterministic continuation and checkpoint version/evidence tests. Run Debug, Release, ASan/UBSan, hosted Windows/Linux CI and relevant benchmarks. Deliver S2_1_RESULTS.md, S2_1_EXPERIMENTS.csv, analysis/plots and reproducible commands on `codex/s2.1-foraging-validation`.
