"""Audit a failed HWiNFO append stream without changing its qualification."""

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import csv
import json
from pathlib import Path

from run_s6_4_wp6b import sha, write_json
from run_s6_4_wp6b_r2_performance import APPEND_LAYOUT, MAPPING
from s6_4_wp6b_r2_append_log import read_record, sensor_row, verify_prefix


def inspect(sensor, receipt, configuration):
    layout = json.loads(APPEND_LAYOUT.read_bytes())
    mapping = json.loads(MAPPING.read_bytes())
    zone = timezone(timedelta(minutes=configuration["before"]["timezone_minutes"]))
    start, end = (receipt[k] for k in ("started_utc_ns", "ended_utc_ns"))
    anomalies, retained, bad_dates = [], [], []
    widths = Counter()
    with sensor.open("rb") as source:
        verify_prefix(source.read(layout["pinned_prefix_bytes"]), layout, mapping)
        source.seek(0)
        next(source)
        for number, line in enumerate(source, 2):
            if not line.endswith(b"\n"):
                bad_dates.append({"line": number, "status": "INCOMPLETE_APPEND_ROW"})
                continue
            try:
                row = read_record(line)
                date = datetime.strptime(f"{row[0]} {row[1]}", "%d.%m.%Y %H:%M:%S.%f").replace(tzinfo=zone)
            except (csv.Error, IndexError, UnicodeError, ValueError):
                bad_dates.append({"line": number, "status": "DATE_OR_CSV_INVALID"})
                continue
            at = int(date.timestamp() * 1e9)
            inside = start - 3_000_000_000 <= at <= end + 3_000_000_000
            widths[len(row), inside] += 1
            width = (layout["observed_header_columns"] if number < layout["first_wider_source_line"] else
                     layout["reference_header_columns"])
            try:
                sensor_row(line, width, zone)
            except ValueError:
                anomalies.append(dict(line=number, columns=len(row), expected_columns=width, local_time=date.isoformat(),
                                      in_timed_window_with_brackets=inside))
                continue
            if inside:
                retained.append(at)
    return dict(disposition="DIAGNOSTIC_ONLY", source_sha256=sha(sensor), source_bytes=sensor.stat().st_size,
                session_start_utc_ns=start, session_end_utc_ns=end, row_widths=[dict(columns=k[0], in_timed_window_with_brackets=k[1],
                rows=v) for k, v in sorted(widths.items())], malformed_rows=anomalies, undated_or_partial_rows=bad_dates,
                parseable_window_rows=len(retained), bracketed=bool(retained and retained[0]<=start<=end<=retained[-1]),
                max_window_gap_seconds=max(((b-a)/1e9 for a,b in zip(retained,retained[1:])), default=None))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("sensor", "session_receipt", "configuration", "output"):
        parser.add_argument(key, type=Path)
    args = parser.parse_args()
    write_json(args.output, inspect(args.sensor, json.loads(args.session_receipt.read_bytes()),
                                    json.loads(args.configuration.read_bytes())))
