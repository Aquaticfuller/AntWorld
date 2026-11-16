# Live nursery continuity and local ecology

## Event history

The Windows reference executable from `6949bb6ac2271fb99cf045ba4ae72b6878d7ef9c` ran `NEW_NURSERY 91 17 2` in one-hour advances. It reached hour 52 with 3,991,320 facts. The advance to hour 53 failed at the four-million-event host cap. The runtime kept the preceding valid cut. Peak process working set through hour 52 was 1,062,690,816 bytes.

The live host seals the hot journal into immutable compressed blocks built from the full canonical payload. It uses the existing journal acknowledgement contract. The interactive hot limit is 65,536 records. When an advance hits that limit, the Core rolls back the attempted interval and the host retries at a shorter time boundary. Compression at 16,384 records keeps routine cuts well below the hot limit. A 192 MiB compressed payload budget pauses progression and allows a manual save. On reopening, the immutable SQLite prefix remains readable and only new facts need to be packed in memory. Live advances produce no archive files.

| Simulated cut | Facts | Updated peak working set | Compressed payload |
| --- | ---: | ---: | ---: |
| 52 h | 3,991,320 | 110,448,640 bytes | 64,053,192 bytes |
| 53 h | 4,067,682 | 111,853,568 bytes | 65,277,374 bytes |
| 72 h | 5,527,831 | 137,248,768 bytes | 88,722,637 bytes |
| 96 h | 7,151,647 | 159,895,552 bytes | 114,881,496 bytes |

Working sets are Windows process measurements. The 52-hour old and updated checkpoint frames matched byte for byte with SHA-256 `0ddfa3d4057eb697ee53ed95ab212571b87ba2d670925e91c580c1c063897bc3`. The updated process ran the hour-by-hour cut in 14.04 s versus 10.68 s in the old process. Compression trades some advance time for a much smaller working set. These observations are outside the historical S6 performance protocol.

A deliberate memory-pressure run on the same nursery paused at 140 h 45 min with 12,689,149 committed facts and 201,457,567 compressed bytes. The last cut was readable and passed the Core ledger checks. The save and reopen workflow is required at that limit.

## Opt-in ecology

The native presets `NEW_NURSERY 91 17 5` and `NEW_NURSERY 91 17 6` use physics 35 and checkpoint schema 28. They share the observed nursery's two chambers, stone partition and surface entrance. Initialization registers one queen, ten workers and four larvae. All births after setup require the queen to pay the existing Core reproduction budget. The new fixture enrolls the queen in the existing care policy, enables two-day reproductive opportunities and schedules minute-scale absorption. These values and all initial resources are `ENGINEERING_FIXTURE`.

| Core input in micrograms | Carbohydrate | Protein | Water with supply | Water without external supply |
| --- | ---: | ---: | ---: | ---: |
| Initial feeder | 4,000 | 500 | 4,000 | 0 |
| Daily release limit | 1,000 | 125 | 1,000 | 0 |
| Initial reserve | 7,000 | 875 | 7,000 | 0 |

The two treatments use the same internal starting body and crop stores. The Core registers the release reserve in its resource ledger at setup and transfers each release to the physical feeder. All subsequent intake requires the existing collection, delivery, ingestion or contact transfer rules. Stock readings in the browser come from committed native data. The physiology inspector reports each sample's timestamp separately from the live simulation clock.

Dussutour and Simpson directly manipulated protein and carbohydrate in *Lasius niger*. Methods §2(a–b) used queenless, broodless groups of 200 workers, hydrated bedding and a 24–26 °C room. The paper supports making dietary components and available water explicit. The test here represents an initialized small colony with a single mixed feeder. It establishes no species intake rate, evaporation rule, reproductive rate or temperature response. [Study, pp. 2402–2408](https://pmc.ncbi.nlm.nih.gov/articles/PMC3350685/).

## Verification

- The browser jumped to the positive food delivery by worker #8 at 207,962 ms, then showed its own body reserves and next scheduled absorption. Chrome rendered the native wet and dry presets and switched the same resource panel to Chinese.
- In the seed-17 wet run the first delivery brought 1,883 µg carbohydrate, 235 µg protein and 1,882 µg water into the nest. During the first hour the Core recorded 30 positive nutrition transfers and 34 nest ingestion acts. The paired dry run still delivered and absorbed carbohydrate. Its carrier absorbed no feeder water in the same observation window.
- In both runs the day-2 cut showed one new egg. By day 4, the first new egg had hatched, a second egg was present and the four initialized larvae had pupated. The material, energy, founding and soil checks passed at the 96-hour cuts. This short comparison establishes no survival effect.
- The save test writes one small SQLite snapshot, restores it, advances at different time boundaries and compares the checkpoint and every canonical fact through the resumed cut. A separate Windows run opened a save written by the reference executable and matched its uninterrupted continuation byte for byte. The standard day-90 MicroWorld golden checkpoint still matches.

Run the native checks after setting `M0_LIVE_CORE` to the Release executable and `M0_LIVE_TEST_ROOT` to a scratch path on the working drive.

```powershell
python -B -m unittest discover -s op0/tests -p test_live.py -v
node op0/tests/browser_smoke.mjs <chromium> http://127.0.0.1:8765 out/browser-smoke ecology
```

The environment has fixed climate and no humidity or thermal response. This work leaves the `ENGINEERING_ONLY` claim intact.
