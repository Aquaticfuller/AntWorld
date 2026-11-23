# Returning liquid meals to the founding chamber

## Watch a transaction

On Windows run these commands from the repository root.

```powershell
py -3 -B -m tools.build_m0_live --jobs 4
.\tools\start_m0.cmd
```

Open colony setup and create a sealed nest. Select **Chamber food sharing · Physics 54**, nearby feeder, wet wick and seed 2. This world has paid transfers to the queen, larvae and a newly eclosed worker. Seek the next food exchange or worker-to-queen transfer. Open its receipt for the donor, receiver and ingredient masses. An intake event tagged with a source ID identifies the collected load. Later absorption belongs to a particular recipient. Mixing in a crop limits how precisely an absorbed molecule can be traced back to a feeder. **Liquid food sharing · Physics 52** and **Local crop exchange · Physics 53** expose the earlier experiments. Ordinary new nests retain their previous configuration.

## Versioned model changes

| Model | Change | Failure addressed |
| --- | --- | --- |
| 50 | Frozen worker hydration and feeding control | Returned sugar can enter the depot, yet a nearby individual may never obtain it. |
| 52 | A worker can ingest the liquid fraction of its own real collection and seek a local nestmate on return. A single action debits one inventory and credits the other. | Extra liquid previously traveled primarily as external cargo destined for stock. |
| 53 | Collection respects crop capacity. The solid part of a mixed meal stays in cargo. Adults retain maintenance reserves and exchange at most half the positive difference in each crop component. A donor can try a second reachable recipient or continue its approach. | Two workers in the first trial returned the same sugar to each other. Gross transferred mass overstated useful dissemination. |
| 54 | A liquid carrier can finish the return connector past an early wall handoff and revisit its own eclosion site. A worker seeking a local mouth can change support level, subject to body clearance, occupancy and paid movement. | Seed 2 had loaded workers on the ceiling and a hungry queen on the floor. |
| 55 | Use the actual mouth for sensory range after a padded lookup of adult body centers. Confirm visibility independently of physical feeding contact. | Twenty-six observed candidates with a possible next step disappeared because the queen's body center was outside sensory range. |
| 56 | Apply the larval feeding transaction's anatomical reach and payable demand when choosing a recipient. Recheck at execution. | A nearby nurse repeatedly selected larvae which were physically out of reach. |

Each new model is selected explicitly. Workers offer food to an actual local recipient. Transactions check stage, reach, ownership, demand and crop capacity at completion. An outside feeder or a funded drink at the wick does not credit an ant until it actually takes the material. The registered load, sharing and search policies are engineering hypotheses.

## Follow an individual mouth

Physics 52 seed 3 provides a compact, independently rerun witness through day 90. Worker 9 fed queen 2, larva 21 and recently eclosed worker 11. Worker 11 received 14 µg of carbohydrate in fact 13,978 and absorbed 14 µg in fact 13,987. Larva 21 received 76 µg of carbohydrate, 65 µg of protein and 99 µg of water in five transactions. Its first subsequent positive carbohydrate absorption was 50 µg. The queen received 83 µg of sugar by worker contact and also obtained sugar from stock through her own intake. Individual identity, dose, source collection and subsequent uptake have separate fields in the [day-90 witness](SOCIAL_CROP_MOUTH_WITNESS.json).

The transfers to worker 11 preceded worker 9's first recorded external collection in that world. Counting them as direct forager deliveries would incorrectly attribute redistributed food to a later trip. For the dose delivered to larva 21 the interval attributable specifically to worker 9's marked social loads is 0–76 µg, and for the queen it is 0–83 µg. The simulator records ingredient masses. It does not distinguish individual molecules of the same sugar after mixing.

## A paid liquid load reaching three kinds of recipient

In the Physics 54 seed-2 replay through day 90, workers 8 and 9 loaded sugar from feeder 4 into their crops (3,189 and 2,187 µg) along with 4,779 and 3,275 µg of water. The founder took zero sugar from the depot. She received 2,416 µg of carbohydrate and 2,230 µg of water in worker oral transfers. At least 1,983 µg of that carbohydrate can be attributed to a donor's own marked collection even under the least favorable mixing order. Workers shared 711 µg of sugar, 325 µg of protein and 564 µg of water with larvae. The soluble load contains no protein; protein receipts include the separate solid-food route. Callow 10 received 13 µg of carbohydrate from worker 8 in event 84,010 and subsequently absorbed 13 µg in event 171,990. Its direct-source interval is 0–13 µg. [Identified loads, mouths, doses and absorption pulses](SOCIAL_CROP_CHAMBER_WITNESS.json)

The queen's last receipt was on day 68.45. Event 413,333 recorded energy depletion on day 79.93, with zero body energy, zero remaining lipid, zero crop sugar, 680 µg body water and 530 µg mobile protein. Workers 8 and 9 then held 523 and 670 µg of crop carbohydrate. The depot contained zero sugar and the surface still held 119,314 µg. An earlier paid meal therefore coexists with a later failure of continued supply. The same seed under Physics 53 had no worker-to-queen sugar transfer and lost the queen on day 73.1. Under the older Physics 50 depot route she survived to day 137.5. These are paired model outcomes.

**A fully attributable callow meal.** In seed 3, worker 8 had zero cargo and an empty crop immediately before collection 12,062. Source 4 paid 400 µg of carbohydrate, 600 µg of water and 364 µg of protein. Ten intakes moved the liquid into the crop. The solid protein was delivered separately. The worker picked up and deposited a second, protein-only parcel. No other liquid entered its crop. At event 12,656 it gave worker 9 **40 µg of sugar and 60 µg of water**, 2 minutes 46 seconds after worker 9 emerged. The donor then held 360 and 540 µg respectively, the recipient 40 and 60 µg. The recipient later absorbed sugar, including additional intake by the time of the pulse. The fine-grained replay removes the source ambiguity for this specific transaction. [Native collection, entry, delivery, emergence and mouth receipt](SOCIAL_CROP_CALLOW_MEAL.json)

## Two-year outcomes

The following supplied pairs used single founding queens, identical feeder inputs and the same finite wick. The worker census lists days 73, 365 and 730. The later cohort includes all eggs outside the first 24-hour laying window. Its survival denominator is the number of workers that actually emerged from those eggs.

| Seed | Physics 50 living workers | Physics 54 living workers | Queen fate, day (50 → 54) | First brood emerged / eggs (both models) | Later workers emerged / alive at day 730 (50 → 54) |
| --- | --- | --- | --- | --- | --- |
| 1 | 0 / 0 / 0 | 0 / 0 / 0 | 73.5 → 73.5 | 3 / 6 | 0 / 0 → 0 / 0 |
| 2 | 1 / 0 / 0 | 2 / 1 / 1 | 137.5 → 79.9 | 3 / 6 | 6 / 0 → 3 / 0 |
| 3 | 1 / 1 / 1 | 3 / 1 / 1 | Alive at 730 → 80.0 | 5 / 5 | 14 / 0 → 7 / 0 |
| 17 | 2 / 1 / 1 | 2 / 1 / 1 | 71.3 → 71.3 | 5 / 9 | 0 / 0 → 0 / 0 |
| 29 | 2 / 1 / 1 | 3 / 1 / 1 | 68.2 → 68.2 | 8 / 14 | 0 / 0 → 0 / 0 |

Both models produced 24 first-brood workers from 40 first-brood eggs. Under Physics 50, four of these workers survived to age 90 days. Under Physics 54, six survived to that age. Three and four, respectively, still lived at the terminal census. All 20 later workers in Physics 50 and all ten later workers in Physics 54 died before day 730. Physics 50 seed 3 retained its queen and produced eight workers in year two. No Physics 54 world retained its queen or produced a worker in year two. Neither model passed the preregistered growth threshold. The worker results mix distinct mechanisms:

- In seed 1 three workers emerged but no one collected sugar. Only three adult worker moves were recorded in the entire Physics 54 run. In seeds 17 and 29 the first paid liquid collection occurred on days 71.45 and 68.42, respectively, after queen death in each world. A better indoor handoff alone cannot deliver a load that has not yet been collected.
- In seeds 2 and 3 the first liquid loads occurred by day 45.58. Worker oral transactions supplied 2,416 and 3,064 µg of carbohydrate to the two respective queens. At their deaths the other measured adult crops still held 1,193 and 881 µg. For these two cases every carrier included in the total was already alive at the preceding cut. The streaming estimate for other cuts tracks adults observed at the preceding cut and can omit a worker that emerged in the intervening interval.
- With external supply absent (seed 2), workers still emerged on the founding budget. Three first-brood workers died, no subsequent worker emerged and no external collection or social load occurred. The queen died on day 73.4.

These five paired software seeds characterize this sealed chamber and feeder configuration. They provide neither biological colony replicates nor an estimate of a wild founding success rate. The replacement is ineligible for promotion as a sustained-colony default.

The complete two-year ablation includes 24 worlds. The table sums five supplied worlds per version and excludes each version's separate no-exterior control. Values in the first three columns count each oral crossing. A worker receiving the same sugar back contributes to the gross flux a second time. The corresponding units are micrograms, not distinct sourced molecules.

| Physics | Sugar to queens (µg) | Sugar to larvae (µg) | Sugar to callows (µg) | Later workers emerged / living on day 730 | Worlds meeting growth criterion |
| --- | ---: | ---: | ---: | ---: | ---: |
| 50 | 0 | 386 | 258 | 20 / 0 | 0 / 5 |
| 52 | 173 | 1,358 | 42,475 | 25 / 2 | 0 / 5 |
| 53 | 0 | 0 | 76 | 0 / 0 | 0 / 5 |
| 54 | 5,480 | 865 | 357 | 10 / 0 | 0 / 5 |

Both surviving later workers in Physics 52 came from seed 2. Their queen died on day 211.30. The gross callow total in this model includes reciprocal handoffs. In seed 3 two workers passed 3,497 µg back in each direction from day 46 to day 49. Counting transfers without measuring net receipt, absorption and survival would favor this failed mechanism.

## What stopped the seed-2 meals

Replay from day 69 to the queen's actual death. Workers 8 and 9 completed 29 and 33 approach segments directed at her. Every segment ended with sugar in the donor's crop. None produced a transfer or a rejected nutrition transaction. In the same window the queen completed 454 brood-approach segments, 53 cleanings, five brood feedings and 67 depot-approach segments. A depot approach can target water. Neither a completed segment nor a nearby ant establishes mouth contact.

A second native replay stopped at the exact simulation time of each of the 62 completions and read both bodies. The median mouth separation was 3.906 mm. In 61 cuts it exceeded the 0.65 mm maximum. At event 283,393 the separation was 0.591 mm, but the target projected 0.165 mm behind the donor's mouth. The permitted rear excursion is 0.120 mm. No approach met both contact tests. No queen-center displacement was committed during any individual segment (98–260 ms); she did move between segments. The final approach occurred on day 73.46, more than six days before death. The snapshot cursor includes events committed at the same timestamp after the movement. [Every approach, its exact time and native mouth geometry](SOCIAL_CROP_CONTACT_CUTS.json)

The controller re-evaluates recipients after each arrival. A diagnostic build inspected the actual candidate filters at all 62 times. It reproduced the original day-69 state and the death cut (event 413,333; SHA-256 `7df7c3971b34ca4a487381e74e3c3304f8c4486fd7aea33551143cb41c247e3d`). The receiver was stationary during the checks and had free crop space and a positive payable dose each time. Ten steps had a continuing offer, 25 had no further legal segment in the bounded path search and 27 had a possible segment to the mouth but lost the candidate. In 26 of those 27 the center-distance filter excluded a queen whose mouth remained in sensory range. In the remaining case the mouths themselves were outside perception. This outcome motivated the [separately registered mouth-range screen](SOCIAL_CROP_MOUTH_RANGE_PROTOCOL.md). None of these filters can deliver food before a first collection.

The instrumented replay writes an auxiliary diagnostic stream. Its records are not canonical facts. To reproduce this optional check, apply [the diagnostic patch](SOCIAL_CROP_CONTACT_TRACE.patch) to native revision `171f13af`, build its live executable, then run `tools.inspect_social_crop_cut` from this branch with `--physics 54 --seed 2 --day 80 --core <diagnostic executable>`. Standard error contains the [62 filter evaluations](SOCIAL_CROP_CONTACT_TRACE.txt) in the listed column order. The normal build contains no probe.

## The mouth-range correction failed its survival screen

Physics 55 searches a slightly larger set of body centers, rejects mouths beyond the original sensory radius or behind soil, then enforces the same contact, capacity and payment rules. It uses a new save identity. **Oral perception trial · Physics 55** is available in the experimental model selector.

In the preregistered supplied seed-2 screen the queen received 3,204 µg of carbohydrate from workers, up from 2,416 in Physics 54. Workers fed larvae 1,150 µg of sugar, 715 µg of protein and 824 µg of water. Seven workers had emerged by day 90, six still alive, compared with three emerged and two alive in Physics 54. But the last worker gift to the queen was already on day 64.99. She died of energy depletion on day 82.11 with zero crop sugar, while the six living workers held a total of 1,727 µg. The coarser streamed cut counted 1,696 µg across the four workers it already tracked. An independent replay stopped exactly at death and counted the two additional workers' 28 and 3 µg. Neither prespecified success condition held. Under no external supply the queen died on day 73.36 and no worker remained alive at the two-year census. As registered, no further supplied two-year panel was undertaken for Physics 55. Extra short-term emergence and a repair to a real spatial filter are insufficient grounds to adopt it for ordinary colonies. [Screen and negative control](SOCIAL_CROP_MOUTH_RANGE_SCREEN.jsonl)

### Where meals went after the queen's final receipt

The exact Physics 55 window from day 65 until her death contains 80 oral transactions to nine other recipients, totaling 1,294 µg of sugar, 390 µg of protein and 1,920 µg of water. The queen received zero and no worker committed a queen-directed approach in that window. She remained active, completing 67 brood approach segments and a feeding. On each of the 17 daily cuts, worker 10's mouth was 2.715 mm from hers, well outside the 0.65 mm contact limit. Its crop sugar fell from 650 to 477 µg between days 66 and 82. Daily samples cannot exclude shorter encounters between cuts. The endpoint shows a failure to initiate and complete a founder meal while other mouths continued to receive food. It cannot establish which uncommitted choices worker 10 considered. [Exact death window, competing recipients and daily mouth distances](SOCIAL_CROP_MOUTH_RANGE_DEATH.json)

Worker 10 recorded 1,039 selected feeding actions, 1,039 interruptions and no movement in that interval. All 1,039 rejected transactions were out of reach (874 to individual 23 and 165 to individual 29). Its position revision held at 2852. It had an empty external cargo and carried no soil at any daily cut. The worker alternated tasks and used its own sugar while repeatedly trying to feed a larva it could not touch. Its food never reached the queen in this interval. This is a reproducible selection/transaction mismatch independent of the proposed bilateral rendezvous. [Prespecified larval eligibility test](SOCIAL_CROP_OFFER_SCREEN.md)

### Does filtering unreachable larval gifts keep the founder alive?

Physics 56 reused the transaction's anatomical contact test in the choice of a larval recipient. Both prespecified seed-2 worlds completed 90 days. In the supplied chamber the founder's last meal, total doses to all four recipient classes and exact energy-depletion time matched Physics 55. The queen died on day 82.11. Seven workers emerged and six were alive on day 90. Individual 16 received carbohydrate as a larva at event 13,519 and subsequently absorbed 46 µg at event 14,284. Without the exterior supply there were zero positive worker meals, three workers emerged, and no adults remained on day 90. This correction did not pass the survival screen. [Paired check and paid intakes](SOCIAL_CROP_OFFER_SCREEN.jsonl)

The independent replay recovered the same 1,039 coarse feeding opportunities for worker 10. The corrected chooser selected none of the unreachable larvae and recorded zero rejected transactions. The worker completed 1,489 inactive actions in this window, compared with 450 previously. Its 112 separate brood approach selections still ended in interruptions and it did not move. The queen received no offers and the other nine recipients received exactly the same 80 meals. The change removed a real defect in recipient selection and isolated the remaining failure in initiating a physical encounter. [Focal worker actions, stocks, positions and competing meals after the correction](SOCIAL_CROP_OFFER_DEATH.json)

The larval selection check alone cannot arrange a new donor–queen meeting. A future controlled experiment could test whether a hungry queen and a loaded worker respond to each other's locally sensed mouths by each taking a legal step. Hold food, collision, contact range and lethal rules fixed. Measure other recipients' uptake and the physical approach along with founder survival. The three worlds with absent or late first collections need a separate test at the foraging stage.

## Reproduce a two-year pair

```powershell
py -3 -B -m tools.measure_social_crop --model callow --seed 3 --supply nearby
py -3 -B -m tools.measure_social_crop --model chamber-return --seed 3 --supply nearby
py -3 -B -m tools.inspect_social_crop_cut --physics 54 --seed 2 --day 69 --until-queen-death
py -3 -B -m tools.trace_social_crop_meal
py -3 -B -m tools.verify_social_crop
```

For the Physics 55 death window run the supplied seed-2 screen with `--model mouth-range --days 90`, save its JSON output, then pass its path to `tools.inspect_social_crop_cut --receipt <file> --physics 55 --seed 2 --day 65 --until-queen-death --counts-only --follow-worker 10`. Repeat with `--model checked-offer` and `--physics 56` for the larval eligibility test. The Physics 56 native implementation is at `b55a4f2c`.

Use seeds 1, 2, 3, 17 and 29. Use seed 2 with `--supply absent` for the no-external-feeder control. The finite founding stores and sheltered wick remain available in that control. Day 73, day 365 and day 730 samples come from the same trajectory. The first brood comprises eggs laid within 24 hours of the first paid birth. A callow is an adult less than seven simulated days past its own recorded eclosion. Living individuals at day 730 are censored there.

For an exact historical executable hash, build the corresponding implementation revision. Native revisions are `7e4df349` (Physics 52), `2aba02b3` (53), `171f13af` (54) and `b4fcddb1` (55). A newer executable can select the older semantics. The executable hash and process memory may differ between builds. The initial and final frame hashes, world identity and event count are the replay checks. Six historical Physics 50 worlds were reproduced against the published initial frame, final frame and committed count. The reader streams committed facts, periodically compacts retained in-memory history and validates the food ledger against the native frame. Later read-only diagnostics add explicit worker emergence IDs, death-cut stocks and optional adult mouth samples. The 24 runs processed 67,506,184 committed facts. Their combined two-year receipt occupies 295,483 bytes and peak native process RSS reached 137,334,784 bytes in the largest run. The measurement did not create full two-year archive files.

Windows Release passed 292 native CTest cases. The live suite passed 42 tests and the additional source-to-callow replay passed separately. The live tests checked marked intake against paid collections, saved populated worlds in both compact and SQLite formats and compared the next day's frame, subsequent event page and native ledger after each restore. The [native CI run](https://github.com/Aquaticfuller/AntWorld/actions/runs/45101673304) covers Windows and Linux Debug/Release and the sanitizer job for Physics 54. The original B06 comparison, historical application performance qualification and biological validation status are independent of these engineering checks.

## Biological interpretation

Worker-to-worker dissemination of liquid food was directly observed in *Lasius niger* groups without brood or queens. This constrains the existence of a social food route. It leaves queen choice, larval dose and long-term founding survival open. Crop fullness affected individual exchanges in *Camponotus sanctus*. Using a half-difference rule in the black garden ant model is an explicit extrapolation with an engineering bound. Neither experiment establishes a two-year population target for this protected world. [Black garden ant dissemination experiment](https://doi.org/10.1038/s41598-019-52019-6) · [Individual crop measurements](https://doi.org/10.7554/eLife.31730)

Protein must also reach developing offspring. Direct feeding experiments with founding *L. niger* queens found more pupae plus workers on cricket or combined diets than on a sugar diet. The endpoint combines stages and does not identify the dose or route received by a particular larva. [Founding diet experiment](https://academic.oup.com/biolinnean/article/142/4/397/7342048)
