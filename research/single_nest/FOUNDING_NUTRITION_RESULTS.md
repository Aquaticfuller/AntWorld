# Founding nutrition and brood allocation

Physics 46 is an opt-in founding experiment. The results support better access
to food already delivered to the nest. The budget arm laid fewer eggs and
raised more workers than the reference in this assay. Early adult survival
and sustained colony growth remain insufficient.

## Mechanisms and evidence

| Mechanism | Implemented rule | Evidence and assumptions |
| --- | --- | --- |
| Foundress access to food | The queen can inspect a familiar depot before her maintenance reserve runs out. She uses local stock only when she can perceive it, approaches the existing feeding patch through legal body poses, and takes a paid crop meal at mouth contact. | Direct *Lasius niger* feeding treatments show that diet and body condition affect founding output. Returning to the depot, the reserve horizon and the physical patch are model assumptions. [Szabó et al., Methods and Results](https://academic.oup.com/biolinnean/article/142/4/397/7342048) |
| Worker feeding and larval uptake | A worker can withdraw real nest inventory in response to local need and prioritize a reachable recipient. Trophallaxis still requires contact and a payable crop. The candidate can pass a water-only cue when hydrated but short of energy. | Brood presence and diet affect demand and foraging in black garden ants. The local demand estimates, bout timing and packet limits are fixtures. [Larval-demand experiment](https://pmc.ncbi.nlm.nih.gov/articles/PMC4553619/) · [Diet experiment and protocol](https://datadryad.org/dataset/doi:10.5061/dryad.g79cnp5n1) |
| Maternal ration | Once the queen has evidence of dietary food, the ration can debit it from her crop, with finite reserves available as before. A larval shortfall covers the remaining stages and upkeep through the first scheduled adult uptake. Assimilation follows the existing physiological events. | The sample and growth observations support finite maternal allocation. The deficit estimate and its delivery rule have no direct calibration. [Founding observations](https://doi.org/10.1111/1365-2435.14536) |
| Reproduction | The budget arm compares maternal energy, protein and water against her own maintenance and the outstanding costs of her locally visible eggs and larvae. One proposed egg needs room in that budget as well as the existing immediate payment and positioning checks. A deferral takes no resources. | The published founding experiments support sensitivity to body condition and brood context. The three-resource budget is a testable model assumption. [Founding treatment and supplementary data](https://academic.oup.com/biolinnean/article/142/4/397/7342048) · [Brood context data](https://doi.org/10.5061/dryad.pnvx0k6wd) |

The projected cost uses the declared phase rates and the larva's own holdings.
The queen's unfamiliar future intake has no place in the birth budget. Current
crop reserves contribute to projected cost coverage and the immediate egg
transaction still requires payable resources in the proper compartments. The
budget covers locally perceived brood and uses the scheduled uptake interval.
Route-dependent future provisioning remains uncertain. The working magnitudes are
`ENGINEERING_FIXTURE`. The experiments used the same stage clocks, supply
budgets and death thresholds in each arm.

## Paired native runs

The three arms were Physics 45 reference, Physics 46 local feeding, and
Physics 46 local feeding plus the brood budget. Each started with a single
queen and a soil plug. The five matched seeds were 1, 2, 3, 17 and 29. Runs
used the Borisovka fixture at 25 °C and 80% relative humidity, the same four
external sources and finite, 730-day resource release. Two more runs used
seed 2 with external food and water absent. Both kept the bounded founding
wick. All 17 runs reached day 730. The unit of comparison is one simulated
world per seed and condition. Raw facts and state frames were consumed in
memory. The [per-world receipts](FOUNDING_NUTRITION_RECEIPTS.jsonl) give state
hashes, stage counts, deliveries, intake, death causes, survival counts
and exact initialization commands.

The first brood consists of eggs born during the 24 hours starting with the
first committed birth. Worker age starts at individual eclosion. The first
brood figures below are pooled counts over the five seeds. Every first-brood
adult had a full observation window for the 7-, 30- and 90-day endpoints.
Counts at day 730 include surviving workers of any brood.

| Endpoint | Physics 45 | Physics 46 feeding | Physics 46 budget |
| --- | ---: | ---: | ---: |
| Eggs laid across five worlds | 147 | 161 | 128 |
| First-brood workers eclosed / eggs | 15 / 49 | 15 / 49 | 16 / 49 |
| First-brood workers alive at age 7 / 30 / 90 days | 4 / 2 / 2 | 5 / 5 / 4 | 7 / 5 / 0 |
| Worker eclosions across all broods | 32 | 46 | 46 |
| Larval deaths | 112 | 101 | 77 |
| Larval protein uptake across all broods (µg) | 2,920 | 4,675 | 4,163 |
| Foundress carbohydrate absorbed through death (µg) | 3,148 | 5,710 | 11,335 |
| Queens alive at day 730 | 0 / 5 | 0 / 5 | 0 / 5 |
| Workers alive at day 730 | 0 | 3 | 1 |

| Seed | Peak live workers, reference / feeding / budget | Queen death day, reference / feeding / budget | Workers at day 730, reference / feeding / budget |
| ---: | ---: | ---: | ---: |
| 1 | 3 / 4 / 3 | 71.19 / 70.05 / 76.32 | 0 / 0 / 0 |
| 2 | 3 / 9 / 3 | 77.22 / 74.79 / 76.70 | 0 / 2 / 0 |
| 3 | 3 / 8 / 5 | 71.57 / 75.08 / 86.96 | 0 / 1 / 1 |
| 17 | 3 / 3 / 4 | 69.03 / 69.03 / 80.42 | 0 / 0 / 0 |
| 29 | 1 / 1 / 3 | 71.12 / 70.52 / 70.81 | 0 / 0 / 0 |
| 2, no exterior supply | 2 / — / 2 | 69.82 / — / 71.22 | 0 / — / 0 |

Adult lifespan among observed deaths stayed short in the budget arm. The
per-world medians were 0.85–4.84 days versus 2.30–13.72 days in the
reference. The budget deferred 78 attempts and reduced the number of larval
deaths, while the first brood's 90-day survival regressed relative to both
other arms. This trade-off rules out treating more eclosions as evidence
of sustained growth. There were no external deliveries or depot meals in
either no-supply run.

## Where the supply chain breaks

* In the original three reference seeds, one queen died with 3,022 µg of
  carbohydrate left in the depot. The other two exhausted their depot
  carbohydrate. Seed 17 delivered none. Seed 29 delivered carbohydrate during
  the run and its queen's absorbed mass was zero. Delivery and absorption are
  separate observations.
* Early experimental rations covered development to eclosion without
  allowing time for early adult uptake. A 120-day pilot yielded at most one
  simultaneous worker per world and no external deliveries. Eight pupae
  in one pilot world died from dehydration. The revised ration budgets
  the first adult uptake interval and preserves pre-supply maternal feeding.
* A later feeding pilot recorded a queen with a familiar pantry only starting
  the approach in her final half-day of reserves. For example, feeding seed
  3 stayed at the same position from the day 55 to 68 cuts. She made partial
  approaches before death with 3,889 µg carbohydrate still at the depot.
  The current candidate checks the familiar pantry using the existing
  maintenance horizon and searches for legal mouth poses around the patch.
* Four budget queens absorbed depot carbohydrate. Seed 29 received only
  water deliveries. All five budget queens ultimately depleted energy.
  Their depots were out of carbohydrate at death, while their outdoor
  sources still contained 111.0–128.7 mg. Thus insufficient sustained
  transport remains a specific bottleneck. The feeding-only seed 3 died of
  dehydration and retained the importance of water as a separate constraint.
* Worker-to-larva protein transfers were zero in the five reference worlds
  and totaled 1,069 µg in the budget arm. Total larval protein uptake
  increased from 2,920 to 4,163 µg. Energy-depleted larvae with crop
  carbohydrate were rare in this panel. One occurred in the feeding-only
  arm. The receipts count this separately from the many larvae that lacked
  fuel at death.

## Biological comparison

The model produced the first worker around day 45–46, yet Physics 46
had at most three living workers at day 49 in the paired panel. Szabó
et al.'s unfed, undisturbed queens had a mean of 15.27 living workers
at that day. Their chambers had wet cotton and were held at 24.5 ± 0.5 °C.
Young worker supply and survival remain a larger discrepancy than
first eclosion time in this comparison. [Appendix S1 and protocol](https://academic.oup.com/biolinnean/article/142/4/397/7342048)

In the twice-weekly diet series, the recorded medians were 11 workers at
day 55, 32.5 at day 163 and 54.5 at day 286. The corresponding budget
medians were 2, 0 and 0. Kramer et al. observed a mean of 250 workers
around month 20 after two winters. Those colonies had cotton-fed water
access, food after worker emergence and periods of overwintering. The
constant warm sealed-shaft simulation and its outside release budget
are a distinct regime. These counts quantify the remaining scale gap.
They cannot identify a target survival probability for each egg. [Longitudinal
counts and censuses](COLONY_LIFECYCLE_REFERENCE.md) · [Diet data](https://datadryad.org/dataset/doi:10.5061/dryad.g79cnp5n1) · [Kramer et al., §2.3](https://www.rug.nl/research/gelifes/tres/_pdf/kramer_etal_expgerontol_2016.pdf)

## Reproduction and verification

```powershell
python -B -m tools.build_m0_live --jobs 4
foreach ($treatment in 'reference', 'feeding', 'budget') {
    python -B -m tools.measure_single_nest_lifecycle --days 730 --treatment $treatment --seed 1 --seed 2 --seed 3 --seed 17 --seed 29
}
foreach ($treatment in 'reference', 'budget') {
    python -B -m tools.measure_single_nest_lifecycle --days 730 --treatment $treatment --seed 2 --supply absent
}
python -B -m unittest discover -s op0/tests
ctest --test-dir build/m0-live -j 4 --output-on-failure
```

Each run checks the native ledgers at the final cut and reproduces the exact
queen death cut for its resource observation. The Physics 45 final frame
hashes for seeds 1–3 match the prior baseline. The new live regression
checks paid brood and queen feeding, resource-budget deferrals, both save
formats, and byte-identical continuation with preserved facts. The absence
control checks that either Physics 46 arm can run without generating an
external delivery or a depot meal.

The Windows Release build passed all 292 CTest cases. The OP0 suite passed
55 tests, with the optional legacy fixture-builder case skipped. Three focused
live tests also passed against the final native build after adding explicit
version checks for retained history. The local verification used the existing
incremental Release build and installed viewer runtime.

The largest encoded in-memory history was 29 MiB for 1,905,702 committed
facts. Native peak working set across the benchmark processes was 47 MiB
rounded up. The 730-day runs wrote no archive or per-event CSV. The tracked
receipts are under 50 KiB. Scenario scalars and stored factual histories
remain independently reviewable. The scientific gate for this candidate
is `ENGINEERING_ONLY`. Historical evidence statuses are B06
`INSUFFICIENT`, application performance `FAIL` and nine
`BIOLOGICAL_BLOCKED` roots.
