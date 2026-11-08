# S0 results

Date: 2026-11-08. Branch: `codex/s0-core`.

Code under test: `1d565af` (`feat: implement deterministic headless S0 runtime`). English design baseline: `1a9f092`. The earlier local and remote histories were preserved by merge `88d1d84`. This report is a subsequent documentation-only commit.

## Completed scope

- Independent C++20 `antworld_core`, headless CLI and diagnostic benchmark.
- Strong world/entity/scheduled/fact identities, int64 millisecond time and checked monotonic allocation.
- Versioned SplitMix64 with five fixed-seed vectors and restorable state.
- Full event-key ordering, cancellation, bounded same-time execution and transactional rollback.
- Detached snapshots/event queries with no observer-induced time or RNG changes.
- Canonical, versioned, integrity-checked in-memory checkpoint with complete S0 continuation state.
- Bounded CLI JSON/schema-profile validation, deterministic summary/state/trace hashes and explicit diagnostic events.
- English tracked documents, code/comments, maintenance scripts and commit messages. Original Chinese ZIP retained locally but no longer tracked. Historical Git commits were not rewritten.

No ant behavior, biological calibration, SDF, dynamic geometry, Unity integration, SQLite, world-command authorization service or GM implementation is claimed.

## Changed files

`cpp/include/antworld/core/` defines public types, RNG, events and runtime. `cpp/src/` implements identity conversion, single-owner mutation, scheduling and checkpoint encoding. `cpp/apps/` contains the scenario boundary, CLI and benchmark. `cpp/tests/` contains the core runner and CLI CMake integration cases. `cpp/CMakeLists.txt` builds and registers tests with strict warnings.

`tools/bootstrap_windows.ps1` pins and verifies the portable toolchain; `tools/build_windows.ps1` builds/tests without persistent environment changes. `README.md` documents usage. `docs/25_S0_Implementation_Decisions.md` records ADR-013 through ADR-019. Existing handoff documents were translated/consolidated; `README_HANDOFF.md` replaces the prior language-specific filename. `.gitignore` excludes local tools, builds, outputs and source archive. The maintained handoff manifest was regenerated; its 38 entries verify successfully. `tools/check_repository.py` guards against leftover CJK in tracked UTF-8 files and commit messages.

## Actual environment

- Windows x64, OS version `10.0.26200.0`.
- Intel Core i7-13620H, 10 physical cores / 16 logical processors.
- LLVM-MinGW `20261104`, Clang `23.1.5`, target `x86_64-w64-windows-gnu`.
- CMake `3.31.10`, Ninja `1.13.2`.
- C++20, `-Wall -Wextra -Wpedantic -Wconversion -Wsign-conversion -Werror`.
- Normal Windows executables statically link the toolchain runtime. Sanitized executables run with the compiler runtime directory on process-local PATH, configured by the build script.

## Commands executed

From the repository root:

```powershell
./tools/bootstrap_windows.ps1
./tools/build_windows.ps1 -Configuration Debug
./tools/build_windows.ps1 -Configuration Release
./tools/build_windows.ps1 -Configuration Debug -BuildDirectory build/sanitized -Sanitizers
./build/release/antworld_headless.exe --scenario scenarios/p0_smoke.json --advance-ms 60000 --output out/smoke.json
./build/release/antworld_headless.exe --scenario scenarios/p0_smoke.json --advance-ms 60000 --diagnostic-events 8 --output out/diagnostic.json
./build/release/antworld_benchmark.exe
```

Each build script invokes CMake configure, `cmake --build ... --parallel 4` and `ctest --test-dir ... --output-on-failure`, failing if any step fails. No external libraries are fetched during configure/build.

Clean-checkout reproduction used:

```powershell
git clone --no-hardlinks --single-branch --branch codex/s0-core . out/clean-checkout
$toolRoot = (Resolve-Path .tools).Path
$env:PATH = "$toolRoot/llvm-mingw-20261104-ucrt-x86_64/bin;$toolRoot/cmake-3.31.10-windows-x86_64/bin;$toolRoot;" + $env:PATH
cmake -S out/clean-checkout/cpp -B out/clean-checkout/build -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=clang++
cmake --build out/clean-checkout/build --parallel 4
ctest --test-dir out/clean-checkout/build --output-on-failure
```

The clone contained only committed source; it reused the already verified external toolchain, not generated files from the original source tree. Its working tree remained clean after build/tests. The commands above changed PATH only inside the command process.

Maintenance commands also executed using the available Python interpreter:

```sh
python tools/update_handoff_manifest.py
python tools/verify_handoff.py
python tools/check_repository.py
```

The cloned handoff verification and language scan also passed. Before adding this report, 60 tracked UTF-8 files and all existing commit messages passed the scan, with zero binary files. This checks for untranslated CJK; the prose was also reviewed during migration.

## Test results

Every case below passed in Debug, Release, Debug with AddressSanitizer/UndefinedBehaviorSanitizer, and the clean Release checkout.

| Test | Result | Evidence covered |
|---|---|---|
| T00 | PASS | Smoke fixture identity/seed, initial time/revision and UUID formatting |
| T01 | PASS | Repeated target preserves complete checkpoint bytes after an RNG event |
| T02 | PASS | Backwards advance and past scheduling reject without mutation |
| T03 | PASS | Phase comparison precedes sequence; runtime executes all eight phases in order |
| T04 | PASS | Ten equal-time/priority events obey known tie/sequence order and repeat exactly |
| T05 | PASS | Self-rescheduling stops with a readable budget error; entire advance rolls back; cancellation recovers |
| T06 | PASS | Repeated snapshots/event reads preserve time, RNG, state hash and checkpoint bytes |
| T07 | PASS | Four frozen outputs for each of five seeds, then 100 restored continuation values per seed |
| T08 | PASS | Future events and RNG execute identically after restore, at their scheduled times |
| T09 | PASS | Complete round-trip bytes/state, canceled-ID history and subsequent ID/event allocations match |
| T10 | PASS | Every truncation of the fixture checkpoint, unsupported versions, corruption, invalid counters/phase/time/count reject without mutation |
| T11 | PASS | Empty scenario with zero diagnostic events runs headless and produces parseable JSON |
| T12 | PASS | Const query signatures return owned values; editing returned copies cannot alter the world; illegal mutation rejects |
| T13 | PASS | Two separate CLI runs with eight diagnostic RNG events produce identical JSON/state/trace hashes |
| CLI_VALIDATION | PASS | Unknown/nested/duplicate fields, fractional/overflow seeds, negative time, wrong units/bounds, nonempty biological arrays and type errors reject |
| CORE_EDGE_CASES | PASS | Cancellation, ID non-reuse/overflow, priority, new same-time work, maximum time, malformed JSON/UUID and partition-independent advancement |

CTest summaries after the final source change:

```text
Debug:          100% tests passed, 0 tests failed out of 16; total 2.04 sec
Release:        100% tests passed, 0 tests failed out of 16; total 1.11 sec
ASan + UBSan:   100% tests passed, 0 tests failed out of 16; total 2.14 sec
Clean Release:  100% tests passed, 0 tests failed out of 16; total 1.10 sec
Handoff:        PASS: verified 38 files
```

No sanitizer finding occurred during these cases. This is evidence for the exercised inputs, not a proof against every possible defect. SCH-01/02/12/19/20/22 are covered only for implemented S0 infrastructure; no Unity camera or external-command-ledger coverage is implied.

## Example results

Empty smoke input, target 60000 ms:

```json
{
  "world_id": "381b1f47-91b8-4b2d-9d51-967a3e2b2a01",
  "status": "ENGINEERING_FIXTURE",
  "scope": "S0_EMPTY_WORLD",
  "seed": 12345,
  "sim_time_ms": 60000,
  "revision": 0,
  "pending_events": 0,
  "committed_events": 0,
  "rng_version": "splitmix64-v1",
  "schema_version": 1,
  "physics_version": 1,
  "hash_version": "fnv1a64-le-v1",
  "state_hash": "084acfcb16ae1997",
  "trace_hash": "cbf29ce484222325"
}
```

With `--diagnostic-events 8`, revision is 16, committed events 8, state hash `ed0618121c362852` and trace hash `8cff272fd18db46a`. These are infrastructure diagnostics, not biological history.

## Diagnostic measurements

A separate Release process ran 64 trials of 128 scheduled diagnostic events, each advancing an otherwise empty clock to 60000 ms. Queue setup is excluded from timing. The memory-observed run reported:

| Metric | Measured value |
|---|---:|
| AdvanceTo p50 | 0.0086 ms |
| AdvanceTo p95 | 0.0134 ms |
| Checkpoint encoding p50 | 0.0196 ms |
| Restore p50 | 0.0147 ms |
| Checkpoint size | 8444 bytes |
| Diagnostic simulated seconds / advance wall second | approximately 6.20 million |
| Observed process peak working set | 4431872 bytes (about 4.23 MiB) |

The process high-water mark was sampled through System.Diagnostics.Process at 5 ms intervals; it includes runtime/benchmark allocations, not just core state. Exact steady-state resident memory was not separately measured. The large empty-clock ratio reflects skipped idle time and excludes queue setup; it says nothing about ant, geometry or complete-map throughput. Geometry/navigation/render/GM timings are not applicable in S0.

## Assumptions, limitations and next gate

ADRs 013-019 document language/provenance, pinned tools, RNG/hashes, copy-on-write authority, revision/ID semantics, same-time processing limits, checkpoint format and the stricter empty-scenario profile. Schema, physics and RNG encoding versions start at 1; future incompatible changes must migrate or reject old data.

Remaining limits: one writer; full state copies for mutations; bounded queue/journal; diagnostic actions only; no durable disk recovery; FNV is non-cryptographic; no floating-point biological cross-platform guarantee. The broader fixture schema is intentionally not fully executable in S0. Linux/GCC, MSVC and other platforms: NOT RUN. GitHub Actions CI: not configured or run. Later biology/geometry/client/Agent tests: NOT RUN and outside scope.

S0 meets its technical gate on the tested Windows environment. Stop here for user review. S1 requires authorization and should add real ant/colony/resource stores, lifecycle identity, Move/CollectFood proposals, same-time material arbitration, fair tie handling and corresponding SCH tests. It must not interpret S0 diagnostic events or fixture values as calibrated ecology.
