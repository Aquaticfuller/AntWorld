# MicroWorld native portability results

The default OP0 MicroWorld demonstrations use physics 29. Physics 30 is the development-only no-hatch-cue variant. The original physics 27/28 runs, public ZIPs, inputs and receipts remain unchanged, as do all physics 24–26 checkpoints. [The portability protocol](PORTABLE_REPLAY_PROTOCOL.md) defines the correction and the unchanged gates.

The first [Core CI run](https://github.com/Aquaticfuller/AntWorld/actions/runs/43648458825) and the [startup follow-up](https://github.com/Aquaticfuller/AntWorld/actions/runs/43648703101) rejected exact-byte replay under the original prototype. Both Release jobs reached identical fact counts but did not match the Windows Clang witness. An independent Linux GCC 11.4.0 build reproduced the issue using the same parameters and initial checkpoint, with SQLite 3.54.1 and the host zlib. In the shaft, worker #4's selected `ReturnToCareShelter` destination (event 8412) differed in the last binary digits of its horizontal coordinates. The subsequent completion and work interval differed by one millisecond. The resulting energy cut differed by one nJ. The dogleg first diverged at event 49351 in the same action. The saved [member comparison](../../experiments/m0/evidence/portable-member-audit.json) identifies the changed bytes and original hashes. These are observed failures of the original numerical policy, regardless of equal counts.

The corrected care norm fixes binary64 operation order before the IEC 559 square root. The chosen displacement, upward whole-millisecond duration, and restore-time duration check share that policy. It does not bypass walls, extend reach or change speed. An exact-coordinate and integer-boundary regression records the previously divergent diagonal. This is a numerical compatibility correction, not a revision of biology or the original science protocol.

The two released physics 29 worlds have exact matches for all seven stable members after a day-45 SQLite save and load on both native Windows (LLVM-MinGW) and Linux (GCC). The comparison includes input, initial checkpoint, final frame, complete framed facts, daily population and physiology, and geometry edits. No data transformation or tolerance is used. The local Linux build was a targeted diagnostic; the Core workflow repeats the check with the repository build and pinned dependencies. The portable roster results and both native run receipts are archived in `experiments/m0/evidence/`.

All 28 portable-panel cases completed on Windows. Their canonical streams contain 2,163,510 facts, with each case retaining its original Windows hash. The derived cohort traces and the two sets of individual work windows are also byte-identical. The original table, negative scenarios and scientific boundaries in [M0 results](M0_RESULTS.md) apply unchanged. State and input headers deliberately differ where physics 29/30 was selected. For example, the original energy-depletion failures and lower complete delivery count remain present.

The portable archive was opened and exercised in Windows Chrome. A [runtime receipt](../../experiments/m0/evidence/portable-browser/m0-browser-receipt.json) and actual screenshots record the journey from the first clutch to care, a loss, food delivery, and excavation. The one measured start was about 0.93 s; the prior browser-start observations, including the 73.7 s result, are retained separately and no general browser latency claim follows.

The Windows launcher opened the portable shaft, sought day 90 and tracked worker #4 with 15 workers alive. The 16 OP0 tests passed, including the local HTTP and native legacy SQLite fixtures. The targeted Release CTest passed the clock, allocation, rollback and save-and-resume checks. Both local logs are included under `experiments/m0/evidence/tests/`.

The first [portable OP0 CI run](https://github.com/Aquaticfuller/AntWorld/actions/runs/43652057167) also recorded a browser harness error at navigation, before checking the world. The follow-up makes readiness polling wait for the new document and actual application state. The browser assertions for positions, histories, care, delivery and excavation are unchanged.

```powershell
py -B tools/run_m0.py build/m0-release/antworld_s6_4_wp6b.exe out/m0-portable-panel --portable-care
py -B tools/run_m0.py build/m0-release/antworld_s6_4_wp6b.exe out/m0-portable-replay --portable-care --durable --case borisovka-shaft-1-slots --case st_petersburg-dogleg-1-slots
py -B tools/verify_m0.py experiments/m0/portable-demo --portable-care --replay out/m0-portable-replay
```

The compact witnesses are independent of local caches. Use the original `experiments/m0/demo` path without `--portable-care` to verify the first published witnesses. Loading those archives for observation does not reinterpret their original clock.
