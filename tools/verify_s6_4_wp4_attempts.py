"""Preserve the initial quota failures and compare unchanged replay histories."""

import argparse
import json
from pathlib import Path
import shutil
import tarfile

from read_s6_4_rm02_sidecar import require
from run_s6_4_rm02 import sha256
from s6_4_wp4_cases import matrix
from verify_s6_4_wp3 import load


def preserve(source, target):
    (target / "receipts").mkdir(parents=True)
    (target / "failed").mkdir()
    for name in ("freeze.json", "completed.json"):
        shutil.copyfile(source / name, target / name)
    for case in matrix():
        folder = source / "raw" / case.key
        shutil.copyfile(folder / "receipt.json", target / "receipts" / (case.key + ".json"))
        if load(folder / "receipt.json")["exit_code"]:
            shutil.copyfile(folder / "raw.tar.gz", target / "failed" / (case.key + ".tar.gz"))


def verify(first, accepted):
    old, new = [load(path / "completed.json")["exit_codes"] for path in (first, accepted)]
    require(set(old) == set(new) == {c.key for c in matrix()} and not any(new.values()), "incomplete matrix")
    require(load(first / "freeze.json")["cases"] == load(accepted / "freeze.json")["cases"], "case matrix changed")
    failures, unchanged = [], []
    expected_files = set()
    for key, code in old.items():
        older = load(first / "receipts" / (key + ".json"))
        current = load(accepted / "raw" / key / "receipt.json")
        require(older["exit_code"] == code and older["case"] == current["case"] == key, "wrong prior receipt")
        same = ["initial.chk", "midpoint.chk"]
        if code == 0:
            same += ["final.chk", "canonical.bin"]
            unchanged.append(key)
        else:
            name = key + ".tar.gz"
            expected_files.add(name)
            path = first / "failed" / name
            require(sha256(path) == older["archive_sha256"] and path.stat().st_size == older["archive_bytes"],
                    "prior failed archive changed")
            with tarfile.open(path, "r:gz") as archive:
                log = archive.extractfile("program.log").read().decode()
            require(log.strip() == "SQLite error 13: database or disk is full", "new failure type needs review")
            failures.append(dict(case=key, exit_code=code, cause=log.strip(),
                                 sidecar_bytes=older["artifacts"]["observer.sqlite"]["bytes"]))
        for artifact in same:
            require(older["artifacts"][artifact] == current["artifacts"][artifact],
                    f"observer scope changed authoritative bytes: {key} {artifact}")
    require(expected_files == {path.name for path in (first / "failed").iterdir()} and failures,
            "negative archive is incomplete")
    return dict(failures=failures, unchanged_completed=unchanged, status="PASS")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("first_attempt", type=Path)
    parser.add_argument("accepted", type=Path)
    parser.add_argument("--preserve-from", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.preserve_from:
        preserve(args.preserve_from, args.first_attempt)
    result = verify(args.first_attempt, args.accepted)
    file = args.first_attempt / "comparison.json"
    data = (json.dumps(result, indent=2) + "\n").encode()
    if args.check:
        require(file.read_bytes() == data, "first-attempt comparison differs")
    else:
        file.write_bytes(data)
    print(f"Preserved {len(result['failures'])} failed archives and matched {len(result['unchanged_completed'])} full histories.")


if __name__ == "__main__":
    main()
