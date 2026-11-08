# Parametric geometry prototype and acceptance (v0.6)

These are technical experiments, not authorization for a complete game. Current implementation stage boundaries are in document 22.

## Geometry work packages

- G0: headless InitialSolid, seed chamber, ordered ExcavatePatch, queries, material accounting, repeated-removal protection and save/load.
- G1: 3D connectivity and clearance: projected crossing, real opening, backfill closure, loaded/unloaded passage.
- G2: local SDF cache, dirty AABB/halo, mesh/normals/seams, cache reconstruction and compaction equivalence.
- G3: C ABI DLL, immutable batches, dirty/mesh packets and stable Unity ownership.
- G4: local biological proposals produce edits, carried parcels, deposition and consistent ledgers.
- G5: long edit histories, interleaved remove/fill, saves, months of acceleration, memory/time/storage measurements.

## Required tests

| ID | Input | Assertion | Priority |
|---|---|---|---|
| GEOM-01 | Repeat identical removal | Second edit removes zero material and creates no mass | P0 |
| GEOM-02 | Different-depth tunnels crossing in projection | No real opening means no connection | P0 |
| GEOM-03 | Excavate sufficient connecting clearance | Actual disconnected-to-connected transition | P0 |
| GEOM-04 | Backfill an open passage | Delete connectivity; invalidate old routes immediately | P0 |
| GEOM-05 | Edit near a chunk seam | Dirty both sides/halo; no mesh crack | P0 |
| GEOM-06 | Simultaneous overlapping digs | Serialized/equivalent arbitration; no duplicate material | P0 |
| GEOM-07 | Dig, carry and deposit | Dry/water balance within declared numerical tolerance | P0 |
| GEOM-08 | Deliver older mesh revision | Client does not overwrite newer geometry | P0 |
| GEOM-09 | Save, load, continue editing | Occupancy, connectivity, IDs, sequence and ledgers agree | P0 |
| GEOM-10 | Compact geometry history | Material/clearance/occupancy queries remain equivalent within error bound | P0 |
| GEOM-11 | Unloaded versus large load | Body/load envelope changes legal passage | P1 |
| GEOM-12 | Toggle transparency/sections | Geometry and ant state remain unchanged | P0 |
| GEOM-13 | Navigation lags geometry | Block/revalidate affected paths; no passage through walls | P0 |
| GEOM-14 | Thin wall/nearly touching voids | Conservatively reject uncertain passage and diagnose | P1 |
| GEOM-15 | Metadata then mesh copy | Same snapshot; capacity failure is safely retryable | P0 |

## Measurements

Report commit p50/p95/p99, nav and mesh rebuild p95, dirty brick count, geometry query throughput, memory per 1,000 edits, save size per 10,000 edits, load/warmup, surface deviation, clearance error and conservation residual. No unmeasured millisecond promises. Compare sweep length, sampling, work batch size and compaction thresholds at the same workload; FPS alone is not correctness.

## End-to-end story

Create test soil and a connected chamber. A worker reaches a real front and proposes digging; C++ commits actual material and ExcavationCommitted. Derive legal connectivity and dirty mesh data, update Unity and change viewing modes without moving the ant. The ant actually transports soil. Queries identify actor, time and quantity; GM prose cannot create tunnels. Repeat headless from the same initial state/seed and compare facts.

The historical geometry plan prioritizes G0/G1/G3 before scaling. The v0.8 roadmap defers Unity to S7 and takes precedence. If ordered edits degrade, first measure/improve indexing and compaction. Changing confirmed authority option A requires an explicit ADR and user review, never a silent fallback to option B.
