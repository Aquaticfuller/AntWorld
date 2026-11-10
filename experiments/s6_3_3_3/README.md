# S6.3.3.3 experiment archive and reproduction

The [frozen protocol](../../docs/61_S6_3_3_3_Frozen_Validation_Protocol.md) identifies the reviewed commit and exact historical evidence. The [stage report](../../S6_3_3_3_RESULTS.md) and [research supplement](../../research/s6_3_3_3) interpret the data.

| Path | Contents |
| --- | --- |
| `assays/b02/{seed}` | The 360 new assay runs. Each directory has the full ordered observation export, configurations, coordinates and summaries for 60 runs |
| `assays/b01/{seed}` | The 108 B01 intervention runs. Each directory has all raw ordered facts, windows and scan rows for 18 runs |
| `behavior` | Secondary reconstruction of 396 reviewed and 360 new B02 runs, the 398 published B02 trials, B01 act windows, and paired bootstrap summaries |
| `ecology` | 72 21-day worlds, full daily snapshots and ordered fact-row projections, and five representation or intervention probes |
| `ecology_cases.csv`, `ecology_sequences.csv` | Validated lifecycle, transfer and program outcomes. Facts in sequence rows are keyed by run and event ID |
| `density` | Both native timing builds, full profiler counters, SQLite save-stage replay, compression measurements, block index and verified canonical fact archives |
| `ecology_workload.csv` | Supplementary phase timings on the complete funded fine-grid and chamber stratum. Identities must match the primary matrix |
| `verification` | Named local regression outcomes, protected workload identities, and exact historical/fidelity replay receipts |

CSV times are in strong integer milliseconds unless a column specifies another unit. Coordinates are meters. Nutrition is in micrograms and body energy is in nanojoules. Volume is in geometry quanta cubed. The native fact enums are defined in `cpp/include/antworld/core/event.hpp` and `cpp/include/antworld/core/care.hpp`. The CSV exports use one row per actual committed fact. The ecology durable comparison checks the complete event encoding. Density fact blocks preserve that complete encoding as little-endian 4-byte record size and canonical payload. Blank derived values indicate unavailable observations or inapplicable quantities. The B02 paper's raw censor markers and the model's cap are 600 s.

## Commands

Use a clean checkout and a C++20 compiler. These commands use a single-configuration generator and shell conventions with executables directly below each build directory. On Windows add `.exe`; a multi-configuration generator places the executable under the selected configuration. Python tools need only the standard library.

```sh
cmake -S cpp -B build/closure-release -DCMAKE_BUILD_TYPE=Release
cmake --build build/closure-release --parallel
ctest --test-dir build/closure-release --output-on-failure
cmake -S cpp -B build/closure-debug -DCMAKE_BUILD_TYPE=Debug
cmake --build build/closure-debug --parallel
ctest --test-dir build/closure-debug --output-on-failure
cmake -S cpp -B build/closure-san -DCMAKE_BUILD_TYPE=Debug -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ -DANTWORLD_SANITIZERS=ON
cmake --build build/closure-san --parallel
ctest --test-dir build/closure-san --output-on-failure

python tools/run_s6_3_3_3_assays.py --binary build/closure-release/antworld_s6_3_3_experiment --raw out/closure/assays
python tools/analyze_s6_3_3_3_biology.py --raw out/closure/assays --out out/closure/behavior
build/closure-release/antworld_s6_3_3_3_ecology out/closure/ecology matrix
build/closure-release/antworld_s6_3_3_3_ecology out/closure/probes probes
python tools/analyze_s6_3_3_3_ecology.py --matrix out/closure/ecology --probes out/closure/probes --raw out/closure/ecology-archive

cmake -S cpp -B build/closure-profile -DCMAKE_BUILD_TYPE=Release -DANTWORLD_PROFILE=ON
cmake --build build/closure-profile --target antworld_s6_3_3_3_density --parallel
build/closure-release/antworld_s6_3_3_3_density out/closure/density-native
build/closure-profile/antworld_s6_3_3_3_density out/closure/density-profile
build/closure-release/antworld_s6_3_3_3_density out/closure/density-persistence --sqlite-replay out/closure/density-native
python tools/analyze_s6_3_3_3_density.py --native out/closure/density-native --profile out/closure/density-profile --persistence out/closure/density-persistence/persistence.csv --out out/closure/density-archive

python tools/run_s6_3_3_3_assays.py
python tools/analyze_s6_3_3_3_ecology.py --verify-only
python tools/analyze_s6_3_3_3_density.py --deep --extract out/closure/extracted-facts
python tools/ci_verify.py
```

Keep output directories fresh. The ecology and density runs write local SQLite databases and can use several GB. Compression comparisons and timings are specific to the recorded host and runtime. The retained summaries and canonical raw digests allow a physics replay independent of wall time.

The dedicated density design isolates real opportunities and manipulation in a fixed population. Its measured cases had no successful feed or release. The supplementary workload uses all 24 balanced fine-grid and mixed chamber cases at the same three seeds, both populations and both policies. Repeat the unchanged 21-day sequence once, splitting setup, summed six-hour advance, observer/export, checkpoint and SQLite save phases. Require exact primary state, trace and event identities. This supplementary diagnostic supplies timings with real transfers and carriage. It has one sample per case and is separate from density quantiles and both protected acceptance gates.

```sh
build/closure-release/antworld_s6_3_3_3_ecology out/closure/ecology-workload workload
python tools/analyze_s6_3_3_3_ecology.py --raw out/closure/ecology-archive --workload out/closure/ecology-workload/timings.csv
```

The [protected contact script](../../tools/verify_s6_3_3_3_contact_workload.py) and [protected birth script](../../tools/verify_s6_3_3_1_reserve_workload.py) accept `--binary`, `--scratch` and `--receipt`. Point them to `antworld_s6_2_benchmark.exe` and `antworld_s6_3_1_birth_benchmark.exe` respectively on Windows. Both check workload identity outside timing admission. The prior [admitted performance evidence](../s6_3_3_2/performance_portable) defines the existing gates. Use `tools/run_s6_3_3_2_assays.py <binary> <scratch>` with either `--replay-report <json>` or `--fidelity-report <json>` to regenerate the 416 and 484 historical replay checks.
