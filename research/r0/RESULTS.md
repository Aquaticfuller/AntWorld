# R0 behavioral realism recovery

## Decision

Physics 32 is an `ENGINEERING_ONLY` motion and space-use prototype. It can be observed in OP0 and compared with a matched physics 29 colony. The protected shaft and bent connector both start with a single queen and produce workers that move, forage, exchange food, care for brood and excavate. The record also contains load-related failures, sparse movement, clustering, and long-run history pressure. No independent species-level calibration is established. B06 remains `INSUFFICIENT`, the historical application gate remains `FAIL`, and all nine biological blockers remain open.

[Windows launch and observation guide](README.md), [frozen conditions](PROTOCOL.md), [source-level and scientific evidence review](REFERENCES.md), [verified paired archives](../../experiments/r0/witnesses), [actual Chrome replay and comparison](../../experiments/r0/browser).

## Defects and changes

- `resolve_autonomy_wakes` used the same precise nest coordinate for delivery, high-level work eligibility and short care returns. Multiple individual programs therefore defaulted to the same place. In R0, a worker whose ordinary choice is Rest can make a paid move to a nearby supported, unoccupied resting site if its current body proxy overlaps another adult. The depot remains an actual destination for transport and care. Available endpoints are ordered around the local site with an identity-stable tie break. Segment clearance and berth availability are checked at the start and at commitment. Workers can stay quiet between reviews and remain eligible for their normal jobs. Endpoint exclusion permits transient body contact in shared transit space.
- `care_destination` already checked swept body clearance. R0 adds finite, distance-reducing diagonal alternatives for an observed brood approach when the direct route clips a corner. Timing comes from the existing unloaded speed and the exact segment length. The centerline is scheduled, paid and committed as a single segment. OP0 uses the real start, motion commit and completion, and refuses to interpolate if geometry changes across that witness. The arrow shows path direction. Body yaw and acceleration are outside the prototype.
- The earlier `local_space_demand` proxy counted floor sites against sampled contact count. R0 checks a bounded set of reachable, supported floor sites, compares that with actually local adult and brood load, and leaves a transit site in the accounting. A dense colony still needs an eligible worker and a real soil face. R0 excavation searches laterally along a supported layer and backtracks a bounded unsuccessful path to the depot. This prevents indefinitely continuing the same empty outbound search. The material mask, route clearance, work time, carrying and real placement still govern each edit. The first relocation-only pilot produced one shaft excavation by day 90 compared with 13 in the reference. That adverse result motivated the separately recorded excavation search correction. [Initial runs and their host-limit stops](../../experiments/r0/diagnostics/initial-failures).
- `checkpoint_ecological`, the care and excavation auditors, and OP0 use explicit schema 25 / physics 32. Saved pending motion keeps its owner, exact end time and true destination. The empty-return flag is linked to committed excavation decisions. The original standard/configured worker clocks still select their own physics in other worlds. The default new-colony checkbox is off.

## Observable outcomes and constraints

These seed-1 pairs use the same queen, source stock and release plan within each initial layout. All adults are naturally eclosed. Reported travel exposure divides summed witnessed motion intervals by summed adult worker time alive. The longest gap extends from a worker's adulthood to its first move, between displacement commits, and through its final observed boundary.

| Day-90 measure | Shaft 29 | Shaft 32 | Dogleg 29 | Dogleg 32 |
| --- | ---: | ---: | ---: | ---: |
| Living workers | 15 | 15 | 14 | 14 |
| Exterior-to-nest deliveries | 19 | 22 | 16 | 20 |
| Excavated material, mm³ | 13.75 | 123.50 | 14.25 | 84.50 |
| Completed rest relocations | 0 | 151 | 0 | 128 |
| Exact-coordinate adult-worker pairs at the cut | 105 | 36 | 91 | 45 |
| Total worker displacement path, m | 17.33 | 23.68 | 12.98 | 16.04 |
| Observed moving time as % of adult exposure | 0.0154 | 0.0209 | 0.0137 | 0.0168 |
| Median of each worker's longest no-displacement interval, h | 266.3 | 36.0 | 260.4 | 36.0 |
| Committed facts | 92,225 | 122,605 | 81,324 | 107,931 |

The modest movement duty fraction, long quiet intervals, and remaining co-location are substantial realism gaps. Field and laboratory endpoints differ. The reference open-canvas rates and laboratory camera detections do not calibrate movement in these small, loaded, three-dimensional spaces. The inherited speed cap is 10 mm/s for the fastest witnessed segments; the open-canvas path median in the existing data audit is about 50.6 mm/s. Read time in a task program, paid physical work, and position changes as separate measures. These worlds cannot yield a sleep time budget.

In the same room and with a controlled eligibility weight, the native density check uses one or eight fixture workers. The low load performs no soil edit in the matched time window; the higher load performs paid excavation. Two additional paired sealed-entrance seeds yield no external delivery or expansion, and by day 90 have no surviving workers. The two showcase layouts reach real soil cuts and matching parcel placement with workers born in the same world. These engineering controls avoid claiming a field relationship between colony size and resultant nest shape.

The web preview's witnessed shaft example follows worker #18 during its approximately 100 ms action on day 78.588, when ten workers are alive. `rest-segment` returns the matching canonical start #71210, move and completion #71215. The geometry and the before/after view share the same simulation clock, level and scale. A slow arrow and worker label expose a movement that a day-scale display can easily miss. The exact committed endpoint remains available in the event detail. A real browser check also switches the comparison to Simplified Chinese.

## Species interpretation of demography

### Founding inputs and seasonal resource pressure

Long cases start with one foundress and use a fixed thermal/physiological profile. The continued source has an accounted 730-day pulse reserve; the finite treatment supplies the same pulse for 120 days; the water-limited profile quarters the water component and retains carbohydrate and protein; the seasonal source alternates 182-day spans of full and quarter release. A finite reservoir is explicit even in the continued world. There is no cold or diapause response in this experiment. The resource cycles, scheduled release amounts and real deliveries are separately observed. No oldest-ant life-table endpoint exists in the candidate or reference model.

The table shows living workers on days 365, 450 and 730. All sixteen worlds reached the first two horizons. Fourteen reached day 730. The seasonal pulses changed the recorded inventories, while both seeds retained the same worker counts as in the continued treatment. [Daily, individual and death records with hashes](../../experiments/r0/diagnostics/long).

| Supply | Seed | Reference 29 workers | R0 32 workers | Queen outcome, reference / R0 |
| --- | ---: | --- | --- | --- |
| Continued | 1 | 25 / 28 / 37 | 41 / 45 / 54 | Both alive at day 730 |
| Continued | 7 | 26 / 28 / 35 | 40 / 42 / 52 | Both alive at day 730 |
| Finite 120-day release | 1 | 23 / 0 / 0 | 0 / 0 / 0 | Energy death day 407.705 / 329.588 |
| Finite 120-day release | 7 | 26 / 0 / 0 | 3 / 0 / 0 | Energy death day 402.790 / 337.703 |
| Water restricted | 1 | 30 / 32 / 34 | 50 / 54 / unobserved | Alive at day 730 / dehydration day 544.883 |
| Water restricted | 7 | 29 / 31 / 34 | 49 / 54 / unobserved | Alive at day 730 / dehydration day 530.683 |
| Seasonal supply | 1 | 25 / 28 / 37 | 41 / 45 / 54 | Both alive at day 730 |
| Seasonal supply | 7 | 26 / 28 / 35 | 40 / 42 / 52 | Both alive at day 730 |

### What causes a small colony or a queen death in these runs

In the first continued shaft pair, day 365 has 39 laid eggs and 25 eclosed workers in physics 29, compared with 56 laid eggs and 41 eclosions in R0. Both have 13 larval deaths and zero adult worker deaths at that cut. Species age mortality cannot explain the population difference. The change bundles local movement, usable floor and excavation, so causal shares of egg output, local care and resource traffic remain unresolved. These are experimental trajectories under the declared source input, not a field census or a target population curve.

In finite supply, seed 1's reference queen dies at day 407.705, canonical event 1,519,119. R0 dies earlier, at day 329.588, canonical event 4,405,565. Both explicitly record `Energy depleted`. Each has zero body energy, zero mobilizable lipid and zero carbohydrate in the crop, in outside stock and at the depot. The deposited stocks at death are 91,305 µg protein and 299,110 µg water in the reference, and 90,232 µg protein and 236,441 µg water in R0. The queen still has 6,826 and 6,994 µg body water respectively. Both worlds recorded 210 exterior loads. R0 ecloses 40 workers before the eventual loss, versus 27 in the reference, and uses its fixed finite ration sooner. For seed 7 the corresponding queens die at days 402.790 and 337.703, with zero body energy, lipid and carbohydrate in the same pools. By day 365 the two finite R0 worlds have lost 40 and 39 workers, while neither reference has yet recorded a worker death. Both pairs show an adverse tradeoff between earlier worker production and earlier exhaustion under a finite ration.

The two water-restricted R0 queens die with positive body energy and zero body, crop, depot and available exterior water. Their death event IDs are 11,743,613 and 11,535,233. The 1,125 µg exterior water on the following daily cuts comes from the scheduled next pulse. The last complete cuts are days 621 and 603, with 19,924,583 and 19,981,658 canonical facts and 59 living workers in each. On those dates there are 13,636 and 13,530 worker displacements, including 5 and 4 rest relocations respectively. The volume of committed steps greatly exceeds the count of the new rest action in these late resource-pressure runs. Individual activity summaries for these two trials are missing beyond their daily aggregates. The stopped histories leave the day-730 worker counts unobserved.

The four paired 90-day witnesses retain complete canonical histories. Long trials retain compact daily and death records, individual movement and program-time summaries for completed trials, and canonical prefix SHA-256 at the horizons of completed trials. The daily and death records survive host-limit stops. Rerunning the declared native input regenerates the history up to the same host limit. The diagnostic executable was built before the final checkpoint provenance check for R0; the panel consumes live frames and performs no restore. The paired archive and restore tests use the final check.

## Size, performance and compatibility

- The four 90-day ZIP witnesses occupy about 6 MB. Midpoint SQLite replays produced byte-identical `parameters.txt`, `initial.chk`, `final.frame`, `facts.bin`, `cuts.csv`, `individuals.csv` and `geometry_edits.csv` for both R0 layouts. Local restore timings were 50.82 and 45.48 ms. The reference shaft canonical digest matches the accepted physics 29 M0 witness.
- Windows native scenario advance costs for the shaft were 278 and 785 ms (29, 32), with peak process RSS about 39.5 and 41.2 MB. In the dogleg they were 509 and 1,174 ms (about 39.4 and 39.1 MB peak RSS). These are diagnostic wall times, with ordinary host load and distinct legitimate event counts. They do not satisfy the conditions of the existing controlled qualification.
- Two earlier attempts stopped at 4 million and 10 million facts. Long diagnostics then reused the native lossless event block codec in RAM. An immutable prefix is published after at least 65,536 pending facts; subsequent demand-driven reads decode the exact bytes. For example, 13,470,407 facts in the first continued R0 run require about 214 MB of encoded prefix at day 730, plus the hot suffix. The paired reference stores about 53 MB of encoded prefix. There is no video frame or interpolation record in a native journal. The app-specific lab host limit is 20 million facts. Ordinary live mode uses the established manual save flow and the normal host limit.
- The 730-day first continued pair took approximately 27.8 versus 358 s to observe on Windows, including application frame capture and streaming projection. Sum of the timed advance/publish calls was about 12 versus 297 s. Long growth drives dense, expensive worker/geometry histories; this large operating cost remains an R0 limitation. This assay keeps a single native trial rolling and writes compact receipts, avoiding repeated full on-disk histories.

## Engineering verification

Windows Release passed all 290 CTests. The native `M0_BROOD_SPACE` test also passed with ASan and UBSan in a Windows Debug build. All 22 Python tests passed together in a local run with the native legacy SQLite fixture enabled. The real browser replay used the published witnesses and recorded canonical event IDs, the tracked actor and elapsed timings. The first warm-index world view took about 1.72 s on the test host. [Browser receipt](../../experiments/r0/browser/browser-receipt.json).

Core Release jobs reproduced the actual R0 archives through SQLite on Windows and Linux. Browser CI passed after the legacy catalogue expectation was updated to include the four R0 archives. [Core workflow](https://github.com/Aquaticfuller/AntWorld/actions/runs/43689829401), [OP0 workflow](https://github.com/Aquaticfuller/AntWorld/actions/runs/43689829394).

## Reproduce

With the repository's Windows CMake and compiler setup, build `antworld_m0_live`, `antworld_m0_tests` and `antworld_s6_4_wp6b`. The same commands work with the corresponding extensionless CMake outputs on Linux.

```powershell
python -B tools/build_m0_live.py
python -B -m tools.run_r0_diagnostics out/r0-long-reproduction
python -B -m tools.run_r0_diagnostics out/r0-sealed-reproduction --supplies blocked --days 90
python -B tools/run_m0.py build/m0-live/antworld_s6_4_wp6b.exe out/r0-paired-reproduction --r0
python -B tools/run_m0.py build/m0-live/antworld_s6_4_wp6b.exe out/r0-durable-reproduction --r0 --durable --case r0-shaft-candidate --case r0-dogleg-candidate
python -B tools/verify_r0.py experiments/r0/witnesses --replay out/r0-durable-reproduction
ctest --test-dir build/m0-live -C Release --output-on-failure
python -B -m unittest discover -s op0/tests -v
.\tools\start_m0.cmd --r0 --replay
```

The long daily, death and worker exposures are gzip-compressed CSV. The JSON lines carry seed, input treatment, time, ledger checks and actual canonical hashes. The recorded interval from adulthood to death or censoring closes the task time denominators. Open paid bouts are excluded until matched by a committed stop. Unknown travel durations have their own count. Units are milliseconds, meters, cubic millimeters, micrograms and nanojoules. Reports identify engineering cases with seeded adults separately from the lifecycle witnesses.
