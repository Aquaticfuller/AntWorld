"""Summarize measured application costs and cross-check each run against canonical archives."""

import argparse
from collections import defaultdict
import csv
import json
from pathlib import Path
import zipfile

from analyze_s6_3_3_1_performance import read
from profile_s6_4_wp6b import percentile
from run_s6_4_wp6b import sha, write_json


FILES = {"initial_sha256": "initial.chk", "frame_sha256": "final.frame", "facts_sha256": "facts.bin",
         "parameters_sha256": "parameters.txt"}


def receipts(root, wanted):
    index = json.loads((root/"completed.json").read_text(encoding="utf-8"))
    found = {}
    for filename, digest in index["archives"].items():
        with zipfile.ZipFile(root/filename) as archive:
            names = set(archive.namelist())
            matches = [name for name in wanted if f"{name}/receipt.json" in names]
            if matches:
                if sha(root/filename) != digest:
                    raise ValueError(f"application reference archive mismatch: {filename}")
                for name in matches:
                    found[name] = json.loads(archive.read(f"{name}/receipt.json"))
    if found.keys() != wanted:
        raise ValueError("application reference case coverage differs")
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("raw", "v1", "r1", "out"):
        parser.add_argument("--"+name, type=Path, required=True)
    parser.add_argument("--both", type=Path)
    args = parser.parse_args()
    samples = [row for session in sorted(args.raw.glob("session*")) for row in read(session/"samples.csv")
               if (session/"samples.csv").exists()]
    roots = {"v1": args.v1, "r1": args.r1}
    if args.both:
        roots["both"] = args.both
    sources = {model: receipts(root, {r["case"] for r in samples if r["model"] == model}) for model, root in roots.items()}
    groups = defaultdict(list)
    for row in samples:
        reference = sources[row["model"]][row["case"]]
        if any(row[metric] != reference["artifacts"][member]["sha256"] for metric, member in FILES.items()):
            raise ValueError(f"observer or restart changed canonical bytes: {row['case']}/{row['model']}")
        groups[row["case"],row["model"],row["treatment"]].append(row)
    output = []
    for (case, model, treatment), values in sorted(groups.items()):
        row = dict(case=case, model=model, treatment=treatment, samples=len(values), events=values[0]["events"],
                   facts_bytes=values[0]["facts_bytes"], frame_bytes=values[0]["frame_bytes"],
                   peak_queue=values[0]["peak_sampled_queue"], midpoint_sqlite_bytes=values[0]["midpoint_sqlite_bytes"])
        metrics = ("setup_ms", "advance_ms", "cut_ms", "checkpoint_ms", "midpoint_save_ms", "midpoint_restore_ms",
                   "total_ms", "process_ms", "common_sync_ms", "optional_sync_ms", "post_cut_ms", "peak_rss_bytes")
        for key in metrics:
            series = [float(v[key]) for v in values]
            for suffix, quantile in (("p50",.5), ("p95",.95), ("p99",.99)):
                row[f"{key}_{suffix}"] = percentile(series, quantile)
        residual = [float(v["process_ms"])-float(v["total_ms"]) for v in values]
        row.update(outer_residual_ms_p50=percentile(residual,.5), outer_residual_ms_max=max(residual))
        output.append(row)
    args.out.mkdir(parents=True)
    if output:
        with (args.out/"phase_costs.csv").open("x", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, list(output[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(output)
    write_json(args.out/"reference_equivalence.json", dict(samples=len(samples), case_models=len({(r["case"],r["model"]) for r in samples}),
               fields=list(FILES), canonical_match=True if samples else None,
               **{f"{model}_index_sha256": sha(root/"completed.json") for model, root in roots.items()}))


if __name__ == "__main__":
    main()
