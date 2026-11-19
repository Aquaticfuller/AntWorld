# AntWorld — Single Nest Realism Refoundation

**Baseline:** `codex/single-nest-preview` at `002844afb0441a6a89cb5cdc30fb4cbbce97698b`  
**Status:** architectural and empirical gap review, not biological qualification  
**Scope:** one naturally founded *Lasius niger* colony, a single enclosed chamber at time zero, real local ecology, read-only observation and optional state continuation  
**Scientific status:** ENGINEERING_ONLY; retain B06 INSUFFICIENT, the inherited application performance FAIL, and all BIOLOGICAL_BLOCKED items.

## Product contract

The essential deliverable is a small living world that can be observed without understanding internal test harnesses. At day zero there is **one queen in one physically enclosed founding chamber**, no workers or pre-seeded brood. The queen lays at a biologically plausible abdominal outlet, approaches and manipulates brood, and can feed developing larvae when local contact and material accounts permit. Workers arise only through development, gradually take over appropriate work, discover and excavate a real exit, carry actual parcels, and deliver external resources into the nest.

The original C++ Simulation Core remains the sole authoritative state owner. The viewer can exaggerate outlines for selection, but must label such exaggeration, preserve physical ordering, and never synthesize positions, events, transfers or biological success. A production-looking interface is not evidence of a biologically valid Core.

### Evidence-based findings in the current baseline

| Gap | Located implementation | What is already true | Material problem |
|---|---|---|---|
| Adult size | `cpp/src/geometry.cpp::body_half`; `op0/web/viewer.js::adultGlyphSize` | The viewer distinguishes queen and worker appearance | Core uses the same unloaded cube for adult castes; renderer independently scales sizes |
| Foundress movement | `cpp/src/care.cpp::resolve_care_wakes` | `ApproachBrood`, `PickUpBrood`, `TransportBrood`, `FeedBrood` and `CleanBrood` are schedulable and real moves exist | No canonical body orientation, head location, mandible reach, grooming contact point or per-target movement denominator |
| Oviposition | `cpp/src/brood_space.hpp::pick_egg_site` | Physics 38 places eggs in a posterior sector using 0.125 mm candidates | Posterior is inferred from the nursery vector rather than a stored gaster pose; deterministic first-legal lattice generates unnaturally regular placement |
| Brood packing | `cpp/src/brood_space.hpp::brood_pitch_m` | Occupancy and clearance are checked | All developing stages share a 0.75 mm exclusion proxy; egg piles and volumetric stacking are not represented |
| Terrain and agents | `cpp/apps/wp6b_fixture.hpp`; `cpp/src/geometry.cpp` | Physics 38 uses one 12 × 7 mm chamber and 0.25 mm terrain quanta | Body center has high precision but solid geometry, collision envelope, orientation and visible morphology do not yet share an accurate anatomical model |
| Attachment | `cpp/src/worker_motion.cpp::supported_wall_segment` | Supported wall / ceiling movements are admitted in limited same-face cases | There is no general floor-wall-ceiling transition, continuous surface-normal orientation or articulated body clearance |
| Soil | `cpp/src/excavation.cpp`; `op0/web/viewer.js::drawSoilParcels` | Digging and same-parcel carry/drop are in the canonical ledger; piles are shown | Loose material is displayed as symbolic deposits, not a locally accumulated, mass-conserving granular pile profile |
| User experience | `op0/web/index.html`, `viewer.css`, `nest_view.js` | Local browser, 3D sections, event browsing and native controls work | Debug-style controls dominate the page, the actual nest occupies too little space, the action narrative is hard to follow |
| History | `cpp/src/checkpoint.cpp::AWRESUM1` | Default compact continuation retains state and a bounded recent fact suffix with exact future continuation | This is **not** a blocker. Complete-life replay must remain opt-in and must not be silently represented by a compact snapshot |
| Colony continuity | `research/single_nest/README.md` | Three finite-supply seed worlds reached 150 days with surviving workers | Their sole founder was dead by day 150 in each; a worker remnant is not a growing, reproductive colony |

The observation that a queen looks stationary is not disproved by one unit test containing a `Moved` event. Quantify movements and physical contact across the first egg and larval cohorts, including failed and skipped opportunities. Equally, an apparent regular row of eggs cannot be fixed by applying a random visual offset: the underlying placement must change first.

## Core design: three independent spatial scales

**Do not convert the entire 24 m world to a dense 50 µm voxel grid.** The single nest is a local high-detail region; the wider ecological environment uses a different representation.

1. **Substrate field:** retain sparse, editable terrain bricks and ordered soil/rock/void edits, initially 0.25 mm in the test nest. Refine terrain locally only when a specific collision, exit geometry or digging experiment demonstrates the need. Preserve integral parcel mass, support checks and bounded queries.
2. **Body and object geometry:** add versioned, stage- and caste-specific morphology with a head, mesosoma and gaster longitudinal envelope; larval and egg shapes have separate dimensions. A body has a stored position and heading/orientation, with explicit head and gaster landmarks. Test real body sweeps, turning and loaded clearances; allow scientifically motivated soft contact only if it has its own rule and provenance. No unrelated visual multiplier may stand in for the collision envelope.
3. **Placement and manipulation:** use finer *local* coordinates than the terrain quantum, e.g. a 25–125 µm engineering search scale in the chamber, or a deterministic fixed-point micro-position representation. This does not imply independently physical 25 µm soil cells. Brood must be able to form an irregular cluster with non-overlapping envelopes and, if needed, supported stacking; do not snap every egg to a globally visible rectangular grid.

Morphology and dimension ranges must be supported by explicitly identified *Lasius niger* measurements when available. If a particular length, joint position, claw force or contact frequency is not supported, label it a calibrated-independent engineering hypothesis or fixture, not a direct species fact. The initial worker/queen rendering values in the experience branch are **illustrative** until the same dimensional model is adopted in Core.

## Founding queen: a real local action chain

- **Oviposition:** physical gaster orientation at the scheduled birth, an outlet behind the body, a short valid deposition action, paid reproduction, an independent egg identity, and an actual new position inside the chamber. If the outlet is blocked, postpone without free birth; retry under an accountable policy.
- **Care goal:** a locally observed egg/larva/pupa, selected based on a bounded care need and existing social/physiological constraints. Record the candidate pool, selected identity, nearest accessible contact site, invalid/blocked candidates and the actual decision.
- **Approach:** approach an appropriate **head-contact pose** by a legal paid path. Do not define contact solely by distance between two body centers. Preserve sensed limits and avoid global knowledge of unsensed brood.
- **Action:** physically reachable inspect, groom/clean, pickup, carry, place and larval feeding with explicit contact time; exchange of protein or water must retain the existing material source and absorption rules. Grooming without material transfer remains a timed interaction, not a fake nutrient receipt.
- **Development of division of labor:** allow maternal care before emergence; later workers may perform care under existing eligibility and experience rules, without instantly disabling queen care. No fixed claim that each egg *must* receive a specific number of grooming bouts until species-specific data support it.
- **Audit:** publish per-brood-item local visit, head-contact, manipulation, payment, absorption and competing-death timelines; measure blocked/rejected rates. Show observed world-coordinate displacement across separate targets, not merely a global action count.

Direct biological starting points: *L. niger* founding-care and division-of-labor study DOI `10.1111/1365-2435.14536`; queen/worker brood retrieval DOI `10.1002/ece3.4475`. Those studies do **not** directly identify the simulator's 0.125 mm lattice, gait duration, queen contact rate or larval survival target.

## Workers, three-dimensional substrate, and earth

- Build a locally connected **support-surface graph** from accessible terrain faces, including floor, wall and underside; orient the body to the supporting face normal and let it cross an adjacent face only when the entire body and load sweep is legal.
- Distinguish attachment, vertical locomotion, ceiling locomotion and unsupported free-space movement. A worker cannot silently fly between faces or pass through a roof; no assumed perfect grip. Use measured adhesion data when calibrating.
- Maintain short-range navigation, experienced return path, food load and actual contact constraints. Keep real traffic and deadlocks visible; do not teleport workers across occupied depots.
- Excavate only a reachable soil face by a worker that has matured and paid the action cost. Parcel mass leaves the wall, remains owned in transport and enters an actual local spoil inventory at deposition. A rendered pile should derive height/shape from deposited positions and volume, with a declared engineering packing/angle rule and clearance consequences if modeled.
- **Initial condition:** physics 38's one enclosed chamber is the correct starting condition. No second initial brood room, pantry or passage; later functional subdivisions must be justified by actual excavation, movement and resource use, not user interface labels.

## Visual product: observe first, inspect second

The normal UI opens to the nest, **not** a statistics dashboard. The focal panel is a large, readable 3D cutaway with soil, the queen and brood visible at default camera distance. Controls for orbit, cut depth and time sit close to the world. Contextual panes show only the selected entity's life, nearby action and resource state. Canonical EventId, numeric ledgers, physics version and technical diagnosis remain available under an explicit inspect / research mode.

- Consistent queen-to-worker and stage dimensions at every zoom; ensure the selectable hit region never redefines physical size. Allow an explicit accessibility magnification setting, labelled as nonphysical.
- Physically supported posture and carried brood/soil/food orientation. The animator can interpolate only from verified start/end and duration; without a committed action the individual remains at the committed pose.
- Real soil mesh, lighting and near-ground texture derived from physics; a small number of reusable low-poly anatomical shapes before committing to expensive photoreal assets.
- Meaningful **watch** shortcuts: queen lays, queen approaches first egg, brood cleaned, first worker, first excavation, first loaded return, queen receives food, and death—only when those events occur. A missing milestone should be shown as a negative outcome.
- Small local overlays, Chinese default when selected, keyboard access, responsive layout, subtitles for color-coded events, and a stable camera.
- Separation of simulation physics, 60 Hz visual presentation and macro simulated speed. At 86,400×, several hours of Core behavior may occur between displayed frames; offer a backed-up event replay or slow-to-event ability rather than inventing intermediate actions.

## Persistence contract

Compact continuation is the default and must remain so. Keep `AWRESUM1` current state, queue, RNG, entities, inventories, motion/care custody, terrain edits, supported cached provenance and a bounded recent history, with absolute IDs and explicit history floor. Provide opt-in full archival replay only when the user enables it. A compact snapshot may not claim to contain an individual's complete earlier life. Test time partitioning and save/load identity, rejection of corrupt snapshots, the unsupported-old-milestone message, and bounded resident memory.

## Evidence and acceptance — avoid an endless pass loop

A first playable single-nest release is **not** ready merely because the Qt/HTML test passes. Require all of:

1. **Day 0:** a single enclosed chamber, queen only, with a correctly sized anatomical body and meaningful camera scale.
2. **Laying and brood:** in a natural simulation, the queen's gaster-relative deposition, later spatial approach to different brood individuals, actual head-contact cleaning/inspection and paid pickup/carry/place are separately recorded; no posthoc visual offset is used.
3. **First worker:** emerges from an actual funded egg with retained lineage and works at a legal local berth; worker rendered smaller than queen under equal scale.
4. **Excavation/egress:** worker opens only real reachable soil, transports the same parcel to a spoil position, exits using a valid supported 3D path and carries food back by real transaction.
5. **Negative controls:** sealed inaccessible rock, no external resources, invalid brood contact, occupied berths, exhausted maternal food/water all preserve failures and ledger conservation. Do not make the queen immortal to meet a cosmetic demo milestone.
6. **Interface:** Windows one-command launch, convincing camera framing, no overlapping essential controls, queen and first brood immediately legible, focus mode, native-action-linked playback, 2D research section retained and evidence visible on request.
7. **Persistence:** compact snapshot continuation matches unbroken state and future canonical events; optional full archive is labelled distinctly. Original physics/replay families still pass.
8. **Performance:** profile Core simulation, terrain mesh build, browser paint, peak RSS and history size under fixed 1/10/100 worker cases, with bounded dense-work experiments. No dense 50 µm full-world allocation.

Declare frozen seeds and paired negative/positive scenes before running validation; publish primary event witnesses and actual UI screenshots, including failures. Human-visible review should include both an uninterrupted 5–10 minute observation session and a saved/resumed session. Every candidate can be **ENGINEERING_PREVIEW_PASS** while biological gates remain open; avoid claiming species calibration by using a successful seed.

## Delivery order

1. **Immediate interface remediation:** immersive observatory, physically intelligible illustrative queen/worker proportions, keyboard access, responsive layout and browser tests. This is the first actual change on the new branch; it does not close the physics gaps.
2. **Authoritative body/pose and local brood action vertical slice:** new physics/version tag, queen and worker morphology, egg outlet, deterministic local micro-position/collision and real head contact; keep prior physics unchanged.
3. **Supported 3D locomotion and spoil deposition:** cross-face support graph, mass-backed piles, traffic arbitration and full same-parcel regression.
4. **Integrated one-nest live demonstration:** real natural founder case, adverse controls, proper render, compact continuation, native/browser cross-platform tests, measured performance.
5. **Independent review:** accept the playable vertical slice or return a finite list of genuine blockers. Do not expand to multiple colonies, the full 24 m world, Unity or Game Master before this single nest becomes genuinely worth observing.

## Review boundaries

No hidden free energy, no fake locomotion, no pre-positioned workers in founding demonstrations, no posthoc random visualization shifts, no ignored old archive failures, and no claim that different platform traces are exact if they diverge. Preserve the previously documented physics and schema generations, real finite inputs and all inherited scientific warnings.
