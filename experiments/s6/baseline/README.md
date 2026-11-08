# Retained pre-S6 baseline

Captured before implementing S6, using the approved S5 Release executable built from `fe4466cb09e913f4c4fe7863a0c5fd84eecf21da` (final report commit `54fc129a02f1e21af93b09a0bce8d7cb0172e62b`). No S6 policy was present. These files supplement, never replace, the original S3-S5 archives.

Commands: `antworld_s3_experiment out/s6-s3-baseline 64` and `antworld_s3_benchmark`. The latter's standard output is `s3_performance.csv`. See the original S3 fixture configuration and the adjacent configuration JSON. Timing includes all work of that benchmark and is not the matched S6 dense-contact comparison.
