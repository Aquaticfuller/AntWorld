# S6.3.1 evidence and correction freeze

Frozen after all 48 historical and 144 unchanged-model protocol-44 runs, before a reproductive-rule modification or corrected outcome. The baseline source is bf61ebf; protocol 45 clarifies inherited physiology. Preserve every baseline run and the original S6.3 evidence.

## Diagnosis from committed facts

The new observer reproduces all 48 historical primary trajectories and final checkpoint bytes exactly. Independent maternal accounting agrees with all 605,421 decision observations and daily snapshots in those runs. All 48 queens die from accounted body-energy depletion. Fifteen retain crop carbohydrate at death. This is not carbohydrate disappearance: crop carbohydrate is unavailable as body energy until the next absorption pulse.

In historical seed 1, eight workers, balanced supply: at day 10, events 1751/1752 record a funded egg after absorption. Maternal body energy falls from 526,000,000 to 16,000,000 nJ, or 4.444 hours of maintenance. Event 1775 transfers 55 ug carbohydrate to her crop, but event 1779 records energy depletion before the next six-hour absorption. Her remaining crop contains 55 ug carbohydrate. Across historical supplied conditions, post-laying maintenance coverage can be as short as ten minutes. Normal funding tests only whether the immediate debit leaves positive stores.

The causal matrix separates several influences. All 24 supplied non-laying queens survive 90 days, versus zero of 24 supplied laying queens. Without external food, laying and non-laying queens live 7.870 and 19.676 days respectively; no queen receives a gift. Disabling colony exchange produces the same queen lifetimes despite external food. Thus both reproductive expenditure and actual worker delivery matter. Suppression also removes offspring demand and future workforce, so it is not a pure instantaneous egg-cost intervention.

In the adequate-access 180-day baseline, zero of six eight-worker queens survive, but five of six 32-worker queens survive with 28-31 births in days 120-180 and 80-83 cumulative emergences. The sixth 32-worker queen dies at day 12.060. Existing local supply can therefore support sustained reproduction under this resource/access fixture. It is not robust to initial population or stochastic timing. Do not describe all baseline positives as failures, or all deaths as missing worker provisioning.

Independent absorption, behavior and metabolic schedule changes produce non-monotone outcomes: no three/six/twelve-hour arm establishes robust 90-day survival. One of six four-day laying-interval cases survives. These controls do not identify measured species rates; they expose coarse scheduling and allocation sensitivity. They are not candidates from which to select a favorable parameter.

## H8: local maternal maintenance reserve

Implement one optional rule: before paying an egg's unchanged resource costs, require remaining **body energy and body water** to exceed the mother's own integrated basal requirements over a declared maintenance horizon. The computation uses only the queen's physiology, current body stores, integer water remainder and reproduction configuration. Crop contents are not counted as already absorbed energy. No worker choice, contact count, gift priority, RNG stream, resource supply, egg cost, or metabolism is changed.

The primary ENGINEERING_FIXTURE horizon is **one configured reproduction interval** (two days in the reference fixture). This is a local allocation horizon, not a lifespan or survival target: ongoing metabolism and water loss continue unchanged, attempts still occur on the same schedule, shortage can block all subsequent laying, and queens can still die without supply. The rule charges nothing for a deferred attempt and adds no food. No future contact or successful feeding is assumed. Both energy and water use strict positive residuals because zero stores at a physiological event cause death before absorption.

This is a phenomenological body-condition hypothesis. The Lasius niger founding-feeding experiment (DOI 10.1093/biolinnean/blad149) supports resource-dependent output; the reproductive hormone experiment (DOI 10.1016/j.jinsphys.2016.09.004) supports physiological modulation. Neither measures this horizon, egg cost, established-queen reserve threshold or queen preference in trophallaxis. Do not claim a validated survival-reproduction trade-off for this species from these two studies.

## Frozen post-change comparisons

Repeat all 144 protocol-44 controls with H8 and all 48 historical fixture conditions. The latter are changed-model comparisons, not byte-identical historical reproductions. Continue to run the unchanged mechanism from the final source separately for compatibility. Primary H8 horizon follows the configured reproduction interval in the four-day arm. Suppressed laying has no reproduction record and consequently remains exactly unchanged.

Add **48** sensitivity cases: seeds 1-6, workers 8/32, balanced ordinary 90-day and adequate-access 180-day fixtures, each at (a) one absorption period and (b) two reproduction intervals. These are shorter/longer allocation horizons, not an optimization sweep. Publish every result. The main one-interval mechanism remains the primary comparison regardless of which horizon produces more births, emergence or survival. No follow-up tuning or additional worker mechanism is authorized by a disappointing result; report the remaining limit.

Use the same reporting, censoring, exact-account and bootstrap rules as protocol 44. Add the count of births that leave insufficient energy/water to reach the next absorption pulse, last-birth time, blocked attempts and post-laying reserve distributions. The 180-day capability endpoint is unchanged. Observation instruments may only change to correct diagnosed accounting errors, with explicit provenance; Core outcomes must remain unaffected.

## Representation and tests

Store the optional nonnegative horizon in ReproductionConfig. Zero preserves legacy scheduling, facts and bytes. Positive horizons use an explicit new checkpoint schema/physics version; restore old version 9/11 exactly without migrating its behavior. Validate numeric products/overflow and bind the new configuration to reproduction enrollment evidence. Test strict funding boundaries, independently limiting water, deferred no-debit attempts, resumption after an actual transfer/absorption, near-death pulse ordering, no-food death, geometry-blocked gifts, local autonomous supply, corruption, transactional allocation failure, irregular continuation and durable saves. Do not add population scans to the decision path.

Stop after these comparisons and engineering verification. SD-04, SD-06, SD-07, trail recruitment and long-history storage remain open. S6.4 is not authorized.
