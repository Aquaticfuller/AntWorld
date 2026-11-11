"""Inventory the pinned BR-02 source assets without fitting a model."""

import argparse
import csv
import hashlib
import io
import json
from collections import Counter, defaultdict
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile


B08_WORKBOOK_SHA = "6c9f0705d4e8969404e90667cc1d48ab861597f5aa6eda53b79a4b9e325cfb98"
B08_SUPPLEMENT_SHA = "c0c2df92320315ed58fc0ae49382eb55d4fb7972515c0556f4384f032654dc4d"
B07_DRYAD_NAME = "doi_10_5061_dryad_g79cnp5n1__v20210610.zip"
B07_DRYAD_SHA = "fa359ee2bfddb20d46cf9e1b1a8354c33be72b2487a4e2797679bd41e96d181e"
N01_PDF_SHA = "b1da7d29b5a7673eba8ccf2f9b0b9270c4024d5db7aadd1f60bf27406c8f0070"
SHEET_NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def verified_bytes(path, expected):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(f"Unexpected source digest for {path.name}")
    return data


def b08_workbook(data):
    with ZipFile(io.BytesIO(data)) as book:
        root = ElementTree.fromstring(book.read("xl/worksheets/sheet1.xml"))
        shared_strings = ElementTree.fromstring(book.read("xl/sharedStrings.xml"))
    rows = root.findall("./s:sheetData/s:row", SHEET_NS)
    labels = ["".join(text.text or "" for text in item.findall(".//s:t", SHEET_NS))
              for item in shared_strings]
    headers = {
        cell.attrib["r"]: labels[int(cell.findtext("s:v", namespaces=SHEET_NS))]
        for cell in rows[2] if cell.get("t") == "s"
    }
    groups = ("ABC", "EFG", "IJK", "MNO", "QRS")
    expected = ("Time (min)", "Id of the donor", "Id of the receiver")
    for columns in groups:
        if tuple(headers[f"{column}3"] for column in columns) != expected:
            raise ValueError("Unexpected B08 header")

    by_group = [[] for _ in groups]
    for row in rows[3:]:
        row_number = int(row.attrib["r"])
        cells = {cell.attrib["r"]: cell.findtext("s:v", namespaces=SHEET_NS)
                 for cell in row}
        for block, columns in zip(by_group, groups):
            values = [cells.get(f"{column}{row_number}") for column in columns]
            if values == [None, None, None]:
                continue
            if None in values:
                raise ValueError(f"Incomplete B08 triplet at row {row_number}")
            time, donor, receiver = map(int, values)
            if not 30 <= time <= 90 or donor == receiver:
                raise ValueError(f"Unexpected B08 time or dyad at row {row_number}")
            block.append((time, donor, receiver))

    blocks = []
    for index, block in enumerate(by_group, 1):
        unique = set(block)
        starts = {(time, donor, receiver) for time, donor, receiver in unique
                  if (time - 1, donor, receiver) not in unique}
        blocks.append({
            "workbook_colony_column": index,
            "scan_rows": len(block),
            "duplicate_scan_rows": len(block) - len(unique),
            "directed_run_starts_unique_tuples": len(starts),
            "directed_run_start_rows_retaining_duplicates": sum(row in starts for row in block),
        })
    return {
        "workbook_sha256": B08_WORKBOOK_SHA,
        "pdf_supplement_sha256": B08_SUPPLEMENT_SHA,
        "workbook_headers_per_block": expected,
        "workbook_blocks": blocks,
        "total_scan_rows": sum(row["scan_rows"] for row in blocks),
        "total_directed_run_starts_unique_tuples": sum(row["directed_run_starts_unique_tuples"] for row in blocks),
        "total_directed_run_start_rows_retaining_duplicates": sum(
            row["directed_run_start_rows_retaining_duplicates"] for row in blocks
        ),
        "published_table_s1_events_in_pdf_order": [129, 104, 90, 77, 95],
    }


def tsv(data):
    return list(csv.DictReader(io.StringIO(data.decode("utf-8-sig")), delimiter="\t"))


def b07_dryad(data):
    with ZipFile(io.BytesIO(data)) as bundle:
        pulse_rows = tsv(bundle.read("Lasius_pulseisotopedata.txt"))
        focal_growth = [row for row in tsv(bundle.read("DATA_combined.txt")) if row["species"] == "niger"]
        members = sorted(bundle.namelist())
    pulse = [row for row in pulse_rows if row["Sample ID"].strip()]
    if any(not row["Sample ID"].startswith("Lneo-") for row in pulse):
        raise ValueError("Unexpected species in B07 pulse table")
    cells = Counter((row["Enriched"], row["Caste"], row["Time"]) for row in pulse)
    treatment = {value: len({row["Colony"] for row in pulse if row["Enriched"] == value})
                 for value in ("Yes", "No")}
    censuses = defaultdict(set)
    for row in focal_growth:
        if row["census_number"] in ("2", "8") and row["num_workers"].isdigit():
            censuses[row["colony"]].add(row["census_number"])
    return {
        "dryad_archive_sha256": B07_DRYAD_SHA,
        "archive_members": members,
        "focal_growth_rows": len(focal_growth),
        "focal_growth_colony_labels": len({row["colony"] for row in focal_growth}),
        "focal_complete_census_2_and_8_pairs": sum(censuses[key] == {"2", "8"} for key in censuses),
        "pulse_species": "Lasius neoniger",
        "pulse_nonblank_sample_ids": len(pulse),
        "pulse_blank_sample_id_rows": len(pulse_rows) - len(pulse),
        "pulse_colonies_by_enriched_diet": treatment,
        "pulse_rows_by_enriched_diet_caste_hour": [
            [enriched, caste, int(hour), count] for (enriched, caste, hour), count in sorted(cells.items())
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch1_dir", type=Path, help="Local Batch 1 directory containing the archived publisher files")
    parser.add_argument("n01_pdf", type=Path, help="Local primary paper with the accepted ACC-009 digest")
    parser.add_argument("--check", action="store_true", help="Compare aggregates with the tracked receipt")
    args = parser.parse_args()
    root = args.batch1_dir
    verified_bytes(root / "B08-supp.pdf", B08_SUPPLEMENT_SHA)
    verified_bytes(args.n01_pdf, N01_PDF_SHA)
    result = {
        "B08": b08_workbook(verified_bytes(root / "B08-supp.xlsx", B08_WORKBOOK_SHA)),
        "B07": b07_dryad(verified_bytes(root / "user_downloads" / B07_DRYAD_NAME, B07_DRYAD_SHA)),
        "N01": {"verified_pdf_sha256": N01_PDF_SHA, "event_level_data": "NOT_AVAILABLE_IN_REVIEWED_ASSETS"},
    }
    rendered = json.dumps(result, indent=2) + "\n"
    if args.check:
        receipt = Path(__file__).with_name("PRIMARY_ASSET_RECEIPT.json")
        if receipt.read_text(encoding="utf-8") != rendered:
            raise SystemExit("BR-02 primary asset receipt differs")
    print(rendered, end="")


if __name__ == "__main__":
    main()
