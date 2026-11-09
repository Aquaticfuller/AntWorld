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
        path=args.source/'probes'/name;shutil.copyfile(path,target/name)
        archive[name]=dict(bytes=path.stat().st_size,sha256=digest(path))
    (target/'archive.json').write_text(json.dumps(archive,indent=2)+'\n',encoding='utf-8')
    accesses=[]
    for path in sorted(args.source.glob('paper_requests_*_access.json')):
        accesses.extend(json.loads(path.read_text(encoding='utf-8')))
    (BASE/'literature_access.json').write_text(json.dumps(accesses,indent=2)+'\n',encoding='utf-8')
    print('Published four raw probe tables and access metadata; all full texts remain ignored')
if __name__=='__main__':main()
