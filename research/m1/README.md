# Open the M1 Live Colony Observatory

On Windows, use Python 3.11 or later, Git, CMake and a C++20 compiler. The first native build uses the repository's pinned SQLite and zlib dependencies. If this is an existing AntWorld checkout, use the active M1 branch and skip cloning. A compatible existing portable toolchain under `.tools` is detected automatically. Install or bootstrap toolchains on the drive chosen for the repository if local disk capacity is limited.

```powershell
Set-Location 'D:\Codex_workspace'
git clone --branch codex/m1-live-colony-observatory --single-branch --depth 1 https://github.com/Aquaticfuller/AntWorld.git
Set-Location AntWorld
py -3 -B -m tools.build_m0_live --jobs 4
.\tools\start_m0.cmd
```

Run the build only after switching to a new source version. If Python is installed as `python` without the `py` launcher, use `python -B -m tools.build_m0_live --jobs 4`. The `.cmd` launcher does not require changing the PowerShell execution policy. If the browser does not open, visit `http://127.0.0.1:8765`. Use `--port 8770` if the default port is in use.

1. Click **Open entrance**, **Shallow soil plug** or **No external supply**. The clock is initially at 1× real time. The founder is selected in the 3D nest. Choose a language from the selector in the header.
2. Drag the view to rotate it, use Shift-drag to pan, or scroll to zoom. With the view focused, the arrow keys also rotate, and `+` and `-` zoom. Set the observation scale to **Chamber**, **Nest** or **Habitat**. Use **Cut depth** and **Transparent ground** to inspect the passage. **Surface** and **Underground** are the original 2D evidence modes.
3. Use **Founding milestones** or the **Target event** menu to find the first egg, hatch, worker, exit, food delivery or dig. An unreached milestone with a fast-forward button stops the live clock after a matching fact commits. Clicking an already observed milestone opens the original event. For exit, delivery and excavation the viewer selects the worker involved when it stops at the event. Resume at 1×. The **Follow** control holds the camera on the selected identity.
4. Click an individual or use **Individuals in view** to distinguish neighboring identities. Use the individual panel for known birth, parent, physiology and lifecycle. Click an event to inspect the EventId, position, quantities, cause or soil parcel when recorded.
5. Open **Save and load** and choose a name. **Load** restores the native world paused. **Replay** indexes that saved copy in read-only mode and opens its recorded time range. **Open save folder** shows its location in Explorer. The clock only writes a persistent save on explicit request.
6. Choose **Archives** to open the M1 witness worlds where present. The shallow-plug archive contains actual excavation and resource delivery. The no-supply archive shows the early colony without external provision. Event replay preserves recorded positions and jumps by fact or timestamp.

The launcher uses `out/m0-op0-cache` for regenerated browse indexes and `out/m0-saves` for manually named saves. Move or clear the browse index only after closing the viewer. Keep the SQLite saves and original witness ZIPs for later replay. The following command opens the archive viewer without starting a simulation.

```powershell
.\tools\start_m0.cmd --replay
```

See the [M1 results](M1_RESULTS.md), [frozen protocol](PROTOCOL.md) and [observation API](../../op0/API.md) for the recorded ecology, performance and limits. All three presets are engineering fixtures.
