# OP0 user acceptance record

**Result:** Windows observation workflow demonstrated on real records. Independent release review is pending. OP0 adds an archive viewer, a loopback service, a terminal client and validation tools. The C++ core, existing physics defaults, existing experiment archives and scientific acceptance records retain their reviewed identities.

Reviewed source base: `a6ca3f439497ce8dd3c6dc11b90fa60fd80e4f9a`.

## Actual Windows walkthrough

Windows 11 x64, Python 3.15.2, SQLite 3.53.4, Chrome 157.0.8103.78 and Node.js 24.22.1 for browser automation. The browser check drove the HTML controls in Chromium, rendered Canvas and captured the screenshots below. The terminal check fed the same commands a reader can enter and asserted rendered lines. The reader did not start or advance a simulation.

| User action | Evidence |
| --- | --- |
| Start the browser with the PowerShell launcher | The localhost view loaded the bundled real 150-day ZIP and drew queen #2 at 0, −4, 0 mm at day 0 |
| Open a real world in the terminal | World 1 opened and displayed its WorldId, physics 25, seed 1, integrity, queen and worker counts. Day 150 showed 45 living workers |
| Observe surface and underground | At #9826, worker #4 was visible on the surface food source and could be selected from the map. #10692 changed the underground quantized material and exposed parcel #37. #10706 recorded its placement. The geometry test queries the material before and after the exact cut |
| Play, pause, scrub and reach day 150 | Real Chromium input played at 30 days/s, paused, resumed, reached day 150, and sought day 90 using the range input |
| Inspect a worker | #9661 is worker #4's eclosion. Movement facts recorded positions below and at the surface before #9826 collection and #9938 delivery by the same worker |
| Find care, trophallaxis and recruitment | Category queries page in canonical order. Activation #17118 links to its cue and the cue's source food-delivery fact. Human-visible details preserve fact IDs and doses |
| Inspect a recorded death | Larva #5's death at #5375 is energy depletion. Its profile shows the earlier resources/biology sample with the sample time and retains its brood-care facts |
| Watch a failure | The no-external-supply world reaches day 150 with zero workers and no live queen. It is keyed separately even though its recorded WorldId is shared with the balanced case |
| Compare the previous and corrected physics 25 | Both have the same recorded population source, seed, shaft geometry and initial maternal inputs. First-ration preference differs, 500,000 ppm before and 0 ppm after. The recorded day-150 worker counts are 43 and 45, respectively. Of four members in the first recorded larval census, zero eclosed before and one after. These are archive outcomes and do not establish an independent effect |
| Reopen without changing the original source | Import verifies the original files. The browser reopened from its browse index with the same facts and source SHA-256. Native SQLite v1 and durable v2 with WAL were exercised. The DB and WAL source hashes remained identical. The v2 test ensures no SHM is created in the original directory |
| Switch between English and Simplified Chinese | Chromium switched the larval profile and comparison in both directions without changing the active fact, identity or source hash. Reload restored the selected language. The terminal test switched languages while tracking the same larva and verified the preference in a new terminal session |

### Real screenshots

| View | Capture |
| --- | --- |
| Day 0 with a single underground queen | [Founding colony day 0](evidence/founding-day-0.png) |
| Worker #4 and the provisioned surface resource | [First food collection](evidence/worker-at-food-source.png) |
| Exact excavation event and material slice | [First excavation](evidence/first-excavation.png) |
| Energy death and earlier physiological cut | [Larva #5](evidence/larval-life-history.png) |
| Extinction at day 150 | [No external supply](evidence/no-external-supply.png) |
| Feeding treatment comparison | [Physics 25 comparison](evidence/physics-25-comparison.png) |
| Larva #5 with the same facts in Simplified Chinese | [Chinese life history](evidence/larval-life-history-zh.png) |

These PNGs came from the running viewer. Spatial dots are recorded positions. Some adjacent facts have the same simulation timestamp. The inspector displays the exact event ID and cursor at those boundaries.

## Source identities

| Archive | Facts | ZIP SHA-256 |
| --- | ---: | --- |
| Corrected balanced, Borisovka shaft | 668,720 | `448d2a7db60487e98113cc27f70cce307b1452a26b0ab36edef48911745a80df` |
| No supply, Borisovka shaft | 20,186 | `0925abfb8e51d8596e61bdee1c0dcaa9644c036e576ccdedca5caaad220afe6f` |
| Prior balanced, Borisovka shaft | 591,390 | `cafc686d5d97accd6a9e73b2d2a746bbd2499f91b635c7c1d380384cdf75042f` |
| Limited supply, St. Petersburg dogleg | 2,120,325 | `d91d7bea05104f90f278d3c865b83c4ad98e64f0689bb1352ce648f3f1c72d7d` |

The corrected balanced WorldId is `00000000-0000-0286-0000-000000018a61` and its canonical fact SHA-256 is `ea07be520ff0bb30b9e423663897b385933e95114182c0ad2ae591c430b84a46`. Its [native experiment manifest](../experiments/s6_4_founding_cohort_release/correction/run.json) supplies producer commit and binary identity. The associated [archive receipts](../experiments/s6_4_founding_cohort_release/correction/archives.jsonl) describe exact members. The [prior experiment manifest](../experiments/s6_4_ecological_mechanism_closure/portable-physics/joint/run.json) supplies the reference producer. The independent witness test reads the length-prefixed facts directly and compares the canonical identity, positions, mass and times without using OP0's codec or index.

## Measured OP0 performance

The table uses a fresh index in each measurement. The OS file cache was not flushed. Each local operation has 21 retained observations in the receipts. Peak working set is measured for the Python process via Windows process counters and includes import and queries. Durable archive replay does not wait for a real-time simulation. These measurements are independent of the historical S6.4 application performance qualification.

| Measurement | Balanced shaft | Limited dogleg |
| --- | ---: | ---: |
| Full cold-index import | 4,259.09 ms | 12,997.04 ms |
| Streaming verification and projection | 3,427.96 ms | 10,959.14 ms |
| SQL index finalization | 752.04 ms | 1,940.28 ms |
| Reopen existing index, median | 0.164 ms | 0.249 ms |
| Time state seek, median | 1.780 ms | 1.653 ms |
| Individual query, median | 10.008 ms | 6.285 ms |
| Geometry slice and clearance, median | 1.373 ms | 1.371 ms |
| 50-event query, median | 2.970 ms | 3.234 ms |
| Peak process working set | 85.9 MiB | 85.8 MiB |
| Browse index on disk | 63.3 MiB | 192.3 MiB |

Real browser navigation painted the shell at **292 ms** and rendered the first real colony at **4.484 s** on a cold derived cache. The worker selection and day-90 scrub took **66.83 ms** and **76.22 ms** with the automation polling interval included. Reopening from the derived cache took **92.76 ms**. See [browser timings](evidence/browser-receipt.json), [bilingual workflow receipt](evidence/bilingual-browser-receipt.json), [balanced import samples](evidence/import-balanced.json) and [large import samples](evidence/import-dogleg.json). Individual query time depends on the available event pages and observations. These are measurements on one host, with no hard latency guarantee.

## Reproduce

The Python checks run on Windows or Linux with the checked-in archives, including physics 24, 25 and 26 and a native v2 WAL. The optional native v1 writer uses the existing Core and `Store` API. It is test-only and excluded from viewer installation.

~~~powershell
py -X utf8 -m unittest discover -s op0/tests -v
node --check op0/web/viewer.js
.\tools\start_op0.ps1 -NoBrowser
~~~

In a second PowerShell, use Node 22+ to repeat the browser controls and capture receipts. Node is needed for this test only.

~~~powershell
node .\op0\tests\browser_smoke.mjs 'C:\Program Files\Google\Chrome\Application\chrome.exe' 'http://127.0.0.1:8765' 'out\op0-browser'
py -X utf8 -m op0.tests.measure "$env:LOCALAPPDATA\AntWorld\OP0-benchmark" 'out\op0-browser\balanced.json' --demo 1
py -X utf8 -m op0.tests.measure "$env:LOCALAPPDATA\AntWorld\OP0-benchmark" 'out\op0-browser\dogleg.json' --demo 4
~~~

Choose a new cache path when measuring a cold index. On Windows with the portable LLVM toolchain and a normal static Release Core build, the optional v1 fixture can be included as follows. Replace the build folder with the one used locally if it differs.

~~~powershell
New-Item -ItemType Directory -Force 'out\op0-browser' | Out-Null
$clang = '.\.tools\llvm-mingw-20261104-ucrt-x86_64\bin\clang++.exe'
& $clang -std=c++20 -Icpp/include -O2 -static op0/tests/legacy_source.cpp build/release/libantworld_storage.a build/release/libantworld_core.a build/release/libantworld_sqlite.a build/release/_deps/antworld_zlib-build/libzs.a -o out/op0-browser/legacy_source.exe
$env:OP0_LEGACY_CLI = (Resolve-Path 'out\op0-browser\legacy_source.exe').Path
py -X utf8 -m unittest discover -s op0/tests -v
~~~

See [OP0 CI](https://github.com/Aquaticfuller/AntWorld/actions/workflows/op0.yml) for the Windows and Linux checks by git commit, and [Core CI](https://github.com/Aquaticfuller/AntWorld/actions/workflows/ci.yml) for the inherited native checks. OP0 does not modify the previous Core CI workflow.

## Known limits and review decision

The spatial viewer offers quantized 3D slices and recorded points. It does not infer between-event trajectories, chamber function or the internal cause of a decision. The 12-block decoded cache does not avoid loading published cut tables during indexing. A new native encoding requires a new reader contract. Unsupported versions and malformed inputs are explicit errors. Directory imports use the CLI and become available to the Web viewer after restart. User-level acceptance is replay of a stable archive. Live Core control, Unity and a biological readiness decision are out of this package. The S6.4 formal gate remains `FAIL`, the B06 match remains `INSUFFICIENT`, and the nine historical root blockers remain `BIOLOGICAL_BLOCKED`.
