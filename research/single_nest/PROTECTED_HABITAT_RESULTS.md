# What happened to the day-73 colony?

The old web default selected the anatomical nest (Physics 39), seed 3, a plugged entrance, a 1.2 µL finite wick, and 120 days of exterior supply. No saved player checkpoint was available. A fresh run with those inputs reproduced extinction before day 73.

## The original default

All 27 paid eggs hatched. Nineteen individuals died as larvae (ten of energy depletion and nine of dehydration). Eight became workers at different times; at most two workers were alive together. Seven of these workers died of dehydration and one of energy depletion. The queen died of energy depletion on day 69.1, with 2,655 µg of carbohydrate in the nest and 106,834 µg still outside. Her crop was empty. Workers had returned 2,666 µg of carbohydrate, but the record contains zero crop intake by the queen from that stock and zero worker-to-larva transfers. The last worker died on day 71.4.

Seven eggs were laid after the first juvenile death. This is a specific problem with how local care, resource access and reproductive decisions interact. A queen can afford an egg while another individual is already low on water, lacks food at its mouth, or has insufficient energy to survive until absorption. Only the identity and resource ledgers can distinguish those cases.

Egg counts in a real nest can also include trophic eggs. In a choice experiment with abundant food, final-instar black garden ant larvae ate conspecific eggs and preferentially selected trophic eggs. This experiment cannot give the egg-to-worker survival rate of a single founding queen. The 27 simulated eggs were all tracked as developmental eggs and hatched. No simulated death in this cohort represents a trophic egg. [Baroni Urbani, 1991](https://doi.org/10.1007/BF01314909)

## How the live world changed

| Mechanism | Implementation and limits |
| --- | --- |
| First brood | The queen considers the energy and water of nearby, visible larvae against maintenance through the next uptake opportunity. A locally payable urgent ration takes priority in care selection. A new egg can be deferred. A different larva across a wall cannot suppress laying. Death and failed contact remain possible. Decisions, reproduction replay and resource deductions run in the Core. |
| Handoff | A loaded worker can unload from a valid handoff berth; paths around occupied adult bodies use the actual anatomical sweep. Read the queen's intake, oxidation and actual larval uptake separately from the amount unloaded. |
| Space | A single sealed chamber has rounded horizontal ends. Contact and path tests use the same 24 adjoining terrain bands as the viewer. The vertical cross section remains stepped. A derived search index accelerates disjoint bands without changing the stored geometry. |
| Food and water | Both outdoor food sources share the original total provision budget. The dry source dispenses up to 25 µg per successful collection, including a final partial portion. The other supplies mixed moist food. The protected nest starts with a finite 1.5 mL wick. Real drinking debits it into an individual's crop. The resource panel separates crops, mixed depot inventory, the wick, exterior stocks and unreleased food. |
| What a food glyph means | The dry-food counts and masses come from the Core. Up to 100 glyphs per component show the quantity. Larger stocks use grouped glyphs. Their arrangement is illustrative. Solid stock still uses a depot account; individual grain positions, food-food collision and a separate granary are not modeled. Free water in a chamber and water contained in mixed food have different representations. |
| Soil | A worker with a parcel can follow an open shallow shaft to a supported rim and drop it. Before breakthrough, a deposit may be underground. The resource panel groups actual deposited volumes by position and can locate the largest pile on each side of the surface. A circular mound is not guaranteed. Physics 49 independently tests local work-site selection and smaller roof cuts, at most 0.125 mm³ at this terrain resolution. Other excavation parcels may be larger. |

## What the default feeder can support

The nearby feeder starts with 6 mg of carbohydrate. It releases 1.5 mg of carbohydrate each day from a finite reserve for 730 days. A native day-0/day-1 comparison measured 6,000 and 7,500 µg at the sources and exactly 1,500 µg in the committed release. The daily food also contains 750 µg of protein. Workers must physically collect and transport it. Previously released stock can remain available after day 730.

At the configured basal rate of 1 nJ/ms and yield of 8,000,000 nJ/µg, one resting worker spends the equivalent of 10.8 µg of carbohydrate per day. A thousand resting workers would require at least 10.8 mg per day from carbohydrate once initial reserves run out, before allowing for the queen, brood or physical work. This budget explains why this feeder cannot sustain a thousand adults indefinitely. It does not explain a worker dying while the nest holds unused carbohydrate. In the two-year Physics 50 seed-3 world, deliveries to the depot averaged only 0.280 mg of carbohydrate per day. This average excludes food eaten from a forager's load and hides the intervals between deliveries. The input rate, collected load, shared stock and an individual's absorbed ration are four different quantities.

## Biological comparison

In the Szabó et al. wet-cotton assay, 30 undisturbed, unfed foundresses at 24.5 ± 0.5 °C had a mean of 15.27 living workers (sample SD 4.73) and 18.73 pupae plus workers (SD 4.74) on day 49. Their day-49 counts cannot identify the survival fraction of each queen's first eggs. They do establish a meaningful comparison at a named age. The model has a finite wick and can receive exterior food after the workers open the roof. [Original experiment and appendices](https://doi.org/10.1093/biolinnean/blad149)

Black garden ant workers collect liquid in their crops and exchange it orally. The spatial transfer experiment used queenless, broodless worker groups and sucrose solution; it cannot give a foundress-to-larva water transfer rate. The black garden ant nest hygiene experiment found localized fecal patches and separate refuse, with no established requirement for a dedicated dry pantry in an incipient colony. The nest construction studies describe craters and mounds at entrances. Grain mass, rounded chamber dimensions, wick volume, rates and care decision rules here are engineering assumptions. [Forager intake](https://pubmed.ncbi.nlm.nih.gov/19393982/) · [Worker trophallaxis](https://doi.org/10.1038/s41598-019-52019-6) · [Nest hygiene](https://doi.org/10.1371/journal.pone.0118376) · [Excavation](https://doi.org/10.1098/rspb.2010.0176)

Kramer et al. report 250 ± 79 workers (range 122–392) at approximately 20 months in source colonies that experienced two winters and received food after first emergence. That observation motivates checking sustained growth alongside the day-49 count. Neither the age nor the seasonal and feeding conditions match a two-year constant-temperature simulation. [Methods, source colonies](https://doi.org/10.1016/j.exger.2016.09.008)

Majidifar et al. followed 24 newly mated queens for 93 days. Twenty-two survived and 17 of the 22 produced workers. In their direct behavioral assay queens sharply reduced their own care after workers emerged. A worker-addition experiment also reduced maternal care within 20 hours. The measured behavior was active manipulation of brood; the paper gives no conversion factor from those observations to delivered micrograms or individual egg survival. In the nearby-feeder simulation only two of five queens survived to day 93. Separately, Tragust et al. observed that some surviving queens produced replacement brood following experimental loss. A rule that forbids any further laying after a juvenile death would contradict that observation. [Majidifar et al., section 3 and Fig. 1](https://doi.org/10.1111/1365-2435.14536) · [Tragust et al., brood loss after founding](https://doi.org/10.3389/fevo.2020.00076)

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

Toffin et al. also estimated pellet volume from outward loaded-worker counts, total excavated dry mass and substrate bulk density. Their Table S1 gives mean volumes of 0.138 mm³ in granular soil and 0.173 mm³ in cohesive soil. The reported masses and trip counts imply mean dry loads of about 208 µg (0.1932 g / 931) and 262 µg (0.0577 g / 220). The Physics 49 roof bite has a maximum volume of 0.125 mm³ and dry mass of 96 µg. Even at this visually plausible scale its density and full work time remain engineering assumptions. Egg volume, dry-food mass, and liquid crop loads require their own evidence. [Author's supplementary material, Table S1](https://www.researchgate.net/publication/305659378_Excavated_substrate_modulates_growth_instability_during_nest_building_in_ants_-_Supplementary_Information)

## Why new workers died despite remaining water

The [individual adult balances](PROTECTED_ADULT_BUDGETS.jsonl) join each worker's actual emergence and death event to the exact native frame at that timestamp, including crop, body, colony stock and finite wick. The two-year end frame must equal the original assay hash. Stock measured at a death cut is shared colony stock, not a meal for the dying worker.

In nearby seed 3, all 18 dehydration deaths were workers that eclosed with 7–8 µg of body water and zero crop water. All died 6.1–7.9 hours after emergence. At their deaths the wick still held at least 1,499,525 µg of water; the mixed nest inventory contained 21,671–219,561 µg of water. Their centre-to-wick distances at death were 6.54–8.40 mm; a straight-line distance does not establish a traversable mouth approach. The five first-brood workers began adult life with 327–507 µg of body water. The seed-1 far control produced three adults with 172–419 µg at emergence; all three exhausted energy, with an empty depot and zero exterior deliveries.

Low starting water alone did not determine every fate. Two further workers also started with 8 µg; one lived 72 days and another remained alive at the end of follow-up. The implementation budgets larval support through just the first adult absorption period. A feeding decision can therefore count a larva as funded even though it will start adult life with only hours of water. A stationary worker with a local wick cue can approach and drink, but an ongoing foraging or excavation action has different ownership and a worker may fail to reach the contact point. Even a reachable reserve requires a completed sip and uptake. The data do not measure natural callow water content or show that every death could be prevented by changing the location of the wick.

## Can a newly emerged worker use food that has already been delivered?

Fjerdingstad et al. followed 660 singly housed, newly mated black garden ant queens in darkness at room temperature. They supplied water during founding, then honey water, water and protein after the first workers emerged. At three months the Uppsala colonies averaged 16 ± 6 workers. At four months the two Lausanne cohorts averaged 22 ± 5 and 24 ± 11 (mean ± SD). Ten of the 660 queens failed to produce workers. Separately, mark–recapture estimates for 17 mature field colonies ranged from 3,908 to 55,266 workers. The early counts are standing populations. They do not report egg-by-egg viability or a requirement that a two-year colony reach the mature field range. [Methods, colony size and productivity, and Table 4](https://doi.org/10.1046/j.1420-9101.2003.00589.x)

Physics 50 changes a larva's local water request to cover the existing adult drinking threshold. A feeding adult must pay that water before metamorphosis. Adult losses, energy expenditure and the rules for pickup, drinking and absorption are unchanged. Compare this opt-in experiment to Physics 48 with the same near feeder, wick, temperature, seed and resource budget.

At seed 3 the founder survived to day 730. The colony laid 17 eggs and eight workers eclosed in the second year. One worker remained on day 730, having emerged on day 45.6. All five first-brood eggs eclosed and lived seven adult days, but only one of those workers survived to adult age 30. Nineteen workers eclosed over two years and the population never exceeded five living workers. There were zero adult dehydration deaths and 18 adult deaths from energy depletion. Twelve larvae and eleven pupae also exhausted energy. One larva dehydrated.

Every one of the 18 workers that exhausted energy had an empty crop and at least 1,669 µg of carbohydrate in the colony depot at its death. Fourteen were later offspring. They emerged with 25–26 µg of water and died 11.9–12.8 hours later. The other four were first-brood workers and survived 10.8–18.5 days. Over the run, 204.370 mg of carbohydrate was delivered. The queen took 195.997 mg of carbohydrate in depot meals. Actual worker-to-larva transfers totaled 75 µg of water and zero carbohydrate or protein. A delivery, a depot meal, a gift, and subsequent absorption are distinct events. The receipts establish a failure of access or distribution in a supplied colony. Stock at death alone cannot identify an individual's earlier perception or a collision-free route.

Four of the five Physics 50 founders died. Their death days were 73.52 (seed 1), 137.5 (seed 2), 71.34 (seed 17) and 68.17 (seed 29). The seed 3 founder was alive with one worker at the end of the 730-day observation. The no-exterior control lost its founder and all workers. Water provisioning addresses a measured cause of early loss. Repeatable colony growth remains an open requirement. Physics 50 remains an explicit experimental choice.

Moving only the wet-cotton point to the brood site produced a different result. In seed 2 the queen survived 416.8 days, versus 122.1 days with the laying-site wick. In seed 3 her survival fell from 656.4 to 154.1 days. In that seed three of eight eclosed workers died of dehydration and zero worker drinks were recorded, compared with 18 dehydration deaths among 25 eclosed workers and two drinks at the original location. The reduced death fraction did not meet the protocol's requirement for actual drinking. None of the five nursery-wick founders survived two years. The same amount of water at a different coordinate cannot substitute for successful ingestion. [Eleven water-treatment and control receipts](PROTECTED_WATER_TRIALS.jsonl)

| Seed | P48 original wick: queen death day / workers on day 730 | P48 nursery wick | P50 paid juvenile water |
| ---: | ---: | ---: | ---: |
| 1 | 73.5 / 0 | 73.5 / 1 | 73.5 / 0 |
| 2 | 122.1 / 0 | 416.8 / 1 | 137.5 / 0 |
| 3 | 656.4 / 1 | 154.1 / 2 | alive / 1 |
| 17 | 71.3 / 1 | 71.3 / 2 | 71.3 / 1 |
| 29 | 68.2 / 1 | 68.2 / 2 | 68.2 / 1 |

The first later-born worker in the seed-3 group of 14 was individual 23. It eclosed about 10 mm from the depot with 46,000,000 nJ, 26 µg body water and an empty crop. In 12.77 hours it moved 85 times, had 53 autonomy reviews and 29 nutrition decisions. The recorded action observations included approach to brood, inspection, cleaning and approach to a nestmate. There was no positive intake from food or from a nestmate. At death the worker still had 14 µg body water and the depot still contained 2,005 µg of carbohydrate. Observation counts include multiple phases of an action; they cannot be interpreted as completed feeding bouts. This individual motivates a test of whether optional brood work displaces a hungry worker's search.

Black garden ant foragers can carry liquid food internally in the crop and take up additional droplets on a return trip. This supports representing liquid-food intake as a transfer of mass into a crop. The feeding experiment measured sugar solution and does not establish a buried reservoir of free water or a mandatory separate granary. Locations of deposited solids and actual exchanges require separate observations. [Mailleux et al., food transport experiment](https://doi.org/10.1016/j.crvi.2008.10.005)

## Local meal search failed its selection test

Physics 51 gives a free worker with a near-term carbohydrate shortfall a local, body-length food search on alternate decisions. It keeps the original sensory range, actual locomotion and nutrient accounting. The comparison and futility criterion were committed in `6ce3f321` before the run. In both worlds all five first-brood eggs became workers. At day 150, Physics 50 retained the queen, one worker, one egg and one pupa. Physics 51 retained two orphan workers, with no immature brood. Its queen dehydrated on day 80.25 with 926 µg of lipid and 6,193 µg depot carbohydrate. Actual worker moves rose from 1,211 to 2,503, while delivered carbohydrate fell from 31.636 to 12.937 mg. Neither world recorded a later-born worker's first positive depot carbohydrate intake by day 150. The extra motions failed the feeding and founder endpoints. Retain this arm for headless reproduction only. The preregistered stop ruled out expansion to the two-year panel for this arm. [Paired raw receipts](PROTECTED_MEAL_SEARCH_SCREEN.jsonl) and [individual 23](PROTECTED_WORKER_23.json)

The outstanding distribution test is a returner's liquid load. The current model can deposit a moist carbohydrate load into one shared stock and immediately allocate another foraging trip. A candidate with biological support is to keep a measured share in the actual forager's crop and unload it to hungry nestmates through completed encounters. Before selecting a share, distinguish soluble carbohydrates from solid food at collection and preserve the forager's own consumption. Compare equal collected masses, positive returning-worker-to-nestmate transfers, actual absorption by newly emerged workers, surviving founders and later brood. The observed failure of local search gives no empirical transfer fraction.

## Engineering checks

The hydration follow-up passed all 40 Windows live-session tests against the archive-compatible native executable. An independent run reproduced the emergence and death balances of every worker in both seed-3 water treatments and the exact day-730 frame hashes. Worker 23's full action counts and intake outcomes also reproduced after segmented advancement. The meal-search executable passed compact restore with identical subsequent native frames and facts. The Windows and Linux browser jobs exercised the depot and death views. The five protected evidence files total 235,393 bytes. The 35 lifecycle and screen receipts cover 16,549,750 committed facts streamed through the analysis process; the published receipts do not retain a second copy of the full histories. [Cross-platform observatory tests](https://github.com/Aquaticfuller/AntWorld/actions/runs/45087651798)

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
py -3 -B -m tools.trace_worker_hydration --run nearby --seed 3
py -3 -B -m tools.trace_worker_hydration --run protected --seed 1
py -3 -B -m tools.measure_single_nest_lifecycle --treatment protected --supply nearby --wick nursery-wick --seed 1 --seed 2 --seed 3 --seed 17 --seed 29 --days 730 --individuals
py -3 -B -m tools.measure_single_nest_lifecycle --treatment callow --supply nearby --wick wet-wick --seed 1 --seed 2 --seed 3 --seed 17 --seed 29 --days 730 --individuals
py -3 -B -m tools.measure_single_nest_lifecycle --treatment callow --supply absent --wick wet-wick --seed 2 --days 730 --individuals
py -3 -B -m tools.trace_worker_hydration --run nursery_wick --seed 3
py -3 -B -m tools.trace_worker_hydration --run callow --seed 3
py -3 -B -m tools.trace_worker_meals --worker 23
py -3 -B -m tools.measure_single_nest_lifecycle --treatment callow --supply nearby --wick wet-wick --seed 3 --days 150 --individuals
py -3 -B -m tools.measure_single_nest_lifecycle --treatment meal-search --supply nearby --wick wet-wick --seed 3 --days 150 --individuals
~~~
