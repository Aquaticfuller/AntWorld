# RM-01 frozen engineering protocol

The comparator is `51436048db93da8fbcfe4ff738ff74644bfa1731` with C++ tree `277cc8e78cc1acd1cf4a74bf39d08dfdb6a99c69`. Core CI run 42983936355 was checked before branch creation. It completed successfully at that SHA with Windows Debug and Release, Ubuntu Debug and Release, and sanitizers all successful. This protocol applies the approved isolation and success criteria. [Core CI](https://github.com/Aquaticfuller/AntWorld/actions/runs/42983936355) [Phase 4 implementation gate](../s6_4_preflight/S6_4_PHASE4_FIRST_IMPLEMENTATION_GATE.md)

## Profiles and fixtures

Resolve an explicit fixed reference row at the application boundary. Parse the declared days exactly into signed integer milliseconds and reject wrong units, unsupported identifiers, nonmatching provenance, malformed values and overflow. The legacy control uses 2 d. The B06 nominal 25 °C treatments with near-24.7 °C egg means use 16.7 d (1,442,880,000 ms) for Borisovka and 15.7 d (1,356,480,000 ms) for St. Petersburg. These inputs refer to specific published means, with no interpolation. Expenditures, reserves, all other biological quantities and assay schedules retain `ENGINEERING_FIXTURE` status. [B06 pp. 166–169, Table 2](https://doi.org/10.1023/B:JOEY.0000033808.45455.75)

| Arm | Focal entry | Reserves and required outcome |
| --- | --- | --- |
| Legacy | Seeded egg and first funded birth | 500,000,000 nJ and 200 µg water. Keep the 2 d clock. Require hatch at entry + 172,800,000 ms. |
| Original budget, both warm rows | Seeded egg and first funded birth for each row | Same reserves, 1 nJ/ms, 1 µg per hour, no egg uptake. Require energy death at entry + 500,000,000 ms with 62 µg water remaining. Preserve later observation through clock + 1 ms and the absence of hatch. |
| Timing sentinel, all three rows | Seeded egg | `ENGINEERING_FIXTURE` reserves of D + 4 nJ and floor((D + 1 ms) / hour) + 1 µg water. Require living egg at D − 1 ms, hatch at D and the same identity at D + 1 ms. |
| Priority | Seeded egg | For each warm row use D nJ and sentinel hydration to tie depletion to hatch. For the 2 d row use sentinel energy and 48 µg water to tie dehydration to hatch. Require an actual death fact on the boundary and zero hatch facts. |
| Interruption | Seeded egg | Schedule a fixture death at clock − 1 ms in a legacy timing sentinel. Require termination and removal of the later physiological transition. |

Use seed 1 for the short matrix. Read the first terminal fact using the egg identity and entry event. Exercise a one-shot advance after entry, segmented advancement, a checkpoint cut partway to the expected first outcome, and segmented SQLite publications at the mid-egg and first terminal cuts. Restore at both cuts. Compare full checkpoint bytes, state and trace, queued events, effective configuration, stored progress and canonical facts. Read observations without advancing state and confirm preterminal reserves and post-outcome records at the declared ticks. Preserve all observed facts from every short arm. Fixture death, invalid application setup and late cut recovery are technical controls.

## Ecology and exact comparison

Use the original S6.3.1 worker counts 8 and 32, balanced ordinary and scarce-protein supply for 90 d, and finite depot supply for 180 d. Retain the original reserve-mode-1 inputs and recorded outcomes. Execute seed 1 matched pairs with each warm row and the legacy clock. The app needs a local setup path because the frozen fixture constructs physiology immediately. Its legacy initialization must be byte-identical to the frozen fixture for each ecology case. Only the queen's transmitted egg clock varies in the warm cases. Compare full state and facts to uninterrupted execution, report all births and first egg outcomes including end-of-run censoring, and reconcile mass, energy and soil. Preserve the S6.3.4 original seeded 21 d and 180 d continuation matrix and inherited tests. [S6.3.1 archive](../../S6_3_1_RESULTS.md) [Durable matrix](../../docs/64_S6_3_4_Frozen_Durable_History_Protocol.md)

## Performance

Use the original TD-01/TD-08 controlled workloads and their frozen `<=6x` threshold. Preserve the current instrument, admission rules, schedules and unsuccessful attempts. Use doc 64's original workload matrix and resource ceilings through its unchanged runner. Qualification uses sequential Release collection, host receipts and the specified admissions. A missing or rejected admission leaves that controlled test `NOT_RUN` for RM-01.

For app observation overhead, use seed 1, 32 workers, finite depot supply and 180 d. Apply doc 64's two Windows five-second CPU load windows before timing. Run one warm-up and five retained legacy off/off pairs first to describe the observed ratio range under matched work. Then run one warm-up and five retained legacy off/on pairs with alternating order. Require equal canonical facts, frame/state hashes and event counts for each off/on pair. Report advance, capture/submission, background, restore, query, peak RSS, durable and sidecar bytes and observation work separately. Use identical cut schedules and the same observation eligibility. Compare the warm ecology workloads on the same horizon with their actual event counts and work per event. Label wall-time comparisons from unqualified hosts accordingly.

## Decisions and outputs

Keep the verified input provenance, exact code commit, compiler, build configuration and executable digest in the run manifest. Collect complete short-arm event and state observations and output SHA-256 values. Report technical results as `ENGINEERING_PASS`, `ENGINEERING_FAIL` or `NOT_RUN`. Separate the isolated assay outcome from full performance qualification. Biological status is `BIOLOGICAL_NOT_VALIDATED` and BR-04 remains open. The timing sentinel is a separately identified technical seed. Original funded budgets and mortality remain active.
