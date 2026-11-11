#!/usr/bin/env python3
"""Check published Table S3 and the Fig. S9 statistic in the García Ibarra supplement."""

import argparse
import hashlib
import json
import re
from collections import defaultdict
from decimal import Decimal, localcontext
from io import BytesIO
from math import comb, fsum
from pathlib import Path
from statistics import fmean
from xml.etree import ElementTree
from zipfile import ZipFile


SUPPLEMENT_SHA256 = "0cbea1bce233b8c09657db5c86cf9f4c1f0c6f64cf86813d0532219ac47d8c90"
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
EXPECTED_TREATMENTS = {"Low temperature": 5, "Medium temperature": 6, "High temperature": 6}


def text(element):
    return "".join(node.text or "" for node in element.findall(".//w:t", NS)).strip()


def colony_rows(document):
    for table in document.findall(".//w:tbl", NS):
        rows = [row.findall("w:tc", NS) for row in table.findall("w:tr", NS)]
        if rows and rows[0] and text(rows[0][0]) == "Treatment":
            break
    else:
        raise ValueError("Table S3 was not found")
    colony_ids = set()
    groups = defaultdict(list)
    treatment = None
    for row in rows[1:]:
        label, colony, start, end, growth, _ = map(text, row)
        if label:
            treatment = label
        elif row[0].find("./w:tcPr/w:vMerge", NS) is None:
            raise ValueError(f"No treatment for {colony}")
        if colony in colony_ids or int(end) - int(start) != int(growth):
            raise ValueError(f"Inconsistent colony row: {colony}")
        colony_ids.add(colony)
        groups[treatment].append(int(growth))
    if {treatment: len(values) for treatment, values in groups.items()} != EXPECTED_TREATMENTS:
        raise ValueError("Unexpected treatment sizes")
    return groups


def growth_anova(groups):
    values = list(groups.values())
    n = sum(map(len, values))
    overall_mean = fmean(x for group in values for x in group)
    means = [fmean(group) for group in values]
    between = fsum(len(group) * (average - overall_mean) ** 2 for group, average in zip(values, means))
    within = fsum((x - average) ** 2 for group, average in zip(values, means) for x in group)
    df_within = n - len(values)
    f_value = (between / 2) / (within / df_within)
    return (2, df_within), f_value, (df_within / (df_within + 2 * f_value)) ** (df_within / 2)


def f_1_18_tail(f_value):
    # Substitute u = sqrt(F/(18 + F)) into the two-sided t(18) tail.
    # The remaining integral is (1 - u**2)**8 from the boundary to 1.
    with localcontext() as context:
        context.prec = 45
        lower = (f_value / (18 + f_value)).sqrt()
        weights = [Decimal((-1) ** k * comb(8, k)) / (2 * k + 1) for k in range(9)]
        return float(sum(w * (1 - lower ** (2 * k + 1)) for k, w in enumerate(weights)) / sum(weights))


def figure_test(document, figure):
    prefix = f"Fig S{figure}."
    caption = next(text(p) for p in document.findall(".//w:p", NS) if text(p).startswith(prefix))
    match = re.search(r"F\s*(\d+),\s*(\d+)\s*=\s*(\d+(?:\.\d+)?),\s*[pP]\s*([<>])\s*(\d+\.\d+)", caption)
    if match is None:
        raise ValueError(f"Fig. S{figure} has no readable F statistic")
    df_a, df_b, statistic, comparison, probability = match.groups()
    return (int(df_a), int(df_b)), Decimal(statistic), f"{comparison} {probability}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("supplement", type=Path, help="Local publisher DOCX matching the recorded SHA-256")
    source = parser.parse_args().supplement
    try:
        content = source.read_bytes()
    except OSError as error:
        parser.error(str(error))
    digest = hashlib.sha256(content).hexdigest()
    if digest != SUPPLEMENT_SHA256:
        parser.error(f"Unexpected supplement SHA-256 {digest}. Expected {SUPPLEMENT_SHA256}.")
    with ZipFile(BytesIO(content)) as archive:
        document = ElementTree.fromstring(archive.read("word/document.xml"))
    groups = colony_rows(document)
    degrees, f_value, p_value = growth_anova(groups)
    s10_df, s10_f, s10_p = figure_test(document, 10)
    if degrees != s10_df or round(f_value, 2) != float(s10_f):
        raise ValueError("Table S3 net counts do not reproduce the printed Fig. S10 F statistic")
    s9_df, s9_f, s9_p = figure_test(document, 9)
    if s9_df != (1, 18):
        raise ValueError("The Fig. S9 check requires its published (1, 18) degrees of freedom")
    print(json.dumps({
        "source": source.name,
        "sha256": digest,
        "table_s3": {
            "unit": "colony",
            "outcome": "end worker count minus start worker count",
            "treatments": {name: {"n": len(rows), "mean_net_workers": fmean(rows)}
                           for name, rows in groups.items()},
            "df": degrees, "F": f_value, "p": p_value,
        },
        "figure_s10_printed": {"df": s10_df, "F": float(s10_f), "p_relation": s10_p},
        "figure_s9_printed": {"df": s9_df, "F": float(s9_f), "p_relation": s9_p},
        "figure_s9_conventional_F_tail": f_1_18_tail(s9_f),
    }, indent=2))


if __name__ == "__main__":
    main()
