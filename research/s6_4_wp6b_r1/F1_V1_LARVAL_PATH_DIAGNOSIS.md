# F1 v1 larval feeding paths

Baseline `bc59187df942720a56e821c3e06f820176ec3132`. The reconstruction read the canonical history and daily individual cuts in all 101 committed ZIPs. All 1,932 attempts reconcile to their published index. The 36 rejected inputs retain their original status. The reader verified every ZIP and every consumed file against its original SHA-256. [Derived paths and receipt](../../experiments/s6_4_wp6b_r1/baseline_paths)

```powershell
python tools/diagnose_s6_4_wp6b_r1.py experiments/s6_4_wp6b/formal out/wp6b-r1-v1-paths
```

`wakes.csv.gz` joins the founding queen's CareWake tick to its actual contact opportunities and selection by scheduled ID. `meals.csv.gz` joins committed rations and the matching completed bout by source. `larvae.csv.gz` retains funded birth, hatch, first contact opportunity, selected act, start, completed ration, next observed positive uptake, tissue requirement, competing exits and censor time by stable identity. In worlds with worker supply, the next uptake is an observed temporal association. It can contain protein from several donors. An opportunity establishes local geometry and reach for that scan. Candidates outside contact reach, the internal random draw, and individual capacity checks not represented by a fact are `UNOBSERVED`. `eligible_p` is a reconstruction of live contact, tissue plus crop deficit and nonzero mobile maternal protein. The full live energy, water, crop capacity and ownership guards remain separate from this necessary condition.

| Primary care-on endpoint | Borisovka | St. Petersburg |
|---|---:|---:|
| Worlds | 192 | 192 |
| Funded births / hatches | 7,173 / 7,061 | 7,150 / 7,042 |
| Wakes with larval contact / recorded larval opportunities | 28,583 / 126,041 | 33,480 / 147,519 |
| In-contact larval target selected | 2,958 | 3,874 |
| Feed selected / started / completed / interrupted | 590 / 590 / 590 / 0 | 796 / 796 / 796 / 0 |
| Larvae with 0 / 1 / 2 / 3 / 4 / ≥5 positive protein meals | 6,612 / 340 / 77 / 32 / 0 / 0 | 6,418 / 505 / 75 / 35 / 9 / 0 |
| Median hatch to first contact scan / first feed among observed (h) | 1.2 / 49.20 | 1.2 / 43.20 |
| Meal followed by another target selection within observation | 321 / 590 | 432 / 796 |
| Median meal to next target selection among observed (h) | 72.0 | 60.0 |
| Median next positive protein uptake after dose (h) | 6.0 | 6.0 |
| Median within-mother Gini of delivered protein among hatched larvae | 0.927 | 0.914 |
| Queen deaths with remaining mobile protein / all queen deaths | 168 / 168 | 168 / 168 |
| Median terminal mobile protein in those deaths (µg) | 462 | 452 |
| Larval exits by energy / water / right censoring | 3,383 / 3,624 / 54 | 1,768 / 5,220 / 54 |

All primary rations were followed by another local opportunity, often the immediate return-to-shelter wake. That wake does not imply another chance to select feeding. Observed retarget delays range from about 6 to 198 hours in Borisovka and 6 to 192 hours in St. Petersburg. The raw rows retain the at-risk endpoint for the remaining doses. Gini includes zero deliveries to hatched larvae and is undefined in worlds with zero total delivery. Death terminates exposure and a blank next observation alone cannot distinguish a death from censoring. The world and parameter profile are the units of simulation comparisons.

Each ordinary larva begins with 20 µg of tissue protein. The 85 µg tissue criterion and up-to-16 µg protein dose require at least five positive doses with subsequent uptake. All nine four-dose larvae dehydrated 400,317,998 ms after their fourth dose with positive body energy. Median post-last-dose exposure of the three-dose larvae was about 95 hours in Borisovka and 127 hours in St. Petersburg. They were still missing at least two positive doses. These are realized exposure windows with the actual subsequent expenditures and inputs. They do not estimate how long a hypothetical fifth dose would sustain a larva through pupation.

The primary decision path in `care.cpp::resolve_care_wakes` first admits a care choice, then uniformly chooses visible brood across applicable stages and then one of the admissible acts. The default 6-hour care cadence and maintenance gate hold. With nine or more in-contact larvae there were 72 feeding selections in 4,344 Borisovka wakes and 104 in 4,824 St. Petersburg wakes. With two to four there were 475 in 21,626 and 620 in 22,298. These strata mix different stages, adult state, competing bouts and return wakes. They locate competition for attention without estimating an isolated effect of ongoing laying. Many newly hatched larvae coexist during the opening-cohort wave. The trace does not identify which change in laying policy would change survival. This candidate leaves laying untouched.

The five wider no-worker successes each paid five protein-positive meals to the first successful larva. Their recipients had 78–92 recorded contact opportunities and 6–10 selections. They emerged 43.35–44.60 days after their own funded births. The two slower opening-spacing worlds produced 42 funded eggs each and 6–7 total meals. The three longer later-spacing worlds produced 23 eggs each and 9–10 total meals. These contrasts also vary timing and exposure. Matched seeds and their non-emerging siblings remain in the archive and will be compared under the candidate. The wider controls establish a feasible committed path for this budget system. They do not establish robustness within the ordinary input range.

The archive supports testing recurrence after a real meal. It cannot establish that a black garden ant queen tracks a persistent individual larval identity. B01 records care and its change with worker access, B03 measures colony output under supplied food, and B06 measures colony-level warm developmental timing with water-bearing cotton. None resolves target-to-target feeding transitions or individual protein transfer dose. [B01 methods and founding outcomes](https://doi.org/10.1111/1365-2435.14536) [B03 food treatments](https://doi.org/10.1093/biolinnean/blad149) [B06 warm development](https://doi.org/10.1023/B:JOEY.0000033808.45455.75)
