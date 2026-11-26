# Local events in the founding task scheduler

## Comparison defined before execution

Use a physics-82 opt-in contrast with the physics-80 navigation, resources, time costs and thresholds. A successful movement toward a personally remembered refill berth can request the next local decision at the next resolution boundary. This applies to a worker with room for a normal refill and an established liquid-food route. A completed move must reduce its distance to the known berth. A blocked, stationary or non-progressing action retains the ordinary schedule. Positive food arriving at the real depot can request an early local founder review when the new food meets her current meal demand, the depot is within perception and she is free. An actual crop reduction across the existing refill-capacity threshold can wake an idle experienced collector. Each wake replaces a later review and uses the same physical candidate validation and resource transaction.

Compare fixed cuts from the supply audit at seeds 2, 3 and 17 with original physics 80. Observe latency after paid work, first collection, founder received and absorbed mass, real distances, interrupted work, total committed facts and the terminal physiology. A positive wake must have actual progress or material as its predecessor. In an inaccessible case the colony must still be able to fail. Verify the pending wake survives exact save, restore and segmented advancement. Follow one seed from birth through its first 24 adult hours and report the full contrast. This is an engineering experiment on task wakeups. Other routine reviews remain available for situations without a corresponding local notification.

## Response-priority contrast

Physics 82 increased real sugar delivery in the seed-3 cut and lost the oral supply seen in the seed-2 control. Test a separate physics-83 arm. Stimulus wakes run the local food decisions and keep a valid feeding or brood-care opportunity ahead of refilling. The stimulus alone does not admit an unrelated ordinary program lottery or the periodic exit search. Hold the same prescribed cuts and observations. Require the fixed seed-17 failure to remain available and compare founder intake, repeated approach steps and throughput against both versions. This contrast reuses the same pre-existing local inputs and changes how an early wake is dispatched.

## Refill intent contrast

Physics 83 reproduced the same motions and supply as physics 82 in the prescribed cuts. The first seed-2 early wake follows a `Move to a resting site` observation. This label does not tell whether the decision chose a refill leg. A geometrical improvement by itself carries no evidence of why the ant moved. Physics 84 carries the refill intention through the selected legal approach step. Only a completed, advancing leg explicitly selected by the refill decision may request the next refill review. Ordinary repositioning and failed actions cannot trigger it. Repeat the matched cuts and the first-day cohort. Preserve the finite resource conditions and keep the positive delivery and crop-space responses.

## Long-horizon comparison

Start physics 84 from birth under the existing two-year supply protocol. Use nearby supply in seeds 1, 2, 3, 17 and 29, and absent supply in seed 2. Hold all ecological inputs other than the wake policy to the published physics-80 inputs. Compare to the frozen physics-80 receipts in `SUSTAINED_SUPPLY_TRIALS.jsonl.gz`. Keep the established 730-day endpoint: a living founder, at least one new adult in year two and more live workers at day 730 than at days 73 and 365. Count founder drinks, oral receipts and physiological uptake separately. Preserve first adult timing and death even when the colony fails early. Read events in bounded blocks and store only compact receipts. Report a resource or host limit as an incomplete run.

## Event ownership and scope

`WorldRuntime::advance_to` advances to the next scheduled event. Its shared queue gives actions and physiological settlement a deterministic order at each simulated timestamp. Each adult owns one pending autonomy wake. A qualifying stimulus can replace that wake with one at the next millisecond. This gives the resolving transaction time to finish and preserves action duration and material costs. The resulting wake goes through normal spatial, ownership and ingredient checks. The existing scheduler still handles ordinary activity, feeding and route exploration where no specific notification is available. The scheduling analogy is gem5's queued completion and external wakeup pattern. [gem5 event documentation](https://www.gem5.org/documentation/learning_gem5/part2/events/)

The new reason travels in the existing scheduled-event payload. Physics 82, 83 and 84 use checkpoint schemas 75, 76 and 77, respectively. In physics 84 the existing care continuation counter carries one refill intent on the chosen movement. Its use ends along with the movement lease. The full journal retains committed fact schema 10. The time-step-free scheduling of owned actions was already present. The added stimuli concern the decision between actions. A general local subscription model for changing physiological needs or every kind of spatial stimulus remains outside the measured coverage.

## Matched cuts

The table gives actual founder oral receipts and uptake. Uptake can include earlier crop stock and direct drinks. The archived six-hour cuts use fixed start and end times. Seed 1 uses the first-worker 24-hour cut.

| Cut seed | Physics | Committed facts | Oral sugar / water, µg | Absorbed sugar / water, µg | Terminal observation |
|---|---|---:|---:|---:|---|
| 2 | 80 | 5,941 | 346 / 179 | 106 / 199 | Founder alive |
| 2 | 82–84 | 8,676 | 0 / 0 | 0 / 125 | Founder alive |
| 3 | 80 | 840 | 165 / 78 | 110 / 97 | Founder alive |
| 3 | 82–84 | 1,588 | 297 / 78 | 110 / 97 | Founder alive |
| 17 | 80 | 585 | 24 / 0 | 50 / 25 | Energy death at 6,260,648,409 ms |
| 17 | 82–84 | 585 | 24 / 0 | 50 / 25 | Energy death at 6,260,648,409 ms |
| 1 | 80 | 2,886 | 547 / 125 | 316 / 139 | Founder alive |
| 1 | 82–84 | 3,721 | 548 / 125 | 316 / 139 | Founder alive |

The seed-3 worker completed another real collection. The sugar debit at the feeder increased by 264 µg. More sugar reached the queen's crop, and physiological uptake at the fixed cut was the same. In seed 2, workers 8 and 9 made 273 reversals in 290 moves and 298 reversals in 310 moves, respectively. The increased movement accompanied a complete interruption of oral transfers. Giving feasible feeding precedence at a stimulus review in physics 83 and requiring explicit refill intent in physics 84 reproduced these outcomes. The seed-2 witness therefore survived the intent check. The `Move to a resting site` label alone gave an ambiguous account of that leg. These tests establish the regression and its timing sensitivity. They leave the precise cause of the repeated reversal sequence open.

The seed-17 worker holding over 550 µg of sugar remained outside usable oral access through all 25 of its reviews. Its movement and the founder's terminal physiology were unchanged across all arms. This cut supplies a counterexample to using a shorter wake as a cure for unreachable feeding positions.

## Queue and persistence witnesses

In the strongest seed-3 physics-84 witness, worker 8 committed move 216,104 at 6,773,157,072 ms. The checkpoint taken at that instant had a local-stimulus wake at 6,773,157,073 ms, which was the source of decision 216,112. The control still had its regular review queued for 6,774,133,521 ms, 16 minutes 16.449 seconds after the witnessed movement time. The 1 ms refers to dispatch after a transaction. It measures neither locomotion speed nor a biological reaction time. The same queue proof was registered for seed 2 in physics 82 and 84, with its regular review due 13 minutes 14.648 seconds after the movement time. Exact restoration and split advancement reproduced the terminal frame and canonical suffix in each witness.

Starting from birth in seed 1, physics 84 raised the first 24 hours of worker reviews from 108 to 118 and committed moves from 222 to 320, with three reversals compared to eight in the control. The longest action gap remained about two hours. Oral sugar reached 544 µg in both runs, and sugar uptake reached 316 µg in both. These counts give a work-load contrast rather than a CPU or memory benchmark. The observed queue witnesses certify the movement stimulus. The crop-capacity and depot-delivery notifications were included in the trial and have no isolated causal witness in this report.

The independent SQLite reader compared the hash of all 13,357 committed facts against the native stream. Reloading the same archive reproduced the frame and the 449 subsequent facts over 30 minutes byte for byte. The temporary archive occupied 2,039,808 bytes. The compact test checks a scheduled wake, while the SQLite test checks durable canonical history and additional actions. Windows Release passed all 292 CTest cases, the timing-input test, pending-wake restore and two focused live-observer tests. CI repeats the timing, pending-wake and SQLite checks on Windows and Linux.

## Selection-to-action consistency contrast

In physics 84 seed 2, every one of worker 8's 23 `Out of reach` interruptions targeted the queen. The first selected approach was fact 264,476. The action was rejected at its start 1 ms later, while the same pair still had visible mouths, a candidate step and a payable oral offer. Worker 8 retained 159 µg of its initial 162 µg of sugar. `local_food_offer` chooses adult meal approaches using mouth visibility. `execute_care_action` additionally checks the straight line between the animals' centers, although the actual walk is a different segment.

Physics 85 uses current mouth visibility as the target sensing condition at both ends of an adult meal approach. Keep the original swept motion, terrain, traffic, distance, same-colony and final oral payment checks. The contrast is successful in this cut if it completes an actual approach and reaches positive founder receipt and uptake, with fewer immediate `Out of reach` rejections of visibly local adult meal approaches. Repeat seeds 1, 3 and 17 at the fixed cuts. A matched inaccessible offer must remain subject to the actual mouth and route constraints. Record all outcomes against both physics 80 and 84. Keep the previous two-year comparison as the engineering screen for physics 84. Run the same from-birth comparison for physics 85 only after evaluating the short contrasts and bounded runtime.

Physics 85 reproduced all four physics-84 cuts, including the 23 seed-2 rejections. Reading the saved care lease for fact 264,476 showed that the selected step had zero *subsequent* approach steps left. The executor used that counter to decide whether the already scheduled step was a meal approach. The last step was therefore checked against a different contact rule from the one that selected it. Physics 86 preserves the mouth-guided approach through that final scheduled step. A zero counter still forbids scheduling a further leg. Compare the original cut and the instant before the rejected action. Require an actual completed segment and preserve the original constraints on blocked encounters and material exchange. Compare founder receipts and uptake over the same four windows before considering the two-year matrix.

Physics 86 completed the registered leg in 9 ms of simulated motion at the existing speed. The movement ended at the selected destination 88.4 µm away. The cut restores exactly inside the movement and reproduces the committed suffix. Over the six hours, worker 8 completed 23 additional moves and its rejected `Out of reach` approaches fell from 23 to zero. It still reversed to a recent position in 299 of 313 moves and retained 159 µg of sugar. The founder's oral receipts stayed at zero, and her absorbed sugar and water remained 0 and 125 µg. This isolates a real execution error and its repair. The timing-related supply regression also depends on reaching an actual payable contact after that leg. The seed-17 inaccessible offer still ended in energy death at the original instant. The seed-1 and seed-3 windows retained their respective physics-84 transfers and uptake. Physics 86 failed the registered short-cut supply endpoint. Its two-year panel was gated on that endpoint.

The new checkpoints are schema 78 for physics 85 and schema 79 for physics 86. The independent archive check repeated on physics 86 and matched all 13,357 events plus the same 449-event continuation with the appropriate model header. `--verify-final-leg` derives a saved cut from the registered prior cut and checks real completion. `--verify-archive --stimulus-version 86` exercises durable history. Both commands run in the Windows and Linux observer workflow.

## Two-year comparison and release decision

All six physics-84 worlds reached the 730-day capture and completed their ledger checks. The independent input comparison verified all 12 initial frames across six seed and supply pairs, including equal geometry, initial populations, material stock and founder reserves in each pair. Physics-80 outcomes come from the previously published same-input panel.

| Seed | Feeder | Founder death, physics 80 | Founder death, physics 84 | Day-730 workers, 80 / 84 |
|---:|---|---|---|---:|
| 1 | Nearby | Day 61.97, dehydration | Day 80.22, energy depletion | 0 / 1 |
| 2 | Nearby | Day 91.22, energy depletion | Day 80.26, energy depletion | 1 / 1 |
| 3 | Nearby | Day 89.42, energy depletion | Day 57.17, dehydration | 1 / 0 |
| 17 | Nearby | Day 72.46, energy depletion | Day 65.77, dehydration | 2 / 1 |
| 29 | Nearby | Day 82.44, energy depletion | Day 87.01, energy depletion | 0 / 0 |
| 2 | Absent | Day 73.36, energy depletion | Day 73.36, energy depletion | 0 / 0 |

The two-year sustained-supply endpoint failed in all five provisioned pairs. Every founder died, and every world had zero new adults in year two. In seed 1, founder sugar uptake increased from 1,132 to 2,031 µg and water uptake increased from 345 to 1,667 µg. In seed 2, sugar uptake fell from 5,434 to 2,279 µg. In seed 3, direct drinking and oral water receipts yielded 2,252 µg of absorbed water in physics 80, and physics 84 recorded zero positive water uptake. Its founder died well before the age of the separate seed-3 matched cut. The extra food transfer in that cut consequently supports an immediate-response result only. The no-feeder control retained its death time and committed event count.

The long runs provide no performance qualification. Seed 1 increased from 3,332,573 to 14,270,307 committed facts. This workload completed in memory with bounded history compaction and compact receipts. Physics 84 remains experimental after divergent founder survival and higher work in specific worlds. Physics 86 remains experimental after passing the selected approach and persistence checks and failing the seed-2 oral supply endpoint. The unresolved path is sustained contact and repeatable intake, with high reversal counts despite legal movement and remaining crop sugar. A useful continuation needs a local encounter that progresses to payable mouth contact across successive actions. Reducing general review frequency would require named replacements for hunger, nearby needs and environmental changes. The measured local cues cover a subset of those decisions.

The final Core built in Release and passed 292/292 Windows CTest cases, two focused native observer tests, the four matched windows, the selected final-leg restore and independent SQLite continuation. The [compressed receipts](FOUNDING_ACTIVITY_RECEIPTS.json.gz) contain 94,447 bytes and SHA-256 `1429aabb3a4ef6822064679f7dc11b2656bab28bcbe525b5f2c927cb60003626`.

## Reproduction

The [compressed receipt](FOUNDING_ACTIVITY_RECEIPTS.json.gz) includes each frozen cut, observed negative outcome, selected-action evidence and compact persistence digest. From the repository root with the native observer built in Release:

```powershell
$core = 'build/m0-live/antworld_m0_live.exe'
py -3 -B -m tools.audit_founding_activity --core $core --stimulus --stimulus-version 84
py -3 -B -m tools.audit_founding_activity --core $core --verify-stimulus 3 --stimulus-version 84
py -3 -B -m tools.audit_founding_activity --core $core --stimulus --stimulus-version 86
py -3 -B -m tools.audit_founding_activity --core $core --verify-final-leg
py -3 -B -m tools.audit_founding_activity --core $core --verify-archive --stimulus-version 86
py -3 -B -m tools.measure_first_meal --core $core --model stimulus-refill-intent --seed 2 --supply nearby --days 730 --feeding-continuity --trace-flux --include-water
```
