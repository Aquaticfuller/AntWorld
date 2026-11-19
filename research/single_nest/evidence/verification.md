# Anatomical nest verification receipt

The verification used the Windows AntWorld workspace on 19 November 2026. The development base was `56840560fa8f2356ca6c857817cfd35d68e195b7`. The base [Core CI run](https://github.com/Aquaticfuller/AntWorld/actions/runs/44608366755) stopped its four configuration jobs at the repository policy check. The preview moved the existing Chinese interface strings into the approved locale catalog, and the English source policy subsequently passed locally. The baseline sanitizer job succeeded.

## Windows Release and browser

The Release binary was built with CMake 3.31.10, Ninja and the existing LLVM-MinGW Clang toolchain. The Python client used Python 3.15. Each command started from the repository root with Python and CMake on `PATH`, or with their local executable paths substituted.

~~~powershell
python -B -m tools.build_m0_live --jobs 4
cmake --build build/m0-live --parallel 4
ctest --test-dir build/m0-live --parallel 3 --output-on-failure
$env:M0_LIVE_CORE = (Resolve-Path 'out/m0-live-bin/antworld_m0_live_v14.exe').Path
python -B -m unittest op0.tests.test_live op0.tests.test_nest_volume -v
python -B -m tools.run_single_nest_overhaul --model anatomical --output out/single-nest-assay/anatomical-ranked.json
python -B -m tools.test_m1_browser --mode overhaul --core $env:M0_LIVE_CORE --browser 'C:\Program Files\Google\Chrome\Application\chrome.exe' --scratch out --output out/single-nest-overhaul-browser
node op0/tests/live_motion.mjs
python -B tools/check_repository.py
python -B tools/verify_handoff.py
~~~

Windows Release CTest passed all 291 tests after building all targets. An earlier invocation in the observer-only build correctly reported missing test executables. The live tests verify conserved mass, birth relative to the posterior, actual transport, excavation, finite-stock delivery, and both compact and SQLite continuation. During custody, a fresh run and a restored checkpoint must end in the same frame. The late case continues through the next day after restoring a 2,048-fact compact suffix or a full archived history. The Windows Chrome case operated the real 3D view and language switch. It sought native birth, manipulation, maturation, excavation and delivery events, saved and resumed the world, and checked rendering. The archived motion projection, repository policy and tracked handoff manifest passed locally.

Windows Debug passed the native `M0_BROOD_SPACE` CTest and both live confirmation cases. The batch launcher's `--help` returned the live server options. The final browser receipt records a 2.50 s first view, a 0.60 ms sample of CPU draw time and a 366,471-byte compact save after delivery. The local sandbox blocked a Chrome crash-reporter startup and one loopback socket test. Browser verification used the ordinary Windows process and local socket permissions.

Windows Release passed all 25 live and bounded-geometry Python tests with loopback available. The first hosted [Windows M1 build](https://github.com/Aquaticfuller/AntWorld/actions/runs/44627111451/job/135923760998) failed because MSVC treated two name-shadowing warnings as errors. The follow-up renames the compass constant and the connector backtracking point. No route, physical value or qualification threshold changes in that fix.

The Physics 38 native comparison used the existing v13 binary and the Physics 39-capable build in reference mode. On the same Windows machine the refactor preserved reference frames through days 0, 10, 60 and 150 in the tested recipe. The day-150 SHA-256 before the final local-search ranking adjustment was `a9cb894922a3c6f1a3f6316c6be6c32f4cfd79bbdb7ac7f8b4ae6bfa08d08e08`. The new ranking operates only inside the Physics 39 brood approach.

## Linux and cross-build limits

The Ubuntu WSL instrumented build used GCC 11.4 and Python 3.10, with `-std=c++20 -ffp-contract=off -fsanitize=address,undefined -fno-omit-frame-pointer -fno-pie` for the Core and its live application. It linked the SQLite amalgamation from the existing pinned CMake source cache and the system zlib. The core objects used `-O1` except the final care edit and checkpoint audit, which used `-O0`. The executable was linked with `-no-pie`. The native MicroWorld geometry, obstruction and persistence fixture passed with `ASAN_OPTIONS=detect_leaks=1:halt_on_error=1` and `UBSAN_OPTIONS=halt_on_error=1`. Both Linux seed 3 live fixtures passed with those options. Python 3.10 used a local context-manager helper for the `unittest` API available in the hosted test version.

| Scenario | Windows Release | Linux GCC ASan/UBSan | Cross-build comparison |
| --- | --- | --- | --- |
| Seed 2 from the same initial pocket, day 5 | 320 committed facts | 347 committed facts | Initial and day-4 frames match. The choice of a first local approach differs at fact 143. |
| Seed 2 through day 30 | 7 completed placements | 0 completed placements | The seed-2 custody smoke test originally failed on Linux at day 12. |
| Seed 3 through day 12 | 1,389 committed facts | 1,389 committed facts | All sampled frames through day 12 have matching hashes. |
| Seed 3 at day 30 | 4,821 facts and 5 completed placements | 4,821 facts and 5 completed placements | The frame bytes differ at this cut. |

The first seed-2 divergence was observed at 367,200,001 ms. The selected target was egg 9 on both builds. The selected approach x coordinate was `+0.0006875` m in Windows and `-0.0006875` m in Linux. Bounded A* rankings now use integer micrometre distances. This eliminated floating-point near-ties in the comparator. The platform divergence persisted. Cross-build trajectory identity is open, including for seed 3 over the longer interval. The positive custody/recovery test now uses the published seed 3 fixture on both systems. It still requires paid birth, pickup, transport, a distinct placement, cleaning and exact local continuation. The seed 2 divergence remains an independent negative witness.

The [Windows](platform-windows.jsonl) and [Linux](platform-linux.jsonl) files contain the sampled frame identities and initial facts. To compare the same cuts, start `NativeCore` with the desired executable and request `NEW_ANATOMICAL_NEST 9202 2 250 80 plugged 1955 reachable finite` or `NEW_ANATOMICAL_NEST 9203 3 250 80 plugged 1955 reachable finite`. Hash the initial frame and the results of `ADVANCE` at days 4, 5, 10, 12 and 30 using 86,400,000 ms per day. `tools.compare_m0_worker_rhythm.facts` reads the canonical facts through the last frame cursor. The regular headless assay documents the same world commands and carries the longer time series.

## Content and resource budget

The tracked data contain the four candidate and four reference receipts, two browser images and a compact browser action receipt. They contain bounded witness facts and state cuts. The assay command regenerates the receipt directly from Core. The base history and existing scenario artifacts remain available in their original paths. The receipt measures an elapsed native advance and a sampled peak native working set. The browser collects startup and CPU draw elapsed times. These values do not constitute a frame-rate benchmark or an admission under the historical S6.4 performance protocol.

| File | SHA-256 |
| --- | --- |
| `anatomical.json` | `1a15a969b811a692aece4c6b8e8ec9de9e21bd3546e3851234327f1fbe5467a9` |
| `reference.json` | `fd3bde393639b572574fd3f494d7c4fc994b79a82e148fdf4fafcbe94334b311` |
| `brood-zh.png` | `5aea89723a39b511c9f3811ea7c30b43921195ddb7be9a8c01d74cf2aad375b3` |
| `delivery-en.png` | `0a1852221f3e9abe4cb6aa669bea3b8a9d1f6e2cade288acfd96c0bf86abcec2` |
| `browser.json` | `69020e64015ee5c9676abbb010e1448f97877923ef3b5192eeecb3316403a9e7` |
| `platform-linux.jsonl` | `998f29bdc126f4fbf583ef9adfb160c57ba4f3c6ae7f6311da4bcf3911feb78d` |
| `platform-windows.jsonl` | `fc8e255523287fe457ef9c3aebcaaf57c4f7b114bbd812294a2662b8a3e9ba65` |

The published Windows binary identity for Physics 39 is `dd3adfa6b7bb104814e4ba12b44b2df78dc176c1756ee9becaeb7de5343e04ed`. The Ubuntu sanitizer binary used in the comparison is `bf4d17b8167be064bbfb51a972cd51cc3d2a0dd65d7222a0b8a2bbde4eb82997`. The retained reference binary identity is recorded in `reference.json`.
