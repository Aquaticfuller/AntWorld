# AntWorld

An autonomous ant ecosystem simulation with an authoritative C++ core, a future Unity/C# client and an evidence-based Game Master. The current implementation is **S0 infrastructure only**: an empty headless world with deterministic diagnostics. No ant biology, 3D excavation, Unity, database or Agent is implemented yet.

## Build and test on Windows x64

The portable toolchain lives under ignored `.tools/`; no global installation or persistent PATH changes are required. Bootstrap downloads fixed official releases and verifies SHA-256. Subsequent builds work offline.

```powershell
./tools/bootstrap_windows.ps1
./tools/build_windows.ps1 -Configuration Debug
./tools/build_windows.ps1 -Configuration Release
./build/release/antworld_headless.exe --scenario scenarios/p0_smoke.json --advance-ms 60000 --output out/smoke.json
```

Normal LLVM-MinGW builds link their C++ runtime statically, so the executable can run without the compiler directory on PATH. `--help` lists options. `--diagnostic-events 8` optionally schedules eight explicitly synthetic infrastructure events that draw RNG values at milliseconds 1 through 8. This does not simulate ants.

The scenario supplies the default observation duration; `--advance-ms` overrides the target. JSON stdout and output files are reproducible; the requested output path is printed separately on stderr. Nonempty biological scenarios are rejected in S0. See [the scenario profile and implementation ADRs](docs/25_S0_Implementation_Decisions.md).

## Other C++20 environments

The core and CLI depend only on the standard library. No dependency download occurs during CMake configure/build.

```sh
cmake -S cpp -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build
ctest --test-dir build --output-on-failure
```

For multi-configuration generators, select the same configuration when building and testing, for example `--config Debug` and `ctest -C Debug`. Actual tested platforms and compiler versions are recorded in [S0_RESULTS.md](S0_RESULTS.md); portability intent is not evidence of unexecuted tests.

## Structure and guarantees

- `cpp/include/antworld/core/`: typed IDs/time, RNG, diagnostic events and the world owner.
- `cpp/src/`: deterministic scheduling, validated mutation and versioned checkpoint codec.
- `cpp/apps/`: bounded scenario parser, headless CLI and diagnostic benchmark.
- `cpp/tests/`: T00-T13 and input/boundary regression checks.
- `docs/`: English product design, contracts, historical context and implementation decisions.
- `scenarios/`, `schemas/`: original engineering fixtures and the broader P0 schema.
- `contracts/`: future C ABI draft, not an implemented native plugin.

All runtime writes use a validated single-writer path. Queries return detached values. Invalid mutations and failed restores leave the prior world unchanged. Checkpoints retain the complete S0 queue, journal, allocators, revision, time and RNG. FNV hashes are regression/integrity checks, not cryptographic authentication. Copy-on-write transactions and bounded journals prioritize correctness in a small prototype, not large-world throughput.

## Verification and repository policy

Use Python 3.10+ for repository maintenance tools (not needed by the C++ runtime):

```sh
python tools/update_handoff_manifest.py
python tools/verify_handoff.py
python tools/check_repository.py
```

The language scan checks tracked UTF-8 files and commit messages for leftover CJK text; manual review still determines English prose quality. Stage deletions/renames before scanning. The original Chinese archive remains locally under ignored `handoff/`, with pre-policy Git history preserved. All current tracked content, code/comments, documentation and commit messages are English. User conversation is Chinese.

Run `antworld_benchmark` for S0 diagnostic-only timing. Its artificial clock span and event counts cannot predict biological, geometry or whole-map performance. See [the current roadmap](docs/22_Development_Roadmap_and_Execution_Gates.md). Review S0 before authorizing S1.

## License

The repository retains the remote baseline's [GNU GPL v3 license](LICENSE).
