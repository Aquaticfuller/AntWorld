"""Reproduce the narrow screening of acquired Leckie sham geometry tables."""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from math import isfinite
from pathlib import Path
from statistics import median

from read_s6_4_rm02_sidecar import require
from verify_s6_4_wp3 import rows, sequence


INPUTS = {
    "architectural_immunity_nest_analysis.csv": "849291610d8b115a83871a6ab056afd0e6b5eda97bef2a2577168db2d2977d51",
    "COLONY_INFO.csv": "92585adf3572e294b127d31feaf9f98dcade5b78f901bbe3d80f19a02e7e2fa4",
}
ENDPOINTS = ("volume", "surface area", "weighted_diameter", "nest_entrances", "junctions", "edge_num")


def screen(root):
    checks = {}
    for name, expected in INPUTS.items():
        data = (root / name).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        require(digest == expected, f"unrecognized acquisition version: {name}")
        checks[name] = dict(sha256=digest, bytes=len(data))
    geometry = sequence(rows(root / next(iter(INPUTS))), lambda r: r["name"])
    metadata = sequence(rows(root / "COLONY_INFO.csv"), lambda r: r["name"])
    require(geometry.keys() <= metadata.keys(), "unmatched scan identity")
    samples = defaultdict(list)
    histories = defaultdict(set)
    source_colonies = set()
    flagged = []
    for name, record in geometry.items():
        other = metadata[name]
        keys = ("colony", "week", "day", "time", "voxel", "subset", "treatment")
        require(all(record[k] == other[k] for k in keys), "geometry disagrees with scan metadata")
        if record["treatment"] != "SHAM":
            continue
        nest, marker, day = name.rpartition("_")
        require(marker and day == record["day"], "unknown longitudinal nest identifier")
        when = int(record["time"])
        require(when not in histories[nest], "duplicate nest-time observation")
        histories[nest].add(when)
        samples[when].append(record)
        source_colonies.add(record["colony"])
        if record["week"] == "1" and when == 72:
            flagged.append(name)
    require(len(flagged) == 1, "published failed-scan exclusion could not be located")
    summary = []
    for when, group in sorted(samples.items()):
        item = dict(time_in_source=when, nests=len(group), measurements={})
        for key in ENDPOINTS:
            values = [float(r[key]) for r in group if r[key]]
            require(all(isfinite(v) for v in values), "nonfinite reported measurement")
            item["measurements"][key] = dict(n=len(values), median=median(values) if values else None,
                                             minimum=min(values, default=None), maximum=max(values, default=None))
        summary.append(item)
    return dict(dataset_doi="10.5281/zenodo.15353580", article_doi="10.1126/science.ads5930",
                inputs=checks, eligibility="DEVELOPMENT_CONTEXT_PROCESSED_SHAM_ONLY", raw_voxels="NOT_ACQUIRED",
                measurements="Unconverted values in the source columns. Repeated measurements within nest.",
                sham_nests=len(histories), sham_rows=sum(map(len, samples.values())),
                source_colonies=len(source_colonies), published_analysis_exclusion=flagged[0],
                sham_rows_after_published_exclusion=sum(map(len, samples.values())) - len(flagged),
                screening_includes_flagged_archive_row=True,
                sampling_patterns=dict(sorted(Counter(";".join(map(str, sorted(v))) for v in histories.values()).items())),
                by_time=summary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("local_files", type=Path)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = screen(args.local_files)
    content = (json.dumps(result, indent=2) + "\n").encode()
    if args.check:
        require(args.receipt.read_bytes() == content, "screening receipt differs")
    else:
        args.receipt.write_bytes(content)
    print(f"{result['sham_rows']} processed scans from {result['sham_nests']} sham nests")


if __name__ == "__main__":
    main()
