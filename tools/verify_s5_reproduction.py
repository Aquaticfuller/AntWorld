"""Compare all S5 simulation metrics, excluding filesystem-dependent storage bytes."""
import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(path):
    with path.open(encoding='utf-8', newline='') as stream:
        return [{key:value for key,value in row.items() if key != 'database_bytes'} for row in csv.DictReader(stream)]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('reproduced', type=Path)
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    expected = read(ROOT/'experiments/s5/raw/summary.csv')
    actual = read(args.reproduced/'summary.csv')
    assert expected == actual, 'S5 exact continuation/metric reproduction mismatch'
    report = dict(source_commit=args.source_commit, rows=len(actual), equal_except_filesystem_storage_bytes=True,
                  excluded_field='database_bytes', reason='WAL/database allocation is a measured storage result, not simulation state')
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(report,indent=2))

if __name__ == '__main__':
    main()
