"""Publish only audit data/receipts, never licensed article bodies or page images."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'experiments/s6_3_2'
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);args=p.parse_args()
    target=BASE/'probes';target.mkdir(exist_ok=True)
    archive={}
    for name in ('eligibility.csv','time_series.csv','events.csv','checks.csv'):
        path=args.source/'probes'/name;raw=path.read_bytes()
        # Git's text policy stores LF. Preserve source hashes separately so the
        # published artifact hash verifies on Windows and Linux alike.
        normalized=raw.replace(b'\r\n',b'\n');(target/name).write_bytes(normalized)
        archive[name]=dict(bytes=len(normalized),sha256=hashlib.sha256(normalized).hexdigest(),source_bytes=len(raw),source_sha256=hashlib.sha256(raw).hexdigest(),normalization='UTF-8 CSV; CRLF to LF only; all values and canonical event payload bytes unchanged')
    (target/'archive.json').write_text(json.dumps(archive,indent=2)+'\n',encoding='utf-8')
    accesses=[]
    for path in sorted(args.source.glob('paper_requests_*_access.json')):
        accesses.extend(json.loads(path.read_text(encoding='utf-8')))
    (BASE/'literature_access.json').write_text(json.dumps(accesses,indent=2)+'\n',encoding='utf-8')
    print('Published four raw probe tables and access metadata; all full texts remain ignored')
if __name__=='__main__':main()
