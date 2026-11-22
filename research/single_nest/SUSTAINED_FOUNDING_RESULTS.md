# Sustained founding and resource delivery

Physics 47 is an opt-in protected founding model. This experiment asks
whether a queen and locally acting workers can maintain resource delivery
and raise successive broods. The model retains its existing stage clocks,
initial queen reserves, egg costs and starvation and dehydration rules.
The assay uses constant temperature and humidity and does not implement
overwintering, age-related mortality, or mature colony growth.

## Defects identified in the resource chain

- An earlier protected trial recorded a worker repeating 42,035 blocked
  decisions at the same position while trying to depart. A worker returning
  from a different nest activity could also lose its ability to forage
  when it was no longer at the exact origin of its old connector.
- In the seed 17 development trial, the first forager made five carbohydrate
  deliveries shortly after emergence. It collected a sixth load on day
  45.55 and still held 1,132 µg of carbohydrate at day 51, unable to move past
  one shaft waypoint. Its previous feeding rule only allowed an autonomous
  forager to eat its cargo at the original feeder. It died of energy
  depletion on day 63.36.
- In another development run, a queen took 35,145 µg of carbohydrate from
  the depot by day 180. The committed maternal rations contained only 25 µg
  of carbohydrate. The remaining worker maintained deliveries and the queen
  laid new eggs. The colony still had just one worker at day 180. This
  separates a delivery fix from a brood provisioning fix.
- In the matched intermediate iteration, the seed 3 queen died of
  dehydration with 5,026 µg of carbohydrate in the nest. In seed 29, brood
  27 and 28 each received six maternal feeds, pupated, and then exhausted
  energy at their pupal sites about two days past their nominal emergence
  dates. The earlier stage gate tested only the default adult heading.

## Model changes

| Change | Scope and rationale |
| --- | --- |
| Legal departures and repeated trips | Workers approach the local handoff area, check load clearance, and can reconnect a departure from a new berth. Unloaded outbound workers can retreat along a real traversed segment. A successful carbohydrate delivery allows another trip while the local depot has room for one more load above the existing buffer. Failed and empty returns still trigger a review. |
| Private route retention | Learned routes have a 24-hour review lifetime in this scenario. A worker must actually have visited the feeder and the next step must remain legal. The lifetime is an engineering choice informed by laboratory memory lasting to the following day, under learned odor cues. It is not a fit to the maximum lifespan of a natural trail. [Czaczkes et al., 2014](https://doi.org/10.1007/s00265-014-1710-2) |
| Return traffic and individual intake | An unloaded worker or queen can use a legal resting move to clear a locally perceived loaded carrier. Collision and yielding use the same anatomical sweep. A hungry carrier can take a timed, paid bite from its own cargo along the route as well as at the source. Advice about general traffic priorities and the intake horizon is an engineering assumption. [Mailleux et al., 2009, studied return and uptake behavior](https://doi.org/10.1016/j.crvi.2008.10.005) |
| Local wick | Queens and workers approach and drink at a real contact point on the finite wet patch. Each sip debits the resource and enters the crop before actual uptake. Workers seek at one day's declared turnover and the slower foundress has two days to approach. They refill toward two and three days respectively, within the sip and crop limits. The contact patch and thresholds are engineering fixtures. The protected wick uses 1.5 mL, informed by a laboratory founding protocol with a cotton barrier. [Turi et al., Methods](https://doi.org/10.1111/imb.12809) |
| From adult crop to larvae | Adults already able to pay their own upkeep through the next absorption retain at most one transmissible carbohydrate ration in the crop. A well-supplied queen with a locally payable larval ration can interrupt the repeated depot top-up cycle and begin ordinary care. Every recipient still needs a successful contact and funded dose. The reproduction budget still accounts for local unpaid brood, maternal upkeep, and the next egg. Diet and maternal condition have direct support in *Lasius niger*. Local crop allocation has cross-species support. The ration and decision rule remain engineering hypotheses. [Szabó et al.](https://academic.oup.com/biolinnean/article/142/4/397/7342048) · [Greenwald et al., *Camponotus sanctus*](https://elifesciences.org/articles/31730) |
| Space at eclosion | The developing worker can assume another valid horizontal heading at its actual pupal site when the original direction interferes with a wall or adult. A carried or fully obstructed pupa still waits and pays maintenance. The recorded pose is checked against reconstructed geometry on archive load. This is a clearance rule, with no separate biological timing coefficient. |

## Matched observation

The paired arms are Physics 46 with brood budgeting and Physics 47 with
sustained supply enabled. Both use seeds 1, 2, 3, 17 and 29, an initially
plugged chamber, the 1.5 mL wick, 25 °C, 80% relative humidity, sheltered
mineral trail conditions and the same four outside sources with a finite
730-day release budget. A Physics 47 no-exterior-supply control uses seed 2
and retains the founding wick. The older small-wick observations remain in
[Founding nutrition and brood allocation](FOUNDING_NUTRITION_RESULTS.md).

Day counts report living adults per world. The first brood covers committed
eggs during the first 24 hours after laying begins. Survival at worker age 7,
30 or 90 days uses the individual's recorded eclosion time and preserves
censoring. Year-two performance requires new eclosions, as well as living
queens and workers. Surviving workers in orphaned worlds are reported
separately and do not establish continuing colony growth.

The measurement reads the native frame and committed events in slices.
When packed history reaches 96 MiB, the tool retains the compact
continuation in memory after consuming the older facts. It verifies the
frame is byte-identical across that operation. It checks resource ledgers
at the final cut and independently advances to each recorded queen death
to recover the body, crop, carried, depot and outside balances at that time.
The run writes only small JSON receipts when redirected.

~~~powershell
py -3 -B -m tools.build_m0_live
py -3 -B -m tools.measure_single_nest_lifecycle --treatment budget --wick wet-wick --days 730 --seed 1 --seed 2 --seed 3 --seed 17 --seed 29
py -3 -B -m tools.measure_single_nest_lifecycle --treatment sustained --wick wet-wick --days 730 --seed 1 --seed 2 --seed 3 --seed 17 --seed 29
py -3 -B -m tools.measure_single_nest_lifecycle --treatment sustained --wick wet-wick --supply absent --days 730 --seed 2
~~~

## Results

All eleven final and reference runs reached day 730 and passed native
resource, energy, water and soil ledger checks. The reference frame hashes
were identical across two local builds. Each original checkpoint and final
frame identity, simulation command, binary identity and census is in the
[receipts](SUSTAINED_FOUNDING_RECEIPTS.jsonl). The five preceding candidate
runs are retained in the same file with their own binary identity and
`before_emergence_and_wick_access_update` label.

| Pooled endpoint across the five paired seeds | Physics 46 | Physics 47 |
| --- | ---: | ---: |
| First-brood eclosions / eggs | 16 / 49 | 45 / 64 |
| First-brood workers alive at age 7 / 30 / 90 days | 7 / 5 / 2 | 32 / 18 / 10 |
| All worker eclosions | 47 | 71 |
| New worker eclosions after day 365 | 0 | 5 |
| Carbohydrate delivered to the nest (mg) | 43.439 | 330.002 |
| Carbohydrate taken into the queen's crop by depot meals or gifts (mg) | 10.449 | 237.494 |
| Larval carbohydrate uptake (mg) | 1.305 | 2.905 |
| Queens alive at day 730 | 0 / 5 | 0 / 5 |
| Live workers at day 730 | 2 | 6 |

| Seed | Live workers on day 49, old → new | Day 90 | Day 365 | Day 730 | Queen death day, old → new |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0 → 5 | 2 → 3 | 0 → 1 | 0 → 1 | 76.32 → 531.45 |
| 2 | 2 → 9 | 3 → 1 | 0 → 1 | 0 → 1 | 76.44 → 99.15 |
| 3 | 2 → 3 | 1 → 4 | 1 → 2 | 1 → 2 | 86.78 → 318.07 |
| 17 | 1 → 4 | 1 → 4 | 0 → 4 | 0 → 1 | 77.08 → 68.42 |
| 29 | 0 → 2 | 1 → 2 | 1 → 1 | 1 → 1 | 70.81 → 104.06 |

First-brood development and adult survival improved in the panel. Twenty-one
adults eclosed at an alternative legal heading. Seed 1 continued laying in
year two and produced all five later workers. Sustained two-year colony
growth remains unachieved. The six final workers were in orphaned worlds.
Four candidate queens depleted energy with no carbohydrate at the depot
or in carrier custody, even though the outside sources held 143–655 mg.
The remaining queen, seed 17, dehydrated on day 68.42 with 6.704 mg of
carbohydrate in the depot and paid energy remaining. Its lifetime was
shorter than the matched reference. The candidate retains repeated blocked
steps in several worlds, including 96,862 no-legal-step decisions in
seed 17, so a plausible foraging mechanism still needs dependable
access along crowded return routes and a better drinking approach.

The no-exterior-supply control delivered zero carbohydrate, protein and
water. The queen died of energy exhaustion on day 69.55, ten workers
eclosed, and all individuals were dead at the final census.

## Verification and storage

Windows Release CTest passed 292/292. OP0 passed 56 tests with one optional
skip. The Chrome smoke test configured and opened Physics 47 in the Chinese
viewer. Python independently read the SQLite archive. Native restore of
both the SQLite archive and the compact save reproduced subsequent frames
and committed facts at the test cut. The local evidence verification reached a mismatch in
the existing `experiments/s6_2/analysis/environment_correlations.csv` using
Python 3.15.2. That comparison is separate from the CTest and OP0 results.

The largest final case committed 2,115,916 facts. Peak packed history was
31.7 MiB and peak native working set was about 50 MiB within the five candidate
runs. The analysis streamed observations and retained only the receipts.
Temporary CTest outputs totaling 452,318,220 bytes were removed after
verification.

## Comparison with colony observations

Szabó et al.'s unfed, undisturbed queens at 24.5 ± 0.5 °C had a mean of
15.27 living workers at day 49, with wet cotton provided. Published
longitudinal censuses under twice-weekly diets reached medians of 11 workers
at day 55, 32.5 at day 163 and 54.5 at day 286. The Kramer et al. colonies
averaged 18 ± 8 workers at about eight months and 250 ± 79 around month 20
after two winters. These contexts distinguish a protected founding period
from extended colony development. The differences in diet, chamber geometry,
season, worker aging and feeding opportunities limit quantitative comparison.
[Szabó et al., Appendix S1](https://academic.oup.com/biolinnean/article/142/4/397/7342048)
· [Longitudinal diet data](https://datadryad.org/dataset/doi:10.5061/dryad.g79cnp5n1)
· [Kramer et al., §2.3](https://www.rug.nl/research/gelifes/tres/_pdf/kramer_etal_expgerontol_2016.pdf)

The daily release distributes 1,500 µg of carbohydrate between two
feeders. At the configured conversion yield this is 12 J/day, before
delivery losses. After the queen's 2.34 J/day basal cost, the remaining
daily release supports at most about 112 idle workers at the model's
0.0864 J/day per worker. Activity, brood expenditure and incomplete
collection reduce that budget. Accumulated stock can temporarily add to
the daily supply. The experiment addresses provisioning in an early
colony, with later population scales requiring separate inputs and
validation.
