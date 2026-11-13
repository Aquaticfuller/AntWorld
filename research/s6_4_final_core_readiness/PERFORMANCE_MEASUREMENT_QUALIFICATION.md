# Application performance and measurement qualification

## The current gate

The original F1 application gate remains `FAIL`. The most recent inherited matrix passes **22/30**. The two v7 collections each pass **4/4** on their own fixed workloads. TD-01 passes at **5.4435×**, TD-08 at **4.2389×**, and the protected observer passes its distinct foreground and overall-cost contract. These are valid controlled observations from the reviewed baseline. The final audit reruns their public analyzers. The authoritative Core tree and original assay path are unchanged. A new native measurement of the added joint scenarios was not used to requalify these gates. [Original protocol](../s6_4_integrated_founding/INTEGRATED_PERFORMANCE_PROTOCOL.md) [Reviewed raw timings and native qualification](../../experiments/s6_4_founding_qualification/performance)

| Complete application collection | Processes | Original passing cells | Observed foreground cuts |
|---|---:|---:|---:|
| F1-R1 | 480 | 17/20 | 10,920 |
| F1-R2 continuation | 720 | 29/30 | 16,380 |
| Integrated inherited | 720 | 23/30 | 16,380 |
| Qualification closure inherited | 720 | 22/30 | 16,380 |
| Integrated v7 | 96 | 4/4 | 3,624 |
| Qualification closure v7 | 96 | 4/4 | 3,624 |

All 2,832 original timings are retained, with exact within-cell input, frame, RNG and fact signatures. The original and closure inherited batches failed 7 and 8 of the same 30 cells respectively, with 3 common failures and 12 failures in their union. Whole-session label reversal changes the in-band A/A decision on 14 of 60 timing-surface comparisons in the former and 5 of 60 in the latter. The permutation results are stability diagnostics. The production protocol made no claim that those particular hypothetical reassignments were its randomization design. The largest v7 closure capture is 15.2008 ms. [Recomputed original cells, agreement and sensitivity](../../experiments/s6_4_final_core_readiness/performance)

| Most recent failed cell | Decisive original measurements |
|---|---|
| Borisovka v1 empty, 8 workers | P50 application/process 1.1407×/1.1440× |
| Borisovka R1 nominal | Application P95 1.2654×, A/A 1.1318×/1.1259× |
| St. Petersburg H1+H2 depot, 8 workers | P50 1.1750×/1.1635× |
| St. Petersburg R1 depot, 8 workers | A/A 0.8661×/0.8658×, single foreground cut 30.4863 ms |
| St. Petersburg v1 depot, 8 workers | A/A 1.2137×/1.1981× |
| St. Petersburg v1 empty, 32 workers | A/A 1.1431×/1.1422× |
| St. Petersburg v1 empty, 8 workers | Application P95 1.2033× |
| St. Petersburg R1 nominal | Application P50 1.1074× |

## Which cost is measured

The 216-sample instrumented batch supplies 54 neighboring on/off pairs and 54 disabled/disabled pairs on fixed authority. The median on-minus-off across the 54 pairs is 6.5663 ms internal and 6.4164 ms process wall. Summed capture differs by 4.0171 ms over 91 cuts, with 1.1449 ms in state reads and 2.6534 ms in CSV emission. The median advance difference is 0.0480 ms. These are medians of separate paired differences and need not sum. Midpoint encode, SQLite save, restore and nested SQLite VFS sync differences have medians −0.0142, −0.6827, +1.1746 and −0.0560 ms. The instrumentation forwards the actual SQLite VFS and separately measures the application sync of output artifacts. It keeps both in total wall time.

Absolute recovery can dominate even with observation off. The St. Petersburg v1 empty-32 enabled diagnostic median is 2,560.04 ms in restore, including 2,294.75 ms in the frame path and 243.31 ms in derived-index checking. Its summed census capture is 4.38 ms and the median forwarded VFS sync across the whole process is 17.57 ms. Its original closure restore reaches about 3.43 s. The CPU timing is a thread counter. Outer-process minus internal time also includes process setup, teardown and measurement. None of these residuals isolates Windows descheduling, paging, disk cache behavior or an individual allocation. RSS is a process high-water mark. The observed median paired change is −83,968 B in the instrumented run. It cannot establish an allocation rate, allocator pause or absence of memory overhead. An allocation attribution would require an allocation/scheduling trace for the exact same native workload, with tracing perturbation measured separately. [Paired phase evidence and input hashes](../../experiments/s6_4_final_core_readiness/performance) [Instrumented phase records](../../experiments/s6_4_founding_qualification/performance/diagnostic)

The 30.4863 ms foreground cut is game day 86, session 1 sample 159, cursor 61,720. Adjacent cuts are 0.1038–0.1667 ms, with 0.0643 ms at the same game time in the other enabled execution of that session. This is a measured overrun under an admitted run. The sampled instruments cannot tell whether it came from descheduling, CSV buffering or another stall inside the measured interval. It remains a hard failure. A/A excursions do not invalidate the overrun. A/A and on/off estimate separate quantities. [Original foreground rows and telemetry](../../experiments/s6_4_founding_qualification/performance/application-inherited) [Extracted violation](../../experiments/s6_4_final_core_readiness/performance/foreground_violations.csv)

Six observations per treatment place 75% of the interpolated P95 on the largest observation. Under independent continuous sampling, the chance of observing any draw above the population P95 is 26.49%. It reaches 95.39% at 60 observations but does not establish a narrow interval. Within-session correlation can reduce effective information. For example, the probability of missing the upper tail under complete within-session dependence is set by the number of sessions, not the nominal process count. [NIST exact quantile intervals](https://www.itl.nist.gov/div898/handbook/prc/section2/prc264.htm) [NIST confidence intervals for percentiles](https://doi.org/10.6028/NIST.TN.2106)

## Prospective replacement under review

The proposal retains the same work, environmental admission, budgets, all foreground samples, full application and process timing surfaces, actual native SQLite synchronization and reopening. It assigns balanced, randomized within-window A/A and A/B pairs, draws windows jointly across cells, requires A/A equivalence and upper bounds within the existing budgets, and returns `INCONCLUSIVE` if the intervals do not resolve the decision. It separates a global intersection-union pass from multiplicity-controlled localization of statistical failures. Direct foreground hard-limit violations remain failures. A randomized independent timing study and a locked confirmation matrix are separate from this analysis. The prospective protocol estimates costs on the same machine and build family. It requires separate approval before any decision replaces the original gate. [Frozen primary study](FROZEN_PERFORMANCE_STUDY.md) [Reserved controls](FROZEN_TIMING_FALSIFIERS.md)

| Synthetic truth and regime | Original estimator passing, 240 trials | Candidate at 96 windows passing, 240 trials |
|---|---:|---:|
| Quiet, true A/B 1.05 with no special tail, reserved seed | 223 | 240 |
| Clustered, true A/B 1.05 with no special tail, reserved seed | 95 | 238 |
| Clustered, process P95 exactly 1.20, median 1.05 | 63 | 11 |
| Clustered, process P95 1.24, median 1.05 | 61 | 2 |
| Clustered, A/A 1.13, A/B 1.05 | 22 | 0 |
| Clustered, one 30.4863 ms foreground overrun | 0 | 0 |

The primary experiment's ordinary clustered 1.05 condition passes 108/240 with the original rule, 171/240 at 32 windows, 229/240 at 64 and 239/240 at 96. In the reserved 1.24 P95 condition 2/240 pass at 96, Wilson 95% interval 0.23–2.99%. At the exact tail boundary, 11/240 pass with a 2.58–8.02% interval. The upper bound exceeds the proposed 5% precision requirement. Tail widths remain large in the heavy-tail cases. Even 238/240 per cell gives about 75% joint pass in a 34-independent-cell illustration, with no established host dependence model. The 96-window candidate shows useful separation but is **not qualified** by this study. Four pairs per arm in each of 96 windows means 52,224 child processes over 34 cells. The pilot must estimate feasible elapsed time, actual covariance and precision before committing to an adequately powered full matrix. The reserved pilot windows can check the instrument and timing effect, with known injections. They cannot directly estimate a rare misclassification frequency from a handful of windows. [Trial data, Wilson intervals and tail width](../../experiments/s6_4_final_core_readiness/performance) [Reserved trial data](../../experiments/s6_4_final_core_readiness/performance-falsifiers)

No further performance patch was adopted. The identified absolute restore work comprises byte, lineage, frame, geometry and index checks and is common to both observation arms. The sampled differences do not identify a removable operation that explains the failed cells or the long foreground cut. A future exact change would have to demonstrate reduced work on fixed timing inputs with equal byte authority, genuine disk I/O and independent recovery before a prospectively authorized native collection. There was no extra host qualification run to select a faster result.
