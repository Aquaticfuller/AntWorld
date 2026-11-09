# S6.3.3 Biological Observability and Founding Queen Care

Engineering correctness: **PASS** (180/180 local Debug, Release and ASan+UBSan; all five GitHub CI jobs pass). P01 local maternal capability/plasticity: **CONDITIONAL PASS within the fixtures**. Quantitative B01/B02 species validation: **NOT PASSED**. Final performance qualification: **NOT QUALIFIED** after three rejected admissions. Stage acceptance is left to independent review; this is not a full biological/performance PASS.

## Scope and evidence

Branch `codex/s6.3.3-queen-care-observability`, from reviewed atlas65e7875. Protocol52 was frozen in e73e761 before implementation. P01/P10 only: caste-specific queen care, real brood placement/nutrition and evidence-based behavior observations. No P02 metabolic coefficient, P03 reproduction allocation or P04 temperature-development rule was corrected. No survival floor, global WorkerCount, hidden supply or centralized task allocation is introduced.

The Evidence Atlas remains the continuing scientific reference. B01 final publisher Methods/Results and B02 complete7-page final paper were read. The user supplied both complete Dryad archives. Source hashes, original rows and locators are in `experiments/s6_3_3/literature`; reading/access and experimental fidelity are documented in `research/s6_3_3/README.md`. Copyrighted papers remain local and untracked.

## Implementation

The opt-in schema11/physics13 contract adds minimal Species/Individual/Environment profiles. Queens have a dedicated care program; they retain the existing ban on worker forage/excavation/autonomy. Founding and established context ages are declared metadata, not fabricated lifetime histories. Local reachable brood and completed close-worker interactions drive the new choices. A finite fading contact cue can reduce care propensity and then expire after workers leave. Its numerical law is F/ENGINEERING_FIXTURE, not a measured hormonal response.

Inspection, arrangement, cleaning, transport and feeding are separate motor acts. Arrangement/transport physically move the same brood ID through swept geometry; feeding transfers existing crop material under the existing recipient demand/capacity rules. No resources or health benefits are invented. Target reservations, interruptions, pending durations, contact memory and placement participate in single-writer rollback and deterministic checkpoints.

P10 records opportunities, selections, starts, completions and interruptions from actual commits. Known motor durations, unknown legacy durations, active/inactive intervals and program residence remain distinct. Historical SQLite queries index recipients; appended flow metrics preserve prior metric IDs. Raw partial/open bouts can be queried with half-open interval clipping. Detail, API limitations and compatibility are in document53.

## Frozen assays and measurement limits

The matrix contains276 primary runs (12 seeds; three queen-context labels; worker absent/present/added/removed/sham/no-brood; close/solid-barrier controls; independent retrieval endpoint) and108 one-at-a-time sensitivity runs (six seeds; memory/inhibition/decision interval). No fitting or seed selection occurs. All saved states are checked for exact continuation/resource consistency. B01 scans use the frozen51-window definition plus a50-window sensitivity matching the deposited reversibility tables.

Source distinctions are retained: B01 reversibility uses50 scans versus51 in text; older queens have14 labels, three NA rows,13 measurements per hour and12 complete records. Available-case and complete12 sensitivity comparisons are both provided. The author's B02 R script explains70 raw worker groups becoming67 queen-worker matched colonies and61 productivity-linked colonies; all-unit, matched67 and author61 comparisons are separate. Independent experimental units are queens or three-worker groups, with two B02 trials averaged within colony. Bootstrap95% intervals resample those units or simulator seeds, not scans. No missing measurement becomes zero.

The close-worker B01 fixture uses passive living workers to isolate the local contact cue. Solid separation excludes antennation and is not the original mesh. Geometry, known-shelter familiarity, mixed brood stages and seeded age labels approximate real conditions. Current code cannot reproduce maturation, odor recognition, parent-offspring correlations, cleaning efficacy or maternal reserve mobilization. Such endpoints are NOT IMPLEMENTED, not positive validation results. B02 count/first-contact comparisons are distinct from the deposited last-minus-first retrieval rate.

## Scientific results

All384 final runs completed; all384 conserve nutrients/energy and reproduce their checked checkpoint state/continuation. The1080 queen-hour windows contain no deaths and no positive active-care scans in no-brood controls. These are short, explicitly supplied behavioral fixtures, not evidence that founding queens survive on calibrated natural reserves.105 completed preliminary cases reproduce all biological paths, endpoints, scans and windows after the observer-only label correction; incomplete preliminary outputs are also preserved.

At the founding55 context,51-scan care fractions are:

|Condition|Baseline|24h|48h|
|---|---:|---:|---:|
|Workers absent|0.2026|0.2353|0.2222|
|Workers present|0.0327|0.0343|0.0310|
|Workers added|0.2026|0.0278|0.0458|
|Workers removed|0.0327|0.1863|0.2239|

Paired12-seed differences at24h: present minus absent=-0.2010 [−0.2239,−0.1797]; removed minus present=+0.1520 [0.1307,0.1732]. At48h, removed minus absent=+0.0016 [−0.0343,0.0408]. Sham and continuously present controls are exactly equal. At24h removal remains0.0490 below absence in this sample; this does not prove a lasting six-hour physiological cue, which has already expired. Intervals are pointwise, without a familywise multiplicity claim. The35/55/932 age labels produce identical outputs because no age-rate law was invented; these are not36 independent biological replicates or validated ontogenetic differences.

The solid-barrier control records no completed worker contact or refreshed social cue. Its24h care fraction0.1520 differs from the geometry-free absent control0.2255. This comparison is confounded by geometry/lattice constraints on arrangement as well as the missing mesh-antennation channel; it cannot identify a real wire-mesh effect. Raw category/placement events are retained for review.

Quantitative errors remain large. B01 comparisons below use raw-aligned50 scans; B02 rows use all deposited units. `comparisons.csv` also gives original-source and simulator confidence intervals, author-cohort sensitivities, older queens and all mesh windows.

|Endpoint|Dryad mean|Simulation mean|Signed error,95% bootstrap CI|
|---|---:|---:|---|
|B01 absent24h care fraction|0.0650|0.2317|+0.1667 [0.1221,0.2108]|
|B01 added24h care fraction|0.00125|0.0283|+0.0271 [0.0158,0.0383]|
|B01 removed48h care fraction|0.0625|0.2200|+0.1575 [0.0983,0.2038]|
|B02 queen brood retrieved/600s|3.7722|0.2500|−3.5222 [−4.0432,−3.0084]|
|B02 three-worker brood retrieved/600s|4.8500|0.5000|−4.3500 [−4.8310,−3.8238]|
|B02 queen capped contact latency,s|94.3740|396.6790|+302.3050 [193.8024,404.1393]|
|B02 three-worker capped contact latency,s|40.5124|230.8515|+190.3391 [125.6707,261.7445]|

Only8/12 queens contact brood and3/12 retrieve any; all12 worker groups contact brood but only6 retrieve any. No simulator unit retrieves more than one item. Noncontacts/nonretrievers remain in the results. A plausible structural limitation is the policy's attention to already-local brood: after an item reaches the shelter, local manipulation can prevent continued search for remaining unseen brood. The current local search cadence and fixture geometry also matter. This is a diagnosis candidate, not a demonstrated unique cause and not permission to retune; the held-out retrieval endpoint is quantitatively inadequate. The author61 cohort yields the same negative conclusion (queen error−3.6352, worker-group error−4.4180).

Sensitivity uses the same six seeds including the base configuration. Inhibition0 retains a smaller contact-occupancy effect while removing the hypothesized memory suppression. Continuous-contact results are little changed by1/6/24h memory because contact repeatedly refreshes it. Observation only at24/48h poorly identifies memory horizons<=24h. Decision intervals15/60/240s strongly change care fractions; this numerical/behavioral timescale is uncalibrated. None of these coefficients was adjusted to fit the source means or improve retrieval. See the matched sensitivity table and plot.

The source `With_workers` group receives workers at setup (B01 Methods2.2.4), so the numerical comparison uses the frozen **added** condition, not the continuously present engineering control. Only the source removal group has prior three-day worker exposure. Glass-tube-to-arena transfer remains an unmodeled source condition. This source-history mapping is independent of whether it improves a numerical error.

Figures: [care and retrieval](experiments/s6_3_3/analysis/care_and_retrieval.png), [sensitivity](experiments/s6_3_3/analysis/sensitivity.png). There are36 matched quantitative comparisons,759 extracted endpoint records (including three explicit missing values),14 care-profile fields,1341 current typed parameter/fixture expressions and268 new implicit-source expressions. All2559 historical provenance records and70 historical rule groups remain intact; the current16-rule extension and SQLite source links are independently checked. Zero behavioral coefficients were fitted.

## Engineering and performance verification

|Check|Actual result|
|---|---|
|Release, LLVM-MinGW clang23.1.5|180/180 PASS;30.05s|
|Debug, same compiler|180/180 PASS;108.10s|
|Windows Clang ASan+UBSan|180/180 PASS;298.67s; leak detection unsupported/disabled locally|
|Inherited regressions|All162 retained;18 additional cases including allocation-failure sweep|
|Frozen matrix conservation/restore|384/384 PASS|
|Observation correction comparison|105/105 completed preliminary cases retain biological outputs|
|Current performance qualification|NOT QUALIFIED: three pre-timing admission rejections; no final timing sample|
|GitHub CI|[PASS,5/5 jobs on5f4f46c](https://github.com/Aquaticfuller/AntWorld/actions/runs/42695868377); Windows/Linux Debug/Release and Linux ASan+UBSan with leak checking|

Full local logs are in `experiments/s6_3_3/verification`. History, state and geometry restore, continuous brood identity, actual protein transfer, target/caregiver death, wall closure, simultaneous caregivers, rejected actions and rollback are covered. Development failures/corrections remain documented: new history-kind filter, removal-fixture movement duration, excavation-fixture work duration, and the adult-queen opportunity label. No biological coefficient was retuned in response.

CI revision5f4f46cf8acf7bf0d57f15b2687d9a0536709476 passed the complete inherited evidence audits, all regression suites and the Linux Release reproduction chain through the complete23-case S6.3.3 primary seed. `verification/ci_final_source.json` preserves the exact job/step outcomes. The later evidence-report commit does not change Core, fixtures, analysis, tests or CI definitions.

A final validation-only guard rejects custom arrangement displacement/duration above the world speed limit. Every frozen case has arrangement<=step, and the pre-existing step-speed guard already holds, so this added check is mathematically inert for all384 configurations. `verify_s6_3_3_validation_guard.py` verifies that implication and retains the exact two pre-guard source files in a SHA256-checked project-source archive. Original run manifests are not overwritten. Regression suites and independent CI reproduction are rerun on the stricter review build.

The first GitHub run42691683492 exposed a portable-verification defect: the archive checker compared a newly encoded ZIP with the original Windows ZIP. ZIP creator metadata is host-dependent. The corrected checker verifies the unchanged archive's pinned SHA256, member list, CRC and every reconstructed source payload directly. The original archive and all run/source hashes remain unchanged. Initial failure annotations are retained; the correction changes only verification, not C++ rules, parameters or experiment outcomes.

The same run's Windows MSVC Debug allocation sweep found an exception-safety defect at `care_select` allocation37. Newly introduced empty vectors used the standard library's default constructor, which is noexcept although MSVC Debug allocates iterator proxies. They now use the throwing zero-count constructor, including each nested opportunity vector, following the existing AntStore/transaction convention. A read-only observation allocation sweep is added. No failure injection, iterator checks, behavior or history is disabled. `verify_s6_3_3_portable_allocation.py` reconstructs and hashes the exact executed source from the limited constructor changes, preserving the original three files separately. All scientific coefficients, empty-container contents and decision order remain unchanged; full suites and event reproduction are rerun.

GCC subsequently rejected three same-line independent `if` pairs in the experiment driver under `-Werror=misleading-indentation`. Each pair is now on separate lines, with no token/value change. The exact executed driver is retained in `research/s6_3_3/executed_experiment.cpp.txt`; the portability checker reconstructs it by reversing only those three line breaks and verifies its frozen SHA256. The source-expression inventory changes only because the lexical rows have different line boundaries. GCC diagnostics remain archived; warning flags are unchanged.

The [performance report](S6_3_3_PERFORMANCE_RESULTS.md) retains every admission and preliminary sample. Core-counter invalid samples were4/1/10 across the three attempts; final core-load p95=51.0686%. Power/temperature/freshness were recorded. No target or invalid-value rule was relaxed. Final wall-time percentiles, growth ratio and CI are NOT ESTIMABLE; an earlier single-session binary is not substituted. The bounded care smoke diagnostic records about32-33ms total process wall time and roughly7.2MB observed peak working set (10ms sampling, a lower bound on the true process peak), plus native phase timings. This is descriptive, not an admitted scale gate. Primary cases span88-281661 committed facts and17878-50953329 checkpoint bytes; concurrent experiment timings are explicitly diagnostic.

## Remaining scientific limits

- P01 capability is distinct from species-level quantitative validity. Fixed equal manipulation choices,6h contact memory,10s motor bouts, movement/sensing scales and urgency threshold remain F.
- P02 remains blocking physiological interpretation: queen care uses the prior basal formula, without a newly calibrated active-cost increment or flight-muscle/fat mobilization.
- SD-04/08 provisioning, scarcity allocation and maternal reproductive costs remain open; this short behavior assay does not repair the old90/180-day survival failures.
- SD-07 activity/rest rhythms are not calibrated by separating observed durations from task residence.
- SD-01/02 recruitment and SD-06 functional nest morphology remain unresolved.
- TD-03/06 full-history growth, synchronous persistence and journal-scanning observation queries remain storage/performance debt. Controlled contact/birth qualification is not unbounded colony scalability.
- TD-11: all-visible-neighbor care perception and per-target opportunity facts can become quadratic under dense simultaneous care. The small maternal/retrieval assays do not qualify that regime.

Next review should decide whether to authorize a separate P01 local retrieval/continued-search hypothesis and improved matched worker/mesh controls, alongside independent telemetry validation. P02-P04, broader nutrition, social recruitment, functional nesting and all follow-on stages remain unimplemented here. Do not choose a decision interval merely because it approaches a measured scan fraction.

## Reproduction

Build with the pinned compiler/CMake described in the repository; portable commands:

```text
cmake -S cpp -B build/s633-release -DCMAKE_BUILD_TYPE=Release
cmake --build build/s633-release --parallel 4
ctest --test-dir build/s633-release --output-on-failure
python tools/run_s6_3_3.py --binary build/s633-release/antworld_s6_3_3_experiment --mode primary --out out/s633-reproduction
python tools/run_s6_3_3.py --binary build/s633-release/antworld_s6_3_3_experiment --mode sensitivity --out out/s633-reproduction
python tools/verify_s6_3_3_reproduction.py out/s633-reproduction/primary_7
python tools/build_s6_3_2_1_atlas.py --check
python tools/build_s6_3_3_evidence.py --check
python tools/analyze_s6_3_3.py --check
python tools/analyze_s6_3_3_performance.py --check
python tools/ci_verify.py
```

Use `.exe` on Windows. Debug uses `-DCMAKE_BUILD_TYPE=Debug`; Clang sanitizers add `-DANTWORLD_SANITIZERS=ON`. Plot regeneration uses the existing pinned matplotlib environment and `python tools/analyze_s6_3_3.py --figures`. Raw data import commands and DOI/archive versions are in the literature manifests. A new compiler/binary requires a newly declared performance binary manifest before measurements, not overwriting the frozen measurement receipts.

Stop after this stage and push only its independent branch. S6.3.4, S6.4 and Unity require a new user decision after independent review.
