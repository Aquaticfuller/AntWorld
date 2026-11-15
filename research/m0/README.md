# AntWorld MicroWorld on Windows

Use the [R0 preview](../r0/README.md) to watch actual rest relocation and compare paired shaft or dogleg chambers.

## Run a live colony

In an existing MicroWorld checkout, start the local viewer from PowerShell.

```powershell
Set-Location 'D:\Codex_workspace\AntWorld'
.\tools\start_m0.cmd
```

If a previous AntWorld service holds the port, press Ctrl+C in its terminal first. Keep the new terminal open and open [MicroWorld](http://127.0.0.1:8765/) if the browser stays closed. The `.cmd` launcher works with PowerShell script execution restrictions. You can also use your Python executable directly.

```powershell
& "$env:LOCALAPPDATA\Python\bin\python.exe" -B -X utf8 -m op0 --micro serve
```

If the page asks for a native build, use a full checkout with Python 3.11 or newer, CMake and the repository's C++ toolchain. The builder reuses the portable toolchain in `.tools` when available. With CMake on PATH it can also use an installed C++ toolchain. Build `antworld_m0_live` once before starting the viewer.

```powershell
python -B tools/build_m0_live.py
.\tools\start_m0.cmd
```

1. Select **New colony**. The C++ Core creates a new world on day zero with a queen in the protected shaft. The default `1×` speed advances one simulated second per elapsed second. The clock shows the day, hours, minutes and seconds. The Web page displays published Core positions and recent events. Choose **15-minute worker checks (experimental)** before starting a colony to try the shorter rhythm.
2. Use **Pause** and **Resume** to inspect the current world. Select `60×` for a simulated minute per elapsed second or `86,400×` for up to one simulated day per elapsed second. The Core can run behind the requested speed when it has more work to process.
3. Choose a target event and select **Fast-forward to event**. The Core runs at up to `86,400×` and pauses at the exact timestamp of the committed milestone. For the first nest exit, food delivery or excavation, the viewer follows the worker that performed the action. Select **Resume** to continue following at `1×`. **Cancel fast-forward** is available while waiting. Earlier milestones display their recorded time in the current world.
4. Select **Save and load**, enter a name, and select **Save colony**. The list shows each save's simulated age, file size and modification time. **Load** restores the saved colony paused at the saved time. Resume to continue. Saving to an existing name asks for confirmation.
5. Select **Open save folder** to manage the SQLite files in Windows File Explorer. Use **Refresh** in the save window after moving or renaming a file. The default folder is `out/m0-saves` in the checkout. Override it with `.\tools\start_m0.cmd --saves 'D:\AntWorldSaves'`.
6. Select **Archive replay** to browse the earlier demonstrations and comparisons. The live Core continues while you browse another view or close the browser tab. Pause or save the colony before stopping the local service with Ctrl+C.

The live preview runs one colony and holds its state and history in memory until you save. Each named save holds one full SQLite snapshot and its committed history. While a loaded colony is open, a private working copy keeps its history accessible if you move its save file. The working copy is removed on normal shutdown. Save storage, the archive index and build output use the checkout's drive by default. The live profile is the reviewed Borisovka balanced-shaft fixture with physics 29 and seed 1. Its `ENGINEERING_ONLY` label applies during live observation as it does during archive replay.

Positions hold between committed movements. **Recent in-place actions** lists recent completed feeding, trophallaxis and brood handling. Select a record to inspect the participants, exact timestamp and any transferred material. Short-lived labels sit at the original event locations. The standard fixture uses hourly intake and exchange checks and six-hour task reviews. See [the worker timing experiment](WORKER_ACTIVITY_TIMING.md) for the paired runs and camera-data limits.

## Replay archived colonies

The bundled MicroWorld archive begins with one queen and ends at day 90. A sparse checkout can browse the archives with Python 3.11 or newer and a local browser. It needs no C++ build.

```powershell
Set-Location D:\Codex_workspace
git clone --filter=blob:none --sparse --depth 1 --single-branch --branch codex/m0-live https://github.com/Aquaticfuller/AntWorld.git AntWorld-M0
Set-Location AntWorld-M0
git sparse-checkout set op0 tools experiments/m0/portable-demo research/m0
.\tools\start_m0.cmd --replay
```

The archive launcher uses `out/m0-op0-cache` for its disposable browse index. To put the index on another drive, run `python -B -m op0 --micro --cache 'D:\AntWorldObservationCache' serve --replay`. The replay viewer also accepts a stable native save for read-only inspection through `.\tools\start_m0.cmd --replay --import-path 'out\m0-saves\My colony.sqlite'`.

1. Open **MicroWorld · shaft**. A horizontal section through the founding chamber shows the queen. Select **Watch egg placement**. The next scene shows the first egg at its committed position. Scrub just before day 5 to see the first clutch, or select **Watch brood arrangement** to replay an actual handling bout. Change the section between horizontal and either vertical direction to inspect the pocket and shaft.
2. Select **Brood fed** to jump to a measured handling completion, or **Watch brood feeding** to see its recorded start and end. The event panel identifies the participants and transferred mass. **Larval death** opens a real lost individual. In **Individual**, the nearest prior sampled physiology still carries its own observation date.
3. Press **Play** to visit the major milestones and the recorded beginnings and ends of care actions. Select **Watch first food delivery** to follow the same worker out of the nest, to its actual food transaction, and back underground. **First excavation** leads to a terrain edit and its soil parcel. **Soil placed** gives a later physical transaction. Use the hourly slider, **Event by event** or **Movement only** for individual commits. The optional colony overview skips intervening seconds. The viewer holds recorded positions between events.
4. Select an ant and then **Individual time budget and physiology**. Choose **Selected day** or **Three-day window**. The panel reports time alive, time in each task program, paid work, committed distance, exact timed movement where witnessed, doses and sampled body energy and water. A blank duration is unknown. A pause in a program does not measure sleep.
5. Switch to **MicroWorld · sealed entrance** to see an imposed barrier and a real resource failure. **MicroWorld · no external protein** shows a different control in which some workers survive on maternal reserves and other nutrients. Under **Compare worlds**, choose **MicroWorld · reference placement** to line up the same shaft geometry, seed and starting materials with the old placement rule. Switch the language between English and Simplified Chinese at the top of the page.

The initial underground section is local to the chamber. The surface shows the full arena. Markers are enlarged for readability and retain their exact coordinates. Older OP0 demonstrations and the terminal viewer are still available. Use `.\tools\start_op0.ps1 -MicroWorld -Terminal -Language zh-CN` to choose a world by number in the terminal. The browser and terminal read the same indexes.

Use `-ImportPath` with a native archive to inspect a new case. The default M0 archives are under `experiments/m0/portable-demo`. Their stable physics 29 clock corrects a cross-platform rounding issue; the original physics 27 witnesses are still importable from `experiments/m0/demo` in a full checkout. The code version, physics generation, file identity and scientific status are displayed in the archive information panel. The demonstrations are `ENGINEERING_ONLY`.
