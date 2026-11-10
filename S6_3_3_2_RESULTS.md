# S6.3.3.2 Brood Care Fidelity and Integration

| Review question | Result |
| --- | --- |
| Engineering correctness and opt-in integration | PASS in the frozen engineering scope. All 195 local tests pass in Debug, Release and ASan/UBSan. Actual care uses the ordinary Core scheduler with a single motor owner. |
| Direct biological support | Both castes retrieve displaced brood. The B01 reversible worker effect and the B02 acute own/foreign context have direct support. Local persistence and physical loaded motion are plausible abstractions. The detailed sensing and task rules remain hypotheses. |
| Species-level quantitative validation | NOT PASSED. All line trials hit the six-item ceiling, early placement and worker first contact are too fast, and far-layout queen discovery still often fails. B01 added-worker care remains above the measured frequency. |
| TD-01 and protected TD-08 | PASS under the unchanged 6x dense advance gates. Current contact and reserve-birth p50 growth are 5.4338x and 4.2285x with all six sessions qualified. |
| TD-11 | OPEN. Exact spatial filtering improves dispersed candidate work. Dense opportunity production and history growth remain. |

The stage is ready for independent review in this scope. The ecological, scientific and engine gates for S6.3.4, S6.4 and Unity remain separate.

## Frozen baseline

The [protocol](docs/58_S6_3_3_2_Frozen_Baseline_and_Protocol.md) and [pre-implementation design audit](docs/59_S6_3_3_2_Care_Design_Audit.md) were committed as `de9107b`, before behavior changes. Reviewed base `05a6847` and its source, experiment and research trees remain in history. The 384 S6.3.3 experiments and 416 S6.3.3.1 experiments are preserved. All 416 latter runs were rebuilt in the current Release executable. Comparisons matched the windows, scans, non-timing endpoints and 9,016,440 exported facts, with the inherited 1e-12 m allowance for coordinate serialization. [Replay receipt](experiments/s6_3_3_2/historical_replay.json).

## Code changes

- [Care profiles and act vocabulary](cpp/include/antworld/core/care.hpp), [care engine](cpp/src/care.cpp), and [movement rules](cpp/src/care_internal.hpp) separate perception and initiation, translation, pickup, actual loaded custody, placement and search. A 1 mm stride limits each local geometric segment. Duration follows the separate caste/load speed and the world cap. Both entities pass actual collision checks. Custody and motion are transactional. A small private revisit is tied to the last physically visited pickup position.
- [Ordinary autonomy](cpp/src/ecology.cpp), [physiology ownership](cpp/src/physiology.cpp), and [reproduction arbitration](cpp/src/long_term.cpp) share a single care motor lease with existing programs. Workers retain their regular scheduler, identity, routes and local nutrition rules. Queens keep a queen-only local care branch. A funded laying event can release an active lease while preserving its resource ledger and timing. Species, Individual and Environment profiles stay distinct. The contract is opt-in at world configuration.
- [Checkpoint format](cpp/src/checkpoint.cpp) and [care restore](cpp/src/checkpoint_care.hpp) preserve older schema/physics paths. Motion-enabled checkpoints use schema 13 and physics 15. Actual held custody, paused state, target identity, queued wakes, raw facts and RNG continuation survive restore. [Surface evidence](cpp/src/checkpoint_s2.hpp), [autonomy evidence](cpp/src/checkpoint_s6.hpp) and [behavior windows](cpp/src/observations.cpp) recognize the new committed acts.
- [Same-colony profiling and indexed query](cpp/apps/antworld_s6_3_3_2_density.cpp) separate neighbor candidate work, factual opportunity generation, journal work and history encoding. The index path retained all facts and order in the 64-case exact comparison. A short paired normal-autonomy probe recorded actual placements, post-care foraging, funded births and food collections, with deterministic partitioned restore. It did not realize nutritional exchange during its short window. Inherited transaction tests remain in place.

The historical motion and review data remain unchanged. The [state-machine audit](research/s6_3_3_2/BROOD_CARE_STATE_MACHINE_AUDIT.md) and [integration contract](research/s6_3_3_2/CARE_AUTONOMY_INTEGRATION.md) describe the guards and spatial limits. Fine surface cells support physical translation. A coarser lattice with centers farther apart than the configured stride can support contact care while preventing translation. The 3D implementation checks local swept paths and can be blocked by corners. Long detours and simultaneous biological actions were outside the frozen scope.

## Biological results

The new archive contains 396 retrieval runs, 76 B01 runs with 11,628 scan records, and 12 paired ecological probes. All recorded continuation and conservation checks passed. The B02 line mean was 6.0 for both groups, compared with 3.772 for queens and 4.850 for first-generation three-worker groups. Queen and worker mean capped contacts were 65.51 s and 10.21 s, compared with 94.37 s and 40.51 s. In the far layout, 8 of 12 queens and 1 of 12 worker groups had no handling contact by 600 s. The mirrored, split, empty and sheltered controls and the one-factor sensitivities retain their separate outcomes.

In B01 the 50-scan active-care estimates were 2.833%, 1.000% and 6.667% for worker absence, addition and removal, compared with 6.500%, 0.125% and 6.250%. These are observed act windows. The scoring separates duration, point sample and program residence. Changing manipulation duration can shift the phase of later bouts relative to a scan. The shift and the worker-contact effects need independent experiment-level measurement before calibration.

The user-supplied full Carthy Part I includes timed carrier paths from two trained workers. Derived normal-light path rates span 11.75–29.89 mm/s, using separately transcribed distances and times. The printed speed column is internally inconsistent. Those observations constrain the plausible context but do not calibrate the 4 mm/s worker load fixture, a caste ratio or a B02 trajectory. Khuong's 69 flat tracks measure unloaded workers. No matched queen loading, unloading or search tracks were found. [Carthy Part I](https://doi.org/10.1163/156853951X00304), [Khuong et al.](https://doi.org/10.1371/journal.pone.0076531).

The [B01/B02 report](research/s6_3_3_2/B01_B02_VALIDATION.md) includes all endpoint errors, paired confidence intervals, published origin contrasts and censored observations. B02 was used for exploratory model revision. New simulator seeds are spatial robustness checks. The independently reserved Okrutniak colony relocation has a different light trigger and group scale. Exact reproduction remains NOT IMPLEMENTED. All new unmeasured parameters remain `ENGINEERING_FIXTURE`. [Full source locators and parameter evidence](research/s6_3_3_2/BROOD_MOTION_EVIDENCE_AND_PARAMETERS.md).

## Verification and reproduction

| Local Windows x64, Clang 23.1.5 | Executed | Outcome |
| --- | --- | --- |
| Release | `ctest --test-dir build/s6_3_3_2-release --parallel 4 --output-on-failure` | 195/195, 33.52 s |
| Debug | `ctest --test-dir build/s6_3_3_2-debug --parallel 4 --output-on-failure` | 195/195, 81.20 s |
| ASan and UBSan | `ctest --test-dir build/s6_3_3_2-sanitizer --parallel 4 --output-on-failure` | 195/195, 152.71 s |

Local Windows ASan uses `detect_leaks=0`. Linux CI enables leak detection. Eight new tests cover independent clocks and exact SQLite continuation, ownership and corruption, controlled conspecific origin, pickup competition, a geometry closure, death while loaded, ordinary task resumption, and funded queen preemption. The allocation test sweeps failures in pickup, loaded motion, release and their checkpoints. All older tests remain registered. [Per-test outcomes](experiments/s6_3_3_2/verification), [cross-platform CI runs](https://github.com/Aquaticfuller/AntWorld/actions/workflows/ci.yml?query=branch%3Acodex%2Fs6.3.3.2-brood-care-fidelity).

The [performance report](research/s6_3_3_2/TD_11_PERFORMANCE_RESULTS.md) separates the profiled same-colony experiment from protected timing. At 128 caregivers and four brood each, the dispersed candidate count fell from 281,600 to 2,419. Dense runs still wrote 164,223 opportunity records and a 35.21 MB checkpoint over 60 simulated seconds. All original fact and state hashes matched. The current protected run retained 504 raw timing rows and every telemetry sample. This is a bounded gate result.

The [experiment index](experiments/s6_3_3_2/README.md) lists the raw CSVs, extraction and plotting commands, exact scripts and profiled reproduction. The tracked source register has DOI, conditions, locator and scope. Full texts remain local.

## Review debt

SD-09 and TD-11 stay open. A later reviewed design can distinguish realistic sheltered placement and proximity sensing, the shape of directed return and undirected search, variation in pickup and drop, and actual biological decision and contact time. Separate datasets are needed for calibration and validation. Historical negative foraging, colony survival, scarcity, readiness and timing evidence is retained. [Open questions and debts](docs/08_Open_Questions.md).
