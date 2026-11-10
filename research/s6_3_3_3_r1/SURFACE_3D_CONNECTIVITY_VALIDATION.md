# Surface and three-dimensional connectivity

The old mixed chamber used a coarse surface step to a terrain center from a depot located at the shaft rim. It had no valid continuation through the rim and no exterior food return in the reproduced 4,310-fact control. The new route attaches the true depot to a bounded geometry waypoint path, then joins a walkable surface tile at the body clearance plane. Ground food stays at its real position. A candidate must be in local reachable cells and pass the physical line check. Collection requires actual reach and clearance. [Before](../../experiments/s6_3_3_3_r1/baseline/chamber_runs.csv) · [Discovery](../../cpp/src/spatial_navigation.cpp) · [Perception and action](../../cpp/src/foraging.cpp)

## Route ownership

Each active worker gets its own deterministic connector from real, locally reachable geometry, bounded by the existing route and node budgets. The search can inspect adjoining candidate geometry inside that bound. It gets no input from the food catalog, the entrance is discovered, and every waypoint is walked with elapsed simulation time. The worker remembers that connector from its familiar depot. Planar cue and route memory stay tile-based, and the worker's physical position supplies the preceding neighbor after route loop erasure. A home-cell encounter continues down the connector even on an empty trip. The last segment reaches the actual depot. [Empty-return addendum](../../docs/63_R1_Isolated_Execution_Addendum.md)

Stored connectors and actual cargo survive interruptions and saves. Each leg checks current clearance. A fill can stop a loaded worker, which stays at the last committed position with its real cargo. The same route becomes passable again when an accounted excavation clears it. A geometrically valid alternative beyond the local route/node bound may remain undiscovered. There is no automatic replacement for a permanently obstructed remembered route. The fixture is a flat ground plane and conservative axis-aligned body clearance. Full terrain following, unsupported climbing dynamics and natural shaft architecture are separate questions.

## Controlled native cases

| Shaft and grid | First collection | Underground delivery or return | Outcome |
|---|---:|---:|---|
| 2 mm straight, 1 mm tiles | 18.122 s | 35.645 s | Food delivered |
| 2 mm offset, 1 mm tiles | 38.360 s | 55.685 s | Food delivered |
| 2 mm straight, 10 mm tiles | 8.213 s | 15.827 s | Food delivered |
| 2 mm offset, 10 mm tiles | 10.217 s | 19.835 s | Food delivered |
| 1.5 mm shaft, both tile widths | — | — | Unloaded geometry route exists, but the return cargo does not fit |
| 2 mm shaft, 10 mm tiles, fill and reopen | 8.213 s | 35.413 s | Stopped with cargo, restored while blocked, then delivered |
| Offset shaft, 10 mm tiles, empty arena | — | 20.435 s | Returned after reaching another exterior cell |

The positive cargo cases deliver 1,300 μg carbohydrate, 130 μg protein and 700 μg water at y = −5 mm. The narrow case tests unloaded geometry separately and rejects entry into the planned foraging round trip atomically. The filled/reopened case verifies three geometry edit facts and the soil ledger. Day-scale return, feeding, placement, birth and maturation are audited separately. [All probe facts](../../experiments/s6_3_3_3_r1/probes/connectivity) · [Ecology evidence](INTEGRATED_ECOLOGY_REGRESSION.md)
