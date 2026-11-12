"""Screen selected local scientific inputs without copying source publications into Git."""

import argparse
from collections import Counter
import csv
import hashlib
from io import BytesIO
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from read_s6_4_rm02_sidecar import require
from run_s6_4_rm02 import sha256


ARCHIVES = {
    "CAND-03": ("doi_10_5061_dryad_9j1cp__v20160504.zip", "10.5061/dryad.9j1cp",
                "ceed6278eaa69028e5917217fb5559896a099521ad5588383cd572622baf6557"),
    "CAND-04": ("doi_10_5061_dryad_qz612jm8x__v20200407.zip", "10.5061/dryad.qz612jm8x",
                "5cb03929342e95062d06661ee202d41e73f5185958b96fc2ffb6ae4d587b3ab8"),
}
OPTICS = "SlowEvap_time_volume.dat"
OPTICS_MD5 = "4cc2abbda27907d97124620a85f42a32"
BRIDGE_METHODS_MD5 = "051d75086827357e6b5199b125764f83"


def inventory(intake, sources):
    output = {}
    for source, (name, doi, expected) in ARCHIVES.items():
        path = intake / name
        digest = sha256(path)
        require(digest == expected, f"accepted input bytes changed for {source}")
        with ZipFile(path) as archive:
            workbooks = [entry for entry in archive.namelist() if entry.endswith(".xlsx")]
            require(len(workbooks) == 1, "ambiguous publisher workbook")
            with ZipFile(BytesIO(archive.read(workbooks[0]))) as workbook:
                root = ET.fromstring(workbook.read("xl/workbook.xml"))
                sheets = [node.get("name") for node in root.iter() if node.tag.endswith("}sheet")]
        output[source] = dict(doi=doi, file=name, bytes=path.stat().st_size, sha256=digest,
                              observed_worksheets=sheets, status="VERIFIED", scope="Workbook identity and sheet inventory")
    path = intake / "ALTAA_data.zip"
    with ZipFile(path) as archive:
        files = sorted(name for name in archive.namelist() if name.endswith(".csv") and "/rslt_" in name)
        require(bool(files), "ALTAA motion streams are missing")
        with archive.open(files[0]) as sample:
            columns = [field.strip() for field in next(csv.reader([sample.readline().decode("utf-8")]))]
        require(columns == ["Cam-idx", "Timestamp", "Key", "Value"], "unexpected ALTAA event schema")
    output["CAND-02"] = dict(doi="10.5281/zenodo.16893940", file=path.name, bytes=path.stat().st_size,
                             motion_stream_files=len(files), files_by_path_prefix=dict(sorted(Counter(
                                 "/".join(item.split("/")[:2]) for item in files).items())), sample_columns=columns,
                             status="VERIFIED", scope="ZIP catalog and one stream header; prior intake verified whole-file SHA-256")
    path = sources / OPTICS
    data = path.read_bytes()
    md5 = hashlib.md5(data, usedforsecurity=False).hexdigest()
    require(md5 == OPTICS_MD5, "optical dataset bytes differ from Zenodo")
    rows = list(csv.reader(data.decode("utf-8").splitlines(), delimiter="\t"))
    require(rows[:2] == [["Time", "Volume"], ["min", "picoliter"]], "unexpected optical units")
    samples = [(float(at), float(volume)) for at, volume in rows[2:]]
    require(samples and all(first[0] < second[0] for first, second in zip(samples, samples[1:])),
            "optical series timestamps are not strictly increasing")
    output["WP3-OPTICS-2026"] = dict(doi="10.5281/zenodo.22111492", file=path.name, bytes=len(data),
                                    sha256=hashlib.sha256(data).hexdigest(), repository_md5=md5,
                                    status="VERIFIED", samples=len(samples), first_time_min=samples[0][0],
                                    last_time_min=samples[-1][0], first_volume_pl=samples[0][1],
                                    last_volume_pl=samples[-1][1],
                                    scope="Time-volume table from one optical sequence; no kinetic fit or biological response")
    path = sources / "sakiyama-wada-methods.docx"
    data = path.read_bytes()
    md5 = hashlib.md5(data, usedforsecurity=False).hexdigest()
    require(md5 == BRIDGE_METHODS_MD5, "bridge methods supplement differs from publisher")
    output["WP3-WADA-METHODS"] = dict(doi="10.1038/s41598-025-02058-z", file="41598_2025_2058_MOESM1_ESM.docx",
                                     bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), publisher_md5=md5,
                                     status="VERIFIED", scope="Methods for projected non-arrival time and reported model fits")
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("intake", type=Path)
    parser.add_argument("sources", type=Path)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = json.dumps(inventory(args.intake, args.sources), indent=2) + "\n"
    if args.check:
        require(args.receipt.read_text(encoding="utf-8") == rendered, "candidate inventory differs")
    else:
        with args.receipt.open("x", encoding="utf-8", newline="\n") as output:
            output.write(rendered)
    print("Verified five scope-limited scientific input receipts.")


if __name__ == "__main__":
    main()
