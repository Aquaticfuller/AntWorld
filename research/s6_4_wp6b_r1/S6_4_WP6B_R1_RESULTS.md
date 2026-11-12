# WP-6B-R1 local feeding persistence and founding viability

| Decision | Result |
|---|---|
| F1-R1 engineering correctness | PASS. The candidate can execute, persist and replay a lawful repeated feed with exact conservation. |
| Local repeat mechanism | PASS. In the primary care-on worlds, 2,645 repeat selections led to actual protein-positive rations. |
| Allocation in multi-larva competition | Improvement for completing the funded pathway, with reduced breadth of feeding and greater concentration. |
| Formal ordinary founding robustness | FAIL. Borisovka missed two factor-level floors, and both populations missed the B06 count-matched timing gate. |
| First-worker long-term viability | FAIL in the primary closed-stock controls. All 606 eclosed workers subsequently died of dehydration. |
| Protected performance | PASS for TD-01, TD-08 and the original observer workloads. |
| F1/F1-R1 application observer performance | FAIL. Three of twenty cells exceeded an original total-time limit. |
| `SIMULATION_CONDITIONALLY_ACCEPTED` eligibility | Not eligible under the frozen protocol. F1-R1 remains an explicit engineering experiment. |
| Independent species validation | All nine BR statuses remain `BIOLOGICAL_BLOCKED`. |

The accepted F1 v1 reference was `bc59187df942720a56e821c3e06f820176ec3132`. The [pre-implementation freeze](FROZEN_R1_PROTOCOL.md) was committed at `809487fd5009c32cfd562e3a822cd5b5730336f7`. The measured C++ source is `0de8a9951090d2120914721e539ba82304593bf7`. The R1 option records one last paid larva, with 48-hour eligibility and a 75% conditional repeat draw. The existing care admission, local geometry, payment, clocks and mortality remain the authority. [Source and formats](R1_MODEL_AND_FORMAT.md)

## Coverage and independent checks

The collection attempted 1,992 configurations. The 960 ordinary cases, 972 original supplemental attempts and 60 additional option-sensitivity cases were all present. There were 1,956 complete runs and 36 planned schema rejections. The offline verifier checked 103 ZIP hashes, 21,624 member hashes and 40,972,910 ordered canonical facts. It reconciled each sampled individual's stocks with committed transfers, actual uptake, conversion and loss, and checked world mass, energy, hydration and soil. It also reconstructed the versioned memory witness and verified its linkage to the observed care decision. The baseline reconstruction produced four byte-identical tables on independent rerun. [Archive audit](../../experiments/s6_4_wp6b_r1/analysis/archive_verification.json) [Baseline reconstruction](F1_V1_LARVAL_PATH_DIAGNOSIS.md)

The F1 v1 replay matched six archived file hashes per case for all 984 ordinary and matched wider controls. The first paid ration remained identical between models in these pairs, including both versions' missing first rations. All 480 application performance trials, with and without observation and with a real midpoint reopen, matched the respective uninterrupted input, initial checkpoint, final frame and canonical facts. [Paired v1 replay](../../experiments/s6_4_wp6b_r1/v1_replay) [Observation and restart equivalence](../../experiments/s6_4_wp6b_r1/performance/application-costs/reference_equivalence.json)

The funded-wall control uses the queen's real approach to move the egg-laying position. The same paid offspring remains locally reachable in the open branch and becomes occluded after a worker commits a soil fill in the closed branch. The child receives a maternal ration in the open branch. The closed branch records zero contact and zero ration for that child. The inherited `contact-blocked` supplemental setup retains its original seeded assay targets and can still rear reachable offspring. The new exact-boundary probes cover single and competing paid larvae, demand-clipped rations, expiry and empty payable protein, same-time competing donor and death priority, active-bout recovery, injected failure after a ration, and malformed witness or wrong block version. [Test implementation](../../cpp/tests/test_s6_4_wp6b_r1.cpp)

| Local Windows run | Tests passed | Wall time (s) |
|---|---:|---:|
| Release | 269/269 | 60.72 |
| Debug | 269/269 | 183.76 |
| Combined ASan/UBSan, initial parallel run | 268/269 | 557.74 |
| Combined ASan/UBSan, isolated warm test retry | 1/1 | 122.44 |
| Combined ASan/UBSan, full serial run | 269/269 | 590.35 |

The first sanitizer run hit the inherited 180 s timeout in `S6_4_RM01_warm` while the formal archive was also processing. It recorded no sanitizer diagnostic. The test passed at the unchanged timeout in the isolated retry and in the full serial run. The initial failure and both retries are retained. The candidate and representative-archive commits passed all five GitHub jobs across Windows, Linux and sanitizers. The archive verifier and inherited tests run in Core CI. [Local log hashes and commands](../../experiments/s6_4_wp6b_r1/tests/local_receipt.json) [Candidate Core CI](https://github.com/Aquaticfuller/AntWorld/actions/runs/43295252890) [Representative archive Core CI](https://github.com/Aquaticfuller/AntWorld/actions/runs/43297929576)

## Repeat feeding and recipient distribution

Primary results below include every care-on world and all hatched larvae. Each row contains 192 worlds. A dose count includes only protein-positive maternal rations. Tissue achievement requires committed positive uptake. The first-ration and outcome chains remain individually traceable by event and scheduled source.

| Population and model | Hatched | Completed meals | Positive protein meals per larva, 0 / 1 / 2 / 3 / 4 / ≥5 | Tissue achieved / pupated / eclosed | Worlds with an eclosed worker |
|---|---:|---:|---|---:|---:|
| Borisovka v1 | 7,061 | 590 | 6,612 / 340 / 77 / 32 / 0 / 0 | 0 / 0 / 0 | 0 / 192 |
| Borisovka R1 | 6,988 | 1,622 | 6,636 / 39 / 4 / 8 / 17 / 284 | 284 / 284 / 284 | 136 / 192 |
| St. Petersburg v1 | 7,042 | 796 | 6,418 / 505 / 75 / 35 / 9 / 0 | 0 / 0 / 0 | 0 / 192 |
| St. Petersburg R1 | 7,005 | 1,955 | 6,599 / 5 / 14 / 43 / 22 / 322 | 322 / 322 / 322 | 154 / 192 |

Of the R1 payments, 1,191 Borisovka and 1,454 St. Petersburg rations followed the memory-specific repeat selection. Every repeat selection in the primary care-on cases produced positive protein. The interruption probes separately verify that a selection carries no guaranteed payment. R1 more often selected the same recipient within 48 hours of a meal. The observed counts were 1,235/1,622 and 1,520/1,955, compared with 135/590 and 197/796 under v1. The denominator includes all meals and the table preserves early competing exits. These are descriptive within-world observations. [Repeat events and per-larva paths](../../experiments/s6_4_wp6b_r1/candidate_paths) [Retarget windows](../../experiments/s6_4_wp6b_r1/comparison/retarget_windows.csv)

R1 uses more of the same mother's resources. Borisovka mother-to-larva payments rose from 9,440 to 20,684 µg protein, 3,540 to 9,700 µg lipid, and 11,800 to 32,440 µg water. The St. Petersburg totals moved from 12,736 to 24,930 µg protein, 4,776 to 11,718 µg lipid and 15,920 to 39,100 µg water. The median terminal maternal mobile protein per primary world fell from 452 to 390 µg in both populations. The same 168 of 192 queens died in each population, with 96 energy deaths and 72 dehydration deaths. Median R1 death days among deaths were 61.33 and 60.17, compared with 61.42 and 61.50 in v1. The original no-supply and mortality controls remain part of the comparison.

Protein concentration increased. Among worlds with some delivery, median within-mother Gini including zero recipients rose from 0.927 to 0.950 and from 0.914 to 0.941. Unfed larvae increased by 24 and 181 despite fewer hatches. The paired profile-and-seed bootstrap puts the mean change in unfed larvae per St. Petersburg world at +0.943 with a 95% interval of [0.682, 1.198]. The Borisovka estimate is +0.125 [−0.146, 0.385]. Absolute larval deaths decreased in both populations, and many larvae still starved or dehydrated. Neither allocation breadth nor a natural larval survival distribution is established. The simulated first-worker world differences from v1 were +70.83 [55.73, 84.38] and +80.21 [70.83, 88.54] percentage points. The bootstrap samples profiles and software seeds within population. [Paired outcomes and intervals](../../experiments/s6_4_wp6b_r1/comparison)

## Ordinary robustness, adverse cases and sensitivity

| Frozen endpoint | Borisovka | St. Petersburg |
|---|---|---|
| Main combinations with at least four successful seeds, required ≥24/32 | 24/32 | 27/32 |
| Additional check combinations, required ≥6/8 | 6/8, 32/48 successful worlds | 8/8, 44/48 successful worlds |
| Factor-level combinations, required ≥10/16 at each level | 8/16 at egg lipid 11 µg and 8/16 at egg basal 22,000,000 nJ/day | All levels reach 10/16 |
| Ordinary care-off pupation | 0 | 0 |
| Complete B06 daily count-matched worlds, required ≥12 | 0 | 0 |

Overall the ordinary experiment produced a first worker in 366/480 R1 care-on worlds and 0/480 v1 care-on worlds. The factor and timing gates both fail. The daily count method retains its original definition. The first observed larval count is two or four in Borisovka and four in St. Petersburg. No world reached its count as simultaneously living pupae at a daily cut, and the largest simultaneous worker count was one in either population. Individual completers have birth-to-worker ages of 41.4–42.0 days in Borisovka and 39.9 days in St. Petersburg. Those conditional ages are compatible with the B06 published ranges, while the observed colony trajectories do not supply the required count-matched comparison. [Factor and profile rows](../../experiments/s6_4_wp6b_r1/analysis) [Count and survival diagnostics](../../experiments/s6_4_wp6b_r1/limits)

The five v1 successes among the 24 matched wider spacing controls reproduced byte-for-byte on the v1 path. All 24 matched R1 worlds eclosed at least one worker. The first successful larva in each of the five original positive controls again received five meals. The first successful identity and its timing can change. These wider controls remain outside the ordinary gate. Across the nominal sensitivity cells the 24-hour window yielded 9/12 successful worlds, the 48-hour nominal and 72-hour sensitivity both yielded 12/12, and zero repeat yielded 0/12. The 50% and 87.5% propensity cells each yielded 12/12 with different meal and pupation counts. These one-at-a-time micro results do not justify changing the frozen nominal or failing factor levels. [Matched wider controls](../../experiments/s6_4_wp6b_r1/comparison/wider_success_controls.csv) [Sensitivity cells](../../experiments/s6_4_wp6b_r1/comparison/option_sensitivity.csv)

Among 12 combined low-stock worlds per treatment, first workers appeared in 7 with low maternal lipid, 5 with low mobile protein and 3 with low water. Every mother in those three treatments died. High joint maintenance rates and the isolated low egg-lipid arm each produced zero workers in 12 worlds. The 8/32-worker depot and low-protein arms had actual outside delivery, while blocked and empty arms had zero outside delivery. Initial worker stocks and paid maternal rations can still produce new workers in the blocked and empty arms. All 96 seeded-worker control queens died by the horizon. [Supplemental and early-worker outcomes](../../experiments/s6_4_wp6b_r1/analysis/cases.csv)

## Residual failure mechanisms

The eight Borisovka failing ordinary profiles share 11 µg initial egg lipid and a 22,000,000 nJ/day egg basal rate. The inherited 16.7-day egg clock leaves 6,600,000 nJ at hatch in the closed budget, equivalent to about 4.526 hours at larval maintenance. All 1,782 hatched larvae in those 48 worlds died from energy depletion within six hours. Only three received a first meal. Those three actually received 6 µg lipid, 16 µg protein and 20 µg water about 1.2 hours after hatch. They died at 4.526 hours with all 6 µg received lipid unconverted and 31 µg water remaining. The next nominal uptake/refill pulse would have been 7.2 hours after hatch. There was no positive uptake before death. The St. Petersburg counterpart begins the larval stage with 28,600,000 nJ under its 15.7-day clock and has 25/48 successful worlds. The fixed geometry and reduced egg cost exposure make this a useful comparison of the model's startup constraint. [Closed budgets and affected identities](../../experiments/s6_4_wp6b_r1/limits)

The repeated feeding candidate can operate only after a first paid meal. It cannot fix a missing initial feeding opportunity or an exhausted body buffer with a future refill. A further limit occurs after emergence. All 284 Borisovka and 322 St. Petersburg primary workers executed ordinary autonomous decisions and committed actions. All 606 subsequently dehydrated. Median post-emergence survival was 26.9 and 29.2 hours, with maxima of 66.9 and 69.2 hours. No primary new worker provisioned the queen or a larva. R1 produced actual first workers and still failed to sustain an early-worker colony under the finite starting hydration treatment. [Stage competition and adult survival](../../experiments/s6_4_wp6b_r1/analysis/stage_exposure.csv) [Adult survival totals](../../experiments/s6_4_wp6b_r1/limits/adult_survival.csv)

The next smallest proposed mechanism experiment is a local, already-funded lipid mobilization boundary at larval exhaustion. Compare the existing periodic refill to an earlier bounded conversion of lipid already owned by a living larva, with the normal exact death boundary and all doses held fixed. Use matched real local first feeds immediately before and after the scheduled pulse, plus a no-received-lipid control, and require a committed debit and conversion before any extra survival. This addresses the demonstrated delivery-to-availability gap in the three affected histories. The much larger missing-first-feed exposure and post-emergence water loss need separate hypotheses and matched data. This proposal has no implementation or adoption authorization.

## Scientific scope and handoff

B06 remains a warm development anchor with moist cotton and count-based observations. R1 uses finite starting hydration. B01's behavior scans and founding series and B03's day-49 food-treatment census remain development comparisons. The R1 B01-like day-55 window had zero recorded handling and feeding scans in the primary worlds, in a distinct simulated care-clock regime. At day 49 the R1 primary cases had 150 living Borisovka pupae and zero living workers, and 134 living St. Petersburg pupae and 24 living workers across their respective 192 worlds. These observations describe the exposure and cohort mismatch. They do not supply independent validation or match the studies' conditions and denominators. The B01/B02 behavioral discrepancies and BR-01 through BR-09 data needs remain open. [B01](https://doi.org/10.1111/1365-2435.14536) [B03](https://doi.org/10.1093/biolinnean/blad149) [B06](https://doi.org/10.1023/B:JOEY.0000033808.45455.75)

The [20-row crosswalk](R1_MULTISCALE_ACCEPTANCE.csv) retains the accepted and deferred scopes. The [performance report](R1_PERFORMANCE_QUALIFICATION.md) records the native passes, the application failure and all slow samples. The [archive index and reproduction commands](../../experiments/s6_4_wp6b_r1/README.md) support independent review. The production model and original accepted data remain the control. F1-R1 is submitted for independent science and code review.
