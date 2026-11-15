# Watch R0-r1 in MicroWorld

Use Windows PowerShell with Git and Python 3.11 or newer. A fresh copy of this branch can open the published archives without a C++ build. The existing `start_m0.cmd` launcher runs from PowerShell under its normal execution policy.

```powershell
git clone --branch codex/r0-r1-motility-morphogenesis --single-branch --depth 1 https://github.com/Aquaticfuller/AntWorld.git
Set-Location AntWorld
.\tools\start_m0.cmd --r0-r1 --replay
```

From an existing checkout, switch to the same branch and run the last command. The service uses localhost and puts derived indexes in `out/m0-op0-cache` under the checkout. World opening validates the source. The first index can take some time, particularly for 300 workers. Press Ctrl+C in the terminal to stop the service. The ZIPs remain read-only. A discarded index can be rebuilt from its ZIP.

## Watch naturally founded workers

The first archive starts with one foundress and no adult workers. Select **Watch movement in an established nest** to follow the first recorded relocation after the colony has at least ten workers. A timed turn and translation accompany the recorded segment. The visual line between known endpoints is an animation of that validated segment. The position before or after that segment comes from the actual Core history. Select the worker and open its **Activity window** to see the duration and distance from the journal. **First delivery**, **Trophallaxis**, and **Brood fed** show separate actual actions. Select **Compare worlds** to see the paired R0 history at the same time. The dogleg pair and the separately tested shorter review pair are also available.

## Watch measured excavation

Choose **R0-r1 · 50 workers · dig score** or **R0-r1 · 300 workers · dig score** from the archive list. The underground floor section opens at the depot height. Start at time zero, then choose **First excavation** or **Soil placed**. Drag the clock to later hours. **Compare worlds** opens the matched random-boundary control. Use its aligned time slider to inspect reachability, room cores, and the actual area and perimeter. Clear **Show ant markers** to see the edited terrain under a crowded group. The starting fixture includes one small cavity and a shaft. All later changes come from paid excavation and carried soil. Groups here were explicitly initialized with adults for the construction assay. The counts and report show whether each run formed additional room cores.

## Run the experiment live

The [live nursery comparison](traffic/README.md) opens a small, matched physics 33 and physics 34 experiment with visible workers, brood and body clearance. Its science and performance scope is separate from the naturally founded and excavation runs below.

On a checkout with CMake and a configured C++ toolchain, build the native launcher as described in the [MicroWorld guide](../m0/README.md). Run `python -m tools.build_m0_live`, then `.\tools\start_m0.cmd`. Enable **Worker motor and dig scoring (R0-r1)** before creating a world to opt in to physics 33. This combines both features in a live experiment. The published motion and excavation trials enable one at a time for attribution. The ordinary setup remains available without enabling this option.

## Reproduce and verify

```powershell
python -B -m tools.run_r0_r1 out/r0-r1-motion --kind motion
python -B -m tools.run_r0_r1 out/r0-r1-cadence --kind cadence
python -B -m tools.run_r0_r1 out/r0-r1-long --kind long
python -B -m tools.run_r0_r1 out/r0-r1-dig --kind dig
python -B -m tools.run_r0_r1 out/r0-r1-dig90 --kind dig90
python -B -m tools.run_r0_r1 out/r0-r1-recovery --kind motion --case motion-shaft-motor --case motion-dogleg-motor --durable
python -B -m tools.verify_r0_r1 experiments/r0_r1/witnesses --replay out/r0-r1-recovery --scratch out
python -B -m tools.trace_r0_r1_queen out/r0-r1-long/motion-shaft-continued-730-p33.json.gz out/m0-live-bin/antworld_m0_live_v6.exe out/r0-r1-death.json.gz
```

Use a new path for each run. Use `--core` to specify another build. `--case` can select individual frozen cases and `--skip-archive` retains compact diagnostics without a full ZIP. Peak usage grows with worker count and event history. The [experiment protocol](PROTOCOL.md) records the conditions. The [results](RESULTS.md) identify the observed gains, failures and limits of use.
