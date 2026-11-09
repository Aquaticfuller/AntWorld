"""Compare complete regenerated cases to preserved S6.3 facts and observations."""
import argparse
import hashlib
import json
import math
from pathlib import Path
from analyze_s6_3 import ROOT, read


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):
            h.update(block)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path)
    p.add_argument('--reference',type=Path,default=ROOT/'experiments/s6_3/ecology')
    p.add_argument('--group',default='review')
    p.add_argument('--cross-platform',action='store_true')
    p.add_argument('--report',type=Path,required=True)
    args = p.parse_args()
    groups = ('primary-v2','spatial-v2') if args.group=='review' else (args.group,)
    expected = {}
    for group in groups:
        for row in read(args.reference/group/'summary.csv'):
            expected[row['run']] = (group,row)
    results = []
    actual = read(args.source/'summary.csv')
    if args.group != 'review':
        assert len(actual)==len(expected)
    else:
        assert {r['run'] for r in actual} == {'1_8_balanced_constant_full_6','1_32_balanced_constant_compact_6'}
    excluded = {'setup_ms','advance_ms'} | ({'state_hash','trace_hash'} if args.cross_platform else set())
    for row in actual:
        group,ref = expected[row['run']]
        assert {k:v for k,v in row.items() if k not in excluded} == {k:v for k,v in ref.items() if k not in excluded}, row['run']
        folder = args.reference/group/row['run']
        for name in ('daily.csv','individuals.csv','life_events.csv'):
            a,b = read(folder/name),read(args.source/row['run']/name)
            assert len(a)==len(b), (row['run'],name,'row count')
            for left,right in zip(a,b):
                assert left.keys()==right.keys()
                for key in left:
                    if args.cross_platform and key in ('x_m','y_m','z_m'):
                        assert math.isclose(float(left[key]),float(right[key]),rel_tol=0,abs_tol=1e-12)
                    else:
                        assert left[key]==right[key],(row['run'],name,key,left[key],right[key])
        if not args.cross_platform:
            archive = json.loads((args.reference/group/'archive.json').read_text())
            assert digest(args.source/row['run']/'events.bin') == archive[row['run']+'/events.bin']['sha256']
            if row['status']=='complete':
                assert digest(args.source/row['run']/'final.aw') == archive[row['run']+'/final.aw']['sha256']
        results.append(dict(run=row['run'],group=group,events=int(row['events']),exact=True))
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(dict(cross_platform=args.cross_platform,excluded_fields=sorted(excluded),
                                          coordinate_tolerance_m=1e-12 if args.cross_platform else 0,cases=results),indent=2)+'\n',encoding='utf-8')
    print('PASS S6.3 reproduction:',len(results),'retained cases, including any censored endpoints')


if __name__ == '__main__':
    main()
