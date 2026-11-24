# Sealed Single-Nest Preview

## Open the protected founding nest

For a fresh Windows checkout, the build requires Python 3.13 or later,
CMake 3.24 or later and a C++20 compiler. The build script also recognizes
the workspace's portable Clang, CMake and Ninja tools when present.

From Windows PowerShell at the repository root:

~~~powershell
git fetch origin codex/single-nest-exit-and-oral-access
git switch codex/single-nest-exit-and-oral-access
git pull --ff-only
py -3 -B -m tools.build_m0_live --jobs 4
.\tools\start_m0.cmd
~~~

With the standalone Python installer and no `py` launcher, use
`& "$env:LOCALAPPDATA\Python\bin\python.exe" -B -m tools.build_m0_live --jobs 4`.
The batch entry point works with the normal PowerShell script policy.
The observer opens locally at `http://127.0.0.1:8765/`.

Select **New sealed nest** to start a Physics 48 colony with a nearby feeder.
For a death investigation choose **Next occurrence** with a larval or worker
death target, then inspect the stopped individual's body, crop, available wick
and mixed nest stock. The resource panel locates deposited soil above and
below ground. In **Colony setup**, **New worker hydration trial · Physics 50**
uses paid larval provisioning for a larger water reserve at emergence.
**Brood-site wick trial** moves the same finite water source in Physics 48.
The [paired two-year results](PROTECTED_HABITAT_RESULTS.md) distinguish
first-brood survival, sustained reproduction and late orphan workers.

To follow a digger's first liquid meal, choose **Worked exit and mouth alignment · Physics 63**,
a nearby feeder, a wet wick and seed 17 or 29. Advance to soil placement, then to food collection.
For the founder and a donor approaching each other on separate occasions, use seed 2.
The [worked-exit results](WORKED_EXIT_RESULTS.md) list the paid events and the 730-day outcomes.

For the earlier first external meal, open **Colony setup**, choose **First forage and nest
feeding · Physics 62**, select the nearby feeder and wet wick, enter seed 1
and start a sealed nest. Follow worker 10 opening the nest and worker 8
collecting food. Founder 2 and worker 8 both approach before the worker's
crop pays the founder. Seed 2 includes a founder death despite sugar in
nearby workers. The [first-meal report](FIRST_MEAL_RESULTS.md) gives the
input settings, exact event IDs and two-year comparison.

For an identified feeder-to-mouth replay, select **Chamber food sharing · Physics 54**,
nearby feeder, wet wick and seed 2. The oral receipts and the subsequent
starvation episode can be inspected in the same live world.
[Paired two-year food sharing results](SOCIAL_CROP_RESULTS.md)

Choose **Colony setup → Sealed nest model → Variable conditions · Physics 45**
before selecting **New sealed nest** to try the seeded activity rhythm, the
feeding patch and the four external sources. The same setup supplies the
temperature, humidity, trail reference time, ventilation and substrate.
**Extended supply · 730 days** extends the finite release reserve. See
[the experiment and survival results](VARIABLE_CONDITIONS.md).
The [colony life-cycle reference](COLONY_LIFECYCLE_REFERENCE.md) compares
the preview with measured founding, overwintering and mature colony counts.

1. Select **New sealed nest** for Physics 48. The starting view contains one queen in one rounded, sealed pocket. The default is seed 3, a finite 1.5 mL water wick and exterior supply budgeted through day 730. **Colony setup** can reproduce the anatomical Physics 39 world with seed 3, the small wick and finite supply. The separate Physics 49 treatment tests local excavation in smaller bites. The nearby surface feeder moves the food without changing the resource budget. [Founding and delivery measurements](PROTECTED_HABITAT_RESULTS.md)
2. Keep **1× real time** for close observation. Use **Next occurrence** on
   the target menu to reach an egg, brood movement, the first worker,
   excavation or food delivery. The simulation pauses at the committed event.
   Use **Configure event group** to select and save several targets. The
   browser remembers the group across reloads. Each click on **Fast-forward to
   next in group** immediately searches for the next matching event, pauses
   the clock and opens its details. Use **Resume** to observe at 1×.
3. Drag to rotate the view and scroll to zoom. **Cut depth** reveals a
   horizontal layer. **Underground** and **Surface** provide the section
   and ground views. Select an individual and use **Follow**. **Research**
   exposes the section, body and stock controls.
4. **Save and load** defaults to a compact continuation. A full SQLite
   archive is an explicit choice while the history prefix is present.
   **Reference model** creates the earlier Physics 38 comparison.

## Watch food reach the queen

To watch a real obstructed delivery, choose **Wall-side food delivery · Physics 43**, software seed **2**, and **Finite food and water**. Open a new sealed nest. Set the event selector to **Worker unloads from a wall** and use **Next occurrence**. Worker 13 completes its first wall delivery on day 106. The event card shows what it added to the nest and the exact fact number. Compact saving is still the default. **Return to a familiar berth · Physics 44** exposes the follow-up comparison. Its late same-worker activity criterion failed. [Measured outcomes and failures](FOUNDER_ACCESS_RESULTS.md)

In **Colony setup**, select **Worker food offers · Physics 41**, **Finite food and water** and software seed **3**. Select **New sealed nest**. In the event menu select **Worker feeds the queen** and **Next occurrence**. The scene pauses at a water transfer. Select **Next occurrence** again to see worker #23 transfer carbohydrate and water to queen #2. Select **Queen absorbs carbohydrate** and **Next occurrence** to follow the queen until the next positive absorption. Each stop shows the committed timestamp, individuals and amounts. **Resume** runs at 1×. The individual's life panel includes crop carbohydrate, body energy, water, lipid and mobilizable protein at the displayed sampling time.

**Food access experiment · Physics 40** plays the comparison with anatomical access to nest stores. In seed 3, select **Food delivered**, **Queen eats from nest stores** and **Queen absorbs carbohydrate** in that order. The three events have separate IDs. The ordinary new-nest choice remains Physics 39. Saved worlds retain their own model version. An absent resource feeder and software seeds 1 and 2 are available from the same controls. See [the paired worlds, failure diagnoses and evidence](FOUNDER_ACCESS_RESULTS.md).

At a paused oral exchange, the filled gold point marks the donor's mouth and the green ring marks the recipient's mouth. For depot transactions the ring marks the storage point. The distance uses the simulation's 3D coordinates and stays the same when you rotate the view. Resume at 1× to release the markers and follow the selected individual. [Actual exchange](evidence/founder-access/oral-contact-zh.webp)

See [the anatomical model and assay](OVERHAUL.md) and the
[review results](OVERHAUL_RESULTS.md). The following sections record the
history and results of the earlier preview.

## Reference preview launch

From Windows PowerShell at the repository root, build the native executable and open the viewer.

~~~powershell
py -3 -B -m tools.build_m0_live --jobs 4
.\tools\start_m0.cmd
~~~

If Python is installed without the `py` launcher, run `python -B -m tools.build_m0_live --jobs 4`. The launcher works without a PowerShell execution-policy change. The live host uses loopback only. Use `--port 8770` to open a separate window while an older session occupies port 8765.

1. Choose **New sealed nest**. Use **Colony setup** to set the software seed before creating a colony. The default is seed 2.
2. Choose **Egg laid**, **Brood moved** or **Brood cleaned** under **Target event**. Choose **Fast-forward to next** to stop at the next committed occurrence. **Resume** returns to 1×.
3. Try **Worker emergence**, **Excavation** and **Food delivered** in order. The same native world advances, with no seeded workers.
4. Use **3D nest**, **Surface** and **Underground** to change the view. Select a body or enter its Ant ID to inspect it. Rotate by dragging in 3D and use Shift-drag to pan. The language picker switches between English and Simplified Chinese.
5. Choose **Save and load**, enter a name and save. The default is **Compact save**. **Open save folder** opens the containing folder. Loading a save resumes paused at the saved state. Select **Full replay archive** to keep a replayable SQLite file when the whole fact stream is available.

## Physics and evidence

Physics 38 and ecological schema 31 identify the opt-in layout. It starts with one enclosed 12 × 7 mm founding chamber and one reproductive queen. A brood area and a handoff position are located within the same chamber. The initial bed and the ordered excavation edits remain authoritative. The local soil quantum is 0.25 mm, with a 0.125 mm search increment for deposition behind the queen. A common 0.75 mm brood envelope reserves room for subsequent stages. These dimensions, reach distances, gait timing, placement policy and reserves are ENGINEERING_FIXTURE values.

An egg is deposited near the current foundress position, in the posterior sector of the laying model. Deposition checks floor support, geometry and nearby brood occupancy. Finite capacity can defer an attempt without payment. A queen or worker can approach, pick up, transport and place a brood individual through the existing timed care transaction. The carrier and held individual both need a clear route to a locally available placement. Inspection, cleaning and feeding use a shorter 1.25 mm handling reach. Larval access to a real maternal ration can take precedence over relocation. A cue at hatch requires a local, unblocked observation. The model retains physiological payments, competing deaths and failures to place or reach a target.

Workers seeking external food can find a reachable soil cap and physically excavate it after emergence. Their first viable entrance route follows the actual resulting geometry. The renderer shows loose soil from deposited parcels with remaining mass. Visual motion uses the native event clock. A brood displacement shares a carrier clock only when both moves belong to the same committing action. Adult glyphs are scaled by caste for readability. The optional body-envelope overlay shows the current collision proxy.

A returning loaded worker can hand off at a clear floor position already inside the local depot contact radius when another body obstructs the next route segment. The scheduled delivery and resource debit still use the ordinary transaction. The worker retains the remaining route from the occupied berth. In seed 2, a pre-change worker held 4,000 µg of water within 0.8 mm of the depot and repeated no-legal-step decisions. The paired run produced 10 deliveries by day 150 before the change and 21 after it, with eight workers alive at day 150 after the change.

Local unloaded worker steps can use a wall or the underside of a roof when the body sweep is clear and the same adjacent support face is present along the segment. This is a limited attachment model with axis-aligned envelopes. A whole-colony ceiling route, calibrated attachment forces and body rotation against a surface remain unverified.

Direct black garden ant studies support claustral founding, active maternal care, and retrieval by queens and workers under the studied conditions. The preview adopts that qualitative scope and uses explicit engineering values for the rest. [Colony co-founding in ants is an active process by queens](https://pmc.ncbi.nlm.nih.gov/articles/PMC7419493/), [Ontogeny of superorganisms](https://doi.org/10.1111/1365-2435.14536), [Queen and worker brood retrieval](https://doi.org/10.1002/ece3.4475).

## Test sustained supply

The **Local water and repeat foraging · Physics 47** option under **Colony
setup** opens a separate model for testing sustained supply. Select **Extended
supply · 730 days** and **Protected wick · 1.5 mL of water** to reproduce the
paired experiment. The smaller wick remains available as a water-limited
condition. The water is an explicit finite inventory and needs mouth contact
before it can enter a crop. Existing worlds retain their original physics.
The [paired lifecycle results](SUSTAINED_FOUNDING_RESULTS.md) give the
matched seeds, resource balances and 730-day observations.

## Compact continuation

`AWRESUM1` stores the current authoritative state, including the queue, RNG, identities, reserves, custody, geometry and local recruitment memory. Up to 2,048 existing canonical facts are retained in the default file. Event IDs stay absolute and the omitted prefix is declared. The native reader checks the checksum and validates state and the retained fact window before installing it. A compact continuation can advance with the same future canonical facts. Earlier history and its full replay audit require the original archive.

In the browser the **Next** action remains available after a compact restore. **First** is disabled when an older prefix is missing. Full SQLite saves and archive replay use the original formats. Compact files can still grow with actual world state, such as more ant identities, pieces of excavated terrain or active resources. The preview writes a persistent file on explicit save, using an atomic replacement in the save directory. The live session can still retain a fuller history in memory.

## Verify locally

~~~powershell
py -3 -B -m unittest op0.tests.test_live
py -3 -B -m tools.test_m1_browser --mode m2 --browser 'C:\Program Files\Google\Chrome\Application\chrome.exe' --output out/m2-preview
~~~

The native integration tests check the single enclosed initial space, posterior deposition, paid maternal transport, worker emergence followed by excavation, soil deposition and food delivery. The continuation test compares an uninterrupted checkpoint frame and every newly committed fact over the same subsequent interval. It also verifies full archive loading, the bounded window, rejection of an altered snapshot and preservation of the active world on failed load.

## Observed cases

Windows Release, seeded native worlds at 25 °C and 80% relative humidity. Worker counts are living adults. The finite arm has separate external food and water inventories. The absent arm retains the same founding queen and her sheltered water site. Seeds are simulation inputs.

| Seed | External supply | Workers at day 60 | Workers at day 90 | Queen at day 150 | Workers at day 150 | Committed facts at day 150 | Eclosed / excavated / delivered |
| --- | --- | ---: | ---: | --- | ---: | ---: | --- |
| 1 | Finite | 1 | 5 | Dead | 6 | 2,331,713 | Yes / Yes / Yes |
| 2 | Finite | 1 | 4 | Dead | 8 | 940,999 | Yes / Yes / Yes |
| 3 | Finite | 3 | 3 | Dead | 7 | 1,193,123 | Yes / Yes / Yes |
| 2 | Absent | 0 | 1 | Dead | 0 | 286,994 | Yes / Yes / No |

The 150-day cases ran in memory with no world archive writes. The Chrome acceptance path used seed 2 and committed events for laying, brood movement, emergence, excavation and delivery. Its compact save at the first delivery was approximately 370 KiB. The stock and worker gains leave maternal survival and continuous late supply unresolved.

The preview is ENGINEERING_ONLY. The B06 INSUFFICIENT result, nine BIOLOGICAL_BLOCKED findings and historical application performance FAIL remain in force.


## Experience-overhaul review branch

The independent experience revision is based on physics 38 without changing its simulation rules. The new optional `experience.css` and `experience.js` provide a calmer, larger local observatory and a focus mode for the existing native C++ world. The 2D/3D adult glyphs now use **illustrative** caste lengths instead of pretending the shared collision cube is an anatomical body. This is a visualization correction, **not** a physical-morphology fix.

From a full repository checkout on Windows:

~~~powershell
git fetch origin codex/single-nest-experience-overhaul
git switch --track origin/codex/single-nest-experience-overhaul
py -3 -B -m tools.build_m0_live --jobs 4
.\tools\start_m0.cmd
~~~

Choose the reference model and select **New sealed nest**. Once the world is visible, press `F` or select **Focus on colony** to expand the scene. Press `Esc` to restore the analytic panels. Compact state snapshots are the default and the save dialog offers full replay archives.

See [the physical and biological realism review](REALISM_REFOUNDATION.md) for the uncorrected queen/worker collision geometry, head-contact care, deterministic brood-site lattice, wall/ceiling transitions, spoil morphology and biological validation. Do **not** classify those issues as closed merely because the viewing layout has improved.
