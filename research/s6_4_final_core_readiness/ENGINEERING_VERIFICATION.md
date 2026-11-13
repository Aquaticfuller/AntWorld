# Engineering verification receipt

The assay implementation is `77cc30f`. The current Core runtime, include tree and storage tree have identical Git object IDs to `73e801946a2419bf33eb78e5240f8af0923ff31a`. The local source uses Clang 23.1.5, CMake/CTest 3.31.10 and Windows build 26200. All build commands and the replay commands are indexed in [reproduction](REPRODUCE_FINAL_QUALIFICATION.md). Windows checks retain the existing test body, timeout, path and model authority.

| Check | Actual result |
|---|---|
| Windows Debug CTest | 281/281, final assay executable. |
| Windows Release CTest | 281/281, final assay executable. |
| Windows ASan/UBSan | With the required runtime DLL on `PATH` and the other long runs complete, the serial full suite finished 280/281. `FND_IF_BOUNDARY_COLONY` timed out at its existing 360 s limit. The same unchanged test passed in isolation under CTest in 216.33 s, and direct execution of the same assertions returned 0. No single full local sanitizer run without an initial setup issue or timeout is claimed. |
| Initial local sanitizer attempts | Initial command omitted the pinned ASan runtime path and failed to start instrumented executables. One concurrent attempt after restoring the runtime had three timeouts. Both logs are retained separately. |
| Prior-model replay | 1,092 v1 and 1,092 R1 cases with exact historical fact, state and census identity. Sixteen R2 midpoint or observation-disabled comparisons pass. |
| Published interruption | Eight original witnesses, 2,633,352 canonical facts, ledger reconstruction and recovery after an actual child exit before publication pass. The previous generation and continued day-150 authority match. |
| New archives | 156 cases retain input, state, fact and archive hashes. All original roomy comparators and all twelve observation-off or segmented-resume comparisons match. The public samples regenerate outcome, source, lineage and soil results from raw events. |
| New durable witness | The saved day-75 SQL blocks and checkpoint anchor independently bind to an exact prefix of the uninterrupted facts. A fresh executable replay also matches full final authority. |
| Timing and evidence | Recomputed archived hardware admissions, original gates and independent B06 endpoints. A new synthetic rerun produced identical trial bytes. The latest inherited application result is still `FAIL`. |

[Local command and test logs](../../experiments/s6_4_final_core_readiness/tests) [R1 and R2 authority receipts](../../experiments/s6_4_final_core_readiness/tests) [Independent prefix receipt](../../experiments/s6_4_final_core_readiness/clock/durable_prefix.json) [Core CI history for this branch](https://github.com/Aquaticfuller/AntWorld/actions/workflows/ci.yml?query=branch%3Acodex%2Fs6.4-final-core-readiness)
