# M0 MicroWorld results

M0 is a working `ENGINEERING_ONLY` preview for a single founding colony under protected conditions. It includes the native opt-in spatial behavior, a 90-day autonomous fixture and read-only observation in OP0. This result preserves B06 `INSUFFICIENT`, the nine `BIOLOGICAL_BLOCKED` roots and the historical application `FAIL`.

## Implementation and recorded behavior

The 31 cm square arena has a 30 × 30 × 15 cm parametric soil envelope, with a fine founding pocket and a 10 mm surface grid. The seed files describe a shaft or a bent connector. A world starts with one reproductive queen and zero brood and workers. No commands place ants after initialization. External food comes from finite initialized stock and scheduled releases from an accounted reservoir. The local water control also has a finite, debited source.

Physics 27 adds a common brood exclusion envelope and occupied local layer. Reproduction proposes a supported position from a bounded mask and checks material clearance and live brood. Clutch adjacency uses local distance and clear segments. If the layer is full, the attempt is recorded as `Capacity`, with no egg, maternal debit or new identity. A nutrient failure is `Depleted`. An actual care bout may change a juvenile's position, with clearance and occupancy rechecked at execution. There is no separate layer of visual offsets. Where a free choice exists, arrangement favors a short improvement to local clustering. A newly emerged worker in contact range of the depot returns by the measured care movement path before depot-owned jobs become eligible.

Schema 23 identifies physics 27 and the development-only hatch-cue suppression contrast (physics 28). Physics 24–26 retains the old header, coordinates and model meaning. The canonical fact record length is unchanged. Recovery re-evaluates the placement result using the geometry and occupancy at the historical cut and checks maternal cost from physiological replay. Old control worlds still replay through the existing decoder. The introduction of a distinct outcome for deferred laying is restricted to the opt-in worlds.

## Frozen simulation panel

The panel contains 28 complete 90-day cases, totaling 2,163,510 committed facts. Four initial H2-off configurations were correctly rejected because they also disabled a dependency of the provisioning profile. The run receipts retain these failures. The corrected contrast suppresses just the hatch cue, uses the same parameter roster and distinct physics 28, and leaves lipid mobilization, provisioning and death policies in force. Main paired cases use the locked inputs from [the protocol](FROZEN_PROTOCOL.md); see `experiments/m0/evidence` for the original and retry manifests and analysis.

| Balanced matched panel, 8 worlds per version | Physics 25 | Physics 27 |
| --- | ---: | ---: |
| First 24 hours of laying, eggs | 96 | 96 |
| First cohort hatched | 96 | 96 |
| First cohort without observed maternal ration | 86 | 84 |
| First cohort dead from energy depletion | 86 | 84 |
| First cohort dead from dehydration | 2 | 0 |
| First cohort pupated and eclosed | 8 | 12 |
| All timed brood arrangements | 0 | 92 |
| All verified exterior-to-nest food deliveries | 208 | 149 |
| All verified excavation-to-drop chains | 143 | 138 |

All four Borisovka pairs had one eclosion in the first 24-hour egg cohort in both variants. All four St. Petersburg pairs went from one to two. No pair reached the preregistered regression flag. This compares the placement rule, the consequences of finite space, and the short return from the brood patch as a bundle. Higher eclosion counts did not imply more work. Exterior deliveries were lower across the balanced slot panel. The eight paired simulated worlds cannot establish biological noninferiority or treatment effects in field colonies.

The first cohort follows the first 24 hours of actual egg births, including deaths and individuals still in the archive at day 90. OP0's original comparison also retains its distinct first recorded living larval census. Open the raw traces for the mother, hatch, contact, feeding selection, start, actual dose, absorption, death and developmental endpoints. Daily physiology cuts and actual transfer facts have their own timestamps. The final cut censors individuals still alive. Maternal protein payments and larval tissue assimilation are separate. The table does not attribute a crop uptake to a donor where mixed material is possible.

In the shaft demonstration, the first worker is #4. Actual stage changes occur at days 20.7, 30.9 and 45.4 after laying on day 4. Five maternal rations account for 65 µg of protein absorbed and 100 µg of water absorbed. The other 11 first-cohort larvae were recorded dying of energy depletion. In the dogleg demonstration two first-cohort workers eclose at days 44.15 and about 44.48 and ten larvae die of energy depletion. All these endpoints describe simulations. They are not estimates of natural mortality.

Both sampled H2/R1-off and single-factor-off combinations had zero first-cohort eclosions across the two affected seeds. H2-off/R1-on produced later work, including 28 complete delivery chains across its two worlds. The no-care arm had zero first-cohort eclosions. The wet arm withdrew 1,200 µg in 55 actual sips and did not produce more first-cohort workers in its one matched run. The sealed and absent arms both had an early eclosion, zero exterior delivery, a dead queen and zero workers at day 90. The no-protein demonstration retained six adult workers at day 90, compared with 15 in the balanced shaft. The dry and wet arms do not match a B06 wet-cotton assay. The remaining causes of sparse first-feeding coverage need a paired experiment with actual local food solicitation and independently recorded doses.

## Worker observation and UI

The two balanced demonstrations produce 19 and 21 exterior-to-nest delivery chains and 13 and 14 excavation/drop chains, respectively. Delivery counts require a committed surface move and a positive collection by the same worker before it delivers underground. Soil counts match excavator and parcel through physical placement. Both archives also contain 370 trophallaxis events and several real brood displacements. The first three workers in each archive have individual one- and four-day traces. For example, worker #4 in the shaft logs 111.06 mm of committed movement in its first day, with 33.116 s of timed movement and 93.116 s of paid work. These are three distinct observations. Program residence is tracked separately from movement, handling and energy-cost intervals.

The OP0 browser supports a nest-centered horizontal view, side sections, actual action boundaries, slow delivery replay, individual histories and one- or three-day time and physiology panels. The user can compare the published shaft against the reference rule and switch between English and Simplified Chinese. Physiology samples may be older than the selected event and display the sample date. Timed care playback holds the recorded positions until the next committed boundary. The browser does not fill unknown motion with synthetic paths. See the [Windows guide](README.md) and screenshots in `experiments/m0/evidence/browser`.

## Recovery, reproducibility and costs

- The Windows recovery runs saved and loaded at day 45 and continued through day 90 with the same authority, then exactly matched each published balanced world's `initial.chk`, `final.frame`, `facts.bin`, daily physiology cuts, geometry edits and input text. No timing bytes are compared as state. The two local SQLite recoveries took about 50 and 52 ms on this host. Matching raw fact SHA-256s are `a4246ada6e183c27a2ac32bb7eea3b1d1754e7310d35813b5c1989851f5bb3b8` and `6d1939ab25c2bbdf1a5a90485b2046e4e01c0d61c65fa43732ca21dc690168dc`.
- The native test covers true phases of laying, collision, a filled layer, a vacated slot, no debit on spatial refusal, resource conservation, failed-transaction rollback and independent time partitions after SQLite restore. The OP0 tests compare native positions with a separate fixed-offset canonical fact reader and check intervals, queries and archive immutability. The same headless fixture and browser journeys run in CI.
- Windows Release CTest passed 290/290. The Debug parallel pass timed out at the existing 180-second limit in two long inherited tests; 288 passed in that run. Both timed-out tests passed when rerun serially at the original limits (129.26 s and 44.79 s). The targeted M0 Windows ASan/UBSan check passed. Both Debug logs and the sanitizer receipt are retained. The OP0 suite passed 15 tests with one optional native SQLite v1 test skipped, then the native SQLite v1 test passed against a locally built fixture writer. Windows PowerShell opened the MicroWorld terminal and reached the verified final cut. GitHub also runs the inherited Windows/Linux and full sanitizer checks.
- The 28 final archives occupy about 30 MiB compressed. The five shipped examples occupy about 6.3 MiB. Native peak RSS peaked at about 70 MiB across the formal world runs. This is an observed small-fixture cost, not the historical controlled application qualification. The first and warm index measurements and Chrome timings are in the evidence directory. Build artifacts and browse indexes are disposable.
- One fresh shaft index used about 8.9 MiB and opened in 603 ms. A warm reopen of that index took 0.48 ms; the day-45 state query took 28 ms. The local browser completed both journeys. The initially recorded browser launch took about 355 ms to show the world. The final journey, with default scene playback verified, recorded about 73.7 s to the first world view, including a 72.5 s first-contentful-paint entry. Both measurements remain visible. This small diagnostic sample does not identify the browser delay or provide a latency guarantee.

```powershell
.\tools\build_windows.ps1 -Configuration Release -BuildDirectory build/m0-release
py -B tools/run_m0.py build/m0-release/antworld_s6_4_wp6b.exe out/m0-worlds
py -B tools/analyze_m0.py out/m0-worlds out/m0-analysis --cache out/m0-analysis-cache --worker-windows borisovka-shaft-1-slots --worker-windows st_petersburg-dogleg-1-slots
py -B tools/run_m0.py build/m0-release/antworld_s6_4_wp6b.exe out/m0-recovery --durable --case borisovka-shaft-1-slots --case st_petersburg-dogleg-1-slots
py -B tools/verify_m0.py experiments/m0/demo --replay out/m0-recovery
ctest --test-dir build/m0-release --output-on-failure
py -B -m unittest discover -s op0/tests -v
```

All production physiology and task weights are inherited. Layered packing, real queen and worker body shapes, age-driven activity, wider 3D route discovery, wet-substrate physics and temperature or humidity effects remain outside this preview. For the correspondence between source studies and fixture choices see [scientific evidence](SCIENTIFIC_EVIDENCE.md). The next research priority is to explain and independently measure first larval feeding and starvation while retaining the verified local space and individual identities.
