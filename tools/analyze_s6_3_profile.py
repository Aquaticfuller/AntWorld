"""Summarize actual instrumented costs and preserve unscoped work explicitly."""
import argparse
import statistics as st
from collections import defaultdict
from pathlib import Path
from analyze_s6_3 import ROOT, read, emit


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=ROOT/'experiments/s6_3/profiles')
    p.add_argument('--out',type=Path,default=ROOT/'experiments/s6_3/performance_analysis/profile.csv')
    args = p.parse_args()
    buckets = defaultdict(list)
    expected = {}
    for batch in ('profile-contacts-before','profile-contacts-final','profile-births-before','profile-births-final'):
        folder = args.root/batch
        births = 'births' in batch
        samples = read(folder/('births.csv' if births else 'contacts.csv'))
        profiles,phases = read(folder/'profile.csv'),read(folder/'phases.csv')
        for r in samples:
            key = births,r['population'],r['layout']
            proof = tuple(r[k] for k in ('events','pending','state_hash','trace_hash'))
            assert expected.setdefault(key,proof)==proof
        for phase in phases:
            r = samples[int(phase['sample'])]
            rows = [x for x in profiles if x['sample']==phase['sample'] and x['phase']==phase['phase']]
            total = sum(int(x['exclusive_ns']) for x in rows)
            if phase['phase'] in ('advance','birth_advance'):
                assert total == int(next(x['inclusive_ns'] for x in rows if x['category']=='advance'))
            for x in rows:
                buckets[batch,r['population'],r['layout'],phase['phase'],x['category']].append((int(x['calls']),int(x['inclusive_ns'])/1e6,int(x['exclusive_ns'])/1e6,float(phase['wall_ms'])))
            buckets[batch,r['population'],r['layout'],phase['phase'],'outside_scopes'].append((0,0,float(phase['wall_ms'])-total/1e6,float(phase['wall_ms'])))
    result = []
    for (batch,population,layout,phase,category),rows in sorted(buckets.items()):
        result.append(dict(batch=batch,population=population,layout=layout,phase=phase,category=category,n=len(rows),
                           calls_median=st.median(x[0] for x in rows),inclusive_ms_median=st.median(x[1] for x in rows),
                           exclusive_ms_median=st.median(x[2] for x in rows),phase_wall_ms_median=st.median(x[3] for x in rows)))
    emit(args.out,result)
    print('PASS actual profile scopes; before/after work and hashes match:',len(result),'groups')


if __name__ == '__main__':
    main()
