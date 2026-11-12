"""Use the existing performance instruments with an exactly matched CPU sensor subset."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

from extract_s6_2_hwinfo import header
from run_s6_4_wp6b import ROOT, write_json


ORIGINAL = ROOT / "experiments/s6_2/hwinfo_columns_v2.json"
MAPPING = ROOT / "experiments/s6_4_wp6b_r2/performance/hwinfo_columns.json"
PROTOCOL = ROOT / "research/s6_4_wp6b_r2/FROZEN_R2_PROTOCOL.md"
APPEND_LAYOUT = MAPPING.with_name("hwinfo_append_layout.json")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def mapping(source):
    fields = header(source)
    original = json.loads(ORIGINAL.read_text(encoding="utf-8"))
    for column in original["columns"]:
        if digest(fields[column["index"]].encode()) != column["original_label_sha256"]:
            raise ValueError(f"CPU channel changed: {column['label']}")
    return dict(source_header_sha256=digest(json.dumps(fields, ensure_ascii=True).encode()), source_columns=len(fields),
                columns=original["columns"], original_header_sha256=original["source_header_sha256"],
                original_columns=original["source_columns"], mapping="Exact original index and label SHA-256 for every CPU channel.")


def check_mapping():
    old = json.loads(ORIGINAL.read_text(encoding="utf-8"))
    new = json.loads(MAPPING.read_text(encoding="utf-8"))
    if (new["columns"] != old["columns"] or new["original_header_sha256"] != old["source_header_sha256"] or
        new["original_columns"] != old["source_columns"]):
        raise ValueError("R2 telemetry channels differ from the approved instrument")


if __name__ == "__main__":
    kind = sys.argv.pop(1)
    if kind == "capture-map":
        MAPPING.parent.mkdir(parents=True, exist_ok=True)
        write_json(MAPPING, mapping(Path(sys.argv[1])))
    else:
        check_mapping()
        import run_s6_3_3_1_performance as native

        native.MAPPING = MAPPING
        use_append_log = "--append-layout" in sys.argv
        if use_append_log:
            from s6_4_wp6b_r2_append_log import AppendLog

            options = argparse.ArgumentParser(add_help=False)
            options.add_argument("--append-layout", action="store_true")
            options.add_argument("--hwinfo-csv", required=True, type=lambda value: Path(value).resolve())
            source, _ = options.parse_known_args()
            sys.argv.remove("--append-layout")
            adapter = AppendLog(source.hwinfo_csv, native.load(APPEND_LAYOUT), native.load(MAPPING))
            native.sensor_tail = adapter.tail
            native.extract = adapter.extract
        dependencies = native.dependencies
        frozen = {Path(__file__).name: native.digest(Path(__file__))}
        if use_append_log:
            reader = Path(__file__).with_name("s6_4_wp6b_r2_append_log.py")
            frozen |= {reader.name: native.digest(reader), APPEND_LAYOUT.name: native.digest(APPEND_LAYOUT)}
        native.dependencies = lambda: dependencies() | frozen
        if kind == "native":
            native.main()
        elif kind == "protected":
            from s6_4_wp6b_r2_protected_observer import main
            main()
        elif kind == "application":
            from profile_s6_4_wp6b_r2 import main
            main()
        else:
            raise ValueError(f"unknown performance scope: {kind}")
