# Reproduce and audit ecological closure

The public evidence lives in [the experiment directory](../../experiments/s6_4_ecological_mechanism_closure). Each collection's `run.json` identifies the source commit, C++ tree, binary SHA-256, ordered cases and original collector hash. Each `archives.jsonl` has a receipt for every attempt. A receipt records the original archive SHA-256, inputs, binary artifacts, wall time, exit status and the final Core cursor, state and trace signatures when available. Fixed public ZIP witnesses contain the original authoritative evidence. Full native archives remain on the experiment host and are checked individually by SHA-256. An independently compiled run is identified by its own binary SHA. Do not use a differing binary hash as evidence of byte-level model equivalence.

## Native build and full regression

```sh
cmake -S cpp -B build/ecological-release -DCMAKE_BUILD_TYPE=Release
cmake --build build/ecological-release --parallel 4
ctest --test-dir build/ecological-release --output-on-failure
cmake -S cpp -B build/ecological-debug -DCMAKE_BUILD_TYPE=Debug
cmake --build build/ecological-debug --parallel 4
ctest --test-dir build/ecological-debug --output-on-failure
cmake -S cpp -B build/ecological-sanitizer -DCMAKE_BUILD_TYPE=Debug -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ -DANTWORLD_SANITIZERS=ON
cmake --build build/ecological-sanitizer --parallel 4
ctest --test-dir build/ecological-sanitizer --output-on-failure
```

Windows uses the appropriate compiler runtime on PATH and appends `.exe` to executable names. The Windows Clang instrumented build ran with `ASAN_OPTIONS=detect_leaks=0:halt_on_error=1` and `UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1`. Linux CI includes leak detection. The local Debug and instrumented linker dropped executable debug sections using `-DCMAKE_EXE_LINKER_FLAGS=-Wl,--strip-debug` to stay within available storage. Compiler mode, checks and instrumentation remained active. The local compiler was LLVM-MinGW Clang 23.1.5 and the collector used CPython 3.15.2. [Core CI configuration](../../.github/workflows/ci.yml)

## Collection and independent replay

Run each historical collection from its recorded commit and its named executable. Use separate output directories. The original 2,000,000-fact budget run uses the original source and leaves out `--expanded`. The following commands collect the corrected 4,000,000-fact roster and the independent scout and care panels. Rebuilding each older panel from its original source retains the logged attempts and dispositions.

```sh
python tools/run_ecological_closure.py joint build/ecological-release/antworld_s6_4_wp6b out/closure-joint --expanded
python tools/run_ecological_closure.py care build/ecological-release/antworld_s6_4_wp6b out/closure-care
python tools/run_ecological_closure.py scout build/ecological-release/antworld_ecological_recruitment out/closure-scout
python tools/verify_ecological_closure.py joint out/closure-joint out/closure-joint-analysis
python tools/verify_ecological_closure.py care out/closure-care out/closure-care-analysis
python tools/diagnose_ecological_care.py out/closure-care out/closure-founder-feeding
python tools/verify_ecological_closure.py scout out/closure-scout out/closure-scout-analysis
python tools/verify_ecological_publication.py out/closure-public-audit --joint-binary build/ecological-release/antworld_s6_4_wp6b --scout-binary build/ecological-release/antworld_ecological_recruitment
python tools/verify_final_core_evidence.py out/closure-inherited-audit
```

Add `--portable-field` to the collection commands for the physics-25 roster. Both policies remain readable. The portable run still uses the 4,000,000-fact limit and the same original cases. `tools/compare_ecological_policies.py OLD_RAW NEW_RAW OLD_ANALYSIS NEW_ANALYSIS OUTPUT` emits complete pair comparisons without changing either archive. The full native collections from the experiment host are under `out/ecological-closure/native-archives`, with `portable-physics/{joint,care,scout}` for the portable panel. The public verification and native replay exercise the new policy. The older local replays retain their version-specific records. [Versioned numerical repair](PORTABLE_REPLAY.md)

The timing collector requires the existing timing-enabled storage build.

```sh
cmake -S cpp -B build/ecological-timing -DCMAKE_BUILD_TYPE=Release -DANTWORLD_STORAGE_TIMING=ON
cmake --build build/ecological-timing --target antworld_s6_4_wp6b --parallel 4
python tools/measure_ecological_output.py build/ecological-timing/antworld_s6_4_wp6b out/closure-output-diagnostic
```

The public audit checks the exact frozen roster, archive/member hashes, conserved quantities and negative outcomes. It rebuilds the published fixed raw endpoints and verifies the SQLite midpoint anchor, block chain and bytes against the uninterrupted facts. With executables supplied it also generates a fresh scout, one 150-day durable replay per layout, and the accessible and blocked founding water pair. It requires the same canonical output in each. Absolute timing is host-specific and requires the separate admission procedure. Both performance modes perform actual SQLite save/reopen and output synchronization.

Raw stage identities, larvae and receiver episodes are supplied as gzip-compressed CSV. Missing values mean unobserved or inapplicable under that assay, with censoring and terminal outcomes in their own columns. `archives.jsonl` identifies host failures and completed runs, including paired observation and restoration. Each ZIP member is independently hashed. The earliest stopped historical witness predates a host feature that writes a final native frame and its matched facts on failure. It retains the complete artifacts that its original runner wrote. [Bounded archive follow-up](FROZEN_HOST_FOLLOWUP.md)
