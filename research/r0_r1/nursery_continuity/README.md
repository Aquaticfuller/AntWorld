# Nursery continuity and live rendering

Restart the Windows observation service from the AntWorld checkout.

```powershell
.\tools\start_m0.cmd --port 8774
```

Open **Live colony**, select **Nursery with food**, and click **Watch the nursery**. The scene starts at 1×. **Find first delivery** pauses on the actual delivery and selects its worker. The **Surface** view shows the finite source. The **Underground** view shows the depot and its live stock. There are four larvae, ten initialized workers, and a queen in this assay. **Previous nursery** opens the original physics 34 fixture. **R0-r1 reference** opens physics 33.

## Reproduction and diagnosis

The previous result covered 120 seconds. Extending the same seed and input to one hour reproduced the reported stall. Between minutes 10 and 60, ten workers stayed in the Nurse program and produced 7,500 periodic decisions. There was no completed care or worker displacement. The fixture checked autonomy every four seconds. Its scheduled nutrition action came from the inherited six-hour physiology profile. Holding the Nurse program on continued local demand could leave a worker waiting for that first action. The program label remained visible after the actual care had ended.

The one-factor control keeps geometry, stock, physiology and physics 34. It changes only the nutrition action review from six hours to four seconds. Seed 17 changes from zero exchanges to 32 positive exchanges during the hour. It still has no movement after minute 10. The earlier 120-second receipt and the extended control have separate scopes.

An initial food-supply prototype uncovered another blockage. A worker collected food and started its real connector return. An adult occupying the depot approach blocked the larger loaded envelope. The attempted trip recorded one collection and zero deliveries by 600 seconds. A one-millisecond excavation retry also accumulated over 1.67 million facts by that cut and exceeded the host budget before the 1,200-second cut. Those development outcomes were rejected.

## Provisioned fixture and compatible state

Physics 35 opts into two local decisions. A worker in contact with the depot can respond to low carbohydrate stock through the usual foraging choice. A stationary worker blocking the next local segment of a visible, loaded, waiting returner can move aside if body clearance and floor support permit. Existing actions retain their leases. The side step has a paid Core motion interval and an identified carrier. Checkpoint schema 28 stores the two opt-in flags. Earlier scenarios preserve their physics numbers and configuration. The restore verifier now also accepts a Nurse transition backed by a successful, matching local encounter.

The preview has a side depot physically separated from the queen, a finite food patch on the surface, an initial worker with lower reserves, four-second nutrition reviews, a one-minute absorption cycle for workers and larvae, and a 1.5-second blocked excavation retry. These are `ENGINEERING_FIXTURE` settings. Geometry, resources and energy stay under normal Core transactions. Motion and inactivity have been observed in flat-nest groups of *Lasius niger*. The study supplies no calibration of these model timing or right-of-way rules. [Oh and Cremer, experimental study and discussion](https://doi.org/10.1111/2041-210X.70277).

| Treatment | Seed | Worker moves after minute 10 | Positive exchanges in 60 min | Collection / deliveries in 60 min |
| --- | ---: | ---: | ---: | ---: |
| Previous nursery | 17 | 0 | 0 | 0 / 0 |
| Nutrition cadence only | 17 | 0 | 32 | 0 / 0 |
| Provisioned | 17 | 971 | 30 | 1 / 1 |
| Provisioned | 29 | 4 | 20 | 2 / 2 |
| Provisioned | 41 | 1 | 17 | 1 / 1 |

The default seed recorded 287 moves between minutes 45 and 60. The other two provisioned seeds recorded no movement after minute 20. The active traffic regression uses seed 41, with four completed yielding acts and an actual return. All three unprovisioned controls recorded zero collection and delivery. Twenty to thirty late minutes in this small fixture do not establish colony-wide task diversity, realistic resting durations, or natural founding. [Complete one-hour windows and state hashes](assay.json).

## Live display and verification

The browser draws on its animation clock from a rolling, read-only window of native cuts. At 1× the nursery uses a 240 ms display buffer. Confirmed timed movements between cuts are also eligible for display. Missing journal coverage or an edit to the terrain cannot create a new route. The renderer stops at the latest known Core time. Pause and milestone seeking use the exact Core cut. Completed action badges in the nursery expire and the individual panel distinguishes the program from an action in progress.

Windows Release ran the native `R0_R1_NEST_DYNAMICS` target, including a SQLite save during a yielding action, byte-exact continuation, ordinary collision cases and a late-movement check. All eight native live Python tests passed, including the ordinary day-90 golden checkpoint and physics 34 restoration. The JavaScript projection checks covered between-cut motion, interrupted paths, unavailable history, edit invalidation, and pause. The local Chrome test measured two different correctly placed poses while the server remained on the same cut and froze at the committed 4,000 microgram delivery at 207,962 simulated ms. [Browser receipt](browser.json).

## Reproduce with limited local output

```powershell
python -B -m tools.run_nursery_continuity out/nursery-continuity.json
node op0/tests/live_motion.mjs
```

The assay advances the native Core in memory and writes one compact result file. It records three seeds in each of four conditions. The existing live builder installs one executable for this revision. Live rendering uses bounded memory and creates no per-frame event or disk record.
