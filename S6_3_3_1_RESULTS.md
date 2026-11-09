# S6.3.3.1 Brood retrieval, behavioral fidelity and performance validation

| Review axis | Outcome |
| --- | --- |
| Engineering and legacy compatibility | PASS locally. Debug, Release and ASan/UBSan each pass 187 tests. The 180 inherited tests and all 384 historical assays remain. |
| Local retrieval capability | PASS in the frozen engineering fixtures. A caregiver can continue a reachable target, complete successive physical trips and revisit one previously used pickup site. |
| Species-level quantitative validation | NOT PASSED. The B02 revision is exploratory, worker delivery remains low in the original layout, B01 care remains high, and independently observed locomotion exposes a different movement scale. |
| Existing Windows performance gate | PASS for the frozen dense contact and reserve-birth workloads. Pooled advance p50 ratios are 5.4154x and 4.2740x against the unchanged <=6x target. |
| TD-11 care density | OPEN. The separate synchronous care study preserves the full neighborhood and opportunity workload. |

The branch is based on reviewed `de4ddc9`. The protocol froze at `e42a98b`. Baseline event diagnosis and the single candidate froze at `bbb03b7` before Core edits and before obtaining the reserved locomotion data. The implementation is opt-in. The preceding P10 Observability and P01 Queen Care Capability review passes retain their original scope. This submission stops for independent review at S6.3.3.1.

## Where retrieval broke down

At the first decision, 1 ms after release, all 48 caregivers had an initially displaced item within the 6 mm perception proxy. No original caregiver started an untargeted search in this layout. The original mean first approach start was 65.00 s for queens and 50.00 s per worker. Queens and workers changed selected brood identity 4.58 and 4.11 times per actor. Mean inactive time was 519.13 of 600 s for a queen and 1,527.39 of 1,800 caregiver-seconds for a worker group. Eight of twelve queens and 28 of 36 workers started a physically reachable handling bout. The group-level contact endpoint counts any of its three workers.

The original 89 transport terminals contain 85 real moves and four duplicate-action reservation interruptions. A completed segment ordinarily took 10 s and moved the item 1 mm. Nine of 44 caregiver-item attempts reached shelter. Elapsed time among those deliveries ranged from 30 to 280 s, including gaps between segments. After the first deliveries with other displaced brood remaining, zero of nine caregivers started an untargeted search, seven started a new outside approach, one reached a new displaced contact, and zero made another delivery. Available follow-up ranged from 20 to 300 s. Censoring and concurrent worker reservation are retained in the per-actor files. The original planner can convert an invalid sweep to inactivity before logging, so these open-arena results cannot measure all possible geometry failures. [Frozen baseline diagnostic CSVs](experiments/s6_3_3_1/diagnosis/)

## Local episode and event contracts

The existing initiation checks still apply. An ant prefers displaced over sheltered brood within its current local neighborhood, retains the selected identity while it is locally eligible, and makes each approach and transport step through the existing geometry and contact checks. A successful nonzero transport remembers one visited pickup position. Once that item reaches shelter, a bounded return toward the pickup position can find another item through the same local sensing path. The return has its own observable act. Failed, blocked or interrupted actions, lost focus, incapacity and reaching the prior pickup site terminate the appropriate episode. A transport still takes simulation time, reserves its actual target and commits each caregiver and brood move transactionally. Positions are committed at segment terminals.

The three care profiles retain species policy, individual role and age context, and environmental assay metadata. The new policy assumptions are F/`ENGINEERING_FIXTURE`. The default keeps the S6.3.3 checkpoint and event layout. Opt-in schema 12 / physics 14 saves one target and one pickup anchor with its observed bout, validates their evidence on restore, and rolls back with the existing single-writer journal. The registered tests cover repeated trips, local-only detection, factual contact, competing reservations, blocking geometry, in-progress checkpoint/SQLite continuation and allocation-failure rollback. [State audit](research/s6_3_3_1/STATE_MACHINE_EVIDENCE_AUDIT.md), [parameter provenance](research/s6_3_3_1/PARAMETER_PROVENANCE.csv)

## B02 exploratory comparison

The historical placement uses six displaced larvae/pupae, a 50 mm square arena, three-minute acclimation and a ten-minute test. The published experiment uses a circular dish and an odor-familiarized tube. Exact placement, surface cues, ages and behavioral contact criteria are only approximated. The simulation counts an originally displaced identity at its first actual move into the 2 mm shelter radius. First contact is a physically validated handling start. Misses stay in the capped 600 s mean and the binary contact endpoint. The measured all-unit means use 79 queens and 70 first-generation worker groups, averaging own/foreign trials within unit. The 67 paired and 61 productivity cohorts are also reported. [Walsh et al.](https://doi.org/10.1002/ece3.4475), [Dryad source](https://doi.org/10.5061/dryad.qm114cj), [all literature comparisons](experiments/s6_3_3_1/analysis/b02_literature_comparison.csv)

| Condition and metric | Measured | Legacy | Local | Paired local minus legacy, 95% interval |
| --- | ---: | ---: | ---: | ---: |
| Queen, retrieved | 3.772 | 0.250 | 3.667 | +3.417 [3.083, 3.750] |
| Three workers, retrieved | 4.850 | 0.500 | 4.167 | +3.667 [3.250, 4.083] |
| Queen, capped first contact (s) | 94.37 | 396.68 | 95.01 | -301.67 [-407.50, -200.01] |
| Three workers, capped first contact (s) | 40.51 | 230.85 | 50.01 | -180.84 [-253.03, -115.84] |

These paired intervals use 4,096 seed resamples. Against the independent resampling of published units, the residual local worker retrieval error is -0.683 items [-1.188, -0.158]. The queen's residual count error is -0.105 [-0.614, 0.416]. First-contact residuals are +0.64 s [-48.58, 52.48] and +9.50 s [-9.23, 28.63]. Those intervals express uncertainty in this comparison and cannot certify equivalence. B02 motivated the revision and no coefficients were fitted.

In the local policy, all 12 queens and all 36 workers reached contact, up from 8/12 and 28/36. The mean first queen approach remains 65.00 s. The improvement follows perception and initial selection. Mean queen and worker-group paths grow from 7.67 to 52.50 mm and 25.89 to 87.34 mm. Mean inactive time falls to 65.00 queen-seconds and 836.59 worker-seconds. Contiguous loaded episodes in the local runs average 5.74 queen and 6.42 worker segments, with actual reserved moves and a two-tick interval between successive segments. Delivered queen trips span 30–90 s and worker trips 40–120 s. Ten of 424 worker transport terminals still conflict. Among caregivers with other displaced items remaining after their first delivery, all 12 queens and all 22 workers start a pickup-site revisit after 2 ms. A second delivery occurs in 12/12 and 16/22 of those caregivers, with observation-window censoring kept. Queen mean inter-delivery time is 100.02 s and the mean for the 16 observed worker second deliveries is 163.78 s. [Paired endpoints](experiments/s6_3_3_1/analysis/paired_retrieval.csv), [first delivery follow-up](experiments/s6_3_3_1/analysis/first_delivery_followup.csv), [transport terminals](experiments/s6_3_3_1/analysis/transport_segments.csv), [continuous episodes](experiments/s6_3_3_1/analysis/continuous_loaded_episodes.csv)

The 288 prospective simulator holdout runs include all 12 preregistered seeds per layout and care group under both policies. The local queen mean is 4.0 items in the line, mirror and split layouts, and 0.417 in the far layout (paired change 95% interval [0, 0.917]). The local three-worker means are 4.000, 4.083, 4.417 and 1.667. The far layout gives contacts in 4/12 queen and 11/12 worker-group local runs, so eight queens and one group remain censored. Both no-brood and sheltered controls yield zero retrievals, and already sheltered brood is handled normally. The mirrored worker-count difference comes from seed 1061, with three deliveries on the line and four on the mirror. Its first non-reflected move is event 136 at 310006 ms, where the same absolute -X exploratory movement occurs in both worlds. Mirroring the brood leaves those seeded compass draws unchanged. [Holdout figure](experiments/s6_3_3_1/figures/holdout.svg), [raw archive manifest](experiments/s6_3_3_1/raw/manifest.json)

## B01 scoring and biological fidelity

The 80 B01 simulations have byte-identical exported events, windows and scans under both retrieval policies. The article records active brood manipulation within the first ten seconds of a minute and excludes carrying alone. The paper describes 51 windows and the released reversal table uses a denominator of 50. Report both simulated overlaps and separate them from point sampling, actual care-bout residence and overall program residence. The 55-day context is a fixture label. Glass-tube transfer is APPROXIMATE, mesh antennation and chronological-age effects are NOT IMPLEMENTED, and the solid wall is an access control. Passive workers cannot reproduce measured worker brood care or its local feedback. [Majidifar et al.](https://doi.org/10.1111/1365-2435.14536), [raw reversal observations](https://doi.org/10.5061/dryad.pnvx0k6wd)

| B01 condition | Measured 50 scans (%) | Simulated 50/51 overlap (%) | Simulated point sample (%) | Actual simulated care time (%) |
| --- | ---: | ---: | ---: | ---: |
| Absent, 24 h | 6.500 | 23.17 / 23.53 | 15.67 | 15.51 |
| Added, 24 h | 0.125 | 2.83 / 2.78 | 2.00 | 1.76 |
| Removed, 48 h | 6.250 | 22.00 / 22.39 | 15.00 | 14.85 |

The 50-scan errors are +16.67, +2.71 and +15.75 percentage points. Their respective 95% intervals are [11.92, 20.92], [1.63, 3.83] and [10.00, 20.46]. The different observation definitions explain part of the discrepancy. The added-workers simulation has 430 worker opportunities and 21.58 completed contacts per queen-hour on average, taking about 43.17 s. Only actual completed contacts update the local cue. The six-seed absence sensitivity gave 60.33%, 25.33% and 4.33% simulated 50-scan overlap at 15/60/240 s inactivity intervals. These controls expose dependence on the decision clock. The paper leaves the causal contribution of direct contact versus worker care reducing local brood demand unresolved. [B01 comparisons](experiments/s6_3_3_1/analysis/b01_literature_comparison.csv), [matched window reconstruction](experiments/s6_3_3_1/analysis/b01_windows.csv), [B02 and B01 figure](experiments/s6_3_3_1/figures/b02_b01.svg)

## Independent scientific evidence

Lenoir's L. niger worker experiments document repeated trips and immediate re-departure after deposition. The different apparatus and relative counts leave queen-trip times and pathway cues unknown. Brood recognition, return orientation and recruitment of other ants are separate questions. Primary L. niger foraging experiments support the combination of trail following and visual orientation. Lenoir's proposal that brood carriers recruit through trails remains a hypothesis. The implemented retrieval uses one private visited position. No task-specific pheromone experiment or comparable timed brood trajectory was located in the examined public records. Carthy Part I is an access lead for loaded orientation. Its pp. 275–303 were unavailable through the consulted routes and no measurements were taken from it. [Evidence and access ledger](research/s6_3_3_1/EVIDENCE.md)

The independently reserved flat-worker Dataset S1 from Khuong et al. contains 69 trajectories from three colonies. Median net speed was 4.684 mm/s, median raw path speed 50.638 mm/s and median 1 s subsampled path speed 37.677 mm/s. The care clock allows 0.100 mm/s per full 1 mm step. This ceiling is about 47 times below the measured median net speed and 377 times below the coarsened path median in the unloaded exploration apparatus. These results show why a matching ten-minute count cannot calibrate the motor timescale. Queen, loaded worker and actual tunnel travel require their own data. [Khuong article](https://doi.org/10.1371/journal.pone.0076531), [Dataset S1](https://doi.org/10.1371/journal.pone.0076531.s005), [derived tracks](experiments/s6_3_3_1/independent_movement/flat_worker_tracks.csv)

## TD-11 and formal performance

The TD-11 matrix covers 1, 8, 32 and 128 concurrent caregivers, with one and four sheltered brood per caregiver, both policy variants, two layouts and four replicates per cell. It reports each phase separately and retains every fact. The open arena scans all C+B individuals per CareWake in both layouts. The initial simultaneous opportunity count is C*(C-1+B) in the shared colony and B with isolated colonies. The difference between candidate examinations and the opportunity journal isolates the effect of local overlap, although dispersal also changes colony partition.

| Local policy, four brood per caregiver | 1 caregiver | 8 caregivers | 32 caregivers | 128 caregivers |
| --- | ---: | ---: | ---: | ---: |
| Dense advance p50 (ms) | 0.016 | 0.281 | 3.236 | 50.872 |
| Dispersed advance p50 (ms) | 0.015 | 0.105 | 0.623 | 6.185 |
| Dense candidates examined | 15 | 640 | 12,000 | 164,480 |
| Dense committed opportunities | 12 | 624 | 11,925 | 164,223 |
| Dispersed committed opportunities | 12 | 76 | 280 | 984 |

At 128 caregivers, the dense and dispersed cases perform 123 and 118 completed brood handling acts, respectively. They retain 166,568 and 3,399 journal facts, encoding to 34,892,172 and 621,735 bytes. Checkpoint/restore p50 is 99.731/78.007 ms dense and 2.061/2.959 ms dispersed. The fixture isolates geometry-free neighborhood and event pressure with no measured nutrition transfers. It leaves geometry-index, longer duration and storage traffic open. An initial harness export used `summary().trace_hash`, which returns a zero placeholder. Its full 128 rows remain. The corrected report reads the actual snapshot trace outside measured phases and retains both sets. Both formal timing executables retained their recorded SHA-256 values. [TD-11 raw and quantiles](experiments/s6_3_3_1/analysis/density_summary.csv), [density figure](experiments/s6_3_3_1/figures/td11.svg)

The independent native counter passed the pinned mapping probe. All six correct-workload formal sessions qualified. The original ordinary-birth executable choice was a setup error discovered by the historical checkpoint and hash comparison. Its 168 rows remain separate. A new freeze and exact workload identity receipt preceded the reserve-birth-only batch. Old failed, preliminary and inconclusive batches remain in history. [Detailed performance results](S6_3_3_1_PERFORMANCE_RESULTS.md)

## Reproduction and review files

- All 384 legacy runs were replayed. The comparison matched all 45,443,005 exported rows by identity, outcome and nutrient amounts, with a 1e-12 m cross-serialization tolerance. Windows and scans were equal and only incidental timing was excluded. [Legacy replay receipt](experiments/s6_3_3_1/historical_replay.json)
- Release, Debug and ASan/UBSan each passed 187/187. Windows sanitizer options use `detect_leaks=0`. Cross-platform CI and the additional retrieval replay run through the existing workflow. [Test logs](experiments/s6_3_3_1/verification/)
- The raw archive contains 48 historical-placement retrieval runs, 288 holdout retrieval runs, and 80 B01 runs. Each new run checks conservation and a checkpoint round trip. Dedicated regressions also compare future continuation. [Artifact index and commands](experiments/s6_3_3_1/README.md)
- The C++ change list accompanies the state audit. Remaining questions include maternal provisioning, calibrated activity, long-distance trail recruitment, functional nest structure and long-history storage. [Code and state audit](research/s6_3_3_1/STATE_MACHINE_EVIDENCE_AUDIT.md), [technical and scientific debt](docs/08_Open_Questions.md)

Engineering capability, conditional fixture performance and species fidelity are separate findings. The next independent review can evaluate the bounded retrieval candidate and the remaining scientific and performance debt.
