#!/usr/bin/env python3
"""Compare clean-build experiment outputs with committed evidence, normalizing only newlines."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--baseline', type=Path, required=True)
parser.add_argument('--fixed', type=Path, required=True)
parser.add_argument('--ablations', type=Path, required=True)
parser.add_argument('--report', type=Path, help='Optional output JSON; no timestamps or machine-specific paths')
args = parser.parse_args()
verified = []
for name, directory, filenames in (
    ('baseline', args.baseline, ('choices.csv', 'social.csv', 'fields.csv')),
    ('fixed', args.fixed, ('choices.csv', 'social.csv', 'fields.csv')),
    ('ablations', args.ablations, ('summary.csv', 'timeseries.csv')),
):
    for filename in filenames:
        expected = ROOT / 'experiments/s2_1' / name / filename
        actual = directory / filename
        content = actual.read_text(encoding='utf-8')
        if content != expected.read_text(encoding='utf-8'):
            raise SystemExit(f'FAIL: reproduced {name}/{filename} differs')
        verified.append(dict(file=f'{name}/{filename}', data_rows=len(content.splitlines())-1,
                             sha256=hashlib.sha256(content.encode('utf-8')).hexdigest()))
report = dict(result='PASS', comparison='Exact UTF-8 text after CRLF/LF normalization only', files=verified)
if args.report:
    args.report.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
print(f'PASS: all {len(verified)} clean-build raw files match committed experiment evidence')
