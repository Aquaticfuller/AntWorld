# AntWorld OP0

OP0 replays real AntWorld C++ Simulation Core archives in a browser or terminal. Both clients use the same read-only API. The checked-in demonstration starts with one queen, no workers and a three-dimensional shaft. Its 150-day histories include colony growth and extinction under different resource conditions.

## Windows quick start

Install [Git for Windows](https://gitforwindows.org/) and [Python for Windows](https://www.python.org/downloads/windows/) if they are missing. OP0 needs Python 3.11 or newer and a current browser. The viewer uses only the Python standard library and bundled HTML, CSS and JavaScript. It requires no C++ build, Node, package manager or network connection after obtaining the repository. With Windows Package Manager, example installation commands are:

~~~powershell
winget install --exact --id Git.Git
winget install --exact --id Python.Python.3.13
~~~

After installing, open a new PowerShell window so it can see the commands.

~~~powershell
git clone --branch codex/op0-observation-preview --single-branch --depth 1 https://github.com/Aquaticfuller/AntWorld.git
Set-Location AntWorld
.\tools\start_op0.ps1
~~~

Keep that PowerShell window open. If the browser does not launch, visit [the local viewer](http://127.0.0.1:8765/). To use another port, run `.\tools\start_op0.ps1 -Port 8766`. If a download's PowerShell policy prevents launching the script, use the equivalent command from the repository root.

~~~powershell
py -X utf8 -m op0 serve
~~~

To choose a particular Python installation, pass its complete executable path with `-Python`. The default cache lives at `$env:LOCALAPPDATA\AntWorld\OP0`. Pass `-Cache 'E:\AntWorldObservationCache'` to use another drive with space. The largest bundled archive needs roughly 193 MiB of index space. Initial indexing may take several seconds. `Ctrl+C` stops the program.

Use the language selector in the top-right corner to switch between English and Simplified Chinese. The viewer keeps the current world, time, selected individual and comparison. The browser remembers the setting for this localhost address. Raw event names, parameters, evidence statuses and archive hashes remain available for review.

### What to look at

1. **Day 0.** The default underground cut shows Queen #2 and the initial shaft. Toggle **Body clearance** for quantized positions that can fit the unloaded Core body cube. Use the section controls to change the axis or the selected layer.
   **First eggs** shows when egg #4 is actually laid on day 4. The queen and early brood can share the same model coordinates. A numbered map marker shows how many individuals are at that projected point. Click the marker, the matching **At marker** button, or **Individuals in view** to select a single egg, larva, pupa or adult. The map never shifts them to invented coordinates.
2. **From the nest to the food.** Click **Watch first food delivery** beside the map to slow down the recorded steps and food transactions leading to the archive's first delivery. In the default world it follows worker #4 from its first departure at 15:36:00.103 on day 45 to collection at 15:36:41.025 and delivery at 15:37:33.049. The camera switches between underground and surface. **First worker**, **First collection**, and **First delivery** remain available for direct jumps to facts #9661, #9826 and #9938. Purple dots are an individual's recorded positions.
3. **Soil and recruitment.** **First excavation** opens fact #10692 and its actual material edit. The nearby **Soil placed** fact #10706 shows what happened to the same parcel. **Recruitment** opens actual activation #17118. Its preceding-fact link leads to the local scout cue and ultimately to the committed food delivery that generated it. Foraging reason labels and recruitment facts are separate.
4. **Larval loss.** **Larval death** takes the cursor to fact #5375. Open **Individual** to see larva #5, its mother, life events, the most recent recorded physiology sample and earlier care facts. A sample measured before death retains its own time. **All facts** and specific filters such as **Brood care** page through canonical events. When **Follow** is active the event list is scoped to the individual.
5. **Play the full history.** Use **Play**, the speed selector, the time slider or the day shortcuts. In **Activity within the day**, click one of the 24 hour cells or use the finer 24-hour slider. The bright cells mark recorded moves. **Movement only** with **Next event**, **Previous event**, or **Play** shows each committed movement in order instead of jumping ahead at days per second. **Event by event** also includes outcomes such as birth, food handling and soil transactions. For a real example, select **D45**, click the **15:00** cell and choose **Movement only**. The first two movement facts happen 101 simulated milliseconds apart. The activity totals include committed observations and updates, and the UI reports movement separately. Physiology uses published cuts. The population and resource counters follow committed facts. The charts share the time cursor.
6. **Observe failure.** Switch the archive to **No external supply**, **Protein-limited colony** or **Limited supply · dogleg**. Each entry is an original experiment with recorded negative outcomes. Open day 150 in **No external supply** to see the recorded extinction.
7. **Compare the feeding change.** From **Founding colony**, choose **Compare worlds**. The default reference is **Before the feeding correction**, the physics 25 run with the same recorded seed, geometry and maternal resources. Inspect the different ecological switches and parameter values. Move the shared cursor to evaluate first-census brood, worker survival, deliveries, recruitment and excavation over time. The profiles remain separate even when the archive headers share a WorldId.

### Terminal

~~~powershell
.\tools\start_op0.ps1 -Terminal
~~~

Enter `1` to verify and open **Founding colony**. Use `d 45` to jump to day 45, `e 9661` to open an exact event, `a 4` to track the first worker, `f food` to filter and `more` to page. `f care`, `f recruitment`, `f soil` and `f death` select other facts. Use `play 15` to advance at approximately 15 simulation days per second and press Ctrl+C to pause playback. `+` and `-` move one day. `w` returns to the world catalogue and `q` exits. The first view of an unopened entry identifies it as unverified until the source is indexed. The world list then includes its WorldId, physics, seed, integrity and recorded final status.

Use `h 15:36` within day 45 to seek by the simulated clock. `n` and `p` step forward and backward to the next or previous recorded outcome or move. The panel shows total committed records and movement counts for the selected day.

On Linux, the equivalents from the repository root are `python3 -m op0 serve` and `python3 -m op0 tui`.

Enter `lang zh-CN` or `lang en` at any terminal prompt. The terminal remembers the language in its local cache. To override the saved setting for one launch, use `.\tools\start_op0.ps1 -Terminal -Language zh-CN`.

## Add an experiment after a Core change

Import a stable backup of a native AntWorld SQLite store or a witness ZIP. For a SQLite backup that has a still-required WAL, place the matching `-wal` next to it. Close the source writer or export a consistent backup first. OP0 uses a temporary private copy and never creates a SQLite sidecar next to the source. A malformed or mismatched file fails verification.

~~~powershell
py -X utf8 -m op0 import 'D:\Experiments\new-world.zip'
py -X utf8 -m op0 import 'D:\Experiments\baseline.sqlite'
.\tools\start_op0.ps1
~~~

You can also run `.\tools\start_op0.ps1 -ImportPath 'D:\Experiments\new-world.zip'` or enter `import D:\Experiments\new-world.zip` in the terminal catalogue. Restart an already running browser service to reload the list. Import labels and caches are stored locally. The browser has no writes or upload route.

For comparable review runs, record the reference and candidate with the same declared seed, reserve profile, geometry, resources, horizon and sampling schedule. Change only the approved treatment. Export the original `initial.chk`, `final.frame` and `facts.bin`, and include `case.json`, `parameters.txt`, `cuts.csv`, `individuals.csv` and `geometry_edits.csv` when provided by the native experiment. Preserve the source commit and any existing experiment receipt separately. If a runner emitted a native export directory without a ZIP, package it as follows.

~~~powershell
py -X utf8 -m op0 pack 'D:\Experiments\candidate-export' 'D:\Experiments\candidate.zip'
py -X utf8 -m op0 import 'D:\Experiments\candidate.zip'
~~~

Select these two worlds in **Compare worlds**. Review exact facts, physiological snapshots and first-census cohort separately before interpreting a difference. Attach each source identity and its SHA-256 to the review. Keep failures and both independent archives. An imported checkpoint cannot provide a previously unrecorded individual measurement.

## Data contract and scope

[API.md](API.md) defines data provenance, times, units, paging, import versions and limits. [OP0_ACCEPTANCE.md](OP0_ACCEPTANCE.md) has actual Windows timings, screenshots, witness identities and automation commands. S6.4 retains its previous `ENGINEERING_ONLY` scope, B06 `INSUFFICIENT`, historical application performance `FAIL`, and nine `BIOLOGICAL_BLOCKED` rows. An observed trajectory is evidence of what this Core did in this experiment.
