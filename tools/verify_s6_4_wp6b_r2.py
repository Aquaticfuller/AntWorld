"""Check the R2 frozen case roster, archive bytes, independent budgets and timing gates."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import zipfile

import run_s6_4_wp6b_r2 as frozen
from analyze_s6_4_wp6b import check
from run_s6_4_wp6b import sha
from verify_s6_4_wp6b_r1 import verify


REPRESENTATIVES = {
    "h1": ("borisovka-03-primary-1-on", "st_petersburg-00-primary-1-off"),
    "h2": ("borisovka-micro-nominal-0-1",),
    "both": ("borisovka-03-primary-1-on", "st_petersburg-00-primary-1-off"),
    "water-r1": ("borisovka-micro-nominal-0-1-water-blocked",),
    "water-both": ("borisovka-micro-nominal-0-1-water-reachable", "borisovka-micro-nominal-0-1-water-absent"),
}


def ci(root):
    measured = None
    for model, names in REPRESENTATIVES.items():
        folder = root / model
        manifest = json.loads((folder / "run.json").read_text(encoding="utf-8"))
        index = json.loads((folder / "completed.json").read_text(encoding="utf-8"))
        audit = json.loads((root / f"{model}-analysis/archive_verification.json").read_text(encoding="utf-8"))
        check(manifest["model"] == model and not manifest["selected_subset"] and audit["case_receipts"] == index["attempts"],
              f"incomplete formal scope: {model}")
        check(audit["archive_index_sha256"] == sha(folder / "completed.json") and
              audit["run_manifest_sha256"] == sha(folder / "run.json"), f"formal audit identity differs: {model}")
        scope = manifest["cpp_tree"], manifest["binary_sha256"], manifest["runner_sources"]
        measured = measured or scope
        check(scope == measured, "different binaries in the same experiment")
        verify(folder, subset=names, r2=frozen)
    for model in frozen.REFERENCES:
        manifest = json.loads((root / model / "run.json").read_text(encoding="utf-8"))
        check(not manifest["selected_subset"] and manifest["model"] == model and
              (manifest["cpp_tree"], manifest["binary_sha256"], manifest["runner_sources"]) == measured,
              f"legacy replay is not bound to the factorial binary: {model}")
        verify(root / model, r2=frozen)
    recovery = json.loads((root / "recovery-saved.json").read_text(encoding="utf-8"))
    for row in recovery["cases"]:
        if row["treatment"] == "durable":
            file = root / "midpoints" / f"{row['mode']}-{row['case']}.zip"
            check(sha(file) == row["midpoint_archive_sha256"], f"midpoint archive differs: {file.name}")
            with zipfile.ZipFile(file) as bundle:
                check(sorted(bundle.namelist()) == sorted(row["midpoint_files"]), f"midpoint file set differs: {file.name}")
                for name, record in row["midpoint_files"].items():
                    data = bundle.read(name)
                    check(len(data) == record["bytes"] and sha256(data).hexdigest() == record["sha256"],
                          f"midpoint member differs: {file.name}/{name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--case", action="append", default=[])
    parser.add_argument("--ci", action="store_true")
    args = parser.parse_args()
    if args.ci:
        ci(args.archive)
    else:
        verify(args.archive, args.out, args.case, r2=frozen)
