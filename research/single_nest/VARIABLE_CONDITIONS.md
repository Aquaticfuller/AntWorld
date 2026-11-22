# Variable conditions in one founding nest

Physics 45 uses checkpoint schema 38, starting from the Physics 43 mouth
contact and delivery rules. Select it explicitly in the sealed nest viewer.
The previous models remain selectable and keep their own checkpoint versions.

## Behavioral clocks

The first founding attempt has a bounded variation of 6 percent around the
reference time. Each queen has a persistent cadence factor between 0.9 and 1.1.
Each subsequent interval multiplies the nominal spacing by that factor and a
triangular draw between 0.6 and 1.4. A separate draw varies ordinary worker
review intervals by up to 25 percent around the nominal cadence. These
`ENGINEERING_FIXTURE` ranges use the world seed, individual identity and
attempt or review count. Setup, actual execution and full replay use the same
function. The first-bout clock schedules opportunities. Food, body reserves
and a legal egg site determine the committed births. The reference two-hour
and two-day spacings are engineering inputs. Egg counts vary between real
queens and over collection time and day under the reported laboratory
protocol. Its figures give evidence for variability and provide no
distribution of uninterrupted nest inter-egg intervals. [Original
observations, Figures 2–4](https://pmc.ncbi.nlm.nih.gov/articles/PMC10087202/)

## Trail exposure

The reference half-life comes from scenario setup. At each cell the elapsed
time is divided by an effective half-life before exponential decay.

```
effective half-life = reference half-life × retention
                      / (temperature rate × exchange × moisture rate × local rate)
temperature rate    = 2^clamp((temperature Celsius - 25)/10, -4, 4)
exchange            = 1 sheltered or 1.35 ventilated
retention           = 1 mineral or 1.25 for the porous hypothesis
moisture rate       = 1 mineral or 1 + 0.5 × (relative humidity fraction - 0.8) porous
local rate          = seeded 0.9–1.1, stable for each surface cell
```

The 1,955-second reference is the half-time of the exponential mark-strength
proxy inferred from black garden ant branch choice. The thermal direction
has cross-species support from heated substrate tests in
*Tapinoma nigerrimum* and *Aphaenogaster senilis*. All response factors are
`ENGINEERING_FIXTURE`. The positive humidity slope in the porous mode
represents a water-displacement hypothesis. Its sign and size need direct
measurement for the compound and substrate. The climate and exposure settings
are fixed during a run. Airflow is a scenario multiplier. Spatial diffusion,
time-varying weather and measured chemical surface retention are outside this
model. Recruitment at the handoff has a separate clock. [Black garden ant
branch choice, equations 3–5](https://doi.org/10.1007/BF01201674)
· [Heating experiment](https://doi.org/10.1007/s10886-012-0130-x)

## Local resources and observation

A finite-supply world splits the same initial exterior budgets and daily
releases over two compositionally different food sources and two water
sources. Extended supply increases the declared release horizon from 120 to
730 days. The founding wick is separate. A contiguous 1.25 mm radius feeding
patch uses the original colony stock and requires a clear connection to
its center and actual mouth contact. Delivery still uses the existing
handoff. Nearby adults without a compatible need are skipped when choosing
a food offer. Food is still paid for and enters the crop before uptake.

The surface and 3D cutaway use the recorded terrain outline and source
positions. The icons for stock and carried material reflect the recorded
components. Stock icons are a symbolic view of a shared pool. At 1× the
viewer can interpolate a checked level-ground Core lease during its
published interval. Lost evidence or an interrupted lease stops that
projection. Underground anatomical movement still uses the committed
sequence.

## Observed survival

Runs used 25 °C, 80 percent relative humidity, sheltered mineral exposure
and the 1,955-second trail reference. The first bout here is the 24 hours
after the first paid birth. The denominator follows individual identities
through hatching, death and eclosion.

| Supply | Seed | First-bout eggs | First-bout eclosions | Queen death day | Workers alive at day 150 | Workers alive at day 730 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Finite | 1 | 11 | 3 | 71.19 | 2 | Unobserved |
| Finite | 2 | 13 | 4 | 77.22 | 1 | Unobserved |
| Finite | 3 | 12 | 4 | 71.57 | 1 | Unobserved |
| Absent | 2 | 13 | 4 | 69.82 | 0 | Unobserved |
| Extended | 1 | 11 | 3 | 71.19 | 2 | 0 |
| Extended | 3 | 12 | 4 | 71.57 | 1 | 0 |

Across the three finite worlds, the first-bout losses included 15 energy
depletions and 10 dehydration deaths. The three queens ingested and absorbed
335, 2,124 and 689 µg of carbohydrate, respectively. Before the patch and
offer change, the corresponding runs registered 25, 15 and zero depot meals.
The seed-3 diagnostic found six completed approach segments with zero
meals, then energy depletion with 2,476 µg of carbohydrate in the depot.
The updated seed-3 world registers its first carbohydrate meal at day 49.5.
The seed-1 queen still dies with 3,022 µg of carbohydrate in the store.
Neither long run sustains a queen or workers to day 365. The ecological
failure remains open despite positive intake and conservation.

Reproduce the finite worlds with `NEW_VARIABLE_NEST 9803 3 250 80 plugged
1955 reachable finite sheltered mineral` in the native live executable.
Use IDs 9801, 9802 and 9803 for seeds 1, 2 and 3. Use `absent` for the
negative seed-2 world and `extended` for the two 730-day runs. Advance with
`ADVANCE` in 432,000,000 ms increments. Count the birth, phase transition,
meal, uptake and death facts via `FACTS_AFTER`. The trials used in-memory
history and passed `CHECK_LEDGERS`. Earlier R0 experiments with 730 days of
accounted release supported 52–54 live workers by day 730. This preview
has no validated trajectory to a mature, thousand-worker colony.
[Historical R0 controls](../r0/RESULTS.md)

## First-bout survival check

In the three finite worlds, all 36 eggs laid within 24 hours of the first
paid birth hatched. Twenty-four died as larvae and one died as a pupa.
The remaining 11 eclosed as female workers. In seed 1, the eight
individuals that died before adulthood received 186 µg lipid, 369 µg
protein and 820 µg water through paid egg provisioning and subsequent
maternal rations. These are gross transfers into those individuals.

The experimental comparison used the same finite worlds and modeled
conditions listed above. A temporary copy of `antworld_m0_live.cpp` set
`c.profile.opening_width = {6 * hour_ms};` for `NEW_VARIABLE_NEST` just
after `live_case(id,seed)`. The normal build used the nominal 24-hour
window. Both executables linked the same Core. Advance to days 49 and 90
with `ADVANCE 4233600000` and `ADVANCE 7776000000`. Match the queen's
committed `AntBorn` records to each individual's `StageChanged` and
`AntDied` records using `FACTS_AFTER`. Count eclosions through day 90.
All six runs passed `CHECK_LEDGERS`.

| Seed | First 24 h eggs, normal / shorter | First-bout worker eclosions, normal / shorter | All worker eclosions by day 90, normal / shorter | Queen death day, normal / shorter |
| --- | ---: | ---: | ---: | ---: |
| 1 | 11 / 4 | 3 / 4 | 5 / 8 | 71.19 / 69.84 |
| 2 | 13 / 3 | 4 / 2 | 7 / 7 | 77.22 / 80.37 |
| 3 | 12 / 3 | 4 / 2 | 8 / 10 | 71.57 / 72.72 |

The shorter window raised first-bout survival from 11/36 to 8/10 and
reduced the absolute first-bout worker count in two seeds. The later
cadence still permitted 18–23 paid births before the first worker in the
shorter-window runs, compared with 25–30 in the normal runs. All three
queens died before day 90 in each treatment. The experiment demonstrates
sensitivity to the timing of investment under the current provisioning
rules. Estimating wild survival or optimal brood size would require
different data and an experimental design at the colony level.

Recalculation of Szabó et al. Appendix S1 gives 15.27 live workers
(sample SD 4.73) and 18.73 pupae plus workers (SD 4.74) at day 49 for 30
unfed, undisturbed single queens kept at 24.5 ± 0.5 °C with wet cotton over
a water reservoir. The corresponding finite simulation worlds held one
or two live workers each on day 49 in both treatments. The paper records
live counts at the experimental endpoint and has no individual birth
denominator for comparison with the model's first 24-hour egg cohort.
The water exposure and founding environment also differ. [Original
study and Appendix S1](https://doi.org/10.1093/biolinnean/blad149)
