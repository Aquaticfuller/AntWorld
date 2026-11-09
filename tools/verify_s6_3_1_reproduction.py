"""Compare regenerated S6.3.1 trajectories with retained observations and hashes."""
import argparse
import json
import math
from pathlib import Path
from analyze_s6_3_1 import BASE,read
from archive_s6_3_1 import digest


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path);p.add_argument('--model',choices=('baseline','corrected'),default='corrected')
    p.add_argument('--matrix',default='review');p.add_argument('--cross-platform',action='store_true');p.add_argument('--report',type=Path,required=True)
    args=p.parse_args();matrix='positive' if args.matrix=='review' else args.matrix
    base=BASE/'ecology'/args.model/matrix;archive=json.loads((base/'archive.json').read_text())
    actual=read(args.source/'summary.csv');expected={r['run']:r for r in read(base/'summary.csv')}
    if args.matrix=='review':assert {r['run'] for r in actual}=={'1_8_balanced_constant_positive_6','1_32_balanced_constant_positive_6'}
    else:assert {r['run'] for r in actual}==set(expected)
    excluded={'setup_ms','advance_ms'}|({'state_hash','trace_hash'} if args.cross_platform else set())
    results=[]
    for row in actual:
        name=row['run'];ref=expected[name]
        assert {k:v for k,v in row.items() if k not in excluded}=={k:v for k,v in ref.items() if k not in excluded},name
        for filename in ('daily.csv','individuals.csv','life_events.csv','decisions.csv'):
            left,right=read(args.source/name/filename),read(base/name/filename)
            assert len(left)==len(right),(name,filename)
            for a,b in zip(left,right):
                assert a.keys()==b.keys()
                for k in a:
                    if args.cross_platform and k in ('x_m','y_m','z_m'):assert math.isclose(float(a[k]),float(b[k]),rel_tol=0,abs_tol=1e-12)
                    else:assert a[k]==b[k],(name,filename,k,a[k],b[k])
        if not args.cross_platform:
            for filename in ('events.bin','final.aw'):assert digest(args.source/name/filename)==archive[name+'/'+filename]['sha256'],(name,filename)
        results.append(dict(run=name,events=int(row['events']),exact=True))
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(dict(model=args.model,matrix=matrix,cross_platform=args.cross_platform,excluded_summary_fields=sorted(excluded),cases=results),indent=2)+'\n',encoding='utf-8')
    print('PASS S6.3.1 reproduction',len(results),'worlds')


if __name__=='__main__':main()
