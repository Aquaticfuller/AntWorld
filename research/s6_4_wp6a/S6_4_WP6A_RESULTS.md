# S6.4 WP-6A modeling policy and authorization package

The accepted baseline is WP-5 `b1dda6745454d81b7413312b1ef011c179bccbce`. The complete `cpp` tree remains `efa5130c13e9e4d66c410810d2a7214e30e8b650`. Core behavior, defaults, histories, accepted evidence and existing codecs retain their original versions. This branch establishes a reviewable decision policy, prospective model design and an independent arithmetic tool.

| Decision | Result |
|---|---|
| Modeling policy | Separate A–D evidence assessment and scoped Simulation Readiness, with admission, withdrawal and revalidation. |
| Nine BR roots | All remain `BIOLOGICAL_BLOCKED`. Under the new readiness policy BR-01, BR-04 and the causal recruitment claim in BR-07 are `NOT_READY`. The other six roots retain `ENGINEERING_ONLY`. No new conditional-use status has been granted. |
| First proposed Core pilot | F1. Finite maternal lipid and protein, individually funded eggs, true local larval rations and separate viable-stage budgets. A funded multi-egg opening is possible without a quota. |
| Competing model | F2. The same F1 material and action paths with timed access to a finite protein compartment. Deferred until F1 leaves a discriminating release-timing discrepancy. |
| Biological implementation and persistence | Awaiting independent approval for the F1 opt-in Core experiment and separate approval for its new checkpoint/history version. Default replacement and independent biological validation have their own future reviews. |

## Results of the independent feasibility screen

The 39 parameter rows distinguish B06's observed clocks and onset, cross-condition and physical derivations, and D-grade engineering ranges. N27's observed warm-room O₂ scale yields about 2.34 J/d under the conditional B05 conversion. FT01 motivates a finite reserve pathway, with effective lipid/protein stock and tissue access still uncertain. A measured wet-mass envelope constrains feasible initial compartments. [Source conditions and equations](FOUNDRESS_AND_BROOD_MODEL_DESIGN.md) [Parameter ranges](FOUNDRESS_PARAMETER_ENVELOPE.csv)

The exact screen recomputes 142 budget rows, including both original warm controls and all 32 ordinary parameter corners for each population in both care arms. The old 0.5 J/200 µg budget still exhausts energy at 500,000,000 ms. At the nominal F1 settings the egg owns 0.408 J of effective lipid energy before its own maintenance. Its positive ideal margin comes from a separate hypothesized stage cost and a funded packet, with the original budget retained as an adverse reference. An ideal single offspring requires at least five positive local rations at the proposed per-act limits, in either population. Sibling competition, real encounter timing, active costs and delayed assimilation can add further limits. All 64 care-on ordinary corners passed the ideal one-offspring necessary inequalities and all 64 care-off corners failed the path that requires local nutrition. Low egg fuel and low water each rule out the ideal hatch in their respective controls. These are bookkeeping bounds. No simulated offspring or actual animal endpoint was observed in this screen.

The 20-row multi-scale matrix separates individual stock, action and stage evidence from colony interactions and long-term survival, provisioning and excavation. The ordinary/check-seed generator emits 960 exact proposed cases. The wider adverse and early-worker arms, observed event receipts, restart, and actual stage/colony diagnostics are WP-6B work. The original paper's sampled cohort outcomes do not set an exact gameplay probability. The planned pattern gate instead requires viable founding across a prespecified ordinary envelope, population and factor strata, with stage clocks, real material transfer and explicit failures. [Protocol](MULTISCALE_ACCEPTANCE_PROTOCOL.md) [Matrix](MULTISCALE_ACCEPTANCE_MATRIX.csv) [Arithmetic receipt](BUDGET_FEASIBILITY.csv)

## Reproduction and checks

Run the following from the repository root. `OUT` is a writable output directory.

```text
python tools/wp6a_budget_screen.py
python tools/test_s6_4_wp6a.py -v
python tools/wp6a_budget_screen.py --emit-cases OUT/f1-case-plan.jsonl
ctest --test-dir build/s6_3_4-release --output-on-failure -j 2
ctest --test-dir build/s6_3_4-debug --output-on-failure -j 2
ctest --test-dir build/s6_3_4-sanitizer --output-on-failure -j 2
```

The local Python checks ran on Python 3.12 and passed all nine tests. The Windows CTest reruns against the unchanged approved builds passed 250/250 in Release (21.00 s), Debug (84.86 s) and ASan/UBSan (302.41 s). The sanitizer run uses `ASAN_OPTIONS=halt_on_error=1` and `UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1`. Linux Release CI verifies the budget receipt and tests. The inherited platform builds and protected evidence steps remain in the workflow. No new native simulation timing was collected for the planning package. The accepted TD-01 and TD-08 budgets remain prerequisites for the subsequent C++ experiment. [Prior controlled evidence](../s6_4_wp5/ENGINEERING_VERIFICATION.md) [Branch CI](https://github.com/Aquaticfuller/AntWorld/actions/workflows/ci.yml?query=branch%3Acodex%2Fs6.4-wp6a-modeling-policy)

| Artifact | SHA-256 |
|---|---|
| `FOUNDRESS_PARAMETER_ENVELOPE.csv` | `4d964635db32371ed13e8e3041f2e6a78900287e3406902366407e97324f1014` |
| `BUDGET_FEASIBILITY.csv` | `ede9eeb266bc4edafcb9f59471803b182797eff962364507eeedda5974db961b` |
| Generated `f1-case-plan.jsonl` | `7a5c5134685726fa794394be4a5c8c33e2e6a08b1ec6469df283b031c73e14e4` |

## Review links

- [Formal policy](../../BIOLOGICAL_MODELING_POLICY.md) and [nine-root evidence and readiness matrix](BR_EVIDENCE_AND_READINESS.csv).
- [Source-level plan, exact tests and ordered WP-6B tasks](WP6B_IMPLEMENTATION_PLAN.md).
- [Independent authorization request and version boundaries](BIOLOGICAL_REMEDIATION_AUTHORIZATION.md).
