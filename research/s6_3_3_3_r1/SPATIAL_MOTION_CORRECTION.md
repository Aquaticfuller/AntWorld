# Spatial motion correction

The reviewed coarse probe saw the displaced brood at 12 mm sensing range. Its 1 mm proposed movement on the 10 mm terrain returned the original position, so it committed one blocked outcome and zero approach starts. The 1 mm terrain moved and then failed during custody. The two 6 mm perception controls retained the expected absence of a cue. The reviewed batch and the fresh reproductions are separate archives. [Baseline cases](../../experiments/s6_3_3_3_r1/baseline/probes.csv)

## Position and topology

For a world with `WorldConfig::continuous_spatial_motion = true`, the entity coordinate in meters is authoritative. A terrain tile indexes surface eligibility, cues, heading and route memory. It also provides ordinary exploration waypoints. Care can end anywhere along its bounded physical segment and shared ordinary Move accepts an interior or crossing segment. An explicit coordinate is never replaced by a cell center. A mask traversal checks all crossed cells and the two incident neighbors at an exact corner. In mixed worlds, the mask covers the at-and-above-datum portion of the segment. The parametric material authority covers the whole segment. [Surface traversal](../../cpp/src/surface_internal.hpp) · [Ordinary resolution](../../cpp/src/world_runtime.cpp)

`continuous_clear()` converts physical positions to the geometry's coordinate frame for the query and partitions the local swept bound with ordered authoritative edits. It tests the segment against each solid box expanded by the required body half-extent. For point membership the geometry is half-open, and a body may touch a boundary with zero overlap. The movement endpoint stays the original double coordinate. Care tries a deterministic, distance-reducing axis segment if its first diagonal clips a corner. This is bounded local avoidance. A blocked destination still records its actual outcome. CSG route and SDF queries retain lattice sample points. [Sweep and clearance](../../cpp/src/geometry_kernel.cpp) · [Care destination and execution](../../cpp/src/care.cpp)

Positions update on a completed, nonzero-duration segment after validating the entire sweep again. An event between departure and completion observes the last committed position. The engine has no subevent interpolation. Exact within-cell walks, 3D straight diagonals and true loaded two-body sweeps have tests. The body proxy is a cubic clearance extent and the terrain is flat at its declared datum. Slope mechanics and body orientation remain open scientific work.

## Frozen representation controls

| Care stride | Carrier plus brood position facts in each width | Completion time in each width | Brood endpoint x |
|---|---:|---:|---:|
| 0.5 mm | 48 | 5,084 ms | 2 mm within arithmetic precision |
| 1 mm | 24 | 5,044 ms | 2 mm |
| 2 mm | 12 | 5,024 ms | 2 mm |

All three matched pairs use 1 mm and 10 mm terrain, identical physical layout and equal committed trace hashes within each pair. Duration differences across strides arise from separate timed segments and their existing clocks. The ordinary Move control ends at x = 10 mm after three valid movements. A masked wall, exact diagonal corner and overspeed proposal leave the prior physical revision unchanged. [Motion records](../../experiments/s6_3_3_3_r1/probes/motion)

## Persistence boundary

The opt-in world uses checkpoint envelope E, schema 14 and physics 16. The envelope records the inherited base contract, preserving existing ecology and care feature variants. It adds a rigid grip and a per-forager local connector where applicable. Restore validates the state, action owner, pending route, committed position facts and historical geometry. Existing saves continue in their original physics with their original encoding. New scenario authors choose the continuous contract explicitly. The inherited binary formats and archive fingerprints are independently exercised. [Codec](../../cpp/src/checkpoint.cpp) · [Connector restore](../../cpp/src/checkpoint_spatial.hpp)
