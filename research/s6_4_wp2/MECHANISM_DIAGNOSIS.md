# WP-2 frozen experiments and mechanism diagnosis

All 228 cases have complete selected histories and exact same-schedule observer-off checkpoints after a midpoint restore. An independent reader verified 13,805,895 examined events, 13,805,265 selected facts and 126,684 cuts with no dropped rows in the completed cases. It verified 2,406,474 focal energy and water balances from actual uptake, loss, egg allocation and body stores. The independently decoded global nutrition ledgers and per-cut soil receipts reconcile throughout. Current body histories cover the initial focal ants. Later births, progression, transfers and deaths remain in the event records. [Case and analysis receipts](../../experiments/s6_4_wp2/analysis) [Assay protocol](FROZEN_PROTOCOL.md)

| Stratum | Complete | Examined events | Scoped facts | Verified cuts | Focal body checks |
|---|---:|---:|---:|---:|---:|
| 90-day activity | 48 | 7,035,291 | 7,035,099 | 103,728 | 2,178,288 |
| 21-day integrated care | 24 | 2,024,515 | 2,024,419 | 12,120 | 181,800 |
| B01 | 36 | 4,589,380 | 4,589,302 | 7,596 | 38,286 |
| B02 | 120 | 156,709 | 156,445 | 3,240 | 8,100 |

The first observation attempt finished 213 of 228, with three database quota failures and twelve oversized cuts. All 72 long cases were then replayed with hourly host cuts. Fifty-seven successful first attempts matched the corrected terminal checkpoint bytes, state, trace, RNG and event counts. The fifteen failed attempts and available data remain linked. The largest corrected long-run database was 54,706,176 B and the largest long-run payload was 1,625,830 B. Care and nutrition facts retain their original IDs and contents. [Cut adjustment](HOURLY_STORAGE_CUT_AMENDMENT.md) [First attempts](../../experiments/s6_4_wp2/baseline) [Activity archives](../../experiments/s6_4_wp2/activity_hourly) [Integrated archives](../../experiments/s6_4_wp2/integrated_hourly)

## RM-03 activity, waiting and expenditure

Means below weight seeds equally. Each per-seed percentage uses the living time of workers seeded as adults. Committed displacement counts include position-changing actions; dwell intervals use changes of the stored program. The word active in the program column means the cost mask in `expenditure`. Known duration for physical work is restricted to timed typed care, and legacy movement supplies only endpoints.

| 90-day arm | Workers | Active program % | Rest program % | Committed moves per worker-day | Dissipated nJ per worker-hour |
|---|---:|---:|---:|---:|---:|
| Depot | 8 | 37.205 | 62.517 | 0.000 | 4,939,379 |
| Depot | 32 | 32.408 | 67.315 | 0.000 | 4,766,670 |
| Ordinary | 8 | 35.632 | 64.091 | 0.863 | 4,882,736 |
| Ordinary | 32 | 26.930 | 72.784 | 39.686 | 4,569,468 |
| Protein scarce | 8 | 38.844 | 60.878 | 1.273 | 4,998,379 |
| Protein scarce | 32 | 26.963 | 72.745 | 39.211 | 4,570,685 |
| Empty | 8 | 2.546 | 96.151 | 249.170 | 3,691,643 |
| Empty | 32 | 1.408 | 97.303 | 214.561 | 3,650,705 |

The empty arms have the most committed moves per exposed worker-day and the smallest active-program exposure. Depot food can be collected at the origin, and Nurse dominates the active mask there with zero committed focal worker displacement. Ordinary-32 and scarce-32 show similar mean task dwell and expenditure under this fixture. Among the 44,455 initial worker Nurse intervals in the activity stratum, 26,758 last exactly six hours and the median is six hours. Rest's median is 12 h, and the median Forage interval is about 178 s. The care experiment also contains short Nurse intervals created by the finite lease. These are different duration processes with a common program label.

The older 97.6% active-program result belongs to another fixture and observation window. WP-2's 1.408–38.844% means demonstrate that it cannot be generalized across these inputs. The source explains a mechanism for misleading occupancy. Dwell and local eligibility can retain an active program between sparse work acts. A short, frequently moving trip can contribute little program time. The elapsed role mask still charges the surcharge throughout Nurse, Forage and Excavate. In the activity stratum all physical activity duration remains `UNOBSERVED`, despite 2,761,820 committed displacement facts across all ages and 1,287 committed Rested facts. Rested establishes an action outcome without a continuous body or sleep interval. [Dwell intervals](../../experiments/s6_4_wp2/analysis/program_intervals.csv) [Paired seed comparisons](../../experiments/s6_4_wp2/comparison/ecology_paired.csv) [Earlier S6 fixture](../../S6_RESULTS.md)

Among workers seeded as adults in the 90-day experiments, 320 energy deaths include 13 with crop carbohydrate at death. For those 320 deaths, elapsed time since the last positive carbohydrate pulse has a median of 458.73 simulated hours. In the 21-day underground stratum, 120 workers seeded as adults die from energy depletion, all in the empty arms. Their observed dead crops contain zero carbohydrate. Young individuals, death censoring and initial crop uptake are separate. The nominal basal plus program surcharge in these worker depletion records matches the committed dissipation. The bookkeeping is evidence about the encoded cost, not a physical calorimetry measurement. Water loss is about 24 µg per worker-day under the configured rate, with small reductions at resource exhaustion. Egg export, maternal dissipation and actual carbohydrate uptake have separate rows. [Individual endpoints](../../experiments/s6_4_wp2/analysis/individuals.csv) [Body state cuts](../../experiments/s6_4_wp2/analysis/body_cuts.csv.gz)

## RM-06 brood handling and feeding

In the 24 paired underground worlds there are 12 unique completed placements, all in the care-on arm. The initial cohort has one displaced brood target per world. Across both arms, 1,265 larval feeding results are joined to positive committed nutrition transfers and 74 actual brood displacements include transport and arrangement. At 16 initial workers with balanced input, the queen absorbs 1,026.0 µg mean carbohydrate with care and 2,104.3 µg in the paired control. The signed paired difference is −1,078.3 µg, with a 95% seed-bootstrap interval of −2,785 to +860 µg. Mean counts of confirmed larval feeds are 37.3 and 273.7, a difference of −236.3 (−280.0 to −158.0). These observed resource-routing outcomes use three seed pairs. They leave the effect of any single decision rule unidentified. [Integrated seed-level endpoints](../../experiments/s6_4_wp2/comparison/ecology_by_case.csv)

The sampled B01 worker-access sequence preserves lower manipulation scans after addition and recovery after removal. Compared with the archived raw biological units, the signed mean scan percentage differences are −2.167 pp without workers, +0.875 pp after addition and +0.750 pp after removal. Intervals are independent resampling of six simulation seeds and sixteen biological queen labels within each focal comparator. The latter data were already used in development. The solid barrier, sham and no-brood results remain in the table. The simulated score is an overlap with a known Inspect/Arrange/Clean interval, including a timed interrupted prefix. Feeding is reported separately. [Per-window rates](../../experiments/s6_4_wp2/comparison/b01_windows.csv) [Empirical comparison](../../experiments/s6_4_wp2/comparison/b01_comparison.csv)

| B01 focal window | Simulation positive scans | Raw biological mean | Difference 95% interval, pp |
|---|---:|---:|---:|
| Without workers, 24 h | 4.333% | 6.500% | −7.625 to 3.458 |
| With added workers, 24 h | 1.000% | 0.125% | 0.083 to 1.667 |
| Workers removed, 48 h | 7.000% | 6.250% | −5.484 to 6.083 |

The B02 near layouts put at least one item within the engineering sensory radius immediately. Line and split first target selection averages 10.001 s, with first close-act onset near 10–11 s. The fixed far layout leaves ten of 24 six-item trials without a target selection by the horizon. In far trials with any selection, mean first selection is 250.158 s. Across the near-line group both simulated actor types place six items per 600 s. The split means are 4.5 for queens and 5.5 for trios, far means are 2.0 and 5.0, and the solid barrier groups place zero. Each layout mean pairs own and foreign sources within each seed, then gives equal weight to the six seeds.

The 371 B02 placements represent 360 distinct trial-target pairs, so 11 placements are repeats. The single-item controls all place the one target, but show nine completed pickups across six queen cases and eleven across six trio cases. The twelve empty controls have zero pickups. Another 228 of 588 trial-target pairs are unplaced and right-censored, with no recorded target selection or contact proxy for those targets. The largest observed B02 interruptions were blocked walking (158) and conflicting pickup before a confirmed custody (15). Every observed completed pickup in this matrix reached placement. This bounds the observed failure location and leaves held-brood interruption frequency unestimated here. Timed known prefixes and selected-only actions remain separate. There are 50 timed active or inactive starts open at the scored boundaries, and 10,089 unmatched selected legacy markers in integrated cases. The latter have an unobserved terminal status.

B02's median completed loaded-motion time is 1.750 s, median pickup-to-placement elapsed time is 2.266 s, and median simulated loaded movement rate over completed recorded segments is 3.994 mm/s. Median selection of the next search after placement is 1.000 s. The separate pickup/placement timers, return and revisit act records and failed pre-pickup choices are retained. The physical first encounter with a target is unobserved, and first target selection is a model proxy. [Per-target sequence](../../experiments/s6_4_wp2/analysis/retrieval_targets.csv) [Custody and continuation](../../experiments/s6_4_wp2/analysis/custody.csv) [Phase and failure counts](../../experiments/s6_4_wp2/analysis/care_phases.csv)

## Archive reanalysis and fresh execution

The original and supplemental catalogs freeze binaries, compiler, sources, protocol, case list and all receipts. The archived cases can be decoded without launching a new simulation. The comparison re-reads the preserved B01 and B02 data with source digests.

```text
python tools/analyze_s6_4_wp2.py experiments/s6_4_wp2/baseline out/wp2-analysis --supplement experiments/s6_4_wp2/activity_hourly --supplement experiments/s6_4_wp2/integrated_hourly
python tools/summarize_s6_4_wp2.py out/wp2-analysis out/wp2-comparison
python tools/summarize_s6_4_wp2.py experiments/s6_4_wp2/analysis experiments/s6_4_wp2/comparison --check
```

For a fresh complete run at the corrected application commit, configure Release with profiling and sanitizers disabled. The same runner may select a full declared stratum with `--stratum activity|integrated|b01|b02`. Historical attempt reproduction uses the separately pinned executable and application source in each catalog.

```text
cmake -S cpp -B build/wp2-release -DCMAKE_BUILD_TYPE=Release
cmake --build build/wp2-release --config Release --target antworld_s6_4_wp2
python tools/run_s6_4_wp2.py --binary <binary> --cache build/wp2-release/CMakeCache.txt --compiler <compiler> --out out/wp2-fresh --scratch out/wp2-scratch
python tools/analyze_s6_4_wp2.py out/wp2-fresh out/wp2-fresh-analysis
python tools/summarize_s6_4_wp2.py out/wp2-fresh-analysis out/wp2-fresh-comparison
```
