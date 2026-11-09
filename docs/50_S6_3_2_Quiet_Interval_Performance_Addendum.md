# S6.3.2 user-arranged quiet-interval completion

## Authority and preserved evidence

After delivery commit `1671737`, the user answered the pending quiet-interval request on 2026-11-09: a quiet interval is now available. This authorizes a measurement-only continuation for the previously untimed birth session 1. It does not authorize biological changes, a different sensor admission rule, a different <=6 target, or later development stages.

Freeze this addendum before new diagnostics or admission. Preserve the original three failed session-1 admissions, all completed sessions, all reports and negative results in Git and their original data directories. Never repeat already timed sessions 2/3. Store the extension separately under `performance_quiet_1/births/session1`; the original series remains an incomplete historical series.

## Unchanged measurement contract

Use exactly protocol 48, the unchanged `run_s6_3_2_performance.py` runner and the original birth executable SHA-256 `c3cdbb06bfdf998568843917c5e2fbc42db2235a3911db001de3d86ba1d5894a`. Reuse the original session-1 56-row ABBA/BAAB schedule byte-for-byte. No contact retest and no new behavioral experiment. The new directory is an explicitly authorized admission series, not removal/resetting of old receipts.

Before admission, record one 60-second diagnostic with the existing Processor Information counter's raw values, type, status and time base; a separately queried legacy Processor counter; and the existing HWiNFO P0 thread usage/temperature/power fields. The alternative collector is a cross-check, not an independently calibrated hardware truth or substitute for invalid primary data. Stop this diagnostic before the unchanged admission/timing runner. A diagnostic interval is not a qualification and is never a timing result.

The new series has at most three admission attempts, at least five minutes apart. Retain every attempt. All 60 primary one-second samples must be valid; system/core p50 <=10%, p95 <=20%, AC on/saver off and fresh HWiNFO remain mandatory. No reclassification of invalid PDH values, no alternate-counter substitution and no favorable-run rerun. If admission exhausts again, stop and report incomplete without further renewals. Once started, retain every timing row regardless of speed or in-run load. No compilation, extraction, analysis or other agent workload overlaps timing.

## Predeclared analysis and stop

Report the new session separately, including raw diagnostic/admission/telemetry, all phase percentiles, paired growth and work/hash equality. If it completes correctly, also report a clearly labeled completion-extension analysis combining this exact session 1 with the unchanged original sessions 2/3, for 168 planned rows total. This is declared before timing; no other session can substitute. Bootstrap uses the same intact session/block method, 4096 draws and seed 63201; the original <=6 pooled advance-p50 growth criterion remains. The earlier two-session statistics and their incomplete verdict are preserved, not retroactively rewritten as an originally complete run. If the completed extension fails, report FAIL and retain all rows.

Use the same CPU affinity, binaries, workload/event counts, state/trace hashes and restore/conservation checks. Report differences in observation date/load and counter reliability. A passing extension cannot explain earlier 24.229x/6.315x/8.154x failures. Update the S6.3.2 reports, debt and reproduction commands with the outcome; commit/push this same branch, verify CI, then stop again for independent review. No Core or biological parameter changes.

## Counter interface references

- [PdhGetRawCounterValue](https://learn.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhgetrawcountervalue): returns provider values; inspect status separately.
- [PDH_RAW_COUNTER](https://learn.microsoft.com/en-us/windows/win32/api/pdh/ns-pdh-pdh_raw_counter): raw first/second values, timestamp and status without interpretation.
- [PdhGetCounterTimeBase](https://learn.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhgetcountertimebase): query the counter's rate time base.

These API contracts do not establish the cause of the historical invalid-denominator status.
