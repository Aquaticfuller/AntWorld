"""Compare native observation output on fixed archived workloads."""

import argparse
import csv
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

from run_s6_4_wp6b import frozen_cases, git, run_one, sha, write_json


WORKLOADS = (
    ("borisovka-early-empty-8-1", ()),
    ("st_petersburg-early-depot-8-1", ("172800000", "750000")),
    ("st_petersburg-early-empty-32-1", ()),
)
AUTHORITY = ("initial.chk", "final.frame", "facts.bin", "cuts.csv", "individuals.csv")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    exe = args.binary.resolve(strict=True)
    output = args.output.resolve()
    output.mkdir(parents=True)
    originals = {c["case"]:(i,c) for i,c in frozen_cases()}
    rows = []
    for name, options in WORKLOADS:
        identity, case = originals[name]
        for pair in range(3):
            order = ("observed","buffered") if pair!=1 else ("buffered","observed")
            verified = {}
            for slot, mode in enumerate(order):
                label = f"{name}-{pair+1}-{mode}"
                retained = output/label
                retained.mkdir()
                with TemporaryDirectory(dir=output) as temp:
                    work = Path(temp)/"world"
                    receipt = run_one(exe,work,identity,case,"profile-"+mode,options)
                    for member in ("case.json","parameters.txt","program.log","timings.csv","phases.csv","profile.csv",
                                   "receipt.json","summary.csv"):
                        if (work/member).exists():
                            shutil.copyfile(work/member,retained/member)
                    if receipt["status"]!="COMPLETE":
                        raise RuntimeError(f"incomplete diagnostic {label}")
                    verified[mode] = [receipt["artifacts"][k] for k in AUTHORITY]
                    with (work/"phases.csv").open(newline="",encoding="utf-8") as phases:
                        timing = next(csv.DictReader(phases))
                    with (work/"profile.csv").open(newline="",encoding="utf-8") as profile:
                        timing.update(next(csv.DictReader(profile)))
                    with (work/"timings.csv").open(newline="",encoding="utf-8") as samples:
                        maximum = max(float(row["cut_ms"]) for row in csv.DictReader(samples))
                    rows.append(dict(case=name,pair=pair+1,slot=slot,mode=mode,wall_ms=receipt["elapsed_ms"],
                        max_cut_ms=maximum, **timing))
            if verified["observed"]!=verified["buffered"]:
                raise ValueError("output changed committed authority or observer bytes")
    with (output/"measurements.csv").open("x",newline="",encoding="utf-8") as csv_file:
        writer=csv.DictWriter(csv_file,rows[0],lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    write_json(output/"run.json",dict(source=git("rev-parse","HEAD"), binary_sha256=sha(exe),
        scope="uncontrolled diagnostic; no formal admission", complete_pairs=len(rows)//2, equal_byte_outputs=AUTHORITY))


if __name__ == "__main__":
    main()
