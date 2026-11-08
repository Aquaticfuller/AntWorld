# Exact S0 tasks and acceptance tests (v0.8)

Only C++ infrastructure, headless execution, deterministic time/events and checkpoint continuation are authorized. No worker behavior, pheromones, SDF, GM or Unity implementation.

## Repository structure

Keep AGENTS.md, CODEX_START_HERE.md, docs/, the draft contracts/ header, schemas/ and scenarios/. Add cpp/ with CMake, public core headers, implementation, a headless application and tests. unity/ and gamemaster/ are future directories, not required S0 scaffolding.

## Required behavior

- WorldId plus seed creates an independent empty runtime at time/revision zero.
- Reject past events and invalid phases; sort same-time work stably; support cancellation/invalidation and finite same-time recursion diagnostics.
- AdvanceTo reaches the exact target and rejects backwards time. Repeating an unchanged target with no new due work is a no-op. Queries do not consume RNG. Mock/diagnostic scheduled events must never be described as implemented ant behavior.
- Use an explicit portable PRNG, versioned seed/state and at least five fixed-seed test vectors. Do not rely on std::uniform_* for cross-implementation bit identity. Restore the next sequence exactly.
- Snapshot exposes identity, time, revision and event counts with clear detached/immutable ownership.
- Versioned in-memory checkpoint saves all S0 state: identity, time, revision, future queue, RNG, allocators and sequence. No SQLite requirement.
- CLI accepts the smoke fixture and a target time and emits parseable JSON with identity, time, revision, counts, RNG version and deterministic trace/state summary. Output location can be a separate diagnostic. Unknown fields are rejected or explicitly diagnosed, never silently ignored.

Example: `antworld_headless --scenario scenarios/p0_smoke.json --advance-ms 60000 --output out/smoke.json`.

## Required tests

| ID | Input | Expected |
|---|---|---|
| T00 | Create p0_smoke | Correct world/seed; now=0 |
| T01 | AdvanceTo(100), repeat | No extra state/revision/RNG change |
| T02 | AdvanceTo(100), then 99 | Reject; revision unchanged |
| T03 | Same time/sequence, different phases | Stable phase ordering |
| T04 | Ten same-time, equal-priority events | Identical order on repeated runs |
| T05 | Self-rescheduling same-time event | Finite readable failure, no hang |
| T06 | Repeated snapshots | Unchanged time, RNG and state hash |
| T07 | Multiple RNG seeds and restoration | Same seed repeats, different seeds differ in test vectors, continuation matches |
| T08 | Checkpoint contains future events | Restored events execute at their correct times |
| T09 | Full round trip | Identity/time/revision/queue/allocators/RNG agree |
| T10 | Unsupported version/truncated checkpoint | Reject without partial world mutation |
| T11 | Empty headless scenario | No Unity/LLM dependency; parseable JSON |
| T12 | Mutation and query interfaces | Legal commit path only; no writable world pointer from queries |
| T13 | Repeat CLI input | Same trace hash and state summary; no absolute paths in deterministic output |

Map applicable SCH-01/02/12/19/20/22 portions to S0. Later systems have later gates.

## Definition of done

Build a clean checkout with `cmake -S cpp -B build -DCMAKE_BUILD_TYPE=Debug`, `cmake --build build`, `ctest --test-dir build --output-on-failure`, or documented platform-equivalent commands. Provide a reproducible Windows x64 generator/preset/script. Report only actually tested platforms/configurations.

README explains headless/test usage. S0_RESULTS.md lists actual commands, T00-T13 PASS/FAIL/NOT RUN, example output and limitations. Keep design/ADRs traceable. No cloud-model, Unity or general-purpose Agent runtime dependency.

After S0, stop for user review before S1. General approval of the roadmap does not silently skip stage gates. Concrete S0 clarifications are in document 25 and must remain within these boundaries.
