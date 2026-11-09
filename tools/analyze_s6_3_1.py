"""Reproduce all frozen S6.3.1 outcomes and seed-paired uncertainty from raw CSV."""
import argparse
import csv
import gzip
import io
import json
import math
import random
import statistics as st
from collections import defaultdict
from pathlib import Path
from archive_s6_3_1 import digest

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'experiments/s6_3_1'
EXPECTED={'historical':48,'causal':72,'restricted':24,'sensitivity':36,'positive':12}
METRICS=('queen_lifetime_days','births','emerged','final_population','queen_gifts','final_received_carbs_ug','final_received_protein_ug','final_received_water_ug','final_body_energy_nj','late_births_120_180','deferred_attempts','unsafe_post_lay_energy')


def read(path):
    if not path.exists():path=Path(str(path)+'.gz')
    op=gzip.open if path.suffix=='.gz' else open
    with op(path,'rt',newline='',encoding='utf-8') as f:return list(csv.DictReader(f))


def quantile(a,p):
    a=sorted(a);x=(len(a)-1)*p;i=int(x)
    return a[i]+(a[min(i+1,len(a)-1)]-a[i])*(x-i)


def interval(a):
    rng=random.Random(63101)
    means=[sum(rng.choices(a,k=len(a)))/len(a) for _ in range(4096)]
    return sum(a)/len(a),quantile(means,.025),quantile(means,.975)


def wilson(success,n):
    z=1.959963984540054;p=success/n;denom=1+z*z/n
    center=(p+z*z/(2*n))/denom
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/denom
    return 0. if success==0 else max(0.,center-half),1. if success==n else min(1.,center+half)


def emit(path,rows,check=False):
    buf=io.StringIO(newline='');w=csv.DictWriter(buf,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    if check:assert path.read_text(encoding='utf-8')==buf.getvalue(),str(path)
    else:path.parent.mkdir(parents=True,exist_ok=True);path.write_text(buf.getvalue(),encoding='utf-8',newline='\n')


def collect(root=BASE/'ecology',verify=False):
    rows=[]
    for model in ('baseline','corrected'):
        expected=dict(EXPECTED)
        if model=='corrected':expected['horizons']=48
        for group,n in expected.items():
            base=root/model/group
            raw=read(base/'diagnosis.csv');summary={r['run']:r for r in read(base/'summary.csv')}
            assert len(raw)==n and len(summary)==n,(model,group,len(raw))
            archive=json.loads((base/'archive.json').read_text())
            if verify:
                for name,record in archive.items():
                    if 'archive' in record:assert digest(base/record['archive'])==record['archive_sha256'],(group,name)
            for r in raw:
                s=summary[r['run']]
                assert r['status']=='complete' and r['observed_days']==r['days'],(model,group,r['run'],'censored outcome requires separate analysis')
                assert s['exact_continuation']=='1'
                assert r['final_population']==s['alive']
                assert int(r['final_alive'])==int(r['queen_alive'])
                assert int(s['events'])*159==archive[r['run']+'/events.bin']['bytes']
                assert int(r['final_body_energy_nj'])==1500000000+int(r['final_absorbed_carbs_ug'])*1000000-int(r['final_basal_cost_nj'])-int(r['final_egg_energy_nj'])-int(r['final_reproductive_dissipation_nj'])
                row=dict(model=model,matrix=group,**r)
                row.update(events=s['events'],geometry_edits=s['geometry_edits'],advance_ms=s['advance_ms'],state_hash=s['state_hash'],trace_hash=s['trace_hash'],durable_checked=s['durable_checked'])
                rows.append(row)
    return rows


def analyze(rows):
    grouped=defaultdict(list)
    for r in rows:grouped[(r['model'],r['matrix'],r['workers'],r['supply'],r['cyclic'],r['arm'])].append(r)
    stats=[];survival=[];pairs=[]
    for key,group in sorted(grouped.items()):
        common=dict(zip(('model','matrix','workers','supply','cyclic','arm'),key))
        assert len(group)==6 and {r['seed'] for r in group}==set(map(str,range(1,7)))
        survived=sum(int(r['queen_alive']) for r in group);lo,hi=wilson(survived,6)
        result=dict(**common,n=6,survived=survived,survival_wilson_low=lo,survival_wilson_high=hi)
        result['sustained_180_count']=sum(int(r['positive']) and int(r['queen_alive']) and int(r['late_births_120_180'])>0 and int(r['emerged'])>0 for r in group)
        for metric in METRICS:
            mean,lo,hi=interval([float(r[metric]) for r in group])
            result.update({metric+'_mean':mean,metric+'_ci_low':lo,metric+'_ci_high':hi})
        stats.append(result)
        times=sorted({0.,float(group[0]['days'])}|{float(r['queen_lifetime_days']) for r in group if r['queen_alive']=='0'})
        for t in times:
            alive=sum(r['queen_alive']=='1' or float(r['queen_lifetime_days'])>t for r in group)
            survival.append(dict(**common,day=t,at_risk_or_alive=alive,survival_fraction=alive/6))
        if common['model']=='corrected' and common['matrix']!='horizons':
            baseline={r['seed']:r for r in grouped[('baseline',*key[1:])]}
            for metric in ('queen_alive',*METRICS):
                changes=[float(r[metric])-float(baseline[r['seed']][metric]) for r in group]
                mean,lo,hi=interval(changes)
                pairs.append(dict(**{k:v for k,v in common.items() if k!='model'},metric=metric,n=6,paired_mean_change=mean,ci_low=lo,ci_high=hi,seed_changes=';'.join(str(v) for v in changes)))
    return stats,survival,pairs


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');args=p.parse_args()
    rows=collect(verify=args.check);stats,survival,pairs=analyze(rows)
    emit(ROOT/'S6_3_1_EXPERIMENTS.csv',rows,args.check)
    for name,result in [('conditions',stats),('survival',survival),('paired_changes',pairs)]:emit(BASE/'analysis'/f'{name}.csv',result,args.check)
    print('PASS',len(rows),'complete frozen worlds;',sum(int(r['verified_observations']) for r in rows),'exact observer accounts;',sum(int(r['durable_checked']) for r in rows),'SQLite checks')


if __name__=='__main__':main()
