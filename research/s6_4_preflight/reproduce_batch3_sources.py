#!/usr/bin/env python3
"""Recompute the Batch 3 flood and dormancy summaries from archived inputs."""

import argparse
import csv
import io
import json
import platform
from collections import Counter, defaultdict
from contextlib import closing
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
from statistics import fmean, stdev
from zipfile import BadZipFile, ZipFile

from verify_batch1 import ROOT, index, require


INPUTS = {
    "flood-2006.tsv": ("10.1594/PANGAEA.865170", "67004a4344044c3bc9ac2f5dc46a4ebc9bddf48e52c695df06b5abb18c296daf"),
    "flood-2013.tsv": ("10.1594/PANGAEA.865171", "3ae2b87ae8bdcbf8a59b36bd961f98caf6e736fd88c9f31aeaf410e751502f70"),
    "flood-duration.tsv": ("10.1594/PANGAEA.865132", "a640af9bc30519c5d93ae3946311ee74d1c82644456e21572cf94e5a807b92f7"),
    "doi_10_5061_dryad_931zcrk1q__v20260429.zip": (
        "10.5061/dryad.931zcrk1q", "0bdbc345a5347cd62c11fd6906c0360f95e97cb3112f9ff8cc5f05ffcf7975dc",
    ),
}
COLD_ARCHIVE = "doi_10_5061_dryad_931zcrk1q__v20260429.zip"
WORKBOOKS = {
    "CTmin": ("data_ctmin.xlsx", "4f59a5b29fd71d62f7b1482e91aed62d29ad4d2dc6c467f31c909f2c07cb4c03", 289),
    "Lte50": ("data_lte50.xlsx", "e5fd43bc7b2ad354c64172116e88d6da205b6df90d462ba26ea3f5b1e76e1565", 20),
    "SMR": ("data_smr.xlsx", "08c9e92603514816575ec9a8c92058f29f39565cf8a9d393c64f8d9a62b67b2e", 57),
}


def read_input(path, name, provenance):
    doi, expected = INPUTS[name]
    content = path.read_bytes()
    digest = sha256(content).hexdigest()
    require(digest == expected, f"{name}: SHA-256 mismatch ({digest})")
    provenance[name] = {"doi": doi, "path": str(path), "sha256": digest}
    return content


def plot_rows(content):
    lines = content.decode("utf-8-sig").splitlines()
    return index(csv.DictReader(lines[lines.index("*/") + 1:], delimiter="\t"), "Experimental plot")


def flood_summary(data):
    before, after, duration = (plot_rows(data[name]) for name in ("flood-2006.tsv", "flood-2013.tsv", "flood-duration.tsv"))
    require(before.keys() == after.keys() == duration.keys() and len(before) == 80, "Unexpected plot IDs or count")
    survey = {}
    for year, records in ((2006, before), (2013, after)):
        counts = [int(row["Ant abund [#]"]) for row in records.values()]
        occurrences = [int(row["Ant occ"]) for row in records.values()]
        require(all(occ == int(count > 0) for occ, count in zip(occurrences, counts, strict=True)), "Inconsistent occurrence flag")
        survey[year] = {"plots": len(records), "present": sum(occurrences), "fraction_present": fmean(occurrences),
                        "bait_worker_count": {"min": min(counts), "max": max(counts), "sum": sum(counts), "mean": fmean(counts)}}
    pairs = Counter(before[plot]["Ant occ"] + after[plot]["Ant occ"] for plot in before)
    days = [int(row["Flood [days]"]) for row in duration.values()]
    require(pairs == {"00": 4, "01": 8, "10": 8, "11": 60}, "Published occurrence summaries drifted")
    require([survey[year]["bait_worker_count"]["sum"] for year in (2006, 2013)] == [823, 3094] and
            (min(days), max(days), fmean(days)) == (4, 24, 14.2625), "Flood or bait counts drifted")
    return {"survey_by_year": survey, "paired_occurrence_2006_2013": dict(sorted(pairs.items())),
            "flood_days": {"min": min(days), "max": max(days), "mean": fmean(days), "sample_sd": stdev(days)}}


def cold_sheet(archive, sheet):
    from openpyxl import load_workbook

    name, digest, count = WORKBOOKS[sheet]
    data = archive.read(name)
    require(sha256(data).hexdigest() == digest, f"{name}: workbook SHA-256 mismatch")
    with closing(load_workbook(io.BytesIO(data), read_only=True, data_only=True)) as workbook:
        values = workbook[sheet].values
        headers = next(values)
        records = list(values)
    require(len(records) == count and headers[0] == "Species", f"{sheet}: sheet layout or count changed")
    return [row[1:] for row in records if row[0] == "Lasius niger"]


def group_means(groups):
    return {label: {"n": len(values), "mean": fmean(values), "sample_sd": stdev(values)}
            for label, values in sorted(groups.items())}


def cold_summary(content):
    ctmin = defaultdict(list)
    smr = defaultdict(list)
    lethal = {}
    with ZipFile(io.BytesIO(content)) as archive:
        for temperature, dormant, value in cold_sheet(archive, "CTmin"):
            ctmin[f"{temperature}/{dormant}"].append(value)
        for temperature, dormant, estimate, low, high in cold_sheet(archive, "Lte50"):
            lethal[f"{temperature}/{dormant}"] = {"estimate_c": estimate, "ci95_c": [low, high]}
        for _, dormant, value in cold_sheet(archive, "SMR"):
            smr[dormant].append(value)

    require({key: len(values) for key, values in ctmin.items()} == {"8/NO": 11, "8/YES": 10, "26/NO": 11, "26/YES": 22}
            and {key: len(values) for key, values in smr.items()} == {"NO": 6, "YES": 5}
            and lethal.keys() == ctmin.keys(), "Unexpected L. niger group counts")
    return {"ctmin_c_by_acclimation_and_dormancy": group_means(ctmin),
            "smr_ul_co2_per_h_per_mg_at_18c_by_dormancy": group_means(smr),
            "reported_lte50_fits_by_acclimation_and_dormancy": lethal}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pangaea-directory", type=Path, default=ROOT / "out/s6_4_preflight/batch3/downloads")
    parser.add_argument("--dryad-archive", type=Path, default=ROOT / "out/s6_3_2_1/manual_downloads" / COLD_ARCHIVE)
    args = parser.parse_args()
    report = {"executed_at_utc": datetime.now(timezone.utc).isoformat(), "platform": platform.platform(),
              "python": platform.python_version(), "inputs": {}}
    provenance = report["inputs"]
    status = 0
    try:
        surveys = {name: read_input(args.pangaea_directory / name, name, provenance) for name in INPUTS if name != COLD_ARCHIVE}
        report["flood"] = {"status": "REPRODUCED", **flood_summary(surveys)}
    except (OSError, ValueError, KeyError) as error:
        report["flood"] = {"status": "NOT REPRODUCED" if isinstance(error, FileNotFoundError) else "FAIL", "error": str(error)}
        status = 1
    try:
        cold = read_input(args.dryad_archive, COLD_ARCHIVE, provenance)
        report["dormancy"] = {"status": "REPRODUCED", **cold_summary(cold)}
        report["openpyxl"] = version("openpyxl")
    except (OSError, ValueError, KeyError, BadZipFile, ModuleNotFoundError) as error:
        unavailable = isinstance(error, (FileNotFoundError, ModuleNotFoundError))
        report["dormancy"] = {"status": "NOT REPRODUCED" if unavailable else "FAIL", "error": str(error)}
        status = 1
    print(json.dumps(report, indent=2, allow_nan=False))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
