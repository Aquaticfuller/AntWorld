# Autonomous 3D nesting and subsurface environment (historical v0.5)

This is a research/engineering specification, not an implemented or measured solver. v0.6 selected option A: ordered parametric excavation/fill edits are authoritative and local SDF is derived cache. Earlier A/B comparisons are historical. Documents 10-12 refine the selected route. The target species is Lasius niger; cross-species evidence remains explicitly qualified.

## Eight invariants

1. Underground space is genuinely 3D. Projected crossings without an opening are disconnected.
2. C++ computes material, positions, excavation, connectivity and environment; Unity cannot change physical facts.
3. Ants use locally perceived/reachable/learned cues, never a global colony blueprint.
4. Removal, carrying, deposition and backfill are real, accountable operations.
5. Meshes, collision and navigation derive from the same authoritative geometry.
6. Fine volumes are local to active/important areas, never a uniform millimeter grid over 24 x 24 meters.
7. L. niger deposition studies do not establish all underground excavation rules; fire-ant and leaf-cutter results need qualification.
8. Every change can be linked to individuals, environment, material quantities, connectivity and simulation time.

## Evidence and assumptions

Garcia Ibarra et al., DOI 10.1111/1365-2656.14040, studied 17 young L. niger colonies in temperature-controlled soil columns over about 100 days. The baseline cites deeper/larger nests and some upper-chamber backfill under warmer conditions. This supports environment/form relationships, not a complete individual decision algorithm. The associated data at https://doi.org/10.23708/ZJTSDI were described as restricted in the original handoff; no quantitative fitting was performed.

Khuong et al. (2016), DOI 10.1073/pnas.1509829113, concerns L. niger deposition construction, local chemical cues and body-size templates. Pillar/roof formation is relevant to self-organization but is not a calibrated underground tunnel-excavation law.

Fire-ant quasi-2D collision-regulated excavation (10.1098/rsif.2022.0597), Atta vollenweideri soil-moisture preferences (10.1371/journal.pone.0095658), and other species' cast nest architectures (10.1093/jis/5.1.9; 10.1093/jis/4.1.21) provide hypotheses or geometric examples, not L. niger constants.

Test local crowding/brood/climate effects, side-wall expansion into chambers, excavation angle/width near existing voids and obstacles, soil-dependent cost/capacity/blockage, and flow/relocation after new connections. These remain model assumptions until calibrated.

## Coordinates, chunks and precision

Use meters with X east, Y up and Z north. Surface height is y_surface(x,z), depth is y_surface-y. Earlier kg/mg proposals are superseded by the v0.8 microgram ledger contract; energy is joules and temperatures have explicit units.

The complete map is 24 x 24 meters. Candidate surface chunks are 2 x 2 meters; underground has an independent sparse 3D index, able to cross surface boundaries. Distinguish simulated material domain, observable domain and external ecological boundary conditions, including migration/resource flux assumptions.

Candidate environmental sampling is 10-25 cm with local nest refinement; active digging samples might be 1-2 mm. A 64 mm brick sampled at 2 mm has 32^3 cells: one 4-byte channel is about 128 KiB, or about 12.5 MiB for 100 bricks before indices, halo, mesh or additional fields. These are engineering examples, not chosen budgets. Batch dirty updates; do not remesh every chamber on every tick.

## Authority and derived spaces

InitialSolid describes soil layers, rocks/roots and legal seeded voids. Ordered geometry edits record excavation and fill. Sparse SDF/occupancy caches are rebuildable. Navigable volumes, portals, nest graphs and rendering/collision representations share source versions. A mesh may arrive late, but navigation must never permit passage through new material.

Chambers/tunnels carry persistent spatial identities, shape, depth, clearance, climate, occupants and historical use. Portals require real openings and loaded-body clearance. Frontiers are reachable soil-air interfaces with normals, material, local conditions and work limits. Chamber function is a derived observation label, never a digging blueprint.

An edit validates reachability/material/capacity, commits authoritative geometry and ledgers, invalidates navigation, then publishes dirty data and facts. Failure leaves no partial material or geometry change. Option B (occupancy authority) is only a future fallback requiring a new ADR, not a parallel first implementation.

## Individual excavation and transport

An ant reaches a connected void boundary and senses local soil/crowding/climate/known demand. It removes a small allowed volume, spends effort/time/energy, obtains a soil parcel, travels along valid routes and deposits or fills an accessible location. Carrying capacity and loaded clearance constrain work. Geometry changes alter movement and environmental boundaries for subsequent behavior. A batch can represent soil without a Unity object per grain, but dry mass, water, provenance and location remain explicit.

Candidate stimulus:

`U_i(f,t)=b_species+w_s*S_soil+w_c*C_local+w_h*H_micro+w_b*B_local+w_m*M_i-theta_i`.

The coefficients are uncalibrated. Test ablations and directional responses. Reject unreachable, non-diggable, obstructed or physically invalid proposals. Conservative water-risk constraints are not a claim of omniscient ant foresight. Preserve task continuity during digging/carrying unless a valid urgent event interrupts. Backfill needs real supplied material and updates connectivity.

`delta_M_dry = rho_dry_bulk * delta_V_inplace` uses bulk dry density, not mineral particle density. Track water separately. `initial_soil + imported = remaining + carried + deposited + exported`, within declared numerical error. Compaction can change volume, never create mass. Individual-grain dynamics are unnecessary for the first model.

Seeded founding chambers are legal initial conditions. Subsequent local wall edits can create wider spaces and loops. Chamber/tunnel classification follows shape and activity, not predefined room dimensions.

## Soil, heat, water and stability

Soil layers/cells store material type, bulk density, porosity, water, heat capacity, conductivity, infiltration, digging difficulty and obstacle tags, optionally conservative stability limits. These are approximations unless measured.

A candidate coarse heat model is `rho*c*dT/dt = div(k*grad(T)) + q_source`, with surface seasonal/daily boundary conditions and local refinement. Chamber air exchanges with surrounding soil and entrances according to volume; full natural convection is not required initially. Validate units, stability and energy direction.

Soil volumetric water content and chamber relative humidity are different fields. Use low-frequency conserved rainfall, infiltration, vertical/lateral drainage and evaporation rather than immediately introducing a full Richards-equation solver. Water enters voids only through actual connections and elevation thresholds. Candidate balance: `rain + initial_storage = infiltration_storage + cave_storage + runoff + evaporation + outflow`. Leaf-cutter moisture thresholds cannot be copied as L. niger values.

Initial stability checks may enforce clearance, covering thickness, rock/root constraints and thin-wall hazards. These are not a complete soil-mechanics or collapse model. Collapse, mud flow and detailed ventilation are separate later topics.

## Synchronization and data

ExcavationCommitted records WorldId, SimTime, AntId, FrontierId, GeometryEditId, before/after versions, dry/water mass, removed volume, changed AABB and connectivity consequences. Commit in C++; immediately invalidate affected routes, conservatively verify/rebuild navigation, queue versioned mesh work, refresh affected environmental/usage statistics and publish facts. Unity lag cannot determine authoritative passability. Immutable batches cross threads/languages.

Suggested responsibilities: spatial material/solid/index, nest volumes/regions/portals/frontiers/parcels, digging actions and ledgers, navigation/clearance, soil heat/water and chamber air, dirty scheduling, morphology metrics and API queries. Persist geometry/edit/frontier/parcel IDs, versions and region lineage. Parcel state distinguishes carried, deposited and filled material. View sections and transparency never modify physics.

## Precision, time and observation

Real events such as digging, narrow contact, brood transport, imminent connection or flooding can demand higher precision even off-screen. Distant areas preserve geometry, identity, state and significant history; do not invent an unobserved tunnel on camera arrival. Event-based completion still records work duration, participants and materials. Physics, navigation, rendering and history sampling may have different frequencies. Save/load, pause, acceleration and offline catch-up obey the same material/connectivity checks.

Expose nest volume/depth/shape, passages and loops; daily dry/water excavation, fill, deposition and transport; connected components and bottlenecks; depth climate and water; brood/worker distributions, moves and usage history. Associations between temperature and depth are not sufficient causal proof. GM queries morphology, excavation, ledgers, microclimate and brood depth before narrating.

## Experiments

| ID | Check |
|---|---|
| X1 | Projected crossings at different depths remain disconnected until a real opening is excavated |
| X2 | Concurrent overlapping excavation never duplicates material |
| X3 | Removal/carry/deposit/fill conserve dry mass and water |
| X4 | Repeated reachable local edits grow real space without a blueprint |
| X5 | Temperature/soil changes have explainable gradients and multi-seed, evidence-qualified responses |
| X6 | Fixed rain and varied infiltration conserve water and respect actual connectivity |
| X7 | Transparency, sections and following leave state/paths/statistics unchanged |
| X8 | Speed/offline modes preserve invariants and satisfy statistical tolerances |
| X9 | Save/load preserves geometry, connectivity, IDs, material and planned activity |
| X10 | Measure commit, query, navigation, mesh, memory and save costs separately |

Failure includes passage through walls, duplicated/lost soil, invented off-screen history, cross-species parameters claimed as calibrated, or a growing nest-level statistic without actual geometry and events. Open work includes numerical primitives/accuracy, conservative stability, coarse microclimate coupling, small-column fixtures and access to calibration data.
