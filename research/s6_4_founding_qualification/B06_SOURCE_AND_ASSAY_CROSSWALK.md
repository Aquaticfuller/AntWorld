# B06 reference and comparison scope

The admitted primary source is Kipyatkov, Lopatina, Imamgaliev and Shirokova (2004), DOI `10.1023/B:JOEY.0000033808.45455.75`. The locally acquired English paper was rechecked against source SHA-256 `b8f897d22096c1d073a00f992ac7f6700e67c12ae1a79476632d38999a53e3de`. Methods on pp. 166–168 describe single post-flight foundresses, a 40 mm Petri dish, regularly moistened cotton, darkness, no added food, and observation once per day at approximately the same time. Their reported precision was approximately half a day. They used the first larval count as the target for subsequent pupal and worker observations. The adult and pupa count endpoint can mix individual lineages. Prepupa is included with pupa. [Original paper, Methods and Tables 1–2](https://doi.org/10.1023/B:JOEY.0000033808.45455.75)

| Measured reference, 1994 warm treatment | Borisovka | St. Petersburg |
|---|---:|---:|
| Founders producing any workers at nominal 25 °C | 20/20 | 22/22 |
| Egg duration at 24.7 °C, days | 16.7 ± 0.07 (138) | 15.7 ± 0.08 (130) |
| Larva duration at 24.8 °C, days | 10.2 ± 0.09 (127) | 10.6 ± 0.09 (114) |
| Prepupa + pupa duration at 25.4 °C, days | 14.5 ± 0.08 (112) | 13.6 ± 0.09 (109) |
| Total ontogenesis, days | 41.1 ± 0.14 (110) | 39.9 ± 0.16 (104) |

The table reports mean ± error and numbers of brood individuals in parentheses. These counts are not independent founding queens. The paper does not give the row-level sequence of daily counts, the correspondence between the published stage times and each queen, individual brood attrition by observation day, water intake, diet transfers or larval tissue budgets. The published 1987 egg results provide a related earlier experimental summary, with no matching whole-colony holdout. Searches for the DOI, study title and repository data located article and institutional records. No original daily-count dataset was obtained. An earlier file received as `REF-B06-ROWS` is the already admitted PDF, with the same hash. [Institutional record](https://pureportal.spbu.ru/en/publications/effect-of-temperature-on-rearing-of-the-first-brood-by-the-founder-females-of-the-ant-lasius-niger-hymenoptera-formicidae%288a0612ed-e402-40b7-a944-40317729e85c%29.html) [Original source acquisition](../s6_4_preflight/S6_4_PHASE4_ACQUISITION_UPDATE.md)

| Condition | Closed-stock simulation | Protected supplied simulation |
|---|---|---|
| Access to water | Finite foundress inventory and internal transfers. There is no regularly moistened cotton source. | A registered offsite liquid diet can be accessed by actual workers through the chamber entrance. No free founder water. |
| Nutrition | No external food. Maternal composition and brood costs are engineering inputs. | External carbohydrate, protein and water are prescribed finite stocks. After the first workers, the source makes this a different assay from B06. |
| Temperature and nest | Population-specific clock anchor. No actual temperature or humidity exposure function. | The same clock anchor, idealized three-dimensional chamber and surface resource. |
| Observation | Whole-world daily living counts plus exact committed stage events and sampled inventories. | The same complete records through day 150 and a separate 180-day source-budget diagnostic. |
| Development | Individual eligible time plus explicit energetic, hydration and larval tissue requirements. | The same gates, followed by worker-supported intake and funded further eggs where possible. |

The original daily algorithms retain their first positive larval count and their separate exact and at-least tests. An individual moving to pupa at its configured age establishes clock execution in that world. It cannot establish the paper's first same-count pupal observation. Actual developmental scarcity can keep the model's simultaneous counts below the target even when many individuals start, hatch or eventually eclose. This is a model outcome. Its quantitative attribution to inappropriate physiological parameters in the real experiment requires matched watering and colony-level data. Development-reference agreement, mechanistic plausibility, bounded simulation readiness and independent biological validation remain different claims.

| v7 comparison | Complete exact count | Complete at-least count | Count-attainment medians in days, egg / larva / pupa / total |
|---|---:|---:|---|
| Borisovka original closed, primary care-on | 0/192 | 0/192 | 17 / 21 / unavailable / unavailable |
| St. Petersburg original closed, primary care-on | 0/192 | 0/192 | 16 / 24 / unavailable / unavailable |
| Borisovka supplied nominal balanced | 6/6 | 6/6 | 17 / 37 / 11 / 65 |
| St. Petersburg supplied nominal balanced | 6/6 | 6/6 | 16 / 38 / 7.5 / 60.5 |
| Borisovka supplied factorial balanced | 17/24 | 20/24 | 17 / 35 / 11 / 65 |
| St. Petersburg supplied factorial balanced | 21/24 | 24/24 | 16 / 38 / 9 / 63 |

Medians are taken separately over the available observations for each stage; the two supplied readers have the same medians in the displayed cases. Only 27 and 16 closed cases reach their pupal count. Their available larval count intervals already exceed the respective B06 observed 7–14 and 8.5–12.5 day ranges. The supplied arms eventually reach the original count in many worlds, but their same-count worker endpoint can involve later broods. Their factorial total times are 18 and 19 days above the upper published ranges, and their apparent pupal intervals can be shorter than the individual pupa clock because multiple cohorts overlap. These supplied descriptive comparisons are not substituted into the original B06 acceptance reader. [Frozen original results](../../experiments/s6_4_integrated_founding/analysis/resupply-closed/timing_comparison.csv)

## Known-age outcomes and competing losses

The median elapsed time among individual transitions equals the nominal 16.7 / 10.2 / 14.5 days in Borisovka and 15.7 / 10.6 / 13.6 in St. Petersburg across the displayed closed and supplied groups. Those values were used as model inputs. They do not establish independently measured clocks or explain the censuses. In the closed primary care-on groups, 514/6,838 Borisovka larvae and 647/6,692 St. Petersburg larvae pupate. Energy deaths number 3,153 and 1,531. Dehydration deaths number 3,159 and 4,505. Twelve and nine larvae are right-censored. Only 24 and 28 completed transitions occur strictly after the larval clock. A total of 6,109 and 5,706 larvae have neither a paid maternal ration nor observed larval protein uptake. The more supplied factorial groups have 878/1,463 and 1,026/1,536 pupations. Of those, 24 and 45 exceed the nominal larval clock. Other larvae die or are censored, and late brood can remain in the pupal stage when observation ends. Counts of individuals are exposures nested within software worlds.

This separates three questions. The clock is executed at the configured length in successful individuals. High immature attrition and narrow overlap of surviving adults are real limitations of the closed simulation. The magnitude of mismatch in a faithfully moistened enclosure is unknown from the current references, because founding water access and attrition are confounded across study and model. Do not alter the stage clock to compensate for a shortfall in access or concurrent cohort survival. [Individual stage exposures and census diagnosis](../../experiments/s6_4_founding_qualification/b06)
