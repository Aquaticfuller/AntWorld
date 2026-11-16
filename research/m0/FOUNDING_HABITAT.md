# Single-queen habitat and entrance work

This is the opt-in `ENGINEERING_ONLY` live MicroWorld habitat. A single queen starts in a small brood pocket linked to an entrance-side handoff alcove. Brood, nest stock, the founding wick, the exterior mixed feeder and the independent water source have their own Core positions. Workers enter the world only by eclosing. The mixed feeder and water outlet have finite initial and scheduled supplies. Relative humidity changes modeled water loss. Body water increases only after a paid draw, ingestion or transfer and subsequent uptake.

The handoff is the `Colony::nest_food` material pool at `nest_position`. An adult can carry resources, retain them in its crop or deliver them into that pool. Separate stands within contact range let workers exchange material and start a real connector journey without occupying the exact same position. The brood room and handoff are initial experimental geometry. Enlargement uses the existing excavation, load, transport and soil deposit actions. The room labels identify how the habitat was initialized and used.

## Evidence and model boundaries

| Mechanism | Evidence and decision |
| --- | --- |
| Brood organization and storage | Lenoir and Ataya observed *Lasius niger* brood work in an artificial humid chamber. Planckaert et al. measured crop-mediated trophallaxis across five queenless groups with a sucrose feeder. The fixed handoff pool and distinct chamber locations are useful physical fixtures. The sources support brood tending and liquid exchange. A dedicated pantry in natural young nests and the size of a stockpile remain uncertain. [Lenoir and Ataya 1983](https://doi.org/10.1111/j.1439-0310.1983.tb00088.x), [Planckaert et al. 2019](https://pmc.ncbi.nlm.nih.gov/articles/PMC6821819/) |
| Cleanup and excavation | Laboratory *L. niger* put corpses and food remnants at exterior refuse piles and formed fecal patches inside. This habitat retains actual brood cleaning and soil removal. It has no corpse or leftover disposal rule. Toffin et al. measured branching and changes in excavated shape under different substrates and worker numbers. Those results constrain local building mechanisms but give no quota for rooms of any single function. [Czaczkes et al. 2015](https://doi.org/10.1371/journal.pone.0118376), [Toffin et al. 2009](https://doi.org/10.1073/pnas.0902685106), [Toffin et al. 2010](https://doi.org/10.1098/rspb.2010.0176) |
| Patrol and recognition | Cuticular hydrocarbon profiles vary across workers, the entrance and the inner nest. Wild-derived experimental groups reacted locally to an alien worker on their foraging platform. The sources do not measure the share of all entrants inspected or fixed guard ages in founding colonies. The preview records paid patrol moves and a proximity-and-clearance antennation proxy when a returning nestmate actually reaches the entrance-side landing. Recognition errors, chemical exchange, foreign workers, other animals and interception are open. Arrival is never made contingent on a simulated guard. [Lenoir et al. 2009](https://doi.org/10.1007/s10886-009-9669-6), [Fourcassié et al. 2012](https://doi.org/10.1155/2012/383757) |
| Age and demand | Task activity is unevenly distributed among *L. niger* workers. Experienced workers can have a greater probability of patrol in this fixture. Each ordinary review can choose another eligible task. The patrol draw has weight `(8 + min(3, adult_days / 2)) / 32` when a resting worker is near the opening, another local worker is present and local patrol coverage is absent. Adult age starts at eclosion in this habitat. The worker moves, pays movement cost, then remains available for a short local watch at that site until the minimum program interval expires or another task takes over. No permanent guard caste is created. Solo, resource-poor, and inaccessible nests can have uncovered periods. [Lenoir and Ataya 1983](https://doi.org/10.1111/j.1439-0310.1983.tb00088.x) |
| Soil-sealed entrance | The optional setup has a 0.5 mm cap above a pre-existing shallow climbable shaft. A worker at the handoff may choose a reachable cap while reserves need replenishing and a loaded-clearance exit is unavailable. It walks to a supported work site, pays the existing excavation and load costs, carries out the removed parcel and is then able to cross the modified geometry. Deeper or irregular soil, rock and genuinely unreachable sites can leave the colony closed. Thin-cap recognition and priorities are engineering approximations. |
| Proactive food replenishment | A worker within physical depot contact evaluates the working buffer of 2,000 µg each for carbohydrate and water. This is a refill threshold, not total storage capacity. A local return cue can still prompt an eligible worker for roughly one additional load above the threshold. A worker uses reserves, local need, clearance and its own current task. A cue is emitted after a successful food delivery and remains locally available for up to six simulated hours in this fixture. It carries no food coordinates. Experiments found recruiter and responder behavior varied with food and colony nutritional conditions. [Mailleux et al. 2006](https://pubmed.ncbi.nlm.nih.gov/17050837/), [Mailleux et al. 2011](https://doi.org/10.1007/s00040-011-0177-7) |
| Surface trail | The old 60-second half-life remains available for comparison. The new 1,955-second half-life uses the approximate half-time implied by the exponential behavioral proxy fit on aged paper in Beckers et al. The study's mean exponential lifetime of 47 minutes corresponds to `47 × ln(2) ≈ 32.6 min`. The study did not measure chemical concentration. The two configured values are sensitivity settings for the model, with the longer setting selected in this experimental viewer. Track trail deposits, response to a local return cue and the responder's actual return carrying food as separate endpoints. [Beckers et al. 1993, p. 756, Eqs. 3–5](https://doi.org/10.1007/BF01201674), [audited source receipt](../s6_4_preflight/BATCH2_SOURCE_VERIFICATION_RECEIPT.md) |
| Temperature and humidity | The three nominal warm regimes use the Borisovka 1994 mean development targets from B06 Table 2. Egg, larva, and prepupa plus pupa targets in days are `20.7 / 13.5 / 20.4` at 22.5 °C, `16.7 / 10.2 / 14.5` at 25 °C, and `14.7 / 8.7 / 12.5` at 27 °C. Effective stage temperatures varied in B06. Larvae still have to satisfy nutrition and hydration gates. The worker review and hold intervals use an engineering Q10 of 2 with 15 min and 1 h at 25 °C. Relative humidity scales water loss using vapor pressure deficit relative to 25 °C and 80% RH. Neither numerical rate rule is fitted to *L. niger*. The humidity effect on development is through the hydration budget. [Kipyatkov et al. 2004, Table 2](https://doi.org/10.1023/B:JOEY.0000033808.45455.75), [Trigos-Peral et al. 2024](https://pubmed.ncbi.nlm.nih.gov/38242447/) |

## Matched 90-day runs

The two trail settings were run at the same 25 °C, 80% RH, open geometry, initial resources and seeds. Results are software outcomes over six paired worlds. Entries count committed events unless identified as workers. The masthead counts the current live workers separately from all cumulative eclosions.

| Seed | Trail half-life (s) | Eclosed | Food deliveries | Independent water deliveries | Cue observations / activations | Recruited workers later delivering food | Patrols / entrance contacts | Live workers at day 90 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 60 | 5 | 2 | 4 | 0 / 0 | 0 | 0 / 0 | 0 |
| 1 | 1955 | 5 | 2 | 8 | 0 / 0 | 0 | 0 / 0 | 0 |
| 2 | 60 | 6 | 3 | 1 | 0 / 0 | 0 | 10 / 0 | 3 |
| 2 | 1955 | 6 | 3 | 1 | 0 / 0 | 0 | 10 / 0 | 3 |
| 3 | 60 | 5 | 3 | 0 | 1 / 1 | 1 | 2 / 1 | 1 |
| 3 | 1955 | 4 | 2 | 2 | 1 / 0 | 0 | 0 / 0 | 0 |
| 4 | 60 | 4 | 2 | 1 | 0 / 0 | 0 | 0 / 0 | 1 |
| 4 | 1955 | 4 | 2 | 1 | 0 / 0 | 0 | 0 / 0 | 1 |
| 5 | 60 | 2 | 2 | 0 | 0 / 0 | 0 | 0 / 0 | 0 |
| 5 | 1955 | 2 | 2 | 1 | 0 / 0 | 0 | 0 / 0 | 0 |
| 6 | 60 | 5 | 6 | 2 | 1 / 0 | 0 | 39 / 1 | 2 |
| 6 | 1955 | 7 | 5 | 8 | 4 / 1 | 1 | 30 / 0 | 4 |

The longer surface trail changed the journeys and which colony had a successful responder. One world in each group completed the cue, activation and food delivery chain. Food deliveries totaled 18 and 16 at 60 and 1,955 seconds respectively. The same groups had 8 and 21 deliveries from the independent water source. These paired examples do not establish a reliable boost in recruitment or continuous entrance coverage. Two entrance contacts occurred in the short-trail runs.

| Seed 2 control at 1,955 s | Eclosed | Food deliveries | Independent water deliveries | Live workers at day 90 |
| --- | ---: | ---: | ---: | ---: |
| Shallow soil cap, 25 °C, 80% RH | 9 | 6 | 5 | 7 |
| Thick closed roof, 25 °C, 80% RH | 6 | 0 | 0 | 0 |
| Open, 22.5 °C, 80% RH | 2 | 1 | 3 | 0 |
| Open, 27 °C, 60% RH | 0 | 0 | 0 | 0 |

In the thin-cap case, worker 16 eclosed before opening the surface at 3,996,721,011 ms (soil event `8382`). It deposited the soil at 3,997,087,171 ms (event `8424`) and first reached the surface at 3,998,888,523 ms (event `8531`). Water delivery `8776` and food delivery `17530` followed. The closed-roof case had worker births and underground excavation with zero surface moves or deliveries. Every one of the sixteen runs passed the Core material, water, energy and soil balance check.

## Reproduction and disk use

The following command runs two trail settings for seeds 1–6, with additional sealed, temperature and dry cases. It reads the committed events in bounded pages and writes summaries to standard output. No experiment archive is generated.

```powershell
python -B -m tools.diagnose_m0_founding_habitat
```

The preview uses checkpoint schema 29 and physics 36. Earlier scene builders and archive formats retain their original version checks. The climate and trail settings live in the Core checkpoint. The habitat uses the existing bounded compressed live history and manual save flow. No new permanent event series is recorded for individual patrol stances between actions.

## Local verification

On Windows Release, the ten `M0_BROOD_SPACE`, `R0_R1_NEST_DYNAMICS` and `ECO_CLOSURE_*` CTests passed. The fifteen Python live tests checked real collection, recruitment, paired soil controls, climate exposure, SQLite restore, split-step continuation and byte equality with the published older day-90 checkpoint. The browser test used Chrome 157 to start a single queen, locate the entrance and depot, switch to Chinese and fast-forward to food delivery `8484`. At that commit worker 16 delivered 1,333 µg of carbohydrate, 667 µg of protein and 2,000 µg of water into the underground pool. That operation paused the real Core and selected the carrier at `1×`. The live motion projection tests also passed.

The installed Windows executable `antworld_m0_live_v10.exe` has SHA-256 `d1469877c875bd4925efda09836f3f9be21c137df84e014fb330c935b9058cda`. The ten selected CTests and five habitat and legacy witness tests were rerun against the final build.

The 16 in-memory assay runs stored at most 7,207,888 bytes of compressed history in the live process. The verification used one disposable Windows build directory. The existing archive and save files are the sources of record for previous experiments.

B06 remains `INSUFFICIENT`, the previously frozen application performance qualification remains `FAIL`, and the original biological blockers remain open. This protected setup has an explicit finite wick, preformed geometry, a warm constant climate and post-emergence supplies. It supports engineering comparisons within that setup.
