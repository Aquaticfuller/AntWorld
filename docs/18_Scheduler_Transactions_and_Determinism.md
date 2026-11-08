# Clock, transactions and deterministic scheduling (v0.8)

This refines document 13 into a shared causal contract. P0 uses one state writer; other systems submit proposals or commands.

## Time

SimTime is strong int64 milliseconds. Check overflow when converting real seconds. WallTime only selects AdvanceTo targets; RenderTime only interpolates. Headless, live, accelerated and offline modes share semantics. Acceleration changes real elapsed time, not model rates. Apply events at their effective time, never after it; external commands commit at safe boundaries.

## Ordering and phases

Compare `(time_ms, phase, semantic_priority, stable_tie, event_sequence)`, never addresses or racing thread order.

| Phase | Meaning |
|---|---|
| 0 Input | Freeze authorized commands; validate revision and idempotency |
| 1 Environment/lifecycle | Due weather, development, death, expiration and continuous effects |
| 2 Perception | Local reads from one consistent committed state |
| 3 Proposals | Produce intentions without changing world state |
| 4 Resolution | Validate shared resources, carrying limits and clearance; arbitrate |
| 5 Atomic commit | Apply all-or-nothing state/material/geometry changes and invariants |
| 6 Publish | Publish facts, increment relevant revision and aggregate metrics |
| 7 Reschedule | Next wakeups, thresholds, cache work and observer candidates |

Death effective before proposals prevents later actions by that individual. Late commands cannot rewrite committed facts. Later exact revision semantics for the S0 diagnostic runner are in document 25.

## AdvanceTo

Require target >= now. While time remains or current-boundary work is due, choose the minimum target/future event/rate boundary/required substep. Shorten at known hard thresholds, integrate, advance now, gather due proposals/commands, resolve and commit, assert invariants, append facts and reschedule. Detect zero-time loops. Return an owned read-only state view/copy.

New same-time earlier-phase work cannot arbitrarily reenter a completed phase. Defer to a legal boundary or use an explicitly bounded same-phase rule. Repeated excess must produce a diagnostic rather than hang. With no newly scheduled due work, repeated AdvanceTo(now) is a no-op.

The implemented S1 cursor persists the full executed key and cumulative timestamp budget across calls/reloads. An action batch closes phases 0-4 at its timestamp. See document 26 for exact transaction, late-event and arbitration semantics.

S2 retains that cursor and freezes all local wake observations/choices before committing their proposals. Each autonomous worker owns one pending wake or action. Death cancels it in the lifecycle phase; completion schedules the next wake at a strictly later time. Analytical sparse field decay uses fixed maintenance boundaries, with pure reads between them. See document 27 for fixture delays, bounded local motion and undo-map extensions.

## Continuous boundaries

Energy integrates input/output power until intake, task, climate or depletion boundaries. Water tracks actual sources/losses until drinking/dehydration/climate changes. Brood progress depends on local stage/nutrition/temperature and stops at stage/starvation/death thresholds. Pheromone decay may be analytical; diffusion uses validated stable steps. Climate fields update at low rates interrupted by rain/geometry. Near motion uses bounded substeps for contact/obstacles; far motion uses route/ETA events invalidated by hazards/topology/contact.

Do not multiply physiological rates by speedMultiplier. Mortality must use timeline-aware cumulative hazard/threshold sampling, not one late draw after actions that should already have been impossible.

## Transactions and competition

Intent -> validation -> arbitration -> commit -> fact. Two 3000 ug requests from 4000 ug stock transfer at most 4000 ug total, with explicit partial/rejected outcomes and per-ingredient balance. Overlapping digs remove only still-present intersection; material, geometry and parcel provenance commit together. Trophallaxis validates contact, living state, donor supply and receiver capacity and transfers both sides atomically. New blockage invalidates affected portals immediately; stale navigation is blocked until rebuilt/verified.

For competing proposals, a candidate stable shuffle uses seed, time, resource ID and proposal-group ID. Fixed input must reproduce while repeated rounds/seeds avoid permanent low-ID priority. Use a specified RNG, not implementation-dependent std::uniform_* behavior. Persist state/counters. Fairness requires distributions, not one outcome.

## Precision, pause and reproducibility

P0 may first use one reference precision while reserving future SimulationLevel concepts. L2 retains identity, plans, materials and significant history; interacting entities regain compatible precision before contact. Deep tracking changes recording, not ability. Playback labels sparse/interpolated reconstruction.

Pause stops SimTime; queries, camera, history and conversation remain available. Ecological commands normally remain pending until the first safe boundary after resume unless a later explicit zero-time-commit mode is designed. Pending is not success.

S0 requires same binary/seed/scenario/command schedule to reproduce event traces and state hashes. Speed changes with the same execution configuration reproduce. Cross-platform floating-point bit identity is not assumed; record versions, constraints and tolerance. LOD/parallel variants need conservation, identity, spatial validity and statistical equivalence, not identical random trajectories. Reads never alter RNG or queue order. See documents 14 and 24.
