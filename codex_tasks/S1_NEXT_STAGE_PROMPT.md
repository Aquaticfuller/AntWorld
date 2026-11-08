# AntWorld S1 — after S0 review only

Precondition: user explicitly approves moving past S0, and `S0_RESULTS.md` reports reproducible builds/tests.

Read `AGENTS.md`, `docs/17_Core_Data_Contracts.md`, `docs/18_Scheduler_Transactions_and_Determinism.md`, `docs/19_Persistence_Analytics_and_Recovery.md`, `docs/21_P0_Behavior_Scenarios_and_Biological_Assumptions.md`, `docs/22_Development_Roadmap_and_Execution_Gates.md`.

Implement exactly S1: persistent world-local ID, Ant/Colony/Resource data stores, deterministic ActionProposal/validation/atomic commit for a minimal CollectFood action. Add no biological sophistication beyond what's required for tests. Include simultaneous 3000 µg + 3000 µg requests for only 4000 µg food, repeated death protection, a repeatable fair tie-break, unit tests, and no global "give colony +food" shortcut.

Mark every fixture parameter as engineering-only, report exact tests and stop after S1.
