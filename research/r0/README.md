# Observe R0 on Windows

From this branch in the AntWorld folder, run:

```powershell
.\tools\start_m0.cmd --r0 --replay
```

Open [the local viewer](http://127.0.0.1:8765/) if a browser did not open. Leave the terminal running. A running M0 service can use another port with `--port 8767`.

1. **R0 · local nest activity** opens a shaft colony started with one queen. Click **Watch movement in an established nest**. The replay selects a worker born in this world and follows one actual movement at the time when ten workers are alive. The line joins the confirmed start and finish. The moving arrow is a slowed visual interpolation, with a bearing derived from those endpoints. The event panel shows the committed end time and the related events.
2. **Watch first food delivery** follows actual exterior collection and return through the shaft. **Watch brood feeding**, **Trophallaxis**, **First excavation** and **Soil placed** open original actions. **Movement only** steps through committed displacements. **Individual time budget and physiology** displays distance, witnessed travel intervals, other paid work, and the separate task clock.
3. Select **Compare worlds**. It preselects the matching standard MicroWorld run for the same shaft. Both sections use the same horizontal layer and scale. The shared time cursor updates material, committed positions, fertility, supplies and actual work. Switch both worlds to the dogleg pair for the bent chamber connector. A number at a point reports recorded coincident individuals.
4. Use the language menu for English or Simplified Chinese. The archive catalogue also includes the inherited blocked and protein-limited examples.

For a fresh live colony, run `.\tools\start_m0.cmd` and select **Local nest activity (R0)** before creating it. Build the updated native executable when needed:

```powershell
python -B tools/build_m0_live.py
```

Physics 32 identifies this opt-in experiment. The standard profile is selected by default. Live mode shows committed positions and recent events; continuous slow motion for an inspected rest segment is provided in the verified archives. The live new-colony fixture uses a 120-day finite reserve. For the four longer supply treatments and instructions for recreating the results see [R0 results](RESULTS.md).
