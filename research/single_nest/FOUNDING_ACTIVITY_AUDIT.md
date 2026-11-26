# Founding activity and interruptions to supply

Reference `26bb5f10ef67f353301a2a13980fb6482e1e5ec7`. Timing controls are headless experiment inputs stored in the existing worker-activity configuration.

## Measurement design

Use the archived six-hour supply cuts and the first 24 hours following the seed-1 adult transition. Measure the time between committed actions, paid work, decision cadence, task labels and completed physical outcomes for each identified animal. Measure receipt and subsequent uptake separately. Clip intervals to the recorded lifespan and observation boundaries. A quiet interval is an absence of documented action or paid work and does not measure sleep. Cooldowns, failed reviews and missing duration fields remain distinguishable.

Compare three from-birth arms in the current protection preset (physics 48, seed 3) and the newest exposed trial (physics 80, seed 1). Both use 25 °C, 80% relative humidity, the nearby finite feeder, wet wick and the same closed geometry per pair. Use the nominal worker check and task commitment of 15/60 minutes, shorten checks to 5/60, and shorten minimum commitment to 15/15. The check interval also sets routine nutrition polling and the worker's urgency forecast horizon in this implementation. The 15/15 arm keeps those values stable and modifies the minimum ordinary program commitment alone. All three use the same deterministic timing variation, physiology, queen clocks, physical contact, initial resources and release rules.

Observe the first adult's first 24 hours in all six arms and follow these six worlds to day 95 in separate headless runs with the same inputs. Record actual collecting, delivering, feeding, handling, motion gaps and reversals, plus the amount and timing of founder oral receipts and uptake, death and workers through day 95. Equal initial state apart from timing, exact pending-work restoration and full resource ledgers are required to interpret a contrast. Report each result. These tests are timing sensitivity experiments and do not assign a species-level activity target or replace the two-year founding protocol.

## Movement, handling and the real review clock

At 25 °C the current founding presets ordinarily review workers every 15 minutes, with deterministic ±25% variation. The ordinary task-switch threshold is one hour. Local urgent work, returns and solicitation have separate paths. An authorized timed movement or handling act finishes on its own clock. `Rest` and `Paused` are program labels. A worker can carry out a short action and still spend most of the day in one program. In the protection preset's day-one witness, worker 12 moved once and made five positive oral transfers to another worker.

The following rows follow the first worker for 24 hours from the same witnessed emergence in each pair. An action-free gap excludes recorded successful handling, actual movement intervals, material transactions and paid work. It includes the observed beginning and end of the window, so a gap touching those boundaries is a lower bound on its full length. A reversal is a return to the position at the end of the preceding but one observed move. The starting snapshot is excluded from this count.

| Model and seed | Checks / commitment, min | Reviews | Moves | Reversals | Longest gap | Founder oral sugar / water, µg |
|---|---|---:|---:|---:|---:|---:|
| Physics 48, seed 3 | 15 / 60 | 102 | 162 | 6 | 20 h 50 min | 0 / 0 |
| Physics 48, seed 3 | 5 / 60 | 292 | 162 | 6 | 22 h 19 min | 0 / 0 |
| Physics 48, seed 3 | 15 / 15 | 102 | 162 | 6 | 19 h 35 min | 0 / 0 |
| Physics 80, seed 1 | 15 / 60 | 108 | 222 | 8 | 2 h 0 min | 544 / 124 |
| Physics 80, seed 1 | 5 / 60 | 305 | 2,640 | 2,155 | 1 h 4 min | 333 / 111 |
| Physics 80, seed 1 | 15 / 15 | 110 | 683 | 272 | 57 min | 594 / 164 |

In the nominal physics-48 window the first worker completed a real excavation and five loaded deliveries. It logged 38.3 minutes of paid work and under 43 seconds of committed movement. The rest of the long action-free interval persisted through many reviews. The current source has concrete brood cleaning and a conditional entrance patrol. Its advertised task enum and scheduler do not implement a separate worker garbage-removal bout. The activity counts do not credit an unimplemented job or treat review events as work.

## Which interruptions affected intake

In the frozen physics-78 seed-1 emergence cut, the first worker made 96 ordinary reviews and completed zero movements over its first 24 hours. It completed zero food collections. Physics 79 with the same worker check and program clocks completed 220 movements, excavated, collected four actual loads and gave the founder access to positive sugar and water receipts in the identical window. A reachable work stance made the observed difference. The from-birth physics-80 lineage later lost its founder to dehydration. [Previous from-birth and intervention records](SUSTAINED_SUPPLY_RESULTS.md)

In the six-hour seed-17 energy cut, physics 80's worker 11 held more than 550 µg of sugar and performed 25 reviews with no evidenced action. Its offer remained outside oral perception of the founder. The founder received only 24 µg of sugar from worker 14 and died. The independent physics-81 distance contrast produced 24 movements from worker 11, including 21 reversals. The measured receipt and time of death were unchanged. In the seed-3 control cut, 24 reviews each proposed the blocked rest-site action at a usable depot. Reusing the valid depot action led to a real collection, founder receipt and uptake with the same decision timing.

Oh and Cremer's *Lasius niger* experiment found that brood concentrated nearby activity and that grouped ants could show less motion per individual. The authors distinguished movement from possible handling or grooming and found weak, varying activity periods. Their flat-nest groups of one, six and ten non-callow workers and the earlier sampled motion detections motivate a finer view of useful actions. The minutes in those camera data have a different observation definition, age and social context from the founding runs. [Primary activity study](https://doi.org/10.1111/2041-210X.70277) · [Prior camera-data replay](../m0/WORKER_ACTIVITY_TIMING.md)

## Through day 95

The three physics-48 founders remained alive at the observation limit. The nominal and faster-check worlds each had one worker at day 95, while the shorter program commitment world had two. In physics 80, shortening minimum program commitment from 60 to 15 minutes extended founder survival from day 61.97 to day 76.04 for seed 1. Absorbed water increased from 345 to 1,333 µg, chiefly through drinking directly from the wick. Direct water receipts rose from 50 to 1,225 µg while oral water gifts fell from 313 to 167 µg. Absorbed sugar fell from 1,132 to 737 µg and the terminal shortage changed from dehydration to energy depletion. This is a causal sensitivity to a single scheduling input in this simulated world. The movements, transfer amounts and physiological outcomes remain separate endpoints.

The five-minute physics-80 founder died on day 80.39 from energy depletion. She had absorbed 2,062 µg of sugar and 1,638 µg of water, and two workers remained at day 95. Faster checking increased first-day worker movement about twelvefold. Approximately 82% of the moves returned to a preceding position, and the initial 24-hour founder receipt was lower. These are mixed changes to route usage and timing. They give direct evidence of wasted motion and delayed access, with a lifetime benefit in a single replay and substantial extra work. Both changed timing arms failed to maintain the founder through day 95.

## Verification and reproduction

All 292 Windows Release CTest cases and two focused live-observer tests passed. The independent initialization check matched all six new initial frames and their physical resources in two groups. Within each group the adult emergence event, pose and physiological starting balance were identical. The previous supply panel's 36 initial frames still match by SHA-256. An explicit nominal timing request generated the same frame as the default request. An invalid interval was rejected and the active session's frame identity was preserved. In the five-minute arm, a compact save at the first worker review preserved the frame and committed suffix through the next 90 minutes. The native food, hydration, energy, lipid and soil ledgers held in each completed run.

The [compressed receipt](FOUNDING_ACTIVITY_RECEIPTS.json.gz) retains all short-cut results, six first-day results, the longer trajectories and the restoration hashes. The experiment streams committed facts in bounded blocks. Run the following from the repository root after building `antworld_m0_live`.

```powershell
$core = 'build/m0-live/antworld_m0_live.exe'
py -3 -B -m tools.audit_founding_activity --core $core
py -3 -B -m tools.audit_founding_activity --core $core --verify-timing
py -3 -B -m tools.audit_founding_activity --core $core --seed 3 --model protected --minutes 5
py -3 -B -m tools.measure_first_meal --core $core --model familiar-site-detour --seed 1 --days 95 --worker-timing 900000 900000 --feeding-continuity --trace-flux --include-water
```

The nominal arm omits the timing option. The shorter check uses `300000 3600000` and the shorter program commitment uses `900000 900000`, both in milliseconds. Use `--model protected --seed 3` or `--model familiar-site-detour --seed 1` for the from-birth runs.
