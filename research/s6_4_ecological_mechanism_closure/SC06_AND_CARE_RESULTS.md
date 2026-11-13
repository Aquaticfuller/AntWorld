# Local recruitment, brood feeding and activity results

## SC-06

All 84 isolated observed worlds and the prespecified SQLite restart completed. At least one receiver completed a linked recruitment episode in all 12 scout-return worlds, above the preregistered 8/12 floor. All 36 receivers in that arm complete the chain. The independently rebuilt episode keeps the same receiver, actual selected source and positive material load from activation to deposit. A changed program without a resulting trip remains a separate outcome. The binary durable repeat retains the same initial authority, final authority and fact bytes. [Raw witnesses and complete per-world outcomes](../../experiments/s6_4_ecological_mechanism_closure/scout)

| Arm, 12 worlds each | Positive collection events, all actors | Committed cues | Receiver cue observations | Activated receivers | Receivers delivering any food | Completed cue-to-delivery receivers |
|---|---:|---:|---:|---:|---:|---:|
| Scout return | 460 | 458 | 119 | 36 | 36 | 36 |
| Response disabled | 418 | 412 | 1,464 | 0 | 0 | 0 |
| Empty source sham | 0 | 0 | 0 | 0 | 0 | 0 |
| Passive/naive without a scout start | 0 | 0 | 0 | 0 | 0 | 0 |
| Existing autonomy | 68 | 68 | 1 | 0 | 36 | 0 |
| Physical source block | 0 | 0 | 0 | 0 | 0 | 0 |
| Depleted after the scout's single load | 12 | 12 | 88 | 28 | 0 | 0 |

Exposure in the disabled arm is higher because passive actors remain eligible to observe. A positive collection count includes all actors and repeat loads. A cue can also be produced by a previous receiver that has become a successful forager, and the chain preserves its actual ID. In completed episodes the median elapsed time from the first cue observation to the successful activation is 31.502 s (range 0–146.001), from departure to local discovery 7 s (1–25), and from collection to delivery 22 s (12–42.001). In the depleted arm all 28 activated receivers leave their forage episode without a linked delivery and eight never activate. Zero or unsuccessful outcomes are retained alongside the eligible population of three receivers. The exact 95% binomial interval over the 12 simulation worlds for 12/12 is approximately 0.735–1.000. Shared source colonies, biological prevalence and uncertainty require a different study. The assay establishes a local causal route to departure and load return under its declared controls. It leaves the species' dose response and naturally realized recruitment benefit open. [Behavior and primary-source boundary](MECHANISMS_AND_EVIDENCE.md)

## First meal, assimilation and maternal water

All 72 matched 55-day worlds completed. Each row below sums six software seeds for one population. Counts refer to distinct larval identities in each case. The mean or median over larvae would weight larger broods more strongly. The per-world median recipients rise from 3.5 to 13.5 in Borisovka and from 4.5 to 13.5 in St. Petersburg, meeting the preregistered breadth endpoint. Positive assimilation is independently verified. Timed actions have their own failure and right-censoring fields. [Full per-larva event links and assay records](../../experiments/s6_4_ecological_mechanism_closure/care)

| Population and treatment | Observed opportunity | Feed started | Paid maternal protein | Positive larval assimilation | All pupae | All workers | First-census workers / larvae |
|---|---:|---:|---:|---:|---:|---:|---:|
| Borisovka, original choice | 143 | 24 | 24 | 24 | 16 | 11 | 3/24 |
| Borisovka, first meal | 130 | 82 | 81 | 81 | 21 | 12 | 1/24 |
| St. Petersburg, original choice | 146 | 29 | 29 | 29 | 20 | 13 | 3/24 |
| St. Petersburg, first meal | 132 | 83 | 83 | 83 | 28 | 19 | 0/24 |

In the first observed larval cohort, the number with no positive maternal protein falls from 21 to 12 in Borisovka and 19 to 11 in St. Petersburg. Energy deaths fall from 21 to 12 and 19 to 11. Water deaths increase from zero to 11 and from two to 13. More first meals and more workers over the whole 55 days can coexist with fewer first-cohort eclosions. The control changes the locally eligible feeding choice; the shift between competing deaths is a realized outcome rather than an identified single biological cause. In care-off all 168 Borisovka and 174 St. Petersburg eggs hatch and none pupate. The unobserved internal candidate list is never inferred from these counts.

The hatch cue and the repeat-memory annotation were traced by their real wake and bout IDs. In Borisovka, the original choice produces 143 local cues, with 12 cue-initiated paid feeds, versus 130 cues and 41 paid feeds with the new choice. St. Petersburg has 146/18 versus 132/42. Repeat-memory selections are 75→157 and 84→160 respectively. Those counts are selections, not additional deliveries. The reachable water arm brings local cues up to 168 and 173, but only 41 and 43 cue-initiated paid feeds result. The actual care conversion remains limited after contact as well as before it. The separate tables retain all unoffered, unfed, interrupted, dead and censored individuals. They cannot identify whether an unrecorded rejection was due to the private choice draw, immediate state, or a candidate's eligibility. [Founding care paths by individual](../../experiments/s6_4_ecological_mechanism_closure/care/analysis/founder_feeding_by_larva.csv)

At the reachable water source, each of the 12 queens takes and absorbs exactly 1,200 µg from an explicitly seeded reserve. Identical isolated stock produces zero maternal debit or uptake. The water and blocked-water arms yield the same 1/24 and 0/24 first-cohort eclosions. Positive maternal hydration under this supply is therefore an engineering result with no evidence of rescuing those early cohorts. Subsequent transfer to larvae still uses the ordinary paid care transaction. The 55-day endpoint does not match the longer wet-cotton B06 exposure. [B06 scope](B06_SCOPE_CHANGE_REQUEST.md)

## Physical work and accounting

Compared with the matching clock-only arm, the paid-time arm spends 7,185,596 ms over six Borisovka worlds and 8,513,988 ms over six St. Petersburg worlds in owned intervals. Within those totals 856,000 and 872,000 ms are physically timed action under the `Paused` program, predominantly founding care in these closed-input controls. Clock-only history has no paid-interval facts. In the short matched assay no pupation or eclosion count changes in either population. The automatic energy-boundary test shows a worker entering a travel interval, spending its existing activity surcharge, dying before completing travel and preserving identical restored authority. Whole-program time, scheduled active effort, actual displacement, handling, rejection and right-censored activity remain separate. The assertion makes no quantitative claim about sleep, resting metabolic rates or unobserved behavior. [Independent calculation](../../tools/verify_ecological_closure.py) [Energy-boundary regression](../../cpp/tests/test_ecological_closure.cpp)
