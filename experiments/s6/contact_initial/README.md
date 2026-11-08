# First matched contact measurements

Source: `80741cb`, Release clang 23.1.5 / Windows x64. Command: `antworld_s6_contact_benchmark out/s6-contacts 10`. Protocol: document 35 and `experiments/s6/CONTACT_PROTOCOL.md`. Captured before integrated ecology experiments. All 120 raw repetitions are retained, including large host-time variation; no trimming or timing sample selection.

Dense 2048 exhaustive/bounded advancement medians: approximately 35,307.049 / 1,176.490 ms (30.01x). Bounded 512->2048 median growth: 7.518x, **FAIL against the <=6x empirical goal**. The candidate cap of 16 passes structurally. These timing distributions do not isolate host contention or allocator/map cost and should not be interpreted as a universal speed guarantee. Subsequent final-source measurements must remain separate, never overwrite these observations.
