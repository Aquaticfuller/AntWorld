# Integrated founding readiness

## Scope

This package starts from R2 `f1d1fe238e95a84f6b2894e2c4143836ef35d03d`, with R1 `74555a0197fe41b6e8183e9c56525d7cca9b549a` as the last approved engineering reference. The final candidate is founding profile 7, selected explicitly. It describes a warm, protected one-queen starting condition and a small early workforce with a physically accessible feeding site. Actual absences, obstruction, component omission, scarce input, brood failure and individual death are retained. See the [frozen thresholds](FROZEN_INTEGRATION_PROTOCOL.md), [evidence and storage versions](INTEGRATED_EVIDENCE_AND_VERSIONS.md) and [reproduction steps](REPRODUCE_INTEGRATED_FOUNDING.md).

## Causal sequence

The environment-only R2 test moves the feeding site from the nest to a real surface location reached through a loaded-clearance connector. All 12 nominal balanced worlds acquired and delivered material, with 93 verified loaded trips. Three queens received a positive worker gift. All 12 died of dehydration. This separates a complete transport route from subsequent intranidal access. The frozen R2 worker and queen failures and first-census counts are described in the [baseline audit](BASELINE_CAUSAL_AUDIT.md).

| Comparison | Directly observed effect | Remaining causal gap |
|---|---|---|
| P and Y | Return-linked local nursing and a separately specified effective sugar yield increase receipt. With both, all 12 nominal balanced queens absorb carbohydrate and water and all die of energy exhaustion around day 71–74. The control and separate switches have their own archives. | Ingestion and uptake remain different transitions. A nurse decision may still result in no delivery, and actual intake can remain too small or late. |
| N and E | Local withdrawal puts previously delivered material into the queen's crop. With N alone all 12 nominal balanced queens live to day 150. E records real body-energy, protein and water payment. Both yield actual late eclosions but all 12 nominal balanced queens die before day 150 under the combined N+E treatment. | Later funded cohorts and terminal survival are separate endpoints. Depot availability and crop contents are intermittent. |
| U | In the original diagnostic pair the queen uses 150 µg of owned crop at day 120.142735, gaining 1.2 J and living another 0.513 d. Nine boundary uses occur among the 12 nominal balanced queens. All still die from energy exhaustion. | That donor was eventually unable to draw from a locally empty depot although the source still held over 140,000 µg carbohydrate. Changing access to already owned crop cannot correct a missing delivery. |
| F | Experienced workers can act on a currently sensed local maintenance shortfall without a new scheduler wake. The twelve nominal balanced worlds complete every endpoint through day 150. | Real first-worker variability, depleted components and blocked routes still constrain the loop. The response proxy remains an assumption, with no measured cutoff in nanitics. |

Mechanism evidence has been updated with the source's experimental unit and cross-condition limits. Mailleux et al. tracked individual scout trips from small incipient black garden ant nests, using a sugar site and up to four observed workers per individual-behavior trial. The smallest standard colonies averaged around eleven months of age. This does not measure the new local shortfall signal or first-day worker timing. [Original Methods §§2–4, Table 1, pp. 25–28](https://doi.org/10.1007/s000400300004)

## Supplied nominal ecology

| Exposure | Full chains / 12 | Queens at day 150 | Workers eclosed | Valid loaded trips | Dietary-funded late eclosions |
|---|---:|---:|---:|---:|---:|
| Balanced | 12 | 12 | 537 | 866 | 369 |
| Limited | 0 | 0 | 412 | 729 | 244 |
| Water only | 0 | 0 | 36 | 32 | 0 |
| Carbohydrate only | 0 | 0 | 37 | 82 | 0 |
| No protein | 0 | 12 | 56 | 1,005 | 1 |
| Blocked | 0 | 0 | 36 | 0 | 0 |
| Absent | 0 | 0 | 36 | 0 | 0 |

All 12 balanced colonies retain a living queen and at least one working adult at both planned census cuts. The witnesses include the same worker delivering on separate days, self-uptake of both water and carbon, actual positive gifts, queen uptake, worker protein incorporated into larvae, later funded eggs and work over multiple weeks. The conservative crop-flow attribution requires at least 34,822 µg of assimilated larval protein from worker gifts over these twelve worlds after accounting for available maternal ration protein. It does not identify which identical molecules came from a particular load. At day 150 there are 537 right-censored eclosed workers in the balanced nominal cases, 533 with recorded adult uptake of both carbon and water. Each limited-arm queen dies of energy depletion, despite real trips and continued brood. Carbohydrate-only queens die of dehydration and water-only queens die of energy depletion. In no-protein worlds some later eggs can draw on initial mobile protein. There is zero positive worker-to-larva protein, so none qualifies as a complete chain. All endpoint zeros and time-to-event exposure are preserved.

## Core changes and verification

The implementation keeps the WorldRuntime transaction, keyed decision sources and real 3D movement. The candidate adds no global food query or seeded worker. It commits the same kinds of physical delivery and local nutrient exchanges, with separate evidence for nest meal, dietary egg funding and adult uptake at exhaustion. Earlier formats use their original bytes and 40-byte reserve record. The internal adult uptake clock uses a separate transaction journal. Read-only observation and segmented recovery preserve the exact state, history and random state in the reference comparisons.

The selected representative worlds compare observed, unobserved and day-75 SQLite recovery. Saved midpoint databases and their original WAL files, where present, allow independent reopening. The reproduction of v1 and R1 reran 1,092 cases each against their archived authority with 2,184 exact matches. Eight representative R2 worlds were reopened in sixteen durable or observer-disabled replays. The new tests include body-stock boundaries, missing ingredients, geometry exclusion, format mismatch, republishing rollback, legacy row size, absence of remote credits and deterministic recovery.

The cross-platform compiler warning was a shadowed local name in the new policy and was corrected without changing its rule. A Debug regression exposed legacy row-size growth in a draft. A sparse opt-in clock restored the accepted size. A sanitizer report exposed a reference to a temporary in a new test. The test now copies the queried profile before using it. Preserve these failures and the corrected verification.

## Biological interpretation

The original B06 experiment used isolated water-supplied foundresses, repeated census and conditional means. Count attainment needs simultaneous living brood and is distinct from individual hatch-to-pupa or pupa-to-worker time. An early single worker, or a later fed cohort, cannot close the original count-based timing criterion. Keep exact and at-least matches, the original twelve complete worlds per population minimum, temperature/reference intervals and every competing death. B06, B01 and B03 helped develop this family and do not qualify as newly held-out evidence. [B06 Methods and Tables 1–2](https://doi.org/10.1023/B:JOEY.0000033808.45455.75)

BR-01 to BR-09 remain `BIOLOGICAL_BLOCKED`. The needed measurements include independently collected stage budgets, worker-to-queen volumes and timing, larval protein uptake, founders in comparable protected watering conditions, and paired whole-colony time series. No new direct evidence supports the fixed cue weights, liquid pool, crop time boundaries, exact diet efficiency, two-interval replenishment signal or natural survival rate.
