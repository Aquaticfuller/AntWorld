# M1 Live Colony Observatory results

This release candidate adds a native live observation workflow and a bounded ecology experiment. The [Windows start guide](README.md) covers the three live presets and the archived witnesses. [Protocol](PROTOCOL.md) defines the independent pairs, observations and stop rules. The reviewed habitat base is `36bbf99bd0cd28c992a6fa830dccfb9ff9e419a8`.

## Observed user workflow

Windows Chrome drove the actual native Core over the loopback service. The test opened a single-queen world, rotated and clipped the 3D view while paused, selected the queen and checked the original 2D section. The first egg was fact `107` at day 4. Worker `16` crossed the surface at fact `8344` on day 46. The same worker delivered **1,333 µg carbohydrate, 667 µg protein and 2,000 µg water** at fact `8484`. The browser selected that worker, restored the save at the same simulation time and independently retrieved the same delivery from the verified SQLite replay. It checked Simplified Chinese, both other native presets, the real shallow plug edit and the no-supply case's committed death reason.

- [Chinese view of the first egg](screenshots/m1-first-egg.png)
- [Completed food delivery and worker physiology](screenshots/m1-worker-delivery.png)
- [Excavation and soil parcel evidence](screenshots/m1-excavation.png)
- [No-supply archive and queen death](screenshots/m1-no-supply.png)
- [Live browser receipt](../../experiments/m1/m1-browser-receipt.json) and [archive browser receipt](../../experiments/m1/m1-witness-browser-receipt.json)

The 3D scene uses the Core surface, initial voids, rock and ordered edits. It merges exposed interfaces into faces and omits the sides of the bounded observation window. Drag, zoom, selection and camera tracking are local browser actions. Motion interpolation at 1× uses contiguous committed segments when the endpoints can be verified against published cuts under one geometry revision. Drawn icons are symbolic and use the recorded position and stage. The 2D view still exposes the independent research cut. The [observation API](../../op0/API.md) defines its evidence levels and live scan limits.

## Founding stability

All 16 original physics 36 day-90 runs reproduced on Windows with the same initial native checkpoint, canonical history and terminal frame SHA-256. [Original binary receipts](../../experiments/m1/baseline-native.jsonl) and [M1 binary receipts](../../experiments/m1/baseline-final.jsonl) retain each run, including the thick closed, cool and warm/dry controls. Native generator inputs, executable SHA-256 and the producing sources are in each receipt and the [producer manifest](../../experiments/m1/witnesses/run.json).

`reference` uses physics 36. `reachable` uses the opt-in physics 37 with schema 30. A worker without an established route may approach a different supported, traffic-clear contact site near the depot when the original anchor is unavailable. The existing route, actual contact tests, perception radius, activity costs, resources and deposits still govern the behavior. The three default live presets use physics 36. Temperature, humidity, trail half-life and berth policy are engineering fixture settings.

All 32 worlds reached both day 90 and day 150 on their original trajectory. Each row below sums four software seeds in an open entrance treatment. Food deliveries exclude water-only deliveries.

| Trail half-life | Policy | Live workers at day 90 | Food deliveries by day 90 | Live workers at day 150 | Food deliveries by day 150 | Water-only deliveries by day 150 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 60 s | Reference | 6 | 14 | 7 | 15 | 9 |
| 60 s | Reachable | 19 | 22 | 9 | 25 | 23 |
| 1,955 s | Reference | 7 | 12 | 5 | 15 | 22 |
| 1,955 s | Reachable | 9 | 14 | 10 | 20 | 29 |

The alternative produced 45 food deliveries across the eight open worlds by day 150 versus 30 for the matched reference. Seed 2 in the 60 s treatment delivered more while retaining one fewer living worker at day 150. At day 90, seed 6 in the 1,955 s treatment had one fewer food delivery with the alternative. Both effects are in the [per-world paired receipts](../../experiments/m1/paired.jsonl), which also record the actual flow, first eclosion, deaths by stage and cause, recruitment, movement duration and distance, daily close-body pairs and the stock gaps. Trail half-life effects differed by endpoint and seed. These fixtures do not define a species trail lifetime.

All 16 thick closed worlds recorded zero external deliveries and zero surface crossings through day 150. Excavation still occurred at accessible underground boundaries. **All 32 queens died of recorded energy depletion between days 70.44 and 79.15.** Increased worker deliveries were insufficient to resolve early queen survival. The shallow-plug witness records six `NutritionTransferred` facts with the queen as recipient, plus 32 maternal rations and 55 withdrawals from the finite wick. Even in this case the queen died near day 70.47. A transfer and its subsequent energetic effect are separate observations.

| Extended trajectory | Last verified day | Last live count | Result |
| --- | ---: | --- | --- |
| Open, finite supply, seed 1 | 240 | 0 | Completed after colony loss |
| Open, finite supply, seed 2 | 202 | 2 workers | Stopped at the 120 s wall budget |
| Shallow plug, finite supply, seed 2 | 93 | 8 workers and 2 pupae | Stopped at the 120 s wall budget |
| Open, absent supply, seed 2 | 240 | 0 | Completed without any external delivery |

The [extended run receipts](../../experiments/m1/extended.jsonl) retain both stops and their exact confirmed cuts. The [independently replayed shallow-plug witness](../../experiments/m1/witnesses/m1-2-plugged-finite-day90.zip) reaches the prior day-90 frame and canonical hashes. It records 32 geometry edits, food and water delivered, seven live workers, three pupae and one larva on day 90. A second [complete witness](../../experiments/m1/witnesses/m1-2-open-absent.zip) records the absent resource control through day 240. The positive witness establishes opening and delivery, with the founder's death retained. The compact ZIPs contain native initial state, terminal frame and complete event journals for their published horizons. They total 4,410,094 bytes. [Independent archive verification](../../experiments/m1/archive-verification.json) checks both sources, terminal states and derived material volumes.

## Observation cost

The actual observation window is at most 64 × 40 × 64 quantized cells. Each volume uses at most 160 KiB of material bytes before transport encoding. For the live delivery test, the local geometry merged into 29 faces. The Windows browser measured 73 frames over 1,200.9 ms at 1×, 0.5 ms for the final draw and 11.7 ms at the reported mesh build. Pause and resume took 85 and 137 ms in that interaction run. A separate earlier run under concurrent local workloads observed a 90.2 ms mesh build. Camera rotation in the paused browser reused the same mesh and preserved the native simulation time.

The [accelerated browser soak](../../experiments/m1/m1-soak-receipt.json) reached the first sampled cut after day 150 with the 3D view active and paused with 600,412 committed facts. The process retained 9,046,617 bytes of packed history and peaked at 28,127,232 bytes of native RSS. The largest sampled Chrome JavaScript heap was 4,516,692 bytes. Native CPU time was 16.20 s, the Python service used 13.72 s and the session wrote zero persistent save bytes. The initial mesh plus nine geometry revisions led to ten rebuilds. The sample includes 21 measurements and distinguishes native RSS from browser JS heap. Those figures do not establish a general latency envelope for every device or colony size.

Independent archive verification took about 13.7 s for 266,265 facts with a 25.8 MB derived index and about 1.6 s for 71,615 facts with a 6.7 MB index. The separate cold browser witness reached the initial view in about 8.0 s. These measurements include different local workloads. Browse indexes can be regenerated. Routine live watching and this soak require no repeated durable saves, and browser performance here is separate from the historical S6.4 application gate.

## Verification and reproduction

```powershell
py -3 -B -m tools.build_m0_live --jobs 4
$core = py -3 -B -c 'from op0.live import core_path; print(core_path())'
py -3 -B -m tools.run_m1_habitat archive36 --core $core > out/m1-physics36.jsonl
py -3 -B -m tools.verify_m1_habitat --rerun out/m1-physics36.jsonl
py -3 -B -m tools.run_m1_habitat paired --core $core > out/m1-paired.jsonl
py -3 -B -m tools.run_m1_habitat extended --core $core > out/m1-extended.jsonl
py -3 -B -m tools.run_m1_habitat witness90 --core $core --output out/m1-witness90
py -3 -B -m tools.verify_m1_habitat
$chrome = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
py -3 -B -m tools.test_m1_browser --core $core --browser $chrome --output out/m1-browser
py -3 -B -m tools.test_m1_browser --core $core --browser $chrome --output out/m1-browser --mode m1-witnesses
py -3 -B -m tools.test_m1_browser --core $core --browser $chrome --output out/m1-browser --mode m1-soak
```

Use PowerShell 7 for the UTF-8 redirection in these reproduction commands. `--platform-report` compares the complete receipt with the published Windows data. `--reference` accepts a reviewed executable's reproduction on the same toolchain and requires byte-for-byte agreement there.

### Platform-specific history

The first cross-toolchain check flagged the shallow-plug control. A subsequent Ubuntu build of the reviewed source matched M1 byte-for-byte in all 16 cases on the same compiler. Across Windows Clang and Linux GCC, 14 cases matched exactly. The shallow and thick-plug controls diverged. The shallow control ended day 90 with 266,265 facts, seven live workers and 32 edits on Windows, versus 253,140 facts, six live workers and 30 edits on Linux. The thick closed control retained the reported population and delivery endpoints with a different journal SHA-256. See the [initial failure](https://github.com/Aquaticfuller/AntWorld/actions/runs/44200610229), [same-platform job and artifacts](https://github.com/Aquaticfuller/AntWorld/actions/runs/44202106272), and [independent local Linux comparison](../../experiments/m1/platform-linux-local.json).

The local Linux shallow-plug witness started from the same native bytes as the Windows witness. Its first different fact was `138444` at `6284296144` ms. Worker `16` selected **Approach a nestmate** in both journals. Windows selected target `61`, and Linux selected target `36` with a different destination. `local_contact_step()` ranks candidates using floating-point distance and strict score comparisons. The first divergent choice is established by the journals, while its exact numeric cause and a future portable ranking policy remain open. Physics 36 retains its historical behavior. See the [decoded fact pair](../../experiments/m1/shallow-first-platform-difference.json). The independent local probe used Ubuntu 22.04 GCC 11.4 with `-std=c++20 -O3 -DNDEBUG`, the same SQLite source and the installed Linux zlib. The official job builds both revisions with the same pinned CMake dependencies.

The local Windows Release CTest sweep exercised all 291 cases. One `FND_IF_BOUNDARY_COLONY` invocation timed out during concurrent experiments and its existing unmodified case passed on the isolated retry in 64.84 s. The four targeted M1 tests passed, including exact continuation of the physics 37 SQLite world. Browser smoke and both published witnesses passed on Windows Chrome. OP0 passed on hosted Ubuntu and Windows. The initial hosted M1 Chrome attempt on Linux stopped before the debugging port became ready. The harness now uses the existing Linux browser temp environment and a longer startup allowance for its automated tool. Hosted Core jobs cover Windows/Linux Debug and Release plus Linux sanitizers. [GitHub Actions](https://github.com/Aquaticfuller/AntWorld/actions?query=branch%3Acodex%2Fm1-live-colony-observatory) shows the run states by exact commit.

## Readiness boundary

M1 provides a runnable Windows observation candidate with real founding, foraging, delivery, excavation, individual tracking and native save/replay. The result still shows a material founding stability gap under the fixed habitat and supply. Both extended stops and observed program differences are part of the evidence. The scene is a local orthographic material view with horizontal clipping and symbolic individuals. Data gaps hold a recorded pose. The life panel progressively indexes history, and archived physiology retains its source sampling resolution. B06 remains `INSUFFICIENT`, the historical S6.4 application performance qualification remains `FAIL`, and all nine BR findings remain `BIOLOGICAL_BLOCKED`. The biological readiness remains `ENGINEERING_ONLY` pending independent review.
