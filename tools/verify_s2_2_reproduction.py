#!/usr/bin/env python3
"""Check clean-build S2.2 reproductions against committed raw data, normalizing only newlines."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
for name in ('baseline', 'fixed', 'social', 'ablations'):
    parser.add_argument('--'+name, required=True, type=Path)
parser.add_argument('--report', type=Path)
args = parser.parse_args(); results = []
for name, files in (('baseline', ('local.csv',)), ('fixed', ('local.csv',)),
                    ('social', ('choices.csv', 'social.csv', 'fields.csv')), ('ablations', ('summary.csv', 'timeseries.csv'))):
    for filename in files:
        expected = ROOT/'experiments/s2_2'/name/filename
        content = (getattr(args, name)/filename).read_text(encoding='utf-8')
        if content != expected.read_text(encoding='utf-8'):
            raise SystemExit(f'FAIL: {name}/{filename} differs from committed evidence')
        results.append(dict(file=f'{name}/{filename}', rows=len(content.splitlines())-1,
                            sha256=hashlib.sha256(content.encode('utf-8')).hexdigest()))
if args.report:
    report = dict(result='PASS', comparison='Exact UTF-8 text after CRLF/LF normalization only', files=results)
    args.report.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
print(f'PASS: all {len(results)} clean-build raw files match committed S2.2 evidence')
