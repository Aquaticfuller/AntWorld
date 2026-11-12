"""Run process-isolated, unadmitted observer timing with a timed-care pressure case."""

import argparse
import csv
import json
from pathlib import Path
import platform
import subprocess
from tempfile import TemporaryDirectory

from analyze_s6_3_2_performance import describe
from analyze_s6_3_3_1_performance import read
from analyze_s6_4_rm02_performance import IDENTITY
from read_s6_4_rm02_sidecar import require
from run_s6_4_wp2 import PROTOCOL, git, sha256, write


CELLS = ("dense512", "dense2048", "depot32", "care8")


def csv_file(path, rows):
    with path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def report(samples, captures):
    result = {}
    for cell in CELLS:
        rows = [r for r in samples if r["cell"] == cell]
        require(len(rows) == 20 and all(r["exact_restore"] == r["conserved"] == "1" for r in rows)
                and len({tuple(r[key] for key in IDENTITY) for r in rows}) == 1, "timing identity differs")
        measured = [r for r in rows if int(r["block"]) >= 0]
        cuts = [r for r in captures if r["cell"] == cell]
        expected = 91 if cell == "depot32" else 7 if cell == "care8" else 1
        for row in rows:
            matched = [c for c in cuts if int(c["sample"]) == int(row["sample"])]
            require(len(matched) == (expected if row["arm"] == "on" else 0), "missing capture row")
            if matched:
                require(matched[-1]["cursor"] == row["events"] and
                        sum(int(c["examined"]) for c in matched) == int(row["events"]) and
                        all(not int(c["dropped"]) for c in matched), "incomplete diagnostic capture")
        stats = {arm: {key: describe([float(r[key]) for r in measured if r["arm"] == arm])
                      for key in ("total_ms", "advance_ms", "flush_ms", "background_write_ms",
                                  "sqlite_bytes", "wal_bytes_at_cut", "peak_queue_bytes", "peak_rss_bytes")}
                 for arm in ("off", "on")}
        result[cell] = dict(events=int(rows[0]["events"]), statistics=stats,
                            foreground_ms=describe([float(c["capture_ms"]) + float(c["publish_ms"])
                                                     for c in cuts if int(c["block"]) >= 0]),
                            total_ratios={q: stats["on"]["total_ms"][q] / stats["off"]["total_ms"][q]
                                          for q in ("p50", "p95", "p99")})
    return dict(status="DESCRIPTIVE_UNADMITTED", timing_rows=len(samples), cells=result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument("--binary", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    output = args.out / "analysis.json"
    if args.check:
        check = report(read(args.out / "samples.csv"), read(args.out / "captures.csv"))
        require(output.read_bytes() == (json.dumps(check, indent=2) + "\n").encode(), "diagnostic analysis differs")
        print(check["status"], check["timing_rows"])
        return
    if not args.binary:
        parser.error("--binary is required to collect timing")
    args.out.mkdir(parents=True)
    write(args.out / "freeze.json", dict(source_commit=git("rev-parse", "HEAD"),
          executable=args.binary.name, binary_sha256=sha256(args.binary), protocol_sha256=sha256(PROTOCOL),
          host=platform.platform(), cells=CELLS, warmup_blocks=1, retained_blocks=4))
    samples, captures = [], []
    with (args.out / "program.log").open("xb") as log, TemporaryDirectory() as temporary:
        for cell in CELLS:
            for block in range(-1, 4):
                arms = ("on", "off", "off", "on") if block % 2 else ("off", "on", "on", "off")
                for slot, arm in enumerate(arms):
                    row = dict(cell=cell, block=block, slot=slot, arm=arm, sample=len(samples))
                    scratch = Path(temporary) / str(row["sample"])
                    code = subprocess.run([args.binary.resolve(), scratch, cell, arm, "0"],
                                          stdout=log, stderr=subprocess.STDOUT, check=False).returncode
                    if code:
                        write(args.out / "incomplete.json", row | dict(exit_code=code))
                        if samples:
                            csv_file(args.out / "samples.csv", samples)
                        if captures:
                            csv_file(args.out / "captures.csv", captures)
                        raise ValueError("incomplete diagnostic timing")
                    sample, = read(scratch / "sample.csv")
                    samples.append(row | sample)
                    captures.extend(row | cut for cut in read(scratch / "captures.csv"))
    csv_file(args.out / "samples.csv", samples)
    csv_file(args.out / "captures.csv", captures)
    write(output, report(samples, captures))
    print("DESCRIPTIVE_UNADMITTED", len(samples))


if __name__ == "__main__":
    main()
