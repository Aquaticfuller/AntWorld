# S6 evidence index

All biological inputs and policy coefficients in this archive are **ENGINEERING_FIXTURE**. The controlling protocol is `docs/35_S6_Integration_and_Validation_Protocol.md`, frozen at `d86372f` before implementation. `CONTACT_PROTOCOL.md` and `INTEGRATION_DETAILS.md` specify previously omitted fixture details before their measurements. No source is added after initialization, no seed is filtered, and no physiological/pheromone coefficient is fitted to keep the colony alive.

## Provenance

| Evidence | Measured source |
|---|---|
| `baseline/` | Approved S5 C++ source `fe4466cb09e913f4c4fe7863a0c5fd84eecf21da`; final S5 report `54fc129`. |
| `nutrition/`, `contact_initial/` | First S6 nutrient/index implementation `80741cb`; all original outcomes and the missed contact scaling target remain. |
| `nutrition_final/`, `surplus/`, `surplus_sensitivity/`, `integrated/` | `e7c36ef858ea92960381213b280f1e5723eca35e`. |
| `sensitivity/`, `long/`, `performance/` | Final measured C++ source `3636f22458d0a6fc0c2c5cb22d776dda98d1d6a9`. |
| `reproduction/` | Full S3/S4/S5 matrices and the first complete S6 seed (eight conditions, 24 modes) on final source `3636f22`. S6 canonical state/trace hashes and every exported semantic field match the earlier source exactly on this host. |
| `executed_tests.csv`, `verification.json` | 601 actually executed local test results, retained inherited names, hardware/toolchain and the five successful source CI jobs. |

The final source change formats new code, replaces vector-containing frozen automatic choices with scalar contact-work records for allocation-failure portability, and adds a remote-state independence test. It does not change model inputs or decision rules. Subsequent delivery commits contain analysis, evidence, documentation and CI integration rather than ecological policy changes.

## Data interpretation

See document 36 for units, metric definitions, source/evidence relationships and export limitations. The 60 S5 metrics retain their existing meanings. Each primary case has one normal, one accelerated and one recovered replica; these are exact-continuation checks, not three independent seed observations. Mirrors are paired within each seed. Food-absent cases have no fabricated source rows. Non-emergers, dead identities and unspent/dead inventories remain included.

`analysis/` and `figures/` are derived, reproducible artifacts. `analysis/nutrition_cases.csv` reconstructs remaining larval protein demand and accessible surplus from the colocated assay's actual donor/brood inventories. Surplus excludes retained tissue and each larva's own unmet requirement. `analysis/audit.json` records canonical-LF SHA-256 hashes of raw files and explicit PASS/FAIL contact targets. Wall-time quantiles use all ten repetitions without trimming. Ecological intervals use 4,096 bootstrap resamples, analysis seed 6006; surplus all-success fractions also carry Wilson intervals.

The first and final SD-04 archives have identical brood endpoints. In 64 zero-protein, initially larval cases the final local-request implementation additionally transfers 430 ug carbohydrate/water per case; it still transfers zero protein and produces zero adult brood. Both original transfer records are retained. Seven legacy cases have remaining larval protein shortfall alongside colocated surplus; the local deficit-cap cases have none. This is a finite local-mechanism result, not a species calibration or a guarantee under inaccessible/insufficient resources.

Every integrated output directory also retains its complete per-case SQLite database locally, including all facts, observations and two checkpoint generations. The CSV event file is a selected evidence projection. SQLite databases are reproducible output, excluded from Git; no fact history is deleted to reduce the reported storage size. Matching replicas intentionally use the same fixture WorldId in separate databases; qualify references by the complete experiment case key when comparing cases.

## Execution notes

Correctness builds and independent ecological suites may overlap on this host. Integrated `setup_ms`/`advance_ms`/`save_ms`/`load_ms` describe those measured executions, not isolated latency acceptance. Final contact benchmarks run after builds and ecological suites complete. Process peak RSS is a lifetime peak over benchmark case order.

The primary matrix began in a sequential shell batch. Sensitivity and long continuation were subsequently launched as independent processes in their own output directories, using the final tested executable and unchanged complete seed grids. After primary completion, the original batch's duplicate sensitivity launch stopped at the runner's explicit existing-CSV guard, without opening or overwriting the independently completed evidence. The shell consequently returned a nonzero status; the three actual suite runs completed successfully. This orchestration guard is separate from biological outcomes and invariant failures. Execution logs remain under `out/`.

Use the exact portable commands in S6_RESULTS.md. Scripts refuse to reinterpret a partial matrix as a completed one. The finite 600/1,800 s protocol does not establish months-long ecology, sustainable reproduction, general underground foraging, reliable long-distance trail recruitment or realistic Lasius niger nest morphology. S7 requires independent review and explicit authorization.
