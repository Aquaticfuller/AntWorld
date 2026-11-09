# S6.3.3 performance qualification

**NOT QUALIFIED / INCOMPLETE.** The unchanged target is512-to2048 simulation-advance growth<=6x. No final-binary wall-time PASS or algorithmic FAIL is awarded. Three contact-session2 admissions failed, so the frozen quiet measurement campaign stopped. Birth timing was not started after this stop. This is a measurement limitation, not evidence that the new biology meets or violates the scaling bound.

## Protocol and environment

Use document52 and the unchanged `run_s6_3_2_performance.py` admission/schedule machinery through `run_s6_3_3_performance.py`. The manifest pins measurement-candidate and subsequent review-build SHA256 values separately. Fixed workload, compiler/build, seeds, populations, events and ABBA/BAAB order are retained. No biological behavior/contact/history reduction, sample exclusion, affinity change to seek a faster core, or threshold adjustment was made.

The manifest distinguishes the measurement candidate from a later review build with an arrangement-speed input-validation guard. That guard is inert for all frozen biological cases and unused by disabled-care benchmarks; both versions remain unqualified. Hashes and rejected-admission history are not relabeled as measurements of a later binary.

Host: Windows, Intel Core i7-13620H (10 cores/16 logical), performance-core logical0, observer affinity excludes its physical core. AC power and battery-saver checks passed. The full CPU/OS/power-plan/topology information, frequency/load series and all HWiNFO sensor values used by admission are recorded in configuration/admission files. Current sensor logs were explicitly restarted by the user; freshness checks passed. These measurements do not establish the cause of earlier anomalous batches.

|Contact session2 admission|Invalid core samples /60|System load p50 / p95 (%)|Core load p50 / p95 (%)|Power and sensors|Result|
|---|---:|---:|---:|---|---|
|1|4|9.7245 /16.3799|10.9382 /22.2709|Valid|Rejected before timing|
|2|1|4.8282 /7.3420|1.5734 /11.1455|Valid|Rejected before timing|
|3|10|4.7966 /10.0140|0.7719 /51.0686|Valid|Rejected before timing|

Invalid status2147485654 is retained verbatim. All60 records per attempt remain; no missing value is filled. The third attempt recorded package52-67C and5.009-21.986W. Neither temperature nor external workload is asserted as the cause of counter invalidity. Five-minute minimum intervals were respected. Own biological experiments were suspended during quiet measurements; no compiler/tests ran concurrently with timed samples.

## Preliminary binary evidence, excluded from final qualification

An earlier observer binary completed contact session1 (112 rows, all preserved). Later review corrected a queen-versus-worker opportunity label in opt-in care worlds; it did not change these disabled-care benchmark decisions. The old binary and samples remain in `performance_pre_observer_correction`; they are not pooled with the final version or promoted to final qualification. Two rejected admissions carry forward to the same three-attempt limit; the rebuild did not reset retries.

Dense measured latency (ms), preliminary binary only. Each cell gives p50 / p95 / p99:

|Population|Setup|Advance|Checkpoint encode|Restore|
|---|---:|---:|---:|---:|
|512|2.1334 /3.6282 /5.0983|43.3658 /47.6983 /48.5081|8.3119 /9.3091 /9.7469|10.7342 /14.1055 /14.4746|
|2048|8.4707 /9.9238 /10.1950|238.8312 /248.9119 /249.4096|32.7176 /34.7150 /34.8232|50.9048 /53.9793 /55.7881|

This session's dense-advance p50 ratio is5.5074, with block-bootstrap95% interval[5.3257,5.5836]; the paired median is5.3860 [5.2818,5.5554]. With only one session these intervals do not estimate between-session uncertainty and cannot qualify the campaign. `performance_pre_analysis` includes all phases, both layouts,128/512/2048 populations, paired samples, computation counts, memory and CPU cycles. During timing,598 OS samples include10 invalid core-counter samples; system-load p95 is29.07%, package temperature52-77C and power5.577-43.217W, with a power-limit flag and no package thermal-throttling flag. No timed row is discarded for these excursions. The original localized HWiNFO snapshot stays local; the33 overlapping CPU sensor rows and original-byte/hash mapping provenance are published in English.

All per-run values, phase CPU/cycles, resident/peak memory and detailed profiler calls/times are preserved. This one session does not meet the required three-session design. Event counts are3970/15874/63490 for128/512/2048; checkpoint bytes720120/2877816/11508600. Final qualification has zero admitted timing rows, so its p50/p95/p99, paired ratio and confidence interval are **NOT ESTIMABLE**, not zero and not substituted from the preliminary binary.

## Care workload diagnostics and next review

The full biological matrix records simulation advance, checkpoint write/restore time, bytes and event counts. These runs are concurrent development workloads, not admitted wall-time samples. Preliminary runs paused for measurement have additionally invalid elapsed times and are excluded from performance inference. A separate small current-binary care smoke diagnostic records repeated process memory and native phase times; it cannot replace the scaling gate.

Recommended next action for review: validate the Windows per-core counter against an independent cumulative per-processor idle/kernel/user-time measurement, retaining both raw streams; identify missing/invalid status semantics before choosing a replacement instrument. Freeze any instrument revision and a new quiet interval before timing. Keep the same<=6x bound, workloads, histories, ABBA pairing and all slow samples. No algorithm change is justified by these rejected admissions.

TD-01/TD-08 scale qualification remains bounded by the existing historical successes and failures. S6.1's24.229x anomaly, S6.3.1's6.315x/8.154x failures and S6.3.2's controlled successes remain intact. TD-03/06 synchronous full-history storage growth and new journal-scanning observation queries remain open.

TD-11 additionally tracks the new care program's all-visible-neighbor enumeration and per-target opportunity facts. Many concurrent caregivers in a small region can create quadratic work/history. A one-queen/three-worker assay and a disabled-care legacy benchmark do not qualify this density regime. Any bounded-care sensing revision requires its own frozen biological/observer semantics and review; no silent thinning of behavior or facts is proposed here.

Reproduce archived interpretation with `python tools/analyze_s6_3_3_performance.py --check`. The underlying session commands and binary hashes are in the manifest/configuration; do not rerun into a completed/rejected session or overwrite its receipts.
