# Performance protocol and repeatability review

The unchanged protocol tests each case/model cell with six observed, six unobserved, six A/A-left and six A/A-right executions. Each treatment has two executions in each of three balanced sessions. A/A exercises the same executable and disabled capture in both arms. The same canonical work is checked using initial and final authority, RNG and facts. The maximum front-cut limit uses every observed cut, while the P95 ratios use six whole executions per treatment. These are distinct denominators. [Original protocol](../s6_4_integrated_founding/INTEGRATED_PERFORMANCE_PROTOCOL.md)

## Original repeatability

The completed R1 collection has 3/20 failed cells. The R2 continuation has 1/30. The integrated inherited collection has 7/30. The sets of failed cells differ across collections. The St. Petersburg v1 nominal and Borisovka v1 eight-worker depot cells fail in R1 and the integrated inherited collection. The one R2 continuation failure is St. Petersburg R1 eight-worker depot, which is a different model from the later St. Petersburg v1 depot failure. In the integrated inherited collection four cells have an A/A excursion, four exceed A/B P50 or P95, and one is counted in both. Neither the R1 nor the R2 completed collection has an A/A excursion. Of the 60 integrated inherited case/metric summaries, 14 have both in-band and out-of-band results under the eight possible whole-session A/A label swaps. This is a descriptive symmetry check. It preserves both same-session duplicates and does not claim the eight order allocations were randomized in the original experiment.

Linear interpolation of P95 with six observations places 75% weight on the maximum and 25% on the next largest observation. Under an illustrative independent continuous distribution, the probability that six observations include any value in the population's upper 5% is only `1 - 0.95^6 = 26.49%`. Common session dependence can reduce effective information further. The original finite-sample statistic remains the gate. It does not estimate the distribution tail precisely. Failing A/A demonstrates an unstable control under the same bytes. It cannot explain every A/B excursion. Conversely, a single passed A/A test cannot establish that on/off overhead is below the limit.

The original P50, P95, A/A, capture and RSS verdict is always reproduced on all rows. Leave-one-session values are sensitivity diagnostics. Every such calculation omits each session in turn, with no preferred subset. The paired bootstrap resamples the three complete session ratios for description, seed 640604 and 4,096 replicates. Its interval cannot replace the gate or establish independence beyond those sessions. Neither metric is adjusted by subtracting any process or I/O residual. A slow observation with correct inputs and qualified telemetry is evidence.

| Original failed cell | Original out-of-band ratios, application / process | What the original evidence identifies |
|---|---|---|
| Borisovka nominal R1 | A/A 1.1046 / 1.1028 | Disabled runs differ. There is no original A/B failure. |
| Borisovka depot v1, 8 workers | P95 1.2573 / 1.2479 | Both timing surfaces fail at the tail. No original A/A failure. |
| Borisovka depot H1+H2, 32 workers | A/A 0.8645 / 0.8669 | Disabled runs differ. Recovery dominates the diagnostic even with capture disabled. |
| St. Petersburg nominal v1 | P50 1.1581 / 1.1362 | Both timing surfaces fail at the median. Short absolute workloads amplify fixed and residual costs. |
| St. Petersburg nominal H1+H2 | Process P50 1.1229 | The outside-process surface alone fails. Instrumented residuals are relatively large, with cause unresolved. |
| St. Petersburg depot v1, 8 workers | P95 1.2235 / 1.2281, A/A 1.1283 / 1.1089 | Both observer and disabled controls exceed their limits. The observation effect cannot be isolated from repeatability. |
| St. Petersburg empty v1, 32 workers | A/A 1.1285 / 1.1295 | Disabled runs differ. Diagnostics place the major absolute cost in history validation during restore. |

## Phase attribution on identical authority

The three admitted sessions contain 216/216 rows and all nine frozen cells. One admission was rejected because system P95 was 21.40%. All recorded cell signatures match the original application runs, including the full canonical facts and RNG. The table gives the median of the six observation-enabled processes per cell. Capture is the sum over 91 daily cuts. The restore measure includes every recovery evidence check. The separate restore encoding checks exact original checkpoint bytes. Forwarded VFS synchronization is nested and includes database open, publication, recovery and close. It is distinct from the application output synchronization.

| Population and case | Model | Advance ms | Capture ms | Midpoint encoding ms | Store save ms | Store restore ms | Restore comparison ms | VFS sync ms | Fact export ms | Outer residual ms |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Borisovka nominal | R1 | 15.04 | 2.22 | 4.28 | 18.17 | 40.78 | 7.58 | 4.58 | 12.66 | 21.90 |
| Borisovka depot, 8 workers | v1 | 147.55 | 3.64 | 21.37 | 63.64 | 215.85 | 38.34 | 7.22 | 59.71 | 21.36 |
| Borisovka depot, 32 workers | R2 H1+H2 | 839.93 | 8.44 | 142.23 | 337.10 | 1,288.33 | 228.39 | 13.12 | 467.03 | 35.21 |
| St. Petersburg nominal | v1 | 12.72 | 3.05 | 5.82 | 24.68 | 56.21 | 10.02 | 5.65 | 14.95 | 36.40 |
| St. Petersburg nominal | R2 H1+H2 | 30.11 | 3.15 | 6.61 | 27.55 | 68.61 | 11.81 | 9.69 | 23.99 | 36.59 |
| St. Petersburg depot, 8 workers | v1 | 230.87 | 5.74 | 31.22 | 105.29 | 326.05 | 61.70 | 7.04 | 92.45 | 46.81 |
| St. Petersburg empty, 32 workers | v1 | 648.62 | 4.38 | 206.07 | 549.76 | 2,560.04 | 387.56 | 17.57 | 445.75 | 22.86 |
| Borisovka nominal control | v1 | 10.46 | 2.32 | 5.16 | 18.29 | 40.28 | 7.64 | 5.46 | 10.71 | 22.79 |
| St. Petersburg depot control, 32 workers | R2 H1+H2 | 1,028.94 | 9.44 | 182.31 | 399.09 | 1,533.68 | 256.60 | 13.10 | 465.59 | 34.57 |

The largest measured process-minus-application residual is 70.94 ms, in a disabled-observation short control. It includes process setup, unmeasured application entry/exit work and outer measurement. The longest recovery median is concentrated in frame validation (2,294.75 ms) and index verification (243.31 ms). The two components are separately measured with exactly the same recovery obligations. A single VFS timing channel cannot identify Windows scheduling, write-cache effects or causes of all prior slow samples. The thread wall-minus-CPU residual includes I/O waits, descheduling, measurement overhead and per-thread counter resolution. The app instrumentation uses a forwarded SQLite VFS for attribution only. Qualification uses the regular native VFS and uninstrumented binary. [Raw diagnostic rows](../../experiments/s6_4_founding_qualification/performance/diagnostic) [Phase and repeatability tables](../../experiments/s6_4_founding_qualification/performance/diagnostic-analysis)

All nine diagnostic cells fall inside the numerical A/A and A/B ratio bands in this separate collection. The diagnostic altered the instrument and sampled a fixed subset. Its improved repeatability is additional evidence of session dependence and does not satisfy full application qualification.

## Single formal inherited reassessment

The frozen uninstrumented collector completed all 720 samples in three qualified sessions. The first attempt at session 3 was rejected at selected-core P95 23.585% and its prescribed retry was admitted. The full inherited verdict is `FAIL`, with 22/30 passing cells. Only three cells fail both this run and the original 23/30 run. The eight failures below are the union across requirements in the new run. Ratios are rounded here and tested on unrounded samples.

| Frozen cell | Model | Out-of-bound measurement |
|---|---|---|
| Borisovka nominal | R1 | Application P95 1.2654× and disabled/disabled 1.1318×. Process disabled/disabled 1.1259×. |
| Borisovka empty, 8 workers | v1 | Application P50 1.1407× and process P50 1.1440×. |
| St. Petersburg nominal | R1 | Application P50 1.1074×. |
| St. Petersburg depot, 8 workers | v1 | Application disabled/disabled 1.2137× and process disabled/disabled 1.1981×. |
| St. Petersburg depot, 8 workers | R1 | Application disabled/disabled 0.8661× and process disabled/disabled 0.8658×. Maximum foreground capture 30.4863 ms. |
| St. Petersburg depot, 8 workers | R2 H1+H2 | Application P50 1.1750× and process P50 1.1635×. |
| St. Petersburg empty, 8 workers | v1 | Application P95 1.2033×. |
| St. Petersburg empty, 32 workers | v1 | Application disabled/disabled 1.1431× and process disabled/disabled 1.1422×. |

Of 16,380 observed daily cuts, one exceeds 20 ms. It occurs at game day 86 in session 1 sample 159 for the St. Petersburg R1 eight-worker depot. The two cuts before it take 0.1667 and 0.1038 ms. The two cuts after it take 0.1180 and 0.1336 ms. Its same-session counterpart at the same game time takes 0.0643 ms. It is included in the original maximum test. The measurement surface cannot distinguish descheduling from a short-lived stall inside observation or output buffering. The application total includes this time and all of its durable output. The presence of A/A excursions and a foreground violation requires two different diagnoses.

All 720 positions match the historical inputs, state, frame, RNG, trace and canonical fact bytes. Among the 30 observed cell medians the median candidate-to-original ratio is 0.997 for advance, 0.901 for midpoint save, 0.958 for midpoint restore, 0.948 for total application and 0.953 for process time. Midpoint save improves in 27 cells and restore in 22. St. Petersburg v1 empty-32 remains at about 2.61 s for midpoint restore and its worst restore grows from 2.74 to 3.43 s. These are same-authority observations across different collection windows. They support reduced common encoding work with substantial residual recovery cost and variability. The measurements cannot isolate a wall-clock codec effect from host conditions. No new timing rerun is used to supersede this outcome. [Raw application archive](../../experiments/s6_4_founding_qualification/performance/application-inherited) [Frozen decisions](../../experiments/s6_4_founding_qualification/performance/application-inherited-analysis) [Matched phase comparisons](../../experiments/s6_4_founding_qualification/performance/application-inherited-paired-codec.csv)

The v7 150-day reassessment passes 4/4 cells with all 96 samples. The first attempt at session 2 was rejected at system P95 26.516% and selected-core P95 31.643%. The frozen retry qualified. The largest observed foreground cut is 15.2008 ms in the balanced St. Petersburg cell. All 96 timings match the previous application authority. This distinct workload qualifies under the unchanged application thresholds. The inherited application gate remains failed. [v7 application decision and cells](../../experiments/s6_4_founding_qualification/performance/application-integrated-analysis)

## Candidate for separate approval

Keep the effect-size budgets, exact workloads, sample persistence, environmental admission and two independent timing surfaces. For any future redesign, freeze a measurement-system study with substantially more independent windows and paired blocks before qualification. Randomize treatment order within each block under a balanced per-cell schedule. Collect the required repeated 45-day durable runs on the same host configuration over multiple admitted windows. Use at least 60 repetitions per arm as a floor for tail observation, because `1 - 0.95^60` is about 95.4% under independence. A separate pilot should set the final block and session counts for estimation precision, including correlated host activity. It cannot serve as the qualification result.

Analyze paired log ratios for median overhead and a prespecified upper confidence bound for the on/off marginal P95 ratio with a session-block bootstrap. Independently verify disabled/disabled equivalence within the current A/A band using all samples and a predeclared rule for `INCONCLUSIVE` when precision is inadequate. Decide how to control familywise uncertainty across 30 cells and two endpoints before collection, and use a reserved validation set to assess false acceptance and false rejection. Preserve true storage and startup cost in process wall-time. A persistent in-process diagnostic can isolate internal work but cannot replace external process and durable observations. Publish both the original and candidate rules on every eligible raw archive before seeking approval. This plan changes evidence quantity and decision design. It has no authority to replace the current protocol.
