# What happened to the day-73 colony?

The old web default selected the anatomical nest (Physics 39), seed 3, a plugged entrance, a 1.2 µL finite wick, and 120 days of exterior supply. No saved player checkpoint was available. A fresh run with those inputs reproduced extinction before day 73.

## The original default

All 27 paid eggs hatched. Nineteen individuals died as larvae (ten of energy depletion and nine of dehydration). Eight became workers at different times; at most two workers were alive together. Seven of these workers died of dehydration and one of energy depletion. The queen died of energy depletion on day 69.1, with 2,655 µg of carbohydrate in the nest and 106,834 µg still outside. Her crop was empty. Workers had returned 2,666 µg of carbohydrate, but the record contains zero crop intake by the queen from that stock and zero worker-to-larva transfers. The last worker died on day 71.4.

Seven eggs were laid after the first juvenile death. This is a specific problem with how local care, resource access and reproductive decisions interact. A queen can afford an egg while another individual is already low on water, lacks food at its mouth, or has insufficient energy to survive until absorption. Only the identity and resource ledgers can distinguish those cases.

## How the live world changed

| Mechanism | Implementation and limits |
| --- | --- |
| First brood | The queen considers the energy and water of nearby, visible larvae against maintenance through the next uptake opportunity. A locally payable urgent ration takes priority in care selection. A new egg can be deferred. A different larva across a wall cannot suppress laying. Death and failed contact remain possible. Decisions, reproduction replay and resource deductions run in the Core. |
| Handoff | A loaded worker can unload from a valid handoff berth; paths around occupied adult bodies use the actual anatomical sweep. Read the queen's intake, oxidation and actual larval uptake separately from the amount unloaded. |
| Space | A single sealed chamber has rounded horizontal ends. Contact and path tests use the same 24 adjoining terrain bands as the viewer. The vertical cross section remains stepped. A derived search index accelerates disjoint bands without changing the stored geometry. |
| Food and water | Both outdoor food sources share the original total provision budget. The dry source dispenses up to 25 µg per successful collection, including a final partial portion. The other supplies mixed moist food. The protected nest starts with a finite 1.5 mL wick. Real drinking debits it into an individual's crop. The resource panel separates crops, mixed depot inventory, the wick, exterior stocks and unreleased food. |
| What a food glyph means | The dry-food counts and masses come from the Core. Up to 100 glyphs per component show the quantity. Larger stocks use grouped glyphs. Their arrangement is illustrative. Solid stock still uses a depot account; individual grain positions, food-food collision and a separate granary are not modeled. Free water in a chamber and water contained in mixed food have different representations. |
| Soil | A worker with a parcel can follow an open shallow shaft to a supported rim and drop it. Before breakthrough, a deposit may be underground. The resource panel groups actual deposited volumes by position and can locate the largest pile on each side of the surface. A circular mound is not guaranteed. Physics 49 independently tests local work-site selection and smaller roof cuts, at most 0.125 mm³ at this terrain resolution. Other excavation parcels may be larger. |

## Biological comparison

In the Szabó et al. wet-cotton assay, 30 undisturbed, unfed foundresses at 24.5 ± 0.5 °C had a mean of 15.27 living workers (sample SD 4.73) and 18.73 pupae plus workers (SD 4.74) on day 49. Their day-49 counts cannot identify the survival fraction of each queen's first eggs. They do establish a meaningful comparison at a named age. The model has a finite wick and can receive exterior food after the workers open the roof. [Original experiment and appendices](https://doi.org/10.1093/biolinnean/blad149)

Black garden ant workers collect liquid in their crops and exchange it orally. The spatial transfer experiment used queenless, broodless worker groups and sucrose solution; it cannot give a foundress-to-larva water transfer rate. The black garden ant nest hygiene experiment found localized fecal patches and separate refuse, with no established requirement for a dedicated dry pantry in an incipient colony. The nest construction studies describe craters and mounds at entrances. Grain mass, rounded chamber dimensions, wick volume, rates and care decision rules here are engineering assumptions. [Forager intake](https://pubmed.ncbi.nlm.nih.gov/19393982/) · [Worker trophallaxis](https://doi.org/10.1038/s41598-019-52019-6) · [Nest hygiene](https://doi.org/10.1371/journal.pone.0118376) · [Excavation](https://doi.org/10.1098/rspb.2010.0176)

Kramer et al. report 250 ± 79 workers (range 122–392) at approximately 20 months in source colonies that experienced two winters and received food after first emergence. That observation motivates checking sustained growth alongside the day-49 count. Neither the age nor the seasonal and feeding conditions match a two-year constant-temperature simulation. [Methods, source colonies](https://doi.org/10.1016/j.exger.2016.09.008)

## What improved, and where growth still fails

In the original default's first brood, four of twelve eggs reached adulthood. None of those four lived to adult age seven days. Four other first-brood individuals received no positive feed. In Physics 48 with the 30 mm feeder and the same seed, all five first-brood eggs reached adulthood and their workers survived at least seven days; one survived to age 30 days. The day-73 census held the queen, one worker, two larvae and one egg. Paid deliveries provided 11.562 mg of carbohydrate over the run. The queen took 11.027 mg from the depot and oxidized 10.981 mg. The last carbohydrate delivery occurred on day 65.12. The queen subsequently exhausted energy on day 110.93, with zero depot carbohydrate and 159.367 mg outside. Eleven larvae died of energy depletion during this run. By day 150 there were no survivors.

The five paired seeds give a less favorable picture than the seed-3 comparison alone. All 40 first-brood individuals in Physics 48 received a positive feed, but only 24 eclosed. The earlier Physics 47 protected comparison had 45 eclosions from 64 first-brood eggs. At day 49, the Physics 48 colonies had zero to five living workers each. Median day-49 workers declined from four in Physics 47 to two in Physics 48. Positive care coverage and the quantity of food released outside both overstate what the colony can sustain.

| Seed | First brood eclosed / laid, P48 | Live workers on day 49 | Live workers on day 73 | Queen death day | Carbohydrate delivered, mg | Carbohydrate in queen's depot meals, mg |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 3 / 6 | 0 | 0 | 73.52 | 0 | 0 |
| 2 | 3 / 6 | 3 | 2 | 124.85 | 17.275 | 15.523 |
| 3 | 5 / 5 | 5 | 1 | 110.93 | 11.562 | 11.027 |
| 17 | 5 / 9 | 1 | 2 | 71.34 | 13.031 | 0 |
| 29 | 8 / 14 | 2 | 2 | 68.17 | 10.122 | 0 |

Delivery totals include the period after queen death. All five queens died with zero carbohydrate in the depot. In four worlds workers deposited soil at the surface; seed 1 recorded no deposit. Only seed 2 recorded a worker's positive transfer to a larva (361 µg carbohydrate, 215 µg protein and 400 µg water across transfers). Four of the five worlds show why adding two workers need not immediately relieve maternal care in this implementation.

The nearby feeder uses the same budget and replenishment as the 30 mm feeder. At seed 3 it enabled 185.798 mg of delivered carbohydrate, 15 eggs laid and 13 worker eclosions after day 365. The founder died on day 656.41 with 808.216 mg of carbohydrate outside, and one orphan worker survived to day 730. Across the whole run 25 workers eclosed, 18 died of dehydration and six died of energy depletion. Only two worker wick-drinking transactions occurred. Seed 1 still made no deliveries; in seed 2 the nearer feeder shortened queen survival. Founder death in the 5 mm condition occurred at days 73.52, 122.14, 656.41, 71.34 and 68.17 in seed order. Repeated delivery and worker hydration both remain material failures even in supplied environments. For new protected play the viewer now selects the nearby feeder, at the original seed 3. This is a setup choice made after the paired experiment. The 30 mm control and depleted environments remain selectable. The 5 mm default has zero surviving founders at day 730 in this panel.

Physics 49 produced no carbohydrate deliveries in any of the five supplied worlds. The workers deposited 0, 18, 2, 10 and 17 parcels underground respectively. Retaining the original work time for each smaller bite, repeated trips, and the chooser's eligibility requirements are separate possible costs. This trial cannot assign the shortfall to any one of them. Keep Physics 49 experimental. The absent-exterior controls made no deliveries; one granular world nevertheless deposited soil at the surface. Excavation or a visible mound alone does not demonstrate successful provisioning.

**Sustained growth remains failed.** First-brood survival, worker drinking and worker-to-larva provisioning require separate checks. The model does not support a projection to hundreds or thousands of workers. The historical B06 result is `INSUFFICIENT`, the historical application performance gate is `FAIL`, and all nine independent biological gates remain `BIOLOGICAL_BLOCKED`.

## Engineering checks

Windows Release passed 292/292 native tests. The Windows live Python suite ran 58 tests with one skipped and no failures; the additional granular-roof continuation check and the final nearby-default archive and snapshot continuation check each passed separately. Chrome exercised the protected startup, finite stock symbols, resource controls and the death card. The seed-3 protected 30 mm witness reproduced all 120,267 facts by count, the day-150 frame SHA-256, each first-brood feed and stage transition, and the exact founder death balance across the original and rebuilt executables. This check does not assert a byte comparison of the full event stream. The independent receipt checker runs in Core CI and checks the compact individual histories and terminal census. No complete two-year SQLite history was written by the lifecycle assay.

## Reproduce

Run the receipt verifier to print every paired seed and check the terminal counts against committed births, transitions and deaths. The [compact receipts](PROTECTED_HABITAT_RECEIPTS.jsonl) include development trials, no-exterior controls, source and terminal frame identities, and individual first-brood records.

Use the [comparison protocol](PROTECTED_HABITAT_PROTOCOL.md). The runner streams committed facts from the native executable, stores only short output receipts, and independently advances to the queen's death to recover balances at the event time. The first brood is the set of eggs laid during the first 24 hours from the first egg, with identity preserved through development. Software seeds are paired computational trials.

~~~powershell
py -3 -B -m tools.build_m0_live --jobs 4
py -3 -B -m tools.measure_single_nest_lifecycle --treatment anatomical --supply finite --seed 3 --days 73
py -3 -B -m tools.measure_single_nest_lifecycle --treatment protected --supply extended --wick wet-wick --seed 1 --seed 2 --seed 3 --seed 17 --seed 29 --days 730
py -3 -B -m tools.measure_single_nest_lifecycle --treatment local-dig --supply extended --wick wet-wick --seed 1 --seed 2 --seed 3 --seed 17 --seed 29 --days 730
py -3 -B -m tools.measure_single_nest_lifecycle --treatment protected --supply nearby --wick wet-wick --seed 1 --seed 2 --seed 3 --seed 17 --seed 29 --days 730
py -3 -B -m tools.measure_single_nest_lifecycle --treatment protected --supply absent --wick wet-wick --seed 2 --days 730
py -3 -B -m tools.measure_single_nest_lifecycle --treatment local-dig --supply absent --wick wet-wick --seed 2 --days 730
py -3 -B -m tools.measure_single_nest_lifecycle --treatment anatomical --supply finite --seed 3 --days 73 --individuals
py -3 -B -m tools.measure_single_nest_lifecycle --treatment protected --supply extended --wick wet-wick --seed 3 --days 150 --individuals
py -3 -B -m tools.verify_protected_habitat
~~~
