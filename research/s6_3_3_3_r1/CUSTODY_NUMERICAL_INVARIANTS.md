# Custody numerical invariants

The reviewed 1 mm test at 12 mm perception picked up one larva and moved it once before the 2 mm boundary produced `OutOfReach`. Independent additions of carrier movement to the held coordinate accumulated different rounding from the carrier coordinate. [Baseline probes](../../experiments/s6_3_3_3_r1/baseline/probes.csv)

## Precision contract

Reach uses the Euclidean distance in meters. An arithmetic overrun is accepted only within

```text
min(2^-32 × reference_scale, 8 × epsilon_double × max(coordinate_scale, reference_scale))
```

The coordinate scale is the largest absolute coordinate of the two positions. The absolute cap for a 2 mm reach is about 0.466 picometers. Thresholds are still their configured physical values. A real separation of 1 nm beyond reach exceeds this envelope by more than three orders of magnitude, including with coordinates translated by 12 m. The same bounded predicate is shared by care, nutrition, ordinary resource interaction, social contact and checkpoint validation. Broad-phase indexes only select candidates. The final contact also has to pass the current solid/mask line check. [Numerical predicates](../../cpp/src/motion_numeric.hpp)

At pickup the transaction acquires the target's exclusive reservation and records the measured offset. Each successful loaded segment reconstructs the target from the new carrier coordinate and that offset. Current reach, ownership and the expected offset are checked before moving. Both sweeps must be clear. Positions, revisions and the two physical facts commit together. At a legitimate interruption the target remains at its last committed position, and the transaction clears the reservation and grip. The journal audit independently reconstructs the grip at pickup and each subsequent transport or release. [Execution and interruptions](../../cpp/src/care.cpp) · [Historical custody](../../cpp/src/checkpoint_care.hpp) · [Historical geometry](../../cpp/src/checkpoint_s4.hpp)

## Checks

- Analytical reach at 2 mm and offsets of plus or minus 1 nm are tested near the origin and at 12 m. Both boundary cases complete, and the two true exterior points reject.
- The diagonal and turning fixtures each record 21 actual position facts. They preserve the brood ID, offset and clearance through repeated segments. A side obstacle forces an actual change in direction. Both binary restore and SQLite restore while holding continue exactly.
- Concurrent target selection gives the target one owner. Carrier death, target death, target maturation and a deliberate pause release the target in place. An edit blocking an active loaded sweep emits a blocked interruption. An event-budget failure rolls the transaction back without moving either participant or changing custody.

The grip is a rigid translation proxy. Its exactness establishes ownership and spatial consistency. Grip shape, orientation changes, deformation, force and biological holding behavior remain uncalibrated. [Custody records](../../experiments/s6_3_3_3_r1/probes/custody)
