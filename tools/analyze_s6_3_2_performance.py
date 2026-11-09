"""Analyze complete or incomplete frozen batches without silently declaring PASS."""
import argparse
import json
import random
import statistics as st
from collections import defaultdict
from pathlib import Path
from analyze_s6_3_1 import read,emit,quantile

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'experiments/s6_3_2'
def describe(values):
    return dict(n=len(values),p50=st.median(values),p95=quantile(values,.95),p99=quantile(values,.99),minimum=min(values),maximum=max(values))
def uncertainty(rows,phase):
    sessions=sorted({r['session'] for r in rows});blocks={(s,b):[r for r in rows if r['session']==s and int(r['block'])==b] for s in sessions for b in range(1,13)}
    pairs={key:st.median(float(r[phase+'_ms']) for r in v if r['population']=='2048')/st.median(float(r[phase+'_ms']) for r in v if r['population']=='512') for key,v in blocks.items()}
    rng=random.Random(63201);pooled=[];paired=[]
    for _ in range(4096):
        selected=[(s,b) for s in rng.choices(sessions,k=len(sessions)) for b in rng.choices(range(1,13),k=12)]
        sample=[r for key in selected for r in blocks[key]]
        pooled.append(st.median(float(r[phase+'_ms']) for r in sample if r['population']=='2048')/st.median(float(r[phase+'_ms']) for r in sample if r['population']=='512'))
        paired.append(st.median(pairs[key] for key in selected))
    return dict(pooled_ci_low=quantile(pooled,.025),pooled_ci_high=quantile(pooled,.975),paired_median=st.median(pairs.values()),paired_ci_low=quantile(paired,.025),paired_ci_high=quantile(paired,.975)),pairs
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    admissions=[];latency=[];growth=[];work=[];telemetry=[];ratios=[];cpu=[];statuses=[]
    for kind in ('contacts','births'):
        base=BASE/'performance'/kind
        if not base.exists():continue
        conf=json.loads((base/'configuration.json').read_text());birth=kind=='births';allrows=[];phases=[];completed=[]
        filename='births.csv' if birth else 'contacts.csv';phase_names=('setup','birth_advance' if birth else 'advance','encode','restore')
        baseline=ROOT/'experiments/s6_3_1/performance'/('births-reserve' if birth else 'contacts')/'session1'/filename
        keys=('events','pending','checkpoint_bytes','state_hash','trace_hash')+(() if birth else ('decisions','candidates','bucket_queries','tree_visits','maximum_candidates'))
        identity={(r['layout'],r['population']):tuple(r[k] for k in keys) for r in read(baseline)}
        for folder in sorted(base.glob('session*')):
            for path in sorted(folder.glob('admission*_receipt.json')):
                a=json.loads(path.read_text());records=read(folder/path.name.replace('_receipt.json','.csv'))
                admissions.append(dict(kind=kind,session=folder.name,attempt=a['attempt'],admitted=a['admitted'],started_utc_ns=a['started_utc_ns'],ended_utc_ns=a['ended_utc_ns'],invalid_core_samples=sum(r['processor_busy_pct']=='' for r in records),invalid_statuses=';'.join(sorted({r['processor_busy_pct_status'] for r in records if not r['processor_busy_pct']})),**a['checks']))
            if not (folder/'receipt.json').exists():continue
            receipt=json.loads((folder/'receipt.json').read_text());assert receipt['exit_code']==0
            a=json.loads((folder/f"admission{receipt['admission_attempt']}_receipt.json").read_text());assert a['admitted']
            assert receipt['binary_sha256']==conf['binary_sha256']
            rows=read(folder/filename);plan=read(folder/'schedule.csv');assert len(rows)==len(plan)==receipt['rows']
            for r,s in zip(rows,plan):
                assert all(r[k]==v for k,v in s.items())
                assert r['exact_restore' if birth else 'continuation_equal']=='1'
                if birth:assert r['mass_balanced']==r['energy_balanced']=='1' and r['births']==r['population']
                assert tuple(r[k] for k in keys)==identity[r['layout'],r['population']],'S6.3.1 workload changed'
            allrows.extend(rows);completed.append(folder.name)
            for r in read(folder/'phases.csv'):
                item=rows[int(r['sample'])];assert r['start_processor']==r['end_processor']==str(conf['selected_logical'])
                if r['phase']=='checkpoint':r['phase']='encode'
                phases.append(dict(session=item['session'],layout=item['layout'],population=item['population'],warmup=item['warmup'],**r))
            os=read(folder/'telemetry.csv');hw=read(folder/'hwinfo.csv')
            telemetry.append(dict(kind=kind,session=folder.name,os_samples=len(os),invalid_core_samples=sum(not r['processor_busy_pct'] for r in os),system_busy_p50=st.median(float(r['system_busy_pct']) for r in os if r['system_busy_pct']),system_busy_p95=quantile([float(r['system_busy_pct']) for r in os if r['system_busy_pct']],.95),temperature_min_c=min(float(r['package_temperature_c']) for r in hw),temperature_max_c=max(float(r['package_temperature_c']) for r in hw),power_min_w=min(float(r['package_power_w']) for r in hw),power_max_w=max(float(r['package_power_w']) for r in hw),p0_effective_mhz_p50=st.median(float(r['p0_t0_effective_clock_mhz']) for r in hw),thermal_flag_max=max(float(r['package_thermal_throttling']) for r in hw),power_limit_flag_max=max(float(r['package_power_limit']) for r in hw),maximum_sensor_gap_s=max((int(b['utc_ns'])-int(a['utc_ns']))/1e9 for a,b in zip(hw,hw[1:]))))
        statuses.append(dict(kind=kind,completed_sessions=len(completed),required_sessions=3,raw_rows=len(allrows),required_rows=168 if birth else 336,status='COMPLETE' if len(completed)==3 else 'NOT_QUALIFIED_INCOMPLETE'))
        if not allrows:continue
        measured=[r for r in allrows if r['warmup']=='0']
        for layout in ('dense',) if birth else ('dense','dispersed'):
            for population in ('128','512','2048'):
                chosen=[r for r in measured if r['layout']==layout and r['population']==population]
                for phase in phase_names:
                    for session in ['pooled',*sorted({r['session'] for r in chosen})]:
                        sample=[float(r[phase+'_ms']) for r in chosen if session=='pooled' or r['session']==session]
                        latency.append(dict(kind=kind,layout=layout,population=population,phase=phase,session=session,**describe(sample)))
                    ps=[r for r in phases if r['warmup']=='0' and r['layout']==layout and r['population']==population and r['phase']==phase]
                    cpu.append(dict(kind=kind,layout=layout,population=population,phase=phase,cpu_ms_p50=st.median(float(r['cpu_ms']) for r in ps),cycles_p50=st.median(int(r['cycles']) for r in ps),cpu_wall_fraction=sum(float(r['cpu_ms']) for r in ps)/sum(float(r['wall_ms']) for r in ps)))
                for metric in (*(key for key in keys if not key.endswith('_hash')),* (('rss_bytes','process_peak_bytes','births') if birth else ('resident_bytes','peak_resident_bytes'))):
                    work.append(dict(kind=kind,layout=layout,population=population,metric=metric,**describe([int(r[metric]) for r in chosen])))
            for phase in phase_names:
                rows=[r for r in measured if r['layout']==layout and r['population']!='128'];ci,pairs=uncertainty(rows,phase)
                ratio=st.median(float(r[phase+'_ms']) for r in rows if r['population']=='2048')/st.median(float(r[phase+'_ms']) for r in rows if r['population']=='512')
                primary=layout=='dense' and phase in ('advance','birth_advance')
                status='DESCRIPTIVE' if not primary else 'INCOMPLETE_NO_VERDICT' if len(completed)!=3 else 'PASS' if ratio<=6 else 'FAIL'
                growth.append(dict(kind=kind,layout=layout,phase=phase,ratio_of_p50=ratio,**ci,status=status,target=6 if primary else ''))
                ratios.extend(dict(kind=kind,layout=layout,phase=phase,session=s,block=b,ratio=value) for (s,b),value in pairs.items())
    for name,rows in [('admissions',admissions),('status',statuses),('latency',latency),('growth',growth),('work',work),('telemetry',telemetry),('paired_ratios',ratios),('cpu_cycles',cpu)]:
        if rows:emit(BASE/'performance_analysis'/f'{name}.csv',rows,args.check)
    print(json.dumps(statuses));print(json.dumps([r for r in growth if r['layout']=='dense' and r['phase'] in ('advance','birth_advance')]))
if __name__=='__main__':main()
