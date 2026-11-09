"""Compare a complete independently rebuilt primary seed with its frozen observations."""
import argparse,csv,gzip,itertools,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(path):
    opener=gzip.open if path.suffix=='.gz' else open
    with opener(path,'rt',newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
def main():
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);p.add_argument('--seed',default='7');a=p.parse_args()
    reference=ROOT/'experiments/s6_3_3/raw'/('primary_'+a.seed)
    for name in ['windows.csv','scans.csv']:assert read(a.output/name)==read(reference/name),name+' differs'
    old,new=read(reference/'runs.csv'),read(a.output/'runs.csv');assert len(old)==len(new)==23
    for x,y in zip(old,new):
        for key in x:
            if key not in ['advance_ms','checkpoint_ms','restore_ms']:assert x[key]==y[key],key
    # Retain exact event identity/outcome/nutrition; allow only floating serialization roundoff.
    events=a.output/'events.csv'
    if not events.exists():events=a.output/'events.csv.gz'
    opener=gzip.open if events.suffix=='.gz' else open
    with gzip.open(reference/'events.csv.gz','rt',newline='',encoding='utf-8') as f,opener(events,'rt',newline='',encoding='utf-8') as g:
        for x,y in itertools.zip_longest(csv.DictReader(f),csv.DictReader(g)):
            assert x is not None and y is not None
            for key in x:
                if key in ['x_m','y_m','z_m']:assert abs(float(x[key])-float(y[key]))<=1e-12
                else:assert x[key]==y[key],(key,x['event_id'])
    print(json.dumps(dict(seed=a.seed,runs=23,matched='windows/scans, physical metrics, every exported event',timing='excluded from deterministic comparison')))
if __name__=='__main__':main()
