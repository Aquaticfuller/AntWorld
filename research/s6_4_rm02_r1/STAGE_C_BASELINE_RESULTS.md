# RM-02 R1 Stage C baseline diagnosis

Stage C used the original frozen matrix after the written Stage B gates qualified. The Release run used C++ tree `a95539621cdf682cb1e0427e1e9f0896aa0bfbb1` and executable SHA-256 `1c329a595bc6cbc141ba8e5e70cf7e9f9a85689f00b1d8f35737f29c3284d0ef`, built with Clang 23.1.5 on Windows. All 72 planned cases exited zero. Six seeds per cell quantify variability of this engineering fixture. Each seed is paired across the relevant conditions. The early window cases share the ordinary seed and initialization with the long-run arm. [Frozen protocol](../s6_4_rm02_sprint/FROZEN_ENGINEERING_PROTOCOL.md#stage-c-frozen-simulated-comparisons) [Run manifest](../../experiments/s6_4_rm02_r1/baseline/freeze.json)

## Audit and scope

| Workload | Cases | Scanned committed events | Scoped facts | Cuts and checked global ledgers | Lost scoped records |
|---|---:|---:|---:|---:|---:|
| 90-day ecology and 180-day depot | 48 | 7,898,937 | 2,334,716 | 5,448 | 0 |
| Ordinary first 48 h | 12 | 7,956 | 7,896 | 240 | 0 |
| Dense 10 s coverage | 12 | 476,184 | 16,896 | 12 | 0 |
| Total | 72 | 8,383,077 | 2,359,508 | 5,700 | 0 |

Each archive has the original input and terminal authoritative checkpoint, Sidecar SQLite database, exact cut list, logs, per-file hashes, state and trace hashes. All 72 applications compared their terminal authoritative checkpoint byte for byte against a single uninterrupted observer-off advance from the initial checkpoint. Each reopened its sidecar against a restored terminal checkpoint and verified the duplicate cut result. The independent decoder verified the ordered sidecar hash chain, exact committed scope, each terminal anchor and all 5,700 mass and energy ledgers. It reconciled 120,216 focal crop cuts. The supplementary analysis checks the queen's body energy and water against actual absorption and egg expenditure at every ecology cut, with 60 horizon ledgers retained. Stage B's existing fault and continuation tests cover restoration beyond the saved endpoint. [Per-run audit](../../experiments/s6_4_rm02_r1/analysis/runs.csv) [Analysis receipt](../../experiments/s6_4_rm02_r1/analysis/analysis_receipt.json) [Queen horizon budgets](../../experiments/s6_4_rm02_r1/diagnosis/queen_body_budgets.csv)

The recorded sidecar payload is 422,016,088 B before encoding and 108,286,612 B stored. All scopes keep committed IDs and source references. Ecology focal body snapshots cover the initial queen and workers. Offspring enter the fact history, but their entire body-store time series is outside this focal scope. Dense cases select the first 64 worker IDs. Their fixed-horizon results are coverage evidence with unadmitted host times.

## Resource paths and outcomes

The finite depot places a large resource source at the origin. Ordinary and protein-scarce arms use the same source position, initial ration and release limits. Their finite protein reserves differ by 40-fold at a given starting population. The positive depot changes both placement and supply. The depot and release reserve quantities also scale with starting worker count. The empty arm retains seeded individual reserves and allows redistribution while providing no external food. Every value in this experiment is an `ENGINEERING_FIXTURE`. [Fixture construction](../../cpp/apps/rm02_fixtures.hpp#L36) [Supply and physiology controls](../../cpp/apps/s6_3_1_fixture.hpp#L45)

Actual flows include worker collection, delivery to nest stock, worker ingestion from that stock and directed gifts. Across the six ordinary-32 runs through day 90, 998 collection and 998 delivery facts each account for 2,148,000 µg carbohydrate. The 48,263 worker nest-ingestion facts also total 2,148,000 µg carbohydrate. The queen received 82,361 µg through 1,404 gifts and absorbed 83,561 µg, which includes the six initial crops of 200 µg. There was no direct queen or larval nest or cargo ingestion in these runs. The empty arm had no external collection or delivery and nevertheless recorded 24 worker-to-larva gifts across its 12 cases, with 160 µg mean larval protein transfer in both group sizes. Its 34 nest ingestions had zero carbohydrate and follow a modeled protein recycling pathway. These are aggregate compartment flows. Individual source bolus lineage is unavailable after crop mixing. [Committed ingestion and supply](../../experiments/s6_4_rm02_r1/diagnosis/committed_ingestion_and_supply.csv) [Gifts by component and recipient](../../experiments/s6_4_rm02_r1/analysis/gifts.csv.gz)

| Day-90 arm | Initial workers | Queen alive / 6 | Mean observed days alive through day 90 | Positive gifts to worker / queen / larva (sum) | Mean queen carb received / absorbed, µg | Mean eggs / eclosed |
|---|---:|---:|---:|---:|---:|---:|
| Depot | 8 | 2 | 54.20 | 1,833 / 539 / 1,673 | 5,642.0 / 5,828.0 | 4.83 / 3.00 |
| Depot | 32 | 6 | 90.00 | 36 / 2,584 / 9,202 | 25,385.0 / 25,585.0 | 35.17 / 29.33 |
| Ordinary | 8 | 1 | 49.98 | 1,799 / 457 / 1,677 | 5,008.5 / 5,199.2 | 4.50 / 3.33 |
| Ordinary | 32 | 0 | 72.30 | 2,179 / 1,404 / 4,334 | 13,726.8 / 13,926.8 | 18.00 / 16.00 |
| Protein scarce | 8 | 3 | 68.15 | 1,913 / 840 / 1,914 | 8,439.8 / 8,639.8 | 7.50 / 4.00 |
| Protein scarce | 32 | 1 | 69.70 | 2,301 / 1,310 / 3,965 | 13,051.5 / 13,251.5 | 16.67 / 13.83 |
| Empty | 8 | 0 | 7.87 | 0 / 0 / 12 | 0 / 200.0 | 2.00 / 0.00 |
| Empty | 32 | 0 | 7.87 | 0 / 0 / 12 | 0 / 200.0 | 2.00 / 0.00 |

Depot-8 had six queen deaths by day 180 (mean observed lifetime 62.56 days). Depot-32 had six surviving queens censored at day 180, with means of 78.67 eggs and 72.50 eclosed workers. Both arms retain every seed. Ordinary-32 has more transfer and eclosion than ordinary-8 on average, and all six ordinary-32 queens still die by day 90. This reproduces the qualitative contrast of the historical depot and ordinary controls on the reviewed R1 C++ tree. [Per-seed endpoints](../../experiments/s6_4_rm02_r1/analysis/horizons.csv) [Earlier controls](../../S6_3_1_RESULTS.md)

Paired seed intervals use 4,096 draws with seed 63101 and describe the simulation cells. At day 90, depot minus ordinary with 32 workers gives +11,658.2 µg queen carbohydrate delivery (95% interval 9,558.5 to 13,161.7), +17.70 observed days alive (10.95 to 23.49) and +13.33 eclosures (8.50 to 16.67). Scarce minus ordinary with 8 workers gives +18.17 observed days (−15.46 to 43.48) and +3,431.3 µg queen carbohydrate (−1,125.8 to 7,244.2). The analogous 32-worker differences are −2.60 days (−14.00 to 8.55) and −675.3 µg (−1,705.7 to 406.5). Neither size shows a resolved scarce-versus-ordinary difference on those endpoints. Feeding, behavior and depletion can change jointly with these treatments. These observed days are limited to day 90, with survivors censored. [All 120 paired contrasts](../../experiments/s6_4_rm02_r1/analysis/paired_contrasts.csv)

## Exposure, choice, dose and uptake

| Scope | Recorded nutrition decisions | Examined candidate ranks | Positive transfers | Positive / zero physiology payloads |
|---|---:|---:|---:|---:|
| Ecology, full horizons | 511,566 | 1,376,046 | 56,636 | 296,299 / 294,545 |
| 48 h, 8 workers | 288 | 0 | 0 | 54 / 378 |
| 48 h, 32 workers | 1,152 | 0 | 0 | 198 / 1,386 |
| Dense-512, first 64 focal IDs | 3,456 | 55,296 | 0 | 3,840 / 0 |
| Dense-2,048, first 64 focal IDs | 3,456 | 55,296 | 0 | 3,840 / 0 |

The work counter measures sampled ranks before eligibility filters. Each 48 h cohort has 120 complete pending and geometric cuts. Every cut includes geometrically near same-colony workers, totaling 960 and 3,840 repeated worker-cut occurrences respectively. Worker snapshots are Paused at initialization (48 and 192 rows) and Rest thereafter (912 and 3,648 rows). All 1,440 nutrition decisions examine zero candidate ranks, consistent with the Nurse gate for gift search. No pending trophallaxis request or typed nutrition opportunity or choice was captured in these windows. The generic rejection counts of 240 and 960 cannot be assigned to a gift without a matching request or typed source. Dense sampling exercises the rank and focal record path while yielding zero committed gifts in its 10 s scope. The early window and dense results cannot estimate failure or choice rates per physical encounter.

Long-run positive gifts comprise 40,793 full and 15,843 partial transfers. The 56,636 recorded donors are in Nurse at the gift event. They give to workers (11,600), queens (10,147) and larvae (34,889). Daily ecology cuts leave many choices and transient requests unobserved. There are 28,374 generic ecology rejections. They do not supply a known zero-dose denominator. Exact zero gift doses from matched rejections are supported by Stage B controls, with zero such matched requests in the Stage C outputs. The 296,309 zero physiology payloads across all 72 cases are a different observation. This zero means no component uptake in that committed physiology update. The positive counts include initial-crop uptake before the first gift, including 200 µg carbohydrate in each empty queen. [Run counts](../../experiments/s6_4_rm02_r1/analysis/runs.csv) [Pending and geometry cuts](../../experiments/s6_4_rm02_r1/analysis/opportunity_coverage.csv.gz) [Uptake records](../../experiments/s6_4_rm02_r1/analysis/uptake.csv.gz)

For 10,147 queen-directed gifts, 10,136 were followed by a positive queen physiology update, nine ended with competing death and two were right-censored. For the 8,758 gifts that contained carbohydrate, 8,756 had a subsequent positive carbohydrate update and two ended with competing death. Observed carbohydrate lags run from 4.679 to 6.000 hours, with median 5.9976 hours. The any-component lag has an observed 120 h maximum. This follows the next positive event in event-ID order and the fixture's six-hour absorption schedule. Several gifts may precede the same pulse. The sidecar has no labeled source boluses and no exact immediate body before/after state for each gift. The lag estimates are temporal associations, with nonobserved endpoints retained as competing or censored. [Gift follow-up rows](../../experiments/s6_4_rm02_r1/analysis/queen_gift_followup.csv) [Distribution and coverage summary](../../experiments/s6_4_rm02_r1/diagnosis/baseline_summary.json)

## Energy deaths with remaining stock

All 37 observed queen deaths are energy depletion. At the preceding daily cut, all 25 deaths with external supply have positive external carbohydrate stock (4,000 to 1,580,000 µg). Fourteen of those have nest carbohydrate (up to 39,057 µg). No living focal initial worker has positive crop carbohydrate at either bracketing cut for these 37 cases. Sixteen cases have some protein in living focal worker crops at the prior cut. Those snapshots neither cover every offspring worker nor measure all stores at the death instant. The median prior-cut lag is 0.655 days. Stock and reach, donor eligibility and dose are different observations.

Two queen corpses have carbohydrate in their observed crop. In depot-8 seed 3, the queen dies at 2,996,000,000 ms with 84 µg in crop and her next scheduled absorption was at 3,002,400,000 ms. In ordinary-8 seed 4, she dies at 2,268,000,000 ms with 56 µg and that same timestamp is the absorption boundary. The existing physiology rule settles energy and processes depletion before an absorption pulse. These facts identify an engineering pathway by which delivered carbohydrate fails to become usable energy in time. They do not identify a biological time constant or support changing the priority in this round. [Death and stock receipts](../../experiments/s6_4_rm02_r1/diagnosis/queen_death_focal_worker_stocks.csv) [Body cuts](../../experiments/s6_4_rm02_r1/analysis/queen_timeseries.csv) [Physiology order](../../cpp/src/physiology.cpp#L63)

## Reproduction

The archived raw directory holds 72 case receipts and complete original files. `freeze.json` pins the executable, compiler, configuration cache, runner, protocol, source commit and all 72 inputs. `completed.json` retains each exit status. Run the verifier to decode and recompute the archived outputs without re-running the model.

```text
python tools/verify_s6_4_rm02_r1_baseline.py
```

To run fresh simulations, use a Release configuration with `ANTWORLD_SANITIZERS=OFF` and `ANTWORLD_PROFILE=OFF`, then use that build's executable, CMake cache and compiler. Supply fresh output and scratch directories.

```text
cmake -S cpp -B build/rm02-r1-release -DCMAKE_BUILD_TYPE=Release
cmake --build build/rm02-r1-release --config Release --target antworld_s6_4_rm02
python tools/run_s6_4_rm02.py --binary <release-executable> --cache build/rm02-r1-release/CMakeCache.txt --compiler <configured-compiler> --out out/rm02-r1-rerun/raw --scratch out/rm02-r1-rerun/scratch --jobs 1
python tools/analyze_s6_4_rm02.py out/rm02-r1-rerun/raw out/rm02-r1-rerun/analysis
python tools/summarize_s6_4_rm02_r1.py out/rm02-r1-rerun/raw out/rm02-r1-rerun/analysis out/rm02-r1-rerun/diagnosis
```
