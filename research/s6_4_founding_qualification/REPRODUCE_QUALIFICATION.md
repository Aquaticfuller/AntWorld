# Reproduce the qualification closure

Use a fresh checkout of this branch with the pinned compiler dependencies and a new output directory. The [original integration commands](../s6_4_integrated_founding/REPRODUCE_INTEGRATED_FOUNDING.md) reproduce the 150-day and closed-stock authorities. The [new freeze](FROZEN_CLOSURE_PROTOCOL.md) identifies every diagnostic, reference, and witness case. The [codec decision](PROSPECTIVE_CODEC_CHANGE.md) specifies byte-for-byte acceptance and the single additional controlled application collection.

## Ordinary build, exact replay and public evidence

```powershell
cmake -S cpp -B build/qualification -DCMAKE_BUILD_TYPE=Release
cmake --build build/qualification --parallel 4
ctest --test-dir build/qualification -C Release --output-on-failure
$bin = 'build/qualification/antworld_s6_4_wp6b.exe'
$evidence = 'experiments/s6_4_founding_qualification'
python tools/verify_founding_qualification_codec.py $bin experiments/s6_4_integrated_founding/performance/application-inherited out/qualification-codec.json out/qualification-codec-work
python tools/founding_qualification_witnesses.py "$evidence/witnesses" --binary $bin --scratch out/qualification-crash-work
python tools/replay_founding_qualification_legacy.py $bin out/qualification-legacy out/qualification-legacy-work
python tools/check_s6_4_wp6b_r2_recovery.py --archive experiments/s6_4_wp6b_r2 --binary $bin --scratch out/qualification-r2-work --out out/qualification-r2-recovery.json
python tools/verify_founding_qualification.py $evidence
python tools/verify_integrated_founding_application.py "$evidence/performance"
```

On a single-configuration Linux build use the executable name without `.exe`. The application collector and its analyzer use the approved Windows instrument. The witness verifier reads published original event streams and daily states, reconstructs ingredient and life-stage evidence, and reopens a fresh copy of the published interrupted store. It also repeats the actual child termination with the built executable and compares both resumed timelines against the original day-150 frame, exact facts, RNG and state. It never opens a published SQLite archive in place. The case CSV maps every representative ZIP to its original complete batch and member hashes. `life_stages.csv` is a readable individual timeline recalculated from the original facts. The source transaction CSVs have `*_ug` columns, `time_ms`, actual source and actor IDs, and resource/carry balances after each included fact. Event kind values use the Core `FactKind` definition. Delivery or cargo-ingestion facts can have resource ID zero because the cargo is then attributed by its actor's preceding source transaction.

To republish the same eight cases from the original full local archive, pass `--local-originals out/integrated-founding` and use a fresh witness destination. The existing three witnesses are read from their accepted Git paths by hash. Other original member bytes, including `initial.chk`, `final.frame`, `facts.bin`, `cuts.csv`, `individuals.csv`, `parameters.txt` and `case.json`, are preserved.

The reused ZIPs are [Borisovka balanced](../../experiments/s6_4_integrated_founding/raw_index/resupply-nominal/borisovka-micro-nominal-0-1-balanced.zip), [St. Petersburg balanced](../../experiments/s6_4_integrated_founding/raw_index/resupply-nominal/st_petersburg-micro-nominal-0-1-balanced.zip) and [Borisovka blocked](../../experiments/s6_4_integrated_founding/raw_index/resupply-nominal/borisovka-micro-nominal-0-1-blocked.zip). The [witness directory](../../experiments/s6_4_founding_qualification/witnesses) holds the other original case ZIPs and the separate interrupted publication.

## Source exhaustion and B06

```powershell
python tools/founding_qualification_scope.py out/qualification-scope --binary $bin
python tools/founding_qualification_scope.py out/qualification-scope --analyze out/qualification-scope-analysis
python tools/analyze_founding_qualification_b06.py out/integrated-founding experiments/s6_4_integrated_founding/analysis out/qualification-b06
```

The B06 analysis requires the original full local v7 archive. It reads all daily individuals and checks every case against the accepted count algorithm. The public verifier recalculates its reduced cohort summaries. The witness verifier independently reads original canonical facts. The 180-day paired scope runner uses a separate 60- or 120-dose finite reserve and emits original case archives. The 120-dose standard must match the first 150 days of actual history, the original initial checkpoint, event cursor and RNG. Changing the reserve alters the initial checkpoint and is the intended physical intervention. The independent reader decodes actual source and cargo movements and checks the carried components against each daily individual cut. The public scope receipt records each full local archive and original member by SHA-256.

## Controlled phase attribution and final application qualification

Use the [original controlled Windows instructions](../s6_4_integrated_founding/REPRODUCE_INTEGRATED_FOUNDING.md) for the inherited and integrated application matrices and native/protected workloads. For phase attribution select commit `12273b88f2707bd94ba5146341b6eca45af8cf5a` and configure a separate Release build with `-DANTWORLD_STORAGE_TIMING=ON`. The timed recorder writes a hardware-provenance receipt for each session. The admissible CPU channels come from the existing instrument. The full log and unrelated process inventory are kept local.

```powershell
$timing = 'build/qualification-timing'
cmake -S cpp -B $timing -DCMAKE_BUILD_TYPE=Release -DANTWORLD_STORAGE_TIMING=ON
cmake --build $timing --config Release --target antworld_s6_4_wp6b
$timingExe = "$timing/antworld_s6_4_wp6b.exe"
$compiler = (Get-Command clang++).Source
python tools/profile_founding_qualification.py --prepare --hwinfo-csv $hw --out out/qualification-timing --binary $timingExe --build $timing --compiler $compiler
python tools/profile_founding_qualification.py --hwinfo-csv $hw --out out/qualification-timing --binary $timingExe --archive out/qualification-timing-private
python tools/archive_s6_4_rm02_performance.py out/qualification-timing out/qualification-timing-public
```

Substitute the actual single-configuration executable path, compiler and existing HWiNFO CSV. The final qualification uses the ordinary uninstrumented Release executable. The instruments, exact-input hashes, original archived failures and raw session records remain available for comparing the outcome. The source-only collector is separate from the public read-only analyzer. Report SQLite VFS times as nested forwarded operations and the thread wall/CPU and outer-process differences as residuals.

The published native and protected reports can be recomputed without new measurements by adding `--native` to `verify_founding_qualification.py`. On Windows, build the inherited `antworld_s6_2_benchmark`, `antworld_s6_3_1_birth_benchmark` and `antworld_s6_4_wp5_benchmark` targets, then run the original Windows workload commands against this Core tree to collect new samples. The live telemetry and hardware admissions apply to measurements. Public verification reads the retained samples and checks their original dispositions.

## File index

| Directory under `experiments/s6_4_founding_qualification` | Review material |
|---|---|
| `witnesses` | Representative complete original archives, exact archived member links, source transactions, life-stage timeline, and interrupted SQLite DB and WAL with receipt. |
| `b06` | All 1,236 world-level census comparisons, compressed known-age exposures and recomputable grouped outcomes. |
| `scope` | The frozen 48-case run receipt, every local archive/member identity, per-world flow totals and four reporting cuts per world. |
| `replay-legacy` and `r2-recovery.json` | Exact prior-model replay receipts and persistence or observation-disabled comparisons. |
| `performance` | Admitted and rejected attempts, schedules, selected telemetry, all timing samples, phase attribution and frozen analyses. |
| `tests` | Complete Windows Debug, Release and sanitizer CTest logs. |
