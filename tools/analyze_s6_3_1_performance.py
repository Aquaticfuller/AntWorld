"""Describe frozen S6.3.1 regression timings without changing TD-01's target."""
import argparse
import json
import statistics as st
import random
from collections import defaultdict
from pathlib import Path
from analyze_s6_3 import read
from analyze_s6_3_performance import describe,paired_interval
from analyze_s6_3_1 import BASE,emit
from analyze_s6_3_1 import quantile


def pooled_ratio_interval(measured,layout,phase):
    blocks={(s,b):[r for r in measured if r['population']!='128' and r['layout']==layout and int(r['session'])==s and int(r['block'])==b] for s in range(1,4) for b in range(1,13)}
    rng=random.Random(63101);values=[]
    for _ in range(4096):
        sizes={'512':[],'2048':[]}
        for s in rng.choices((1,2,3),k=3):
            for b in rng.choices(range(1,13),k=12):
                for r in blocks[s,b]:sizes[r['population']].append(float(r[phase+'_ms']))
        values.append(st.median(sizes['2048'])/st.median(sizes['512']))
    return quantile(values,.025),quantile(values,.975)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');args=p.parse_args()
    latency=[];growth=[];work=[];sensors=[];ratios=[];cpu=[];cycle_growth=[]
    for name in ('contacts','births-reserve'):
        base=BASE/'performance'/name;conf=json.loads((base/'configuration.json').read_text())
        assert conf['before']['power_plan']==conf['after']['power_plan']
        birth=name.startswith('birth');allrows=[];identity={};phase_records=[]
        phases=('setup','birth_advance' if birth else 'advance','encode','restore')
        for folder in sorted(base.glob('session*')):
            receipt=json.loads((folder/'receipt.json').read_text());assert receipt['exit_code']==0
            rows=read(folder/('births.csv' if birth else 'contacts.csv'));plan=read(folder/'schedule.csv')
            assert len(rows)==len(plan)==receipt['rows']
            for r,s in zip(rows,plan):
                assert all(r[k]==v for k,v in s.items())
                assert r['exact_restore' if birth else 'continuation_equal']=='1'
                if birth:assert r['mass_balanced']==r['energy_balanced']=='1' and int(r['births'])==int(r['population'])
                keys=('events','pending','checkpoint_bytes','state_hash','trace_hash')+(() if birth else ('decisions','candidates','bucket_queries','tree_visits','maximum_candidates'))
                record=tuple(r[k] for k in keys);key=(r['layout'],r['population'])
                assert identity.setdefault(key,record)==record,'work or decisions varied across repetitions'
                allrows.append(r)
            for phase in read(folder/'phases.csv'):
                row=rows[int(phase['sample'])]
                assert phase['start_processor']==phase['end_processor']==str(conf['selected_logical'])
                if phase['phase']=='checkpoint':phase['phase']='encode'
                phase_records.append(dict(session=folder.name,layout=row['layout'],population=row['population'],warmup=row['warmup'],block=row['block'],**phase))
            telemetry=read(folder/'telemetry.csv');sensor=dict(batch=name,session=folder.name,os_samples=len(telemetry),hwinfo_samples=0,maximum_hwinfo_gap_s='',temperature_min_c='',temperature_max_c='',power_min_w='',power_max_w='',thermal_flag_max='')
            sensor.update(system_busy_p50=st.median(float(r['system_busy_pct']) for r in telemetry if r['system_busy_pct']),ac_values=';'.join(sorted({r['ac'] for r in telemetry})),saver_values=';'.join(sorted({r['battery_saver'] for r in telemetry})))
            if (folder/'hwinfo.csv').exists():
                hw=read(folder/'hwinfo.csv');times=[int(r['utc_ns']) for r in hw]
                if hw:
                    sensor.update(hwinfo_samples=len(hw),maximum_hwinfo_gap_s=max((b-a for a,b in zip(times,times[1:])),default=0)/1e9,temperature_min_c=min(float(r['package_temperature_c']) for r in hw),temperature_max_c=max(float(r['package_temperature_c']) for r in hw),power_min_w=min(float(r['package_power_w']) for r in hw),power_max_w=max(float(r['package_power_w']) for r in hw),thermal_flag_max=max(float(r['package_thermal_throttling']) for r in hw))
            sensors.append(sensor)
        measured=[r for r in allrows if r['warmup']=='0']
        if not birth:
            old=read(BASE.parent/'s6_3/performance/contacts-final/session1/contacts.csv')
            for r in old:
                keys=('events','pending','checkpoint_bytes','state_hash','trace_hash','decisions','candidates','bucket_queries','tree_visits','maximum_candidates')
                assert tuple(r[k] for k in keys)==identity[(r['layout'],r['population'])],'legacy workload changed'
        for layout in ('dense',) if birth else ('dense','dispersed'):
            for population in ('128','512','2048'):
                rows=[r for r in measured if r['layout']==layout and r['population']==population]
                for session in ('pooled','1','2','3'):
                    selected=rows if session=='pooled' else [r for r in rows if r['session']==session]
                    for phase in phases:latency.append(dict(batch=name,layout=layout,session=session,population=population,phase=phase,**describe([float(r[phase+'_ms']) for r in selected])))
                for phase in phases:
                    selected=[r for r in phase_records if r['warmup']=='0' and r['layout']==layout and r['population']==population and r['phase']==phase]
                    cpu.append(dict(batch=name,layout=layout,population=population,phase=phase,n=len(selected),cpu_ms_p50=st.median(float(r['cpu_ms']) for r in selected),cpu_ms_mean=st.mean(float(r['cpu_ms']) for r in selected),cycles_p50=st.median(int(r['cycles']) for r in selected),cpu_wall_fraction=sum(float(r['cpu_ms']) for r in selected)/sum(float(r['wall_ms']) for r in selected),zero_cpu_samples=sum(float(r['cpu_ms'])==0 for r in selected)))
                for metric in ('events','pending','checkpoint_bytes',* (('rss_bytes','process_peak_bytes','births') if birth else ('resident_bytes','peak_resident_bytes','decisions','candidates','tree_visits'))):
                    work.append(dict(batch=name,layout=layout,population=population,metric=metric,**describe([int(r[metric]) for r in rows])))
            for phase in phases:
                blocks=defaultdict(list)
                for session in range(1,4):
                    for block in range(1,13):
                        rows=[r for r in measured if r['layout']==layout and int(r['session'])==session and int(r['block'])==block]
                        a,b=[st.median(float(r[phase+'_ms']) for r in rows if r['population']==n) for n in ('512','2048')]
                        blocks[session].append(b/a);ratios.append(dict(batch=name,layout=layout,phase=phase,session=session,block=block,ratio=b/a))
                a,b=[st.median(float(r[phase+'_ms']) for r in measured if r['layout']==layout and r['population']==n) for n in ('512','2048')]
                lo,hi=pooled_ratio_interval(measured,layout,phase)
                growth.append(dict(batch=name,layout=layout,phase=phase,ratio_of_p50=b/a,p50_ratio_ci_low=lo,p50_ratio_ci_high=hi,**paired_interval(blocks)))
                cycle_blocks=defaultdict(list)
                for session in range(1,4):
                    for block in range(1,13):
                        selected=[r for r in phase_records if r['warmup']=='0' and r['layout']==layout and r['session']==f'session{session}' and int(r['block'])==block and r['phase']==phase]
                        a,b=[st.median(int(r['cycles']) for r in selected if r['population']==n) for n in ('512','2048')]
                        cycle_blocks[session].append(b/a)
                cycle_growth.append(dict(batch=name,layout=layout,phase=phase,**paired_interval(cycle_blocks)))
    for name,rows in [('latency',latency),('growth',growth),('work',work),('telemetry',sensors),('paired_ratios',ratios),('cpu_and_cycles',cpu),('paired_cycle_growth',cycle_growth)]:emit(BASE/'performance_analysis'/f'{name}.csv',rows,args.check)
    dense=next(r for r in growth if r['batch']=='contacts' and r['layout']=='dense' and r['phase']=='advance')
    print('TD-01 measured ratio',dense['ratio_of_p50'],'paired',dense['paired_median'],'95% CI',dense['ci_low'],dense['ci_high'],'target <=6; report does not change the target')


if __name__=='__main__':main()
