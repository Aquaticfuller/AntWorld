# S6.1 Integrated Ecology Corrections

**Overall: FAIL against the complete frozen acceptance gates because TD-01's <=6x scaling target is not met.** Engineering correctness passes; SD-04 materially improves in the reviewed supplied integrated fixture, with important scarcity/density counterexamples retained. S7 remains withheld. All biological rules and numeric fixtures remain **ENGINEERING_FIXTURE**.

| Review question | Conclusion |
|---|---|
| Engineering correctness, conservation, identity, rollback and continuation | **PASS**: 655 local test executions, five-job source CI, complete raw evidence reconciliation and 816 durable execution replicas |
| SD-04 integrated nutrition/task coupling | **Substantively improved in the declared supplied fixture**; broader SD-04 remains OPEN because scarce/dense conditions do not uniformly improve |
| TD-01 frozen performance goals | Candidate cap and matched exhaustive speedup PASS; 512->2,048 latency growth **FAIL**, 24.229x against <=6x |
| Calibrated Lasius niger ecology | **NOT ESTABLISHED**: no parameter or categorical behavioral mechanism is promoted to a measured biological fact |

## Review scope and protocol

The reviewed S6 baseline is `2505f53e9ec8b6ba72828a651bd244934fde4431`. Document [37](docs/37_S6_1_Corrections_Validation_Protocol.md) was committed at `03ae833` before instrumentation, corrections or new measurements. [Document 38](docs/38_S6_1_Implementation_and_Metric_Definitions.md) specifies flags, state versions, observers and metric denominators. All original S0-S6 results and 124 test registrations remain. The delivery branch is `codex/s6.1-ecology-corrections`.

The fixed grids are 576 supply/density/arm cases, 128 non-default sensitivity cases, 512 integrated observer cases (legacy and combined), and 272 corrected durable cases with three execution modes each. No seed or negative condition is excluded. The default task minimum, contact radius/budget, gift quantity, resource composition, physiology, movement and behavioral weights are not fitted to the outcomes.

## Diagnosis before correction

The complete original seed-7 history contains 66,658 canonical facts at 1,800 s. Its 63,143-fact 600 s prefix is exact. The original five emergences, seven brood without emergence, 45 deaths and 1,549 ug final crop protein are reproduced. Another 651 ug is retained tissue: all 2,200 introduced protein micrograms, including the declared 200 ug initial pupal tissue, reconcile. See [complete reconstruction](experiments/s6_1/diagnosis/README.md), raw event CSV, timeline and hashes.

Workers 19 and 20 become Nurses at 15 s, make ten nest intakes each, retain 222 ug crop protein each, make no gift and leave for Forage at 25 s. Their actual private samples at that decision contain four and six needy larvae. Workers 21, 30 and 31 leave at 35 s with 368/368/347 ug crop protein after only one 54/55/53 ug protein gift each; each samples seven needy larvae. Missing contact samples cannot explain these particular departures.

Two mechanisms interact. The nurse wake checks ordinary half-crop refilling before contact/gift selection; ongoing water/carbohydrate absorption creates room for more mixed intake despite held protein. At the minimum task duration, the existing weighted reconsideration includes local demand but does not retain compatible ongoing nursing work. A new traveling program then limits routine switching until a physical return. These facts justify two separate corrections, rather than a larger Nurse weight or a global nutrient allocator.

## Implementation

- `gift_first`: an existing Nurse tries a real compatible gift before routine refilling. Urgent own energy/water need with no usable corresponding crop keeps precedence. No eligible local recipient means the ordinary fallback. Every gift still goes through the original proposal, scheduler, single-writer transaction and commit-time inventory/capacity/contact/barrier checks.
- `local_work_continuation`: at an eligible reconsideration, an existing Nurse with current compatible crop and currently sampled reachable demand keeps nursing unless self-maintenance is urgent. A lost cue or depleted compatible inventory returns to the original weighted policy. There is no new colony-wide signal, permanent assignment, demand memory or guaranteed feeding.
- Both flags default to false, retaining `legacy`, `gift_first`, `local_continuation` and `combined` ablations. Schema 8 / physics 9 encode the flags. Legacy social checkpoints add exactly two bytes; no-social S5/S4 fixture deltas remain +1/+9. Older schemas are rejected explicitly; migration is not claimed.
- Measured contact rank selection repeatedly looked up each tree edge in a map. Disposable cached child-node references preserve the exact canonical tree, candidate order and work counts. Stable map-node addresses and journal rollback preserve links; restore rebuilds them. No pointer enters a checkpoint or public state.
- Optional host-only profiling measures nine nested categories without changing authority, RNG, history or checkpoints. Profiling-on/off and optimized/old seed-7 replay match all 66,658 original fact bytes. Benchmark state/trace comparisons match all 12 scenario groups after only declared disabled-flag/version normalization.

## TD-01 performance: original target failed

All 120 original-source baseline samples, 36 matched uninstrumented controls, 36 instrumented before samples, 36 instrumented after samples and 120 final uninstrumented samples are retained. Final acceptance measurements ran from 2026-11-09 01:17:02 to 01:27:00 UTC, separately from builds and ecological experiments. The host used the same pinned toolchain and Balanced power plan. No sample was trimmed.

| Final bounded layout | Workers | p50 ms | p95 ms | p99 ms | Current RSS p50 MiB |
|---|---:|---:|---:|---:|---:|
| Dense | 128 | 8.533 | 10.187 | 10.592 | 9.324 |
| Dense | 512 | 42.868 | 49.104 | 51.617 | 19.164 |
| Dense | 2,048 | 1,038.641 | 1,076.712 | 1,084.293 | 53.592 |
| Dispersed | 128 | 4.029 | 4.893 | 5.044 | 9.271 |
| Dispersed | 512 | 16.274 | 17.917 | 18.083 | 18.842 |
| Dispersed | 2,048 | 356.366 | 409.882 | 429.748 | 54.250 |

| Frozen target | Actual final evidence | Result |
|---|---|---|
| At most 16 bounded candidates per decision | Maximum 16 | PASS |
| Dense 2,048 p50 at least 4x faster than matched exhaustive | 39.682x | PASS |
| Dense bounded 512 to 2,048 p50 growth at most 6x | 24.229x | **FAIL** |

Every 2,048-worker run retains 63,490 facts, 4,096 pending events and 18,432 contact decisions. Bounded dense sampling still examines 294,912 candidates, performs 497,664 bucket queries and visits 3,749,887 rank-tree nodes. No history, collision validation, task frequency or behavior is reduced. Full p50/p95/p99/max, setup, encode/restore, RSS/peak RSS, checkpoint bytes and work counts for both policies and layouts are in [the raw performance archive](experiments/s6_1/performance_final/contacts.csv) and [derived tables](experiments/s6_1/analysis/performance.csv).

Profiling establishes a candidate-selection cost, with zero index maintenance during the stationary advancement phase. Before optimization, the dense bounded 2,048 median exclusive sampling cost is 198.098 ms out of a 412.700 ms root advancement median. Spatial qualification, scheduling, transaction/journal maintenance, history, physiology and policy remain visible separately. The nine exclusive scopes partition each instrumented advancement exactly; restore and setup are separate phases. Timings include scope overhead and are attribution only.

| Dense bounded 2,048 advancement scope | Before exclusive p50 ms | After exclusive p50 ms | Calls, both runs |
|---|---:|---:|---:|
| Contact index maintenance | 0 | 0 | 0 |
| Candidate sampling | 198.098 | 319.148 | 18,432 |
| Spatial validation | 7.423 | 28.408 | 294,767 |
| Event scheduling | 24.104 | 92.534 | 114,688 |
| Transaction/journal | 16.964 | 59.722 | 78,044 |
| Fact append | 5.140 | 14.694 | 57,344 |
| Physiology | 67.507 | 210.946 | 333,679 |
| Policy outside nested scopes | 76.332 | 280.197 | 9 |
| Root residual | 16.672 | 63.657 | 10 |

The root inclusive median changes from 412.700 to 1,073.813 ms. These are sequential instrumented host samples, not a controlled absolute before/after speedup. Category medians need not add to the root median; the exact per-sample exclusive sums are audited. Setup and restore include the measured nonzero index maintenance omitted by a stationary-only advancement table.

A causal total-latency speedup is **not established** by these sequential timing archives. The unchanged baseline's full-matrix growth is 2.446x, its later matched uninstrumented growth 6.497x; instrumented before/after growth is 6.060x/5.129x. The final dispersed bounded growth is also unusually large, despite exactly four times as many bucket queries and tree visits there. This inconsistency is evidence of an unresolved timing/context effect as well as remaining implementation costs, not proof of a particular thermal, CPU-frequency, cache or scheduling cause. Those host telemetry channels were not recorded during the frozen runs. The failed final target is not replaced by the favorable instrumented result.

Review proposal, **not adopted**: retain all semantic/work-count obligations and the existing 6x target, but assess scaling in prespecified interleaved 512/2,048 blocks with balanced order, process affinity/power conditions and frequency/thermal telemetry; report paired block ratios and their interval together with all absolute percentiles. If a different quantitative threshold is desired, it requires a new reviewed workload/latency budget. This batch does not silently raise the target or declare TD-01 closed.

## SD-04: integrated effect and its limits

All 32 seeds, both mirrors and four conditions are retained. Confidence intervals below are 95% percentile bootstrap intervals from 4,096 resamples with analysis seed 6106; mirrors are averaged within seed. Execution modes and repeated observers are verification replicas, not extra independent samples. These intervals describe this engineering fixture's seed variation, not uncertainty in real ant biology.

| Supplied, 600 s; 32 paired seeds / 64 layouts | Legacy mean | Combined mean | Paired difference [95% CI] |
|---|---:|---:|---:|
| Cumulative emergences / 12 seeded brood | 11.4375 | 12.0000 | +0.5625 [0.1094, 1.1406] |
| Unmet larval protein exposure, ug*s | 55,121.41 | 15,066.69 | -40,054.72 [-64,890.47, -19,827.33] |
| Demand coexisting with reachable protein, ug*s | 18,820.00 | 8,749.22 | -10,070.78 [-12,828.54, -7,543.87] |
| Reachable adult crop supply coexisting with demand, ug*s | 23,468.28 | 9,245.31 | -14,222.97 [-16,608.22, -11,848.26] |
| Protein actually transferred, ug | 965.23 | 1,000.00 | +34.77 [5.94, 74.06] |
| Nurse exits despite currently sampled compatible work | 4.7813 | 0 | -4.7813 [-5.3125, -4.1875] |

Mean unmet-demand exposure falls by 72.7%. All 64 supplied layouts reach 12 cumulative emergences; legacy has seven incomplete layouts. A degenerate [12,12] bootstrap interval does not guarantee unseen-condition success. Physical supply/demand coexistence is an observer diagnostic, not a maximum-flow calculation or a policy input. Current task ownership, self-maintenance and future accessibility can still prevent an immediately feasible gift.

In reviewed unmirrored seed 7, actual transferred protein rises from 451 to 1,000 ug, cumulative emergence from 5 to 12, and unmet-demand exposure falls from 336,600 to 14,038 ug*s. At 1,800 s, all 45 individuals have died in both versions. Corrected retained protein is 1,000 ug crop + 1,200 ug tissue = 2,200 ug introduced; original is 1,549 + 651. The residual 1,000 ug is surplus beyond this fixed brood cohort's requirement, not evidence of another 1,000 ug unmet larval demand. No hidden input or automatic completion was added.

### Independent ablations

The 180 s, 32-worker, 2,000 ug cell uses all 16 seeds, unmirrored. It is a different horizon/seed set from the integrated table.

| Arm | Emerged mean | Unmet demand ug*s | Supply-with-demand ug*s | Resolved gift attempts | Mean completion rate | Program changes |
|---|---:|---:|---:|---:|---:|---:|
| Legacy | 10.500 | 36,965.88 | 24,561.88 | 18.69 | 91.89% | 81.75 |
| Gift first | 11.875 | 16,971.44 | 9,767.50 | 41.56 | 98.27% | 83.19 |
| Local continuation | 12.000 | 21,143.88 | 21,237.50 | 22.81 | 81.39% | 81.69 |
| Combined | 12.000 | 15,662.13 | 8,043.13 | 42.00 | 97.19% | 82.06 |

This separates the mechanisms: earlier gifts reduce prolonged protein retention; current local work continuation removes nonurgent exits while compatible demand is actually sampled. Continuing a task alone does not fix refill priority and does not monotonically improve transaction efficiency. Local continuation alone retains **68 failed gift resolutions** versus 29 in legacy across this cell; every failure is the actual `EmptyInventory` outcome at commit, meaning no compatible transferable inventory remains for that resolution. Filled recipient demand and depleted donor supply are not distinguished by that outcome alone. No failed action is counted as nutrition or erased. Full rates, attempt counts, switch frequencies and confidence intervals are in [ecology.csv](experiments/s6_1/analysis/ecology.csv); undefined zero-attempt rates remain undefined.

### Scarcity and density counterexamples

Every cell below includes all 16 paired seeds and the same 12 brood at 180 s. Values are combined minus legacy. Density also changes initial reserves and brood IDs; it is not a pure density intervention at fixed total energy/identity.

| Workers | Source protein ug | Emergence difference [95% CI] | Unmet exposure difference ug*s [95% CI] |
|---|---:|---:|---:|
| 8 | 0 | 0 [0,0] | 0 [0,0] |
| 8 | 500 | **-0.500 [-0.813,-0.188]** | -9,687.8 [-15,828.3,-4,140.4] |
| 8 | 2,000 | +4.313 [2.438,6.313] | -47,489.9 [-67,152.4,-30,158.4] |
| 32 | 0 | 0 [0,0] | 0 [0,0] |
| 32 | 500 | -0.375 [-0.938,0.188] | -12,377.4 [-18,279.1,-6,971.8] |
| 32 | 2,000 | +1.500 [0.313,3.000] | -21,303.8 [-34,889.9,-10,405.0] |
| 128 | 0 | 0 [0,0] | 0 [0,0] |
| 128 | 500 | -0.188 [-0.563,0.188] | **+2,374.2 [1,759.2,2,998.2]** |
| 128 | 2,000 | +0.313 [-0.313,0.875] | -2,009.6 [-6,985.0,4,195.2] |

The low-supply failures are retained, not explained away. At 8 workers / 500 ug, actual transfer increases by 76.19 ug [30.80,126.74] while fewer brood emerge. Post-hoc endpoint inspection finds mean partially provisioned brood increasing from 4.5 to 9, and fully provisioned brood decreasing from 3 to 2.4375 (both include the same two initially provisioned pupae). This supports a distribution-versus-completion-threshold tradeoff in this fixture; it is not a proof of optimal or biological allocation. At 128 workers / 500 ug, actual transferred protein instead decreases by 14.94 ug [-18.75,-11.00], alongside greater unmet exposure. The specific dense-scarcity interaction is not fully diagnosed by this batch. The post-hoc tables and [reproducible diagnostic](tools/analyze_s6_1_scarcity.py) are separate from the frozen acceptance analysis; no rule was changed in response.

### Prespecified task-duration/contact sensitivity

For the same 16 seeds / 32 workers / 2,000 ug / 180 s, combined-minus-legacy effects are:

| Encounter budget / minimum task ms | Emergence difference [95% CI] | Unmet exposure difference ug*s [95% CI] |
|---|---:|---:|
| 8 / 10,000 | +1.875 [0.625,3.313] | -22,964.8 [-35,935.1,-12,083.9] |
| 16 / 5,000 | +5.188 [3.500,6.813] | -62,280.3 [-78,908.2,-45,659.6] |
| **16 / 10,000, unchanged default** | +1.500 [0.313,3.000] | -21,303.8 [-34,889.9,-10,405.0] |
| 16 / 20,000 | +0.250 [0,0.750] | -3,956.1 [-8,493.5,-831.4] |
| 32 / 10,000 | +1.438 [0.313,2.875] | -21,824.5 [-35,813.4,-10,519.5] |

The greater effect under short minimum duration and smaller effect under long duration agree with the diagnosed early-exit mechanism. Increasing contact budget is not the sole fix. These are sensitivity observations, not a search for a replacement default.

## Activity, excavation and finite-resource decline

The initial adult workers spend 97.5825% of living time in active programs under legacy and 97.5901% under combined in supplied integrated cases; paired change is +0.0076 percentage points [-0.0313,+0.0463]. Their away-from-depot fractions are 95.5925% / 95.6761%; 96.1414% / 96.2299% of autonomy reconsiderations are blocked by travel/cargo ownership. Thus the high fraction is predominantly owned travel programs and their switching gate, not a record of continuous effective work. Open no-food cases remain about 97.70% active; sealed cases are 0%. The model has no calibrated fatigue/inactivity budget, and active metabolic cost follows program ownership. The correction does not resolve this scientific limitation (SD-07).

Excavated volumes remain exactly equal across all three open resource conditions for every one of the 64 seed/mirror pairs, in both policies. Mean volume is 398.96875 fixture q^3; sealed volume is zero and autonomous fills remain zero. First excavation occurs at 6.103-6.604 s, before the first food delivery at 13.808 s. However, last excavation occurs at 37.779-321.829 s: resource invariance cannot be attributed solely to all digging finishing before food arrives. The current shared initial crowding/soil cues, continuing excavation ownership and initial reserves coexist with a model that has no explicit chamber-demand, brood-organization or climate feedback. Nutrition affects actual energy feasibility, but that is not a calibrated construction-need model. Both fixture conditions and missing feedback matter; no new nesting rule was added to force a different graph (SD-06).

Higher emergence is not higher survival: mean supplied living population at 600 s falls from 3.46875 to 1.9375. In this model, maturation permits active adult programs and their higher costs; the finite energy supply is unchanged. All 16 extended supplied/no-food cases have zero survivors at 1,800 s, with complete death/identity histories and retained nutrients. No-protein/no-food/sealed controls retain only the two initially provisioned pupal emergences. There is no laying, replenishment, rescue feeding or claim of indefinite colony growth.

Figures (PNG and SVG, generated from audited data): [nutrition ablations](experiments/s6_1/figures/nutrition_matrix.png), [integrated outcomes](experiments/s6_1/figures/integrated_outcomes.png), [activity and excavation](experiments/s6_1/figures/behavior_feedback.png), [seed 7](experiments/s6_1/figures/seed7_nutrition.png), [performance](experiments/s6_1/figures/contact_performance.png).

## Verification and reproduction

Source `c8dd6d0329497a13b5d59e01fdfbf16a2f63edc4` includes the full measurement exporters and the tested Core. Source `fbe8852` adds only contiguous seed-interval execution, its merger and CI observer audit; Core, test rules and biological parameters are unchanged. All 124 inherited test registrations remain; 11 new cases cover correction ablations, self-maintenance, cue loss, controls, partition/restore, locality, corruption, cached links, allocation rollback and durable integration.

| Local executed configuration | Passed / total | CTest seconds |
|---|---:|---:|
| Debug | 135 / 135 | 113.95 |
| Release | 135 / 135 | 14.83 |
| Windows ASan / UBSan | 135 / 135 | 699.03 |
| Clean exported-source Release | 135 / 135 | 50.36 |
| Storage-independent Core Release | 115 / 115 | 29.94 |

These are **655 executed checks**, with logs and source associations in [verification.json](experiments/s6_1/verification.json) and [executed_tests.csv](experiments/s6_1/executed_tests.csv). Correctness runtimes overlap ecological workloads and are not isolated benchmarks. [Source CI](https://github.com/Aquaticfuller/AntWorld/actions/runs/42545756277) and [interval-tool CI](https://github.com/Aquaticfuller/AntWorld/actions/runs/42546825019) each pass five jobs: Linux/Windows Debug/Release plus Linux ASan/UBSan. The latter also executes and independently audits the complete first S6.1 observer seed on Linux.

The 1,536-run S3 matrix, complete S4/S5 seed sets and first complete original S6 seed have been reproduced on the same host. All biological/factual fields match, with only declared version/checkpoint byte differences and host timings excluded. S6 retains exact trace equality. All inherited S2-S6 archived audits pass.

All **1,216 observer cases** pass independent ingredient/energy/identity/fact/ordered-geometry reconciliation. The **272 durable cases / 816 modes** pass exact state, queue, RNG and continuation comparison at every common boundary. Every corrected integrated observer matches its independent SQLite case exactly; all 256 legacy observers reproduce original S6 facts. Interrupted serial prefixes reproduce all 102 matrix cases, 64 observer cases and 69 durable mode rows, including full canonical fact checksums. The analyzer independently verifies declared initial inputs, so balanced ledgers alone cannot conceal added resources. See [audit.json](experiments/s6_1/analysis/audit.json), raw archives and execution provenance.

The initial Linux CI failure was confined to an omitted explicit standard header and a range-loop copy warning in the experiment executable. Correcting those produced five successful jobs at [run 42544457489](https://github.com/Aquaticfuller/AntWorld/actions/runs/42544457489); later source CI results above also pass. The complete first-seed observer export has independent integer-ledger/identity/geometry reconciliation and all 36 canonical fact streams match its earlier pilot.

Reproduction commands and artifact layout: [experiments/s6_1/README.md](experiments/s6_1/README.md). The canonical fact streams and SQLite stores remain complete local generated artifacts; tracked CSV projections, all fact-kind counts and checksums identify their evidence. Large CSVs are split only by file size, with every row and original ordering retained.

## Remaining review obligations

SD-04's reviewed supplied-case coupling improves, but scarce/dense counterexamples, local signaling, selective liquid composition, inaccessible/dead inventories and biological calibration remain open. TD-01 remains a failed latency gate; the alternative measurement proposal above is not adopted. TD-03/06 still require evidence-preserving asynchronous persistence, archival and memory budgets. TD-04/05 retain geometric expressiveness and the later versioned Geometry Dirty API. SD-01/02/06/07 retain long-distance following, real recruitment, nest organization and activity-budget validation. All are tracked in [Open Questions](docs/08_Open_Questions.md).

Implementation stops at S6.1. No Unity, Game Master, laying, weather or S7 functionality has been added. Independent review must decide the next authorization.
