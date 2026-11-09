"""Retain every sample and separate semantic parity, attribution and acceptance."""
import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path
from analyze_s6 import quantile

ROOT=Path(__file__).resolve().parents[1]


def read(path):
    with path.open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def audit(root, archives):
    rows, targets, hashes, profiles = [], {}, {}, []
    for name, repetitions in archives:
        path=root/name
        raw=read(path/'contacts.csv')
        expected={(str(n),l,p,str(r)) for n in (128,512,2048) for l in ('dense','dispersed')
                  for p in ('exhaustive','bounded') for r in range(repetitions)}
        key=lambda x: tuple(x[k] for k in ('population','layout','policy','repetition'))
        assert len(raw)==len(expected) and {key(x) for x in raw}==expected
        grouped=defaultdict(list)
        for x in raw:
            n=int(x['population'])
            assert int(x['events'])==31*n+2 and int(x['pending'])==2*n
            assert int(x['decisions'])==9*n
            if x['policy']=='bounded':
                assert int(x['maximum_candidates'])<=16
                assert int(x['bucket_queries'])==27*int(x['decisions'])
            grouped[key(x)[:3]].append(x)
        medians={}
        for (n,layout,policy), group in grouped.items():
            for metric in ('setup_ms','advance_ms','encode_ms','restore_ms','resident_bytes',
                           'peak_resident_bytes','checkpoint_bytes','events','pending','decisions',
                           'candidates','bucket_queries','tree_visits','maximum_candidates'):
                values=[float(x[metric]) for x in group]
                rows.append(dict(archive=name,population=n,layout=layout,policy=policy,metric=metric,
                    samples=len(values),p50=statistics.median(values),p95=quantile(values,.95),
                    p99=quantile(values,.99),minimum=min(values),maximum=max(values)))
                if metric=='advance_ms': medians[(n,layout,policy)]=statistics.median(values)
        speedup=medians[('2048','dense','exhaustive')]/medians[('2048','dense','bounded')]
        growth=medians[('2048','dense','bounded')]/medians[('512','dense','bounded')]
        targets[name]=dict(dense_2048_speedup=speedup,dense_512_to_2048_growth=growth,
                          speedup_at_least_4x='PASS' if speedup>=4 else 'FAIL',
                          growth_at_most_6x='PASS' if growth<=6 else 'FAIL',
                          timing_role='attribution only' if name.startswith('profile_') else 'uninstrumented')
        if (path/'states.csv').exists():
            state=read(path/'states.csv')
            assert len(state)==len(expected) and {key(x) for x in state}==expected
            for x in state:
                k=key(x)[:3]
                pair=(x.get('s6_normalized_state_hash',x['state_hash']),x['trace_hash'])
                if k in hashes: assert hashes[k]==pair,(name,k,'changed authoritative semantics')
                hashes[k]=pair
        if name.startswith('profile_'):
            data=read(path/'profile.csv')
            phases=defaultdict(list)
            for x in data: phases[(*key(x),x['phase'])].append(x)
            assert len(data)==len(expected)*27 and len(phases)==len(expected)*3
            for k, values in phases.items():
                assert len(values)==9 and len({x['category'] for x in values})==9
                if k[-1]=='advance':
                    root_ns=int(next(x['inclusive_ns'] for x in values if x['category']=='advance'))
                    assert sum(int(x['exclusive_ns']) for x in values)==root_ns
            group=defaultdict(list)
            for x in data:
                group[(x['population'],x['layout'],x['policy'],x['phase'],x['category'])].append(x)
            for k, values in group.items():
                profiles.append(dict(zip(('archive','population','layout','policy','phase','category'),(name,*k),strict=True),
                    samples=len(values),calls_p50=statistics.median(int(x['calls']) for x in values),
                    inclusive_ms_p50=statistics.median(int(x['inclusive_ns'])/1e6 for x in values),
                    exclusive_ms_p50=statistics.median(int(x['exclusive_ns'])/1e6 for x in values)))
    return rows, profiles, dict(targets=targets,canonical_hash_groups=len(hashes),semantic_parity='PASS')


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,default=ROOT/'experiments/s6_1')
    p.add_argument('--before-only',action='store_true')
    p.add_argument('--check',action='store_true')
    a=p.parse_args()
    archives=[('performance_baseline',10),('unprofiled_before',3),('profile_before',3)]
    if not a.before_only: archives += [('profile_after',3),('performance_final',10)]
    rows, profiles, report=audit(a.root,archives)
    output=a.root/('analysis_before' if a.before_only else 'analysis')
    if not a.check: output.mkdir(parents=True,exist_ok=True)
    for name, data in (('performance.csv',rows),('profile.csv',profiles)):
        if a.check:
            assert read(output/name)==[{k:str(v) for k,v in row.items()} for row in data]
        else:
            with (output/name).open('w',encoding='utf-8',newline='') as f:
                w=csv.DictWriter(f,list(data[0])); w.writeheader(); w.writerows(data)
    encoded=json.dumps(report,indent=2)+'\n'
    if a.check: assert (output/'performance.json').read_text(encoding='utf-8')==encoded
    else: (output/'performance.json').write_text(encoded,encoding='utf-8',newline='\n')
    print(encoded)


if __name__=='__main__': main()
