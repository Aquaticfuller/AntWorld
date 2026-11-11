# WP-2 host observation design

The WP-2 scope uses the RM-02 append, codec, paging and durable checkpoint anchor. Its manifest discriminator binds the expanded selection rule to its history. A mismatch on rejoin is rejected, including attempts to open a WP-2 store with the RM-02 plan. The existing RM-02 plan has its original identity and record selection. WP-2 only reads published Core facts and focal state, then commits detached cuts to the host database. Timed and untimed facts keep their original canonical bytes.

## Preflight storage adjustment

A Release engineering preflight for the B01 no-brood case with one-hour observation cuts failed with SQLite error 13 at the 64 MiB sidecar limit. One-hour payloads were often above the existing 400 KiB sparse codec cutoff. The failure occurred after the 121 h cut was queued with 367,936 examined facts. Its original database was 67,067,904 B. That failed observation is separate from the formal matrix.

WP-2 B01 uses 30-minute host cuts so that payloads can use the existing codec. This is the first specified B01 host cut frequency. The study's simulated intervention, 10 s scoring windows, duration, seeds and selection stay as frozen. No quota, pace of modeled behavior, codec, fact kind, or timing threshold changes. The observer-off run uses the same advance partition and intervention schedule. The archived checkpoints and captured facts remain available for independent comparison.

## Time and identity

The analyzer pairs typed starts and terminals by actor, act, target and bout. Incomplete selections and starts are retained. A later reconstruction can check externally commanded displacements by source and exact timestamps. Endpoint movement and known act intervals use separate denominators. The observer produces no extra authoritative fact.

The midpoint flow flushes, anchors and closes the sidecar before restoring the canonical checkpoint. An immediate repeat of the anchored cut must be a duplicate. The same case then continues to its terminal checkpoint and compares bytes with the off-arm replay from the initial checkpoint. Each cut stores the mass and energy ledger. A separate receipt verifies soil volumes at the same cut. The off/on comparison includes queue, RNG, authoritative history, geometry and other state encoded in the checkpoint.
