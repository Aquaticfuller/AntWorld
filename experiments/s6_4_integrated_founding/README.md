# Integrated founding evidence

The [readiness report](../../research/s6_4_integrated_founding/INTEGRATED_FOUNDING_READINESS_REPORT.md) defines the profile, claims and unresolved gates. The [reproduction instructions](../../research/s6_4_integrated_founding/REPRODUCE_INTEGRATED_FOUNDING.md) include the exact collection and analysis commands.

- `raw_index/index.json` identifies all 25 batches, 4,692 actual case receipts and 391 complete local archives by SHA-256. `world_receipts.jsonl` includes every case, timing, exit, input and output hash. The full raw ZIP archives are retained under `out/integrated-founding` on the development host. Their aggregate size is several gigabytes. Git carries the full R2 nominal archives, sixteen selected original canonical witnesses, the archived SQLite midpoints and the complete per-case receipt inventory.
- `analysis/` provides world, census, resource, worker and developmental endpoint tables. `comparison/` contains paired bootstrap estimates and cause-specific cumulative incidence. Observations and conditional endpoints describe simulation data.
- `replay/` contains explicit observed/unobserved/durable equivalence, SQLite anchors, prior-model replay and hashes. `tests/` includes the failed draft and corrected tests.

Verify the public receipts with `python tools/verify_integrated_founding_public.py experiments/s6_4_integrated_founding/raw_index`. For a full individual archive audit on the development host run `python tools/run_integrated_founding_audits.py out/integrated-founding out/integrated-founding/audit-rerun`. All actual input states, facts and side artifacts can be rebuilt independently. Canonical member hashes allow independent matching even when the measured runtime fields or ZIP container metadata differ.
