# R0-r1 validation and run receipts

The reviewed reference is `9d04ed5dcf8993e7cddf7cde1556696112ce0469`. The native experiment implementation is `d31b331f37535f9f406f3408ad2d11de4a8be9da`, with C++ tree `cc7d84ad3d7a63d8ee6f080fb87d9a11ddd1991f`. The experiment executable SHA-256 is `b020910135d7cbe10c6b85396820c7b25bea44682879a3b3b62e6ad7f6df0890`. Individual acquisition receipts identify the protocol hash and physical command. The preview and recovery verifier ran from `ae1a05d437049bc39395121aa651aae81cb74550`.

## Local execution

| Check | Observed result |
| --- | --- |
| Windows Clang Release, all CTests | 291/291 passed in 57.03 s |
| Windows Clang Debug, all CTests | 291/291 passed in 197.43 s |
| Windows Clang ASan and UBSan, `R0_R1_NEST_DYNAMICS` | 1/1 passed in 4.79 s, sanitizer diagnostics empty |
| OP0 Python suite with native `antworld_m0_live` | 23 passed, one optional legacy fixture builder skipped. The Core CTest legacy migration passed. |
| Real Chrome replay | Paired founding shafts, 50- and 300-worker excavation previews, marker visibility, a true 262 ms motor lease and Simplified Chinese controls verified |
| Native journal and independent replay | Ten ZIPs verified, with complete fact/member hash checks, actual carried-envelope census and soil ledger. Two native runs reproduced the same initial, final and canonical fact bytes with SQLite recovery. |
| Repository policy | Local design manifest and English checks passed. JavaScript parsed and `git diff --check` passed. The remaining local historical audit encountered the precision difference below. |

The live application test caught the v33 manual save header whitelist. The save reader now uses the same ecological version set as the archived reader. The last test opened a real v33 save after worker emergence and compared the resumed frame with an uninterrupted reference. The unit-level Core test also recovers a movement while it is pending, then checks death, overlapping unit destinations, stationary rock walls and an injected journal-capacity rollback.

The local browser used Chrome 157.0.8103.78 and the loopback service. The archived repeated-load receipt reached the world view about 245 milliseconds after navigation on this host. This informal timing is separate from historical application qualification. Images show the worker segment, matched founding worlds, and the two excavating group sizes. The [exact event receipt](views/r0-r1-browser-receipt.json) identifies fact `71085` and its surrounding committed observations.

The first hosted preview run of the new smoke test timed out on the Linux transition from slow motion to the delivery milestone. The revised test waits for the exact terminal event and the visible event panel before activating the next milestone. Its Windows Chrome rerun passed. The failed run remains in Actions history. [Initial hosted preview run](https://github.com/Aquaticfuller/AntWorld/actions/runs/43752594152).

The local Python 3.15.2 full `ci_verify.py` run stops on one rounding difference in the frozen S6.2 `environment_correlations.csv`. Recomputing it in scratch identifies the dense package-power Pearson correlation as `-0.1332296623367503` versus `-0.13322966233675027` in the frozen table. The absolute change is `2.7755575615628914e-17`. The frozen input, output and audit rules are byte-identical to the reviewed ancestor. All five hosted Core jobs on the unchanged native implementation passed, including their repository audit where applicable. [Native implementation Core CI](https://github.com/Aquaticfuller/AntWorld/actions/runs/43751262129).

## Commands

```powershell
cmake -S cpp -B out/r0-r1-release -DCMAKE_BUILD_TYPE=Release
cmake --build out/r0-r1-release --parallel 4
ctest --test-dir out/r0-r1-release -C Release --parallel 2 --output-on-failure
cmake -S cpp -B out/r0-r1-debug -DCMAKE_BUILD_TYPE=Debug
cmake --build out/r0-r1-debug --parallel 4
ctest --test-dir out/r0-r1-debug -C Debug --parallel 2 --output-on-failure
cmake -S cpp -B out/r0-r1-sanitized -D CMAKE_BUILD_TYPE=Debug -D ANTWORLD_SANITIZERS=ON -D CMAKE_C_COMPILER=clang -D CMAKE_CXX_COMPILER=clang++
cmake --build out/r0-r1-sanitized --target antworld_r0_r1_tests
ctest --test-dir out/r0-r1-sanitized -C Debug --output-on-failure -R '^R0_R1_NEST_DYNAMICS$'
$env:M0_LIVE_CORE = (Resolve-Path 'out/m0-live-bin/antworld_m0_live_v6.exe').Path
python -B -m unittest discover -s op0/tests -v
python -B tools/ci_verify.py
python -B -m tools.verify_r0_r1 experiments/r0_r1/witnesses --replay out/r0-r1-recovery --scratch out
python -B -m tools.summarize_r0_r1 experiments/r0_r1/diagnostics out/r0-r1-tables
```

To repeat the browser run, serve `python -B -m op0 --micro --cache out/r0-r1-index serve --r0-r1 --replay --port 8768 --no-browser` in one terminal. In the other, run `node op0/tests/browser_smoke.mjs '<installed Chromium executable>' http://127.0.0.1:8768 out/r0-r1-browser r0r1`. The smoke test drives the actual canvas and checks archived facts, coordinate differences and visible application state. The viewer never instantiates a Core when serving these read-only archives.

The [results](RESULTS.md), [compact diagnostics](../../experiments/r0_r1/diagnostics) and [native witnesses](../../experiments/r0_r1/witnesses) are the evidence for this iteration. Published archives are sufficient to replay the observed demonstrations. Downloads and browser indexes are derived or read-only files. All temporary builds, native history stores and browser profiles for the validation above were kept in the project's D-drive output area.
