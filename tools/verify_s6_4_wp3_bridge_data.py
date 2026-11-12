"""Recompute the descriptive feeder-arrival table from Sakiyama and Wada's supplement."""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from statistics import mean, median, stdev
import xml.etree.ElementTree as ET
import zipfile

from read_s6_4_rm02_sidecar import require


DOI = "10.1038/s41598-025-02058-z"
SOURCE = ("https://static-content.springer.com/esm/art%3A10.1038%2Fs41598-025-02058-z/"
          "MediaObjects/41598_2025_2058_MOESM2_ESM.xlsx")
SHA256 = "49178270e8be4e7e27f4ad756f4919c28adf42f60a4da6d6a426fe9a7afa9498"
MD5 = "3e112462760b2b0f58885484c3cf3710"
NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
ARM_COLUMNS = {"A": "HIJ", "B": "MNO", "C": "RST", "D": "WXY"}


def workbook_rows(bundle, sheet, strings):
    root = ET.fromstring(bundle.read(f"xl/worksheets/sheet{sheet}.xml"))
    for row in root.findall(".//s:sheetData/s:row", NS):
        result = {}
        for cell in row:
            raw = cell.findtext("s:v", namespaces=NS)
            if raw is not None:
                name = cell.attrib["r"].rstrip("0123456789")
                value = strings[int(raw)] if cell.get("t") == "s" else raw
                result[name] = (value, int(cell.get("s", 0)))
        yield int(row.attrib["r"]), result


def observations(bundle, sheet, strings, columns):
    groups = defaultdict(list)
    for ordinal, row in workbook_rows(bundle, sheet, strings):
        if ordinal == 1:
            for letters in columns.values():
                require([row[col][0] for col in letters] == ["time", "colony", "experiment"], "unexpected sheet")
            continue
        for arm, (time_col, colony_col, arm_col) in columns.items():
            if time_col not in row:
                require(colony_col not in row and arm_col not in row, "partial workbook trial")
                continue
            require(row[arm_col][0] == arm, "treatment label does not match trial column")
            seconds, style = row[time_col]
            groups[arm].append((int(row[colony_col][0]), float(seconds), style))
    return groups


def screen(path):
    data = path.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    md5 = hashlib.md5(data, usedforsecurity=False).hexdigest()
    require((len(data), sha, md5) == (27778, SHA256, MD5), "workbook differs from registered publisher supplement")
    with zipfile.ZipFile(path) as bundle:
        strings = ["".join(si.itertext()) for si in
                   ET.fromstring(bundle.read("xl/sharedStrings.xml")).findall("s:si", NS)]
        arrivals = observations(bundle, 1, strings, ARM_COLUMNS)
        sensitivity = observations(bundle, 5, strings, {"A": "HIJ", "D": "MNO"})
        sheets = [node.attrib["name"] for node in ET.fromstring(bundle.read("xl/workbook.xml")).findall(".//s:sheet", NS)]
    require(sheets[0] == "time" and sheets[4] == "time_including_non-reaching", "workbook identity differs")
    results = {}
    for arm, (n, colonies) in zip("ABCD", ((42, 4), (50, 4), (43, 4), (36, 10))):
        data = arrivals[arm]
        trial_counts = Counter(nest for nest, _, _ in data)
        require(len(data) == n and len(trial_counts) == colonies, "arrival cohort differs from the Methods")
        seconds = [time for _, time, _ in data]
        results[arm] = dict(trials=n, colonies=colonies, trials_by_colony=dict(sorted(trial_counts.items())),
                            mean_s=mean(seconds), sd_s=stdev(seconds), median_s=median(seconds),
                            minimum_s=min(seconds), maximum_s=max(seconds))
    extras = {}
    for arm, extended in sensitivity.items():
        # The publisher labels added values as normalized estimates, so keep
        # them out of the observed arrivals and preserve their separate count.
        exact = Counter((nest, round(seconds, 8)) for nest, seconds, _ in arrivals[arm])
        extension = Counter((nest, round(seconds, 8)) for nest, seconds, _ in extended)
        extras[arm] = dict(rows=len(extended), additional_rows=sum((extension - exact).values()),
                           original_pairs_not_in_sheet=sum((exact - extension).values()),
                           worksheet_styles=dict(sorted(Counter(style for _, _, style in extended).items())))
    return dict(doi=DOI, source=SOURCE, bytes=27778, sha256=sha, md5=md5, worksheets=sheets,
                method="Descriptive completed-arrival summaries; no GLMM fit and no inferred censor times.",
                sampling_unit="One introduced target ant; trials nested within source colony.",
                complete_arrivals=results, separate_nonreach_sensitivity=extras)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = json.dumps(screen(args.workbook), indent=2) + "\n"
    if args.check:
        require(args.receipt.read_text(encoding="utf-8") == data, "workbook receipt differs")
    else:
        with args.receipt.open("x", encoding="utf-8", newline="\n") as output:
            output.write(data)
    print("Verified publisher workbook and four conditional arrival cohorts.")


if __name__ == "__main__":
    main()
