"""Audit and summarize equal-authority storage diagnostics without a release verdict."""

import argparse
import json
from pathlib import Path
from statistics import median, quantiles

from analyze_s6_4_wp6b import check, rows
from measure_founding_cohort_history import AUTHORITY, FIXED, ORIGINAL
from run_s6_4_wp6b import sha, write_json
from verify_ecological_publication import manifest


SCHEDULES = {"bounded": ("history-resident", "history-bounded"),
             "bounded-cache": ("history-resident", "history-bounded"), "midpoint": ("reference", "cache")}
MEASURES = ("advance_ms", "checkpoint_ms", "vfs_sync_ms", "midpoint_encode_ms", "midpoint_save_ms",
            "midpoint_restore_ms", "decode_block_ms", "vfs_read_ms", "vfs_write_ms", "commit_ms",
            "restore_frame_ms", "check_indexes_ms", "fact_export_ms", "thread_cpu_ms")


def describe(sample):
    percentiles = quantiles(sample, n=100, method="inclusive")
    return dict(n=len(sample), p50=median(sample), p95=percentiles[94], p99=percentiles[98], max=max(sample))


def summarize(evidence):
    reference = {r["case"]: r["receipt"] for r in manifest(ORIGINAL)}
    output = {}
    for label, modes in SCHEDULES.items():
        location = evidence / label
        records = rows((location / "samples.csv").read_bytes())
        expected = [(case, str(pair), mode) for case in FIXED for pair in range(1, 4)
                    for mode in (modes if pair != 2 else modes[::-1])]
        check([(r["case"], r["pair"], r["mode"]) for r in records] == expected, "missing or reordered timing sample")
        study = {}
        for r in records:
            case, mode, pair = (r[k] for k in ("case", "mode", "pair"))
            path = location / f"{case}-{pair}-{mode}"
            sample = json.loads((path / "sample.json").read_bytes())
            check(all(r[k] == str(v) for k, v in sample.items()), "raw timing row differs")
            receipt = json.loads((path / "receipt.json").read_bytes())
            check(sample["status"] == receipt["status"] == "COMPLETE", "retain incomplete attempts separately")
            check(all(receipt["artifacts"][k] == reference[case]["artifacts"][k] for k in AUTHORITY),
                  "timing arm changed committed or observed bytes")
            for file in path.iterdir():
                if file.name in receipt["artifacts"]:
                    check(sha(file) == receipt["artifacts"][file.name]["sha256"], "timing phase file changed")
            cuts = rows((path / "capture_phases.csv").read_bytes())
            check(len(cuts) == 151, "foreground cuts omitted")
            observed = {phase: describe([float(c[phase]) for c in cuts]) for phase in
                        ("foreground_wall_ms", "thread_cpu_ms", "state_ms", "csv_ms", "write_ms", "space_ms")}
            hard = [c for c in cuts if float(c["foreground_wall_ms"]) > 20]
            phase, = rows((path / "phases.csv").read_bytes())
            data = {k: float(r[k]) for k in ("wall_ms", "peak_rss_bytes", "decode_block_calls")}
            data.update({k: float(r.get(k) or phase[k]) for k in MEASURES if k in r or k in phase})
            data["process_ms"] = float(receipt["elapsed_ms"])
            if label != "midpoint":
                costs = rows((path / "history_cost.csv").read_bytes())
                data["save_ms"] = sum(float(x["durable_save_ms"]) for x in costs)
                data["validated_restore_ms"] = sum(float(x["validated_restore_ms"]) for x in costs)
                data.update({k: float(r[k]) for k in ("max_hot_bytes", "final_hot_bytes", "sqlite_bytes", "publications")})
            else:
                data["database_bytes"] = float(r["database_bytes"])
            study.setdefault(case, {}).setdefault(mode, []).append(dict(pair=int(pair), **data, cuts=observed, hard=hard))
        for groups in study.values():
            reference_run, candidate_run = groups[modes[0]], groups[modes[1]]
            groups["paired_candidate_over_reference"] = {
                key: [b[key] / a[key] for a, b in zip(reference_run, candidate_run, strict=True)]
                for key in ("peak_rss_bytes", "wall_ms", "process_ms", "advance_ms")}
            groups["descriptive_samples"] = {mode: {
                key: describe([r[key] for r in groups[mode]]) for key in groups[mode][0] if key not in {"pair", "cuts", "hard"}}
                for mode in modes}
        output[label] = study
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = summarize(args.evidence)
    if args.check:
        check(json.loads(args.output.read_bytes()) == result, "derived storage diagnostics differ")
    else:
        write_json(args.output, result)
