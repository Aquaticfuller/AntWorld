#!/usr/bin/env python3
"""Recalculate Batch 2 source summaries from locally held, hash-pinned files."""

import argparse
import csv
import io
import json
import math
import platform
from collections import Counter, defaultdict
from contextlib import closing
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from statistics import fmean, median
from zipfile import BadZipFile, ZipFile

from verify_batch1 import REVIEW, ROOT, index, require, rows
from verify_batch2 import ACCESS_LOG


DATA = "out/s6_4_preflight/batch2"
INPUTS = (
    ("f01-zip", "B2-F01", "B2-ACC-002", "out/s6_3_3_1/sources/Khuong_2013_Dataset_S1.zip"),
    ("p03-workbook", "B2-P03", "B2-ACC-032", f"{DATA}/downloads/P03_data.xlsx"),
    ("p04-workbook", "B2-P04", "B2-ACC-017", f"{DATA}/downloads/P04_data.xlsx"),
    ("p06-s2", "B2-P06", "B2-ACC-034", f"{DATA}/downloads/P06_S2.xlsx"),
    ("p06-s3", "B2-P06", "B2-ACC-035", f"{DATA}/downloads/P06_S3.xlsx"),
    ("p15-pdf", "B2-P15", "B2-ACC-046", f"{DATA}/user_downloads/Beckers1993.pdf"),
)


def f01(data):
    colony_counts = Counter()
    path_speed_by_track = []
    chord_speed_by_track = []
    window_count = 0
    interval_count = 0
    with ZipFile(io.BytesIO(data)) as archive:
        tracks = sorted(name for name in archive.namelist() if name.endswith(".txt"))
        require(len(tracks) == len(set(tracks)) == 69, "F01: expected 69 unique track files")
        for name in tracks:
            require(Path(name).parts[0] == "Incline1", f"{name}: track is outside the flat assay")
            with io.TextIOWrapper(archive.open(name), encoding="utf-8-sig") as stream:
                samples = list(csv.DictReader(stream, delimiter="\t"))
            conditions = {(row["Pente"], row["Colonie"], row["Temperature"], row["Humidite"]) for row in samples}
            require(len(conditions) == 1, f"{name}: inconsistent track conditions")
            incline, colony, temperature, humidity = conditions.pop()
            require((incline, temperature, humidity) == ("1", "26", "50"), f"{name}: unexpected flat-assay metadata")
            colony_counts[colony] += 1

            points = [(float(row["Time"]), float(row["X"]), float(row["Y"])) for row in samples]
            steps = []
            for (t0, x0, y0), (t1, x1, y1) in zip(points, points[1:]):
                require(math.isclose(t1 - t0, 0.04, rel_tol=0, abs_tol=1e-8), f"{name}: sample cadence changed")
                steps.append(math.hypot(x1 - x0, y1 - y0))
            interval_count += len(steps)
            path_speeds = []
            chord_speeds = []
            for start in range(0, len(steps) - 24, 25):
                stop = start + 25
                t0, x0, y0 = points[start]
                t1, x1, y1 = points[stop]
                elapsed = t1 - t0
                path_speeds.append(math.fsum(steps[start:stop]) * 1000 / elapsed)
                chord_speeds.append(math.hypot(x1 - x0, y1 - y0) * 1000 / elapsed)
            require(path_speeds, f"{name}: no complete one-second window")
            window_count += len(path_speeds)
            path_speed_by_track.append(fmean(path_speeds))
            chord_speed_by_track.append(fmean(chord_speeds))

    path_speed = median(path_speed_by_track)
    chord_speed = median(chord_speed_by_track)
    require(colony_counts == {"A": 24, "C": 26, "D": 19} and window_count == 5797 and interval_count == 145654,
            "F01: archive counts drifted")
    require((round(path_speed, 3), round(chord_speed, 3)) == (50.643, 38.133), "F01: speed summaries drifted")
    return {
        "tracks": sum(colony_counts.values()), "track_counts_by_colony_label": dict(colony_counts),
        "sample_intervals": interval_count, "complete_one_second_windows": window_count,
        "median_track_mean_path_mm_per_s": path_speed, "median_track_mean_chord_mm_per_s": chord_speed,
    }


def workbook_rows(data, sheet, identity, fields):
    from openpyxl import load_workbook

    with closing(load_workbook(io.BytesIO(data), read_only=True, data_only=True)) as workbook:
        values = workbook[sheet].values
        headers = next(values)
        selected = {}
        for field in (identity, *fields):
            require(headers.count(field) == 1, f"{sheet}: absent or duplicate column {field}")
            selected[field] = headers.index(field)
        return [
            {field: row[column] for field, column in selected.items()}
            for row in values if row[selected[identity]] not in (None, "")
        ]


def choice_summary(values):
    counts = Counter(values)
    require(counts.keys() <= {0, 1, None}, "Unexpected choice code")
    observed = counts[1] + counts[0]
    return {
        "correct": counts[1], "incorrect": counts[0], "missing": counts[None],
        "correct_fraction_among_observed": counts[1] / observed if observed else None,
    }


def p03(data):
    records = workbook_rows(data, "cleaned for R", "treatment",
                            ("mazetreatment", "pherotreatment", "Colony", "ant", "trip", "correct", "bifurcation"))
    labels = {(row["Colony"], row["ant"]) for row in records}
    colonies = {colony for colony, _ in labels}
    all_choices = choice_summary(row["correct"] for row in records)
    trip_seven = defaultdict(list)
    for row in records:
        if row["trip"] == 7:
            group = "/".join(row[key] for key in ("mazetreatment", "pherotreatment", "bifurcation"))
            trip_seven[group].append(row["correct"])
    groups = {key: choice_summary(values) for key, values in sorted(trip_seven.items())}
    expected = {
        "confined/allowed/1st": (22, 43, 15), "confined/allowed/2nd": (46, 19, 15),
        "confined/removed/1st": (18, 56, 11), "confined/removed/2nd": (57, 17, 11),
        "open/allowed/1st": (35, 40, 5), "open/allowed/2nd": (50, 25, 5),
        "open/removed/1st": (35, 34, 6), "open/removed/2nd": (51, 18, 6),
    }
    require((len(records), len(labels), len(colonies)) == (4930, 260, 8), "P03: workbook counts drifted")
    require(tuple(all_choices[key] for key in ("correct", "incorrect", "missing")) == (3334, 846, 750),
            "P03: all-trip choice counts drifted")
    require({group: (row["correct"], row["incorrect"], row["missing"]) for group, row in groups.items()} == expected,
            "P03: trip-seven choice counts drifted")
    return {
        "rows": len(records), "worker_colony_labels": len(labels), "colony_labels": len(colonies),
        "all_rows": all_choices,
        "trip_seven_pooled": choice_summary(value for group in trip_seven.values() for value in group),
        "trip_seven_by_layout_marking_fork": groups,
    }


def p04(data):
    zone = "Proportion_Frames_MiddleZone"
    records = workbook_rows(data, "Exp 1", "ant_ID", ("Colony", "Path_length", "Pheromone", zone))
    zones = defaultdict(list)
    for row in records:
        require(isinstance(row[zone], (int, float)) and 0 <= row[zone] <= 1, "P04: invalid per-ant frame fraction")
        zones[f"{row['Path_length']}/{row['Pheromone']}"].append(row[zone])
    zone_groups = {group: {"ants": len(values), "mean_frame_fraction": fmean(values)}
                   for group, values in sorted(zones.items())}
    require(len({row["ant_ID"] for row in records}) == len(records), "P04: duplicate Exp 1 ant ID")
    colonies_exp1 = len({row["Colony"] for row in records})
    require(colonies_exp1 == 6 and
            {group: (row["ants"], round(row["mean_frame_fraction"], 5)) for group, row in zone_groups.items()}
            == {"s/y": (26, 0.53892), "s/n": (25, 0.23722), "l/y": (25, 0.47134), "l/n": (26, 0.23179)},
            "P04: Exp 1 zone summaries drifted")

    choices = workbook_rows(data, "Exp 2", "date", ("colony", "ant", "treatment", "phero_side", "decision", "correct"))
    choice_groups = defaultdict(list)
    for row in choices:
        require(row["phero_side"] in {"Left", "Right"} and row["decision"] in {"Left", "Right"},
                "P04: invalid branch label")
        correct = int(row["decision"] == row["phero_side"])
        require(correct == row["correct"], "P04: branch labels disagree with workbook correct code")
        choice_groups[row["treatment"]].append(correct)
    colonies_exp2 = len({row["colony"] for row in choices})
    require(colonies_exp2 == 8 and {key: (sum(values), len(values)) for key, values in choice_groups.items()}
            == {"ON": (88, 100), "OE": (88, 100), "RE": (88, 99), "RN": (84, 99)},
            "P04: Exp 2 choice counts drifted")
    return {
        "exp1_rows": len(records), "exp1_colony_labels": colonies_exp1, "exp1_by_length_marking": zone_groups,
        "exp2_rows": len(choices), "exp2_colony_labels": colonies_exp2,
        "exp2_by_treatment": {key: choice_summary(values) for key, values in sorted(choice_groups.items())},
        "exp2_pooled": choice_summary(row["correct"] for row in choices),
    }


def mark_summary(values):
    observed = [value for value in values if isinstance(value, (int, float))]
    require(all(value >= 0 and value == int(value) for value in observed), "P06: invalid mark count")
    return {
        "rows": len(values), "observed": len(observed), "missing_or_nonnumeric": len(values) - len(observed),
        "total_marks": sum(observed), "mean_marks": fmean(observed),
    }


def mark_counts(summary):
    return {group: (row["rows"], row["observed"], row["total_marks"]) for group, row in summary.items()}


def p06_s2(data):
    records = workbook_rows(data, "exp1", "antID", ("phero_or_not", "correct_or_not", "Total_phero_eye"))
    by_marking = defaultdict(list)
    by_marking_and_route = defaultdict(list)
    for row in records:
        marking, route, count = row["phero_or_not"], row["correct_or_not"], row["Total_phero_eye"]
        by_marking[marking].append(count)
        by_marking_and_route[f"{marking}/{route}"].append(count)
    require(len({row["antID"] for row in records}) == len(records), "P06 S2: duplicate trial ID")
    main_groups = {key: mark_summary(values) for key, values in sorted(by_marking.items())}
    route_groups = {key: mark_summary(values) for key, values in sorted(by_marking_and_route.items())}
    require(mark_counts(main_groups) == {"phero": (252, 241, 1663), "no_phero": (252, 245, 1823)},
            "P06 S2: marking totals drifted")
    require(mark_counts(route_groups) == {
        "no_phero/correct": (126, 124, 970), "no_phero/incorrect": (126, 121, 853),
        "phero/correct": (126, 118, 857), "phero/incorrect": (126, 123, 806),
    }, "P06 S2: route totals drifted")
    return {"rows": len(records), "by_marking": main_groups, "by_marking_and_route": route_groups}


def p06_s3(data):
    records = workbook_rows(data, "for_analysis", "Data_number", ("Date", "Colony", "Ant", "Treatment", "segment", "pheromone"))
    require(len({row["Data_number"] for row in records}) == len(records), "P06 S3: duplicate row ID")
    by_length = defaultdict(list)
    segments = defaultdict(list)
    for row in records:
        treatment = row["Treatment"]
        by_length[treatment].append(row["pheromone"])
        segments[treatment, row["Date"], row["Colony"], row["Ant"]].append(row["segment"])
    groups = {key: mark_summary(values) for key, values in sorted(by_length.items())}
    require(mark_counts(groups) == {"long": (1040, 1039, 689), "short": (208, 204, 75)}, "P06 S3: segment totals drifted")
    worker_labels = Counter(group[0] for group in segments)
    require(worker_labels == {"long": 104, "short": 104}, "P06 S3: worker label counts drifted")
    # Retain the two uneven long-path segment series as supplied.
    lengths = {length: dict(Counter(len(indices) for group, indices in segments.items() if group[0] == length))
               for length in sorted(groups)}
    require(lengths == {"long": {9: 1, 10: 102, 11: 1}, "short": {2: 104}}, "P06 S3: segment coverage drifted")
    return {
        "rows": len(records), "by_length": groups, "worker_date_colony_labels_by_length": dict(worker_labels),
        "segment_row_counts_per_worker_label": lengths,
    }


def p15(data):
    require(data.startswith(b"%PDF-"), "P15: input is not a PDF")
    return {"bytes": len(data), "author_regressions": "NOT REPRODUCED", "reason": "Trial-level choice counts were not recovered."}


def check_input(path, source, access_id, entry, calculate):
    result = {"source": source, "access_id": access_id, "path": str(path), "expected_sha256": entry["SourceSha256"]}
    try:
        require(entry["SourceId"] == source and len(entry["SourceSha256"]) == 64, f"{access_id}: missing digest pin")
        data = path.read_bytes()
        result["sha256"] = sha256(data).hexdigest()
        require(result["sha256"] == entry["SourceSha256"], "File digest differs from the recorded SHA-256")
        result["summary"] = calculate(data)
        result["status"] = "VERIFIED" if calculate is p15 else "REPRODUCED"
    except (FileNotFoundError, ModuleNotFoundError) as error:
        result.update(status="NOT REPRODUCED", error=str(error))
    except (OSError, ValueError, KeyError, BadZipFile) as error:
        result.update(status="FAIL", error=str(error))
    return result


def package_version(name):
    try:
        return version(name)
    except PackageNotFoundError:
        return "NOT INSTALLED"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag, source, _, path in INPUTS:
        parser.add_argument(f"--{flag}", type=Path, default=ROOT / path, help=f"Local input for {source} (default: {path})")
    args = parser.parse_args()
    access = index(rows(REVIEW / ACCESS_LOG), "AccessId")
    calculations = (f01, p03, p04, p06_s2, p06_s3, p15)
    results = [
        check_input(getattr(args, flag.replace("-", "_")), source, access_id, access[access_id], calculate)
        for (flag, source, access_id, _), calculate in zip(INPUTS, calculations, strict=True)
    ]
    report = {
        "executed_at_utc": datetime.now(timezone.utc).isoformat(), "platform": platform.platform(),
        "python": platform.python_version(), "openpyxl": package_version("openpyxl"),
        "et_xmlfile": package_version("et-xmlfile"), "inputs": results,
    }
    print(json.dumps(report, indent=2, allow_nan=False))
    return int(any(result["status"] not in {"REPRODUCED", "VERIFIED"} for result in results))


if __name__ == "__main__":
    raise SystemExit(main())
