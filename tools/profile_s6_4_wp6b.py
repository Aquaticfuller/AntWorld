"""Measure the same F1 cases with and without read-only census export and a durable restart."""

import argparse
import csv
import json
from pathlib import Path
import platform
from statistics import median
from tempfile import TemporaryDirectory

from run_s6_4_wp6b import frozen_cases, git, run_one, sha, write_json


def percentile(values, fraction):
    values = sorted(values)
    position = fraction * (len(values) - 1)
    left = int(position)
    right = min(left + 1, len(values) - 1)
    return values[left] + (values[right] - values[left]) * (position-left)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--scratch", type=Path, required=True)
    args = parser.parse_args()
    binary = args.binary.resolve(strict=True)
    args.out.mkdir(parents=True)
    args.scratch.mkdir(parents=True, exist_ok=True)
    workload = [(identity, case) for identity, case in frozen_cases() if case["software_seed"] == 1 and
                ((case["group"] == "micro" and case.get("arm") == "nominal") or
                 (case["group"] == "early" and case.get("arm") in ("empty", "depot")))]
    assert len(workload) == 10
    samples, captures, results = [], [], []
    freeze = dict(source=git("rev-parse", "HEAD"), binary_sha256=sha(binary), workload=[c["case"] for _, c in workload],
                  sequence=["observed", "unobserved", "unobserved", "observed", "unobserved", "observed", "observed", "unobserved"],
                  qualification="DESCRIPTIVE_ONLY", host=platform.platform(), interval="90 fixed daily advances")
    write_json(args.out / "freeze.json", freeze)
    for identity, case in workload:
        name = case["case"]
        reference = None
        for i, mode in enumerate([*freeze["sequence"], "durable"]):
            with TemporaryDirectory(dir=args.scratch) as tmp:
                folder = Path(tmp) / "data"
                receipt = run_one(binary, folder, identity, case, mode)
                if receipt["status"] != "COMPLETE":
                    raise ValueError(f"profiling run failed: {name}/{mode}: {(folder/'program.log').read_text()}")
                signatures = [receipt["artifacts"][key]["sha256"] for key in ("initial.chk", "final.frame", "facts.bin")]
                reference = reference or signatures
                if signatures != reference:
                    raise ValueError(f"observer or recovery changed canonical authority: {name}/{mode}")
                samples.append(dict(case=name, trial=i, mode=mode, process_ms=receipt["elapsed_ms"], **receipt["summary"],
                                    initial_sha256=signatures[0], frame_sha256=signatures[1], facts_sha256=signatures[2]))
                with (folder/"timings.csv").open(newline="", encoding="utf-8") as stream:
                    captures.extend(dict(case=name, trial=i, mode=mode, **r) for r in csv.DictReader(stream))
        on = [float(r["process_ms"]) for r in samples if r["case"]==name and r["mode"]=="observed"]
        off = [float(r["process_ms"]) for r in samples if r["case"]==name and r["mode"]=="unobserved"]
        foreground = [float(r["cut_ms"]) for r in captures if r["case"]==name and r["mode"]=="observed"]
        results.append(dict(case=name, same_bytes=True, total_p50_ratio=median(on)/median(off),
                            total_p95_ratio=percentile(on,.95)/percentile(off,.95),
                            foreground_p95_ms=percentile(foreground,.95), foreground_max_ms=max(foreground)))
        print(name, "identical canonical facts and state", flush=True)
    for name, values in (("samples.csv", samples), ("cuts.csv", captures), ("summary.csv", results)):
        with (args.out/name).open("x", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, list(values[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(values)
    write_json(args.out / "completion.json", dict(cases=len(workload), runs=len(samples), all_exact=True,
               schema="experimental F1 frame and AWFACT02"))


if __name__ == "__main__":
    main()
