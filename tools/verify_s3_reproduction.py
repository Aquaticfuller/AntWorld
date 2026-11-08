#!/usr/bin/env python3
"""Compare an independently rerun S3 experiment with the committed complete evidence."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('rerun',type=Path)
parser.add_argument('--source-commit',required=True)
parser.add_argument('--report',type=Path,default=ROOT/'experiments/s3/reproduction.json')
args = parser.parse_args()
files = []
for name in ('summary.csv','individuals.csv','configuration.json'):
    original = (ROOT/'experiments/s3/raw'/name).read_text(encoding='utf-8')
    repeated = (args.rerun/name).read_text(encoding='utf-8')
    if original != repeated:
        raise SystemExit(f'FAIL: reproduction differs: {name}')
    files.append({'file':name,'sha256_normalized_utf8':hashlib.sha256(original.encode()).hexdigest(),'identical':True})
args.report.write_text(json.dumps({'source_commit':args.source_commit,'seeds':64,'runs':1536,'files':files},indent=2)+'\n',encoding='utf-8',newline='\n')
print('PASS S3 exact clean-source reproduction: 1536 runs and all three raw artifacts')
