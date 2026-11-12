"""Read a verified HWiNFO append stream with one documented layout change."""

import csv
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
import time

from extract_s6_2_hwinfo import MAPPING as CPU_FIELDS


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_record(line):
    return next(csv.reader([line.decode("utf-8-sig")], strict=True))


def verify_prefix(prefix, layout, mapping):
    if len(prefix) != layout["pinned_prefix_bytes"] or digest(prefix) != layout["pinned_prefix_sha256"]:
        raise ValueError("the append stream is not the verified source prefix")
    fields = read_record(prefix.split(b"\n", 1)[0].rstrip(b"\r"))
    narrow, wide = layout["observed_header_columns"], layout["reference_header_columns"]
    if len(fields) != narrow or narrow != mapping["source_columns"] or wide != mapping["original_columns"] or wide != narrow + 1:
        raise ValueError("the recorded sensor header widths disagree")
    header_sha = digest(json.dumps(fields, ensure_ascii=True).encode())
    if (header_sha != mapping["source_header_sha256"] or header_sha != layout["observed_header_sha256"] or
            layout["reference_header_sha256"] != mapping["original_header_sha256"]):
        raise ValueError("sensor header identity changed")
    indices = {item["index"]: item["label"] for item in mapping["columns"]}
    if (indices != CPU_FIELDS or len(indices) != layout["matching_cpu_columns"] or
            max(indices) != layout["maximum_used_cpu_column"] or max(indices) >= layout["reference_extra_column_index"]):
        raise ValueError("one of the measured channels falls outside the verified common prefix")
    for item in mapping["columns"]:
        if digest(fields[item["index"]].encode()) != item["original_label_sha256"]:
            raise ValueError("the identity of a measured CPU channel changed")


def sensor_row(line, width, zone=None):
    row = read_record(line)
    if len(row) != width or row[-1]:
        raise ValueError("unrecognized sensor record layout")
    at = datetime.strptime(row[0] + " " + row[1], "%d.%m.%Y %H:%M:%S.%f").replace(tzinfo=zone).timestamp()
    values = {}
    for index, label in CPU_FIELDS.items():
        value = row[index]
        values[label] = 1 if value in ("Yes", chr(0x662f)) else 0 if value in ("No", chr(0x5426)) else float(value) if value else ""
    return at, values


class AppendLog:
    def __init__(self, path, layout, mapping):
        self.path = path
        self.layout = layout
        self.mapping = mapping
        self.prefix_size = layout["pinned_prefix_bytes"]
        self.wide = layout["reference_header_columns"]
        self.narrow = layout["observed_header_columns"]
        self.first_wide = layout["first_wider_source_line"]
        with path.open("rb") as stream:
            verify_prefix(stream.read(self.prefix_size), layout, mapping)

    def tail(self, path, fields):
        if path != self.path or len(fields) != self.narrow:
            raise ValueError("admission source differs from the frozen append stream")
        with path.open("rb") as stream:
            size = stream.seek(0, 2)
            if size < self.prefix_size:
                raise OSError("the append stream was truncated")
            start = max(0, size - 65536)
            stream.seek(start)
            tail = stream.read(size - start).splitlines(keepends=True)
        available = [line for line in tail[1:] if line.endswith(b"\n")]
        empty = dict(sensor_utc_ns="", sensor_age_s="", source_prefix_bytes=size)
        if not available:
            return empty
        try:
            stamp, values = sensor_row(available[-1], self.wide)
        except (ValueError, UnicodeError, csv.Error):
            return empty
        return dict(sensor_utc_ns=int(stamp * 1e9), sensor_age_s=time.time() - stamp, source_prefix_bytes=size, **values)

    def extract(self, root, mapping_path):
        if json.loads(mapping_path.read_text(encoding="utf-8")) != self.mapping:
            raise ValueError("the frozen CPU mapping was replaced")
        configuration = json.loads((root / "configuration.json").read_text(encoding="utf-8"))
        minutes = configuration["before"]["timezone_minutes"]
        zone = timezone(timedelta(minutes=minutes))
        for folder in sorted(root.glob("session*")):
            if (folder / "hwinfo_provenance.json").exists():
                continue
            receipt = json.loads((folder / "receipt.json").read_text(encoding="utf-8"))
            data = (folder / "hwinfo_after.raw").read_bytes()
            verify_prefix(data[:self.prefix_size], self.layout, self.mapping)
            rows = []
            lines = data.splitlines(keepends=True)
            trailing_partial = int(not lines[-1].endswith(b"\n"))
            for number, line in enumerate(lines[1:len(lines) - trailing_partial], 2):
                stamp, values = sensor_row(line, self.narrow if number < self.first_wide else self.wide, zone)
                ns = int(stamp * 1e9)
                if receipt["started_utc_ns"] - 3_000_000_000 <= ns <= receipt["ended_utc_ns"] + 3_000_000_000:
                    rows.append(dict(utc_ns=ns, source_line=number, **values))
            if not rows:
                raise ValueError("no verified sensor rows bracket the declared interval")
            output = io.StringIO(newline="")
            writer = csv.DictWriter(output, list(rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
            (folder / "hwinfo.csv").write_bytes(output.getvalue().encode())
            provenance = dict(source_prefix_bytes=len(data), source_prefix_sha256=digest(data),
                              mapping_sha256=digest(json.dumps(self.mapping, sort_keys=True).encode()),
                              append_layout=self.layout, retained_rows=len(rows), incomplete_rows=trailing_partial,
                              first_utc_ns=rows[0]["utc_ns"], last_utc_ns=rows[-1]["utc_ns"],
                              timezone_offset_minutes=minutes,
                              selection="All CPU rows in the timed interval and its three-second brackets. No values imputed.")
            (folder / "hwinfo_provenance.json").write_text(json.dumps(provenance, indent=2) + "\n",
                                                        encoding="utf-8", newline="\n")
