# Single-nest preview review

## Decision

Physics 39 is a playable engineering preview. The closed-pocket sequence from egg to workers, excavation and a positive resource delivery occurred in all three finite-supply simulation seeds. The wider stage remains open because none of those colonies retained a living worker through day 150. This is an early-life result for a protected laboratory fixture. The independent biological status and historical B06 and performance findings are outside this result.

## Native results

The [assay definition and commands](OVERHAUL.md) record the initial conditions, stopping points and evidence window. The [Physics 39 receipt](evidence/anatomical.json) contains actual initial and final cut hashes, the seed geometry, material ledger, resident and packed event sizes, sampled stocks, and the first four brood trajectories through the scan limit. The [Physics 38 receipt](evidence/reference.json) retains the matched older treatment from the preceding build. The two receipts identify their binaries separately. Running without `--model` repeats both arms with the current binary.

| Physics | Seed | Supply | Eclosions by day 60 | Cleaning / placements by day 60 | Deliveries by day 60 | Living workers day 60 / 150 | Queen death, day and cause |
| ---: | ---: | --- | ---: | --- | ---: | ---: | --- |
| 38 | 1 | Finite | 1 | 0 / 1 | 8 | 1 / 6 | 95.51, energy |
| 38 | 2 | Finite | 1 | 0 / 1 | 8 | 1 / 8 | 99.82, energy |
| 38 | 3 | Finite | 3 | 0 / 0 | 6 | 3 / 7 | 82.81, energy |
| 38 | 2 | Absent | 1 | 0 / 1 | 0 | 0 / 0 | 76.25, energy |
| 39 | 1 | Finite | 6 | 23 / 0 | 1 | 1 / 0 | 69.67, dehydration |
| 39 | 2 | Finite | 3 | 15 / 7 | 1 | 0 / 0 | 70.09, energy |
| 39 | 3 | Finite | 7 | 20 / 5 | 1 | 1 / 0 | 69.11, energy |
| 39 | 2 | Absent | 3 | 15 / 7 | 0 | 0 / 0 | 70.11, energy |

Each Physics 39 world removed 256 terrain quanta and deposited the same parcel through actual transport. The resulting spoil volume was 4 mm³. On seed 3, the first excavation was at day 50.86. Worker #21 delivered 1,333 µg carbohydrate, 667 µg protein and 2,000 µg water at 4,731,382,227 ms. The browser screenshot records that actual delivery. The other two finite seeds delivered at days 48.60 and 48.01. The absent arm opened the pocket and recorded zero deliveries.

The recorded founder brood-food rations by day 60 were 65, 57 and 76 in the finite seeds. Eclosions were followed by substantial loss. The first four individuals and their paid transfers are available in the receipts. Cleaning is a timed contact behavior without a new growth or survival bonus. Seed 1 never completed a brood placement in the recorded interval. Seeds 2 and 3 completed pickup, movement and placement of the same offspring. The development trials exposed repeated unreachable transport, a support loss at the lip of a freshly opened shaft, and excessive retries after a body turned beside a wall. The final implementation checks a local berth before lifting, replans with body clearance, and keeps short-range attachment available at the lip. The custody interruption path releases the reservation before lowering a live brood item.

## Limits indicated by the experiment

The finite arm failed sustained colony operation. The founders accumulated zero oxidized carbohydrate in these four Physics 39 runs. At death, the seed 1 founder had zero body water and 365,792,628 nJ of energy. Seeds 2 and 3 had 420 and 719 µg body water and exhausted their energy. Each finite case retained positive depot food or water at day 150. This locates a failure between resource delivery and maternal use. A stock entry alone leaves the local approach, timing of access, crop filling and absorption unresolved. The next assay should separate these gates with matched depot contact, ration accessibility and time-to-absorption endpoints.

Spatial behavior near the day-zero pocket is demonstrable. Terrain-controlled climbing has a wall-to-ceiling clearance fixture and the complete seeded colonies commit shaft ascents and descents. Continuous six-leg contacts, performance under crowded ceiling traffic, arbitrary chamber expansion and food handling with deformable cargo remain out of scope for this qualification. A deposited parcel is shown at the nearest supporting plane under the committed drop location. Only a fill edit makes it collidable geometry. The 3D view supports a horizontal cut and the analytic view offers the three orthogonal directions. The underlying gross emergence constraint and body contacts are engineering hypotheses.

The three finite seeds each exercised actual digging, material accounting, collection and delivery. They do not estimate a species founding probability. Independent survival and excavation records are still needed. The original B06 `INSUFFICIENT`, historical application performance `FAIL`, and nine `BIOLOGICAL_BLOCKED` conclusions remain.

## Evidence and reproducibility

- [Chrome browser receipt](evidence/browser.json), [Chinese brood view](evidence/brood-zh.png), and [first delivery view](evidence/delivery-en.png). The observer uses native events and body poses. The session starts with one queen, seeks actual events, switches language, saves and restores.
- Windows Release headless timing is an elapsed-time observation. The Physics 39 finite arms took approximately 0.6, 7.0 and 58.1 seconds of simulated advance in this run, with a measured peak working set of 12.0–13.1 MiB. The host also ran builds and tests. Differences in survival, routing, activity and event counts make these figures unsuitable for an efficiency claim against Physics 38.
- The tests include a compact cut during brood custody and a late save after actual delivery. The late case reopens both SQLite and a 2,048-event compact continuation and checks the next day's frame against the uninterrupted run. The native audit reconstructs footprint legality before eclosion. The resume path bounds recent-action scans at the declared history floor.
- Launch and reproduction commands appear in the [Windows instructions](README.md) and [assay protocol](OVERHAUL.md). Asset hashes and platform observations are in the adjacent [verification receipt](evidence/verification.md).
