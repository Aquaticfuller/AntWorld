# Open AntWorld MicroWorld on Windows

The archive begins with one queen and ends at day 90. You can open it without a C++ build. Use Python 3.11 or newer, Git and a local browser. OP0 uses the Python standard library and files bundled in the repository.

```powershell
Set-Location D:\Codex_workspace
git clone --depth 1 --single-branch --branch codex/m0-microworld https://github.com/Aquaticfuller/AntWorld.git AntWorld-M0
Set-Location AntWorld-M0
.\tools\start_op0.ps1 -MicroWorld
```

In an existing MicroWorld checkout, run the last command from its root. If the browser stays closed, open [the viewer](http://127.0.0.1:8765/). The terminal window runs the local service. Press Ctrl+C there to stop it. The launcher uses `out/m0-op0-cache` inside the checkout for its disposable browse index. To put the index on another drive, use `-Cache 'D:\AntWorldObservationCache'`. If a PowerShell execution policy blocks the script, the equivalent command is `py -B -m op0 --micro --cache out/m0-op0-cache serve`.

1. Open **MicroWorld · shaft**. A horizontal section through the founding chamber shows the queen. Select **Watch egg placement**. The next scene shows the first egg at its committed position. Scrub just before day 5 to see the first clutch, or select **Watch brood arrangement** to replay an actual handling bout. Change the section between horizontal and either vertical direction to inspect the pocket and shaft.
2. Select **Brood fed** to jump to a measured handling completion, or **Watch brood feeding** to see its recorded start and end. The event panel identifies the participants and transferred mass. **Larval death** opens a real lost individual. In **Individual**, the nearest prior sampled physiology still carries its own observation date.
3. Press **Play** to visit the major milestones and the recorded beginnings and ends of care actions. Select **Watch first food delivery** to follow the same worker out of the nest, to its actual food transaction, and back underground. **First excavation** leads to a terrain edit and its soil parcel. **Soil placed** gives a later physical transaction. Use the hourly slider, **Event by event** or **Movement only** for individual commits. The optional colony overview skips intervening seconds. The viewer holds recorded positions between events.
4. Select an ant and then **Individual time budget and physiology**. Choose **Selected day** or **Three-day window**. The panel reports time alive, time in each task program, paid work, committed distance, exact timed movement where witnessed, doses and sampled body energy and water. A blank duration is unknown. A pause in a program does not measure sleep.
5. Switch to **MicroWorld · sealed entrance** to see an imposed barrier and a real resource failure. **MicroWorld · no external protein** shows a different control in which some workers survive on maternal reserves and other nutrients. Under **Compare worlds**, choose **MicroWorld · reference placement** to line up the same shaft geometry, seed and starting materials with the old placement rule. Switch the language between English and Simplified Chinese at the top of the page.

The initial underground section is local to the chamber. The surface shows the full arena. Markers are enlarged for readability and retain their exact coordinates. Older OP0 demonstrations and the terminal viewer are still available. Use `.\tools\start_op0.ps1 -MicroWorld -Terminal -Language zh-CN` to choose a world by number in the terminal. The browser and terminal read the same indexes.

Use `-ImportPath` with a native archive to inspect a new case. The shipped archives are under `experiments/m0/demo`. The code version, physics generation, file identity and scientific status are displayed in the archive information panel. The demonstrations are `ENGINEERING_ONLY`.
