# Worker activity timing experiment

## Evidence from camera detections

Oh and Cremer recorded laboratory black garden ant groups for a week at a time. The experiments used different group sizes, brood conditions and arena shapes. The authors avoided freshly emerged workers. Their intensity measure counts motion points, and their walking measure applies a separate displacement criterion. See Sections 2.6 and 3 of the [article](https://doi.org/10.1111/2041-210X.70277).

The following replay uses three public single-worker CSV members from the `202208_3nests/worker01` series. `tools/sample_altaa_activity.py` reads the members by HTTP range from the [archived dataset](https://doi.org/10.5281/zenodo.16893940). This run transferred 17,238,558 bytes and kept the ZIP data in memory. The fixed window starts 60 hours after the file timestamp and lasts 24 hours. A minute contains detections if a nonempty `motionPts` row falls within it. The durations below are consecutive complete one-minute bins between positive bins. Empty segments at both window boundaries are censored.

| Recording date | Minutes with detections, out of 1,440 | Interior empty bouts | Median empty bout, min | P90, min | Longest, min |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2022-09-04 | 1,091 | 128 | 2 | 6 | 17 |
| 2022-09-18 | 1,150 | 136 | 2 | 4 | 9 |
| 2022-09-25 | 994 | 142 | 2.5 | 6 | 12 |

SHA-256 in the same order, calculated from the uncompressed CSV bytes.

```text
5874e15eed9cd2760a7a6287cc6b3d63922a1722bfe36600b74b15569b91bf34
f53fd73b440b6e90d3c6d3a4d578114ed9c476631fad7d9d38e3b2f012c4389e
161752a93b35532f745a50cb80cd1916d24a047b835e06a56b07d08c74abacf5
```

These are camera-detection gaps within a flat-nest assay, which include the effects of detection thresholds and any unrecorded gaps. The CSVs lack individual task labels and the instants at which an ant reconsidered a task. They motivate looking for activity on a minutes scale. Newly emerged workers in a founding colony and working individual ants need matched evidence for a quantitative fit.

## Paired Core sensitivity run

The legacy fixture has a 60-minute nutrition wake, a six-hour task review and a six-hour minimum program time. The shortened variants change both adult-worker review clocks together and use 30- or 60-minute minimum program times. The queen, juvenile phases, stock forecasting horizon, movement rates, resource inputs and task policies retain their existing settings. The shorter checks can choose only already enabled local actions.

`python -B -m tools.compare_m0_worker_rhythm` ran three deterministic seeds (1, 7 and 19) through day 90 for each timing. The script streams the original fact journal through the native process and checks nutrition, energy, reserves and soil conservation. In the first worker's first 24 hours, an action minute contains committed movement, intake, transfer, delivery, excavation or completed brood handling. The quiet-gap analysis counts minutes without one of those events and includes the window boundaries. This observation differs from camera motion detection.

| Worker timing | First worker's active minutes across seeds | P90 quiet bout, min | Longest quiet bout, min | Day-90 journal fact count |
| --- | --- | --- | --- | --- |
| Standard | 13, 13, 14 | 335, 335, 113 | 418, 418, 719 | 92,225 / 73,560 / 65,582 |
| 5-min checks, 30-min minimum | 112, 137, 127 | 24, 14.5, 23.2 | 339, 339, 339 | 1,433,052 / 1,004,902 / 974,335 |
| 15-min checks, 60-min minimum | 69, 76, 60 | 30, 30, 29.9 | 299, 329, 314 | 580,597 / 407,148 / 397,347 |

In each run the first worker survived at least seven days, and the three colonies ended with 15, 13 and 13 live workers respectively for all three timings. The 15-minute runs recorded 20, 18 and 22 deliveries, 663, 534 and 447 positive worker transfers, and 6,142, 4,418 and 4,456 completed worker brood-handling acts. Standard brood-handling counts were 374, 260 and 254. The change can make brood handling much more frequent, and the longest quiet bouts still span hours. Exact calibration requires matched sequences of field or laboratory work and inactivity.

Expose the 15-minute option for new live colonies as an `ENGINEERING_FIXTURE`. It spreads observed actions across more time bins and keeps a smaller journal than the 5-minute option. The journal still contains 5.5–6.3 times as many facts as the standard run over these three seeds. The standard option remains the default. A new opted-in world persists its timing under checkpoint schema 24 and physics 31. Existing worlds retain their saved settings and history.
