# Parametric geometry and local SDF specification (v0.6)

Architecture only, not implemented or measured. Option A is confirmed: InitialSolid plus ordered parametric excavation/fill operations is authoritative. Local SDF is disposable/rebuildable. Local ant actions accumulate shape; parameterization never authorizes whole-nest blueprints. Retain C++ authority, Unity views, real 3D and the expandable full-world target.

## Ordered CSG model

InitialSolid includes terrain materials, rocks/roots and creation-time seed voids. For material set S_k, excavation is `S_(k+1)=S_k \ E_k`; actual removal is `S_k intersect E_k`. Fill is `S_(k+1)=S_k union F_k`, only with available material, reachability and no illegal replacement. Remove/fill/remove order matters.

Record sequence, time, edit ID, cause/actor, before/after geometry versions, material deltas, volume estimate and error bound. Authoritative EvaluateSolid, QueryMaterial, surface intersection and clearance use ordered state, not independently mutable mesh/SDF/nav data. Smoothing cannot silently alter mass or volume.

| Primitive | Parameters/use | Constraint |
|---|---|---|
| ExcavatePatch | Contact point, normal, local shape/size | Starts at a reachable material interface |
| ExcavateSweep | Ordered control points, varying section radius, end caps | Aggregates actual small edits; cannot skip intermediate work |
| ExcavateLocalBlob | Center, axes, orientation, local shape | Emergent lateral enlargement, not a room template |
| FillPatch/Deposit | Shape, material batch, compaction | Supplied reachable material only |
| SeedChamber | Initial chamber and founding context | Creation provenance, not a newly observed excavation |

Capsules, piecewise/Bezier sweeps and ellipsoidal patches are candidates. Work and capacity bound each edit.

## Implicit queries and cache

Define phi_s < 0 in material, > 0 in void; phi_E < 0 inside the cutting tool. Difference uses `max(phi_old,-phi_E)` and union uses `min(phi_old,phi_F)`. Their signs implement CSG but absolute values near intersections are not necessarily true Euclidean distances. Do not use them as guaranteed clearance without appropriate redistancing or conservative verification.

EvaluateSolid uses authoritative edit history/index. LocalSDFCache samples active AABBs for mesh, surface neighborhoods and prefilters, never as an independent edit path. Internal coordinates are double meters, X east/Y up/Z north; Unity may use chunk-local float vertices. Fix axis mapping, winding and rotation at the ABI.

Index edit AABBs; dirty regions include sufficient halo for normals, filters, clearance and navigation across chunk boundaries. Candidate 1-2 mm active sampling and 64 mm/32-cubed bricks are experiments. Far-wall rendering may be coarser, but passability needs conservative body-scale checks. All caches have source/build revisions. Thin or uncertain geometry is blocked/diagnosed rather than assumed passable.

Avoid linear scans over a lifetime of edits. Versioned checkpoints/compaction may replace history with an equivalent compact authority plus tail edits; retain source event IDs and verify occupancy, materials, boundaries and connectivity before/after. Do not sever historical attribution.

## Six-step digging commit

1. Discover locally reachable frontiers with material/normal/cues.
2. Local physiology, thresholds, crowding and climate produce a proposal, without global information.
3. Reserve a bounded work request containing actor, frontier, tool, effort and carrying capacity.
4. Validate obstacles, current material intersection, reachability, load and safety constraints.
5. Atomically commit edit, soil parcel, ledger and geometry revision; mark dirty regions and invalidate affected navigation. Failure leaves all unchanged.
6. Verify/rebuild navigation and publish committed facts/dirty mesh data; rendering may arrive later, physical legality cannot.

The second overlapping excavation recomputes against remaining material; an existing void yields zero soil. Complex intersection volumes can use bounded adaptive integration rather than pretending an exact analytical solution exists. `delta_M_dry = rho_dry_bulk * delta_V_removed + bounded_error`; global mass balance includes remaining/carried/deposited/exported material and bounded residual. Derive material and volume accounting from one estimate chain. Separate water and dry mass; density/compaction changes do not create mass.

## Connectivity and identity

Actual 3D void connectivity plus body/pose/load clearance defines F_ant. Neither centerline crossing nor overlapping top-view projections guarantees passage. Derive portals and NavRegions from verified clearance. Excavation can add connections; backfill can remove them, so merge-only union-find is insufficient. Rebuild affected components conservatively. Hierarchical pathfinding may use known topology but cannot disclose unperceived food.

If nav_revision is stale, block or revalidate affected routes. Chamber/tunnel labels derive from shape, local thickness and activity. Stable region IDs, hysteresis and split/merge lineage prevent small mesh changes from destroying history; some spaces need not fit a binary chamber/tunnel taxonomy. Loaded ants may require more clearance than unloaded ants.

## Representation responsibilities

| Representation | Role |
|---|---|
| BaseSolid + OrderedEdits | Sole authoritative material/void geometry, atomic and persistent |
| SDF/occupancy bricks | Versioned query/mesh acceleration |
| NavRegion/NestGraph | Derived movement, blocked/rebuilt when stale |
| CollisionProxy | Derived, current or conservatively validated |
| Unity RenderMesh | Versioned presentation, may lag |
| Unity MeshCollider | Optional camera/picking aid, never ant physics authority |

Do not require thousands of Unity rigid bodies or frequent whole-nest collider cooking. Mesh only changed AABBs, comparing Marching Cubes and Dual Contouring for walls, seams and normals. C++ may prepare meshes asynchronously; Unity applies the latest packet on its main thread. Transparency/section shaders do not excavate or reconnect space. Unity mesh APIs are references, not a locked implementation choice: https://docs.unity.com/en-us/engine/6000.3/script-reference/unityengine/mesh/applyanddisposewritablemeshdata .

## Modules and persistence

Suggested classes: ConstructiveSolid and EditSpatialIndex for authority/queries; GeometryTransaction for atomic edits/materials; SdfBrickCache and DirtyRegionTracker; ClearanceQuery, ConnectivityValidator and LocalNavRebuilder; RegionLineage; MeshRebuilder without Unity dependencies; SoilParcelLedger; local soil heat/water and chamber environment.

Save world/schema/geometry versions, InitialSolid/material data, seed edits, compact authority/tail edits, unfinished work, material ledger, entity state, event references and RNG. Rebuildable caches are not the only save truth. Each edit event retains actor/world/time, before/after versions, changed AABB, dry/water amounts, parcel and connectivity consequences.

Confirmed: authority route and single-writer/view separation. Proposed: primitives, transaction/query organization and conservative cache design. To validate: primitive set, numerical error, robust portals/regions, resolution, refresh cost and external library choices.
