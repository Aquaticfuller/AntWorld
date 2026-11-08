#!/usr/bin/env python3
"""Compare a clean S4 run and optional full S3 semantic regression with archived evidence."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('reproduced', type=Path)
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--s3-regression', type=Path)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    report = dict(source_commit=args.source_commit, s4={}, s3_semantic_regression={})
    for name in ('summary.csv','edits.csv','trajectories.csv','configuration.json'):
        expected = (ROOT/'experiments/s4/raw'/name).read_text(encoding='utf-8')
        actual = (args.reproduced/name).read_text(encoding='utf-8')
        assert expected == actual, f'clean-source mismatch: {name}'
        report['s4'][name] = dict(equal=True, sha256=hashlib.sha256(actual.encode()).hexdigest())
    if args.s3_regression:
        for name in ('summary.csv','individuals.csv'):
            with (ROOT/'experiments/s3/raw'/name).open(encoding='utf-8',newline='') as stream:
                expected = list(csv.DictReader(stream))
            with (args.s3_regression/name).open(encoding='utf-8',newline='') as stream:
                actual = list(csv.DictReader(stream))
            def normalize(rows):
                return [{k:v for k,v in row.items() if k != 'physics_version'} for row in rows]
            assert normalize(expected) == normalize(actual), f'S3 biological regression: {name}'
            report['s3_semantic_regression'][name] = dict(rows=len(actual), equal_except_physics_version=True)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
