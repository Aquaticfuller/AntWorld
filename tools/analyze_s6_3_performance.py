"""Report all frozen ABBA samples, workload equality and hierarchical uncertainty."""
import argparse
import json
import random
import statistics as st
from collections import defaultdict
from pathlib import Path
from analyze_s6_3 import ROOT, emit, read, quantile


def describe(values):
    return dict(n=len(values), p50=st.median(values), p95=quantile(values,.95), p99=quantile(values,.99),
                minimum=min(values), maximum=max(values))


def paired_interval(blocks):
    assert set(blocks) == {1,2,3} and all(len(x)==12 for x in blocks.values())
    rng = random.Random(6303)
    estimates = [st.median([rng.choice(blocks[s]) for s in rng.choices([1,2,3], k=3) for _ in range(12)])
                 for _ in range(4096)]
    return dict(paired_median=st.median([v for values in blocks.values() for v in values]),
                ci_low=quantile(estimates,.025), ci_high=quantile(estimates,.975))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=ROOT/'experiments/s6_3/performance')
    p.add_argument('--out', type=Path, default=ROOT/'experiments/s6_3/performance_analysis')
    p.add_argument('--check', action='store_true')
    args = p.parse_args()
    names = ('contacts-baseline-final','contacts-final','birth-before-index','birth-after-index')
    data, latency, ratios, growth, memory, sensors, phase_cpu = [], [], [], [], [], [], []
    evidence = {}
    for name in names:
        base = args.root/name
        conf = json.loads((base/'configuration.json').read_text())
        assert conf['affinity_mask'] == 1
        assert conf['before']['power_plan'] == conf['after']['power_plan']
        birth = name.startswith('birth')
        layouts = ('dense',) if birth else ('dense','dispersed')
        phases = ('setup','birth_advance' if birth else 'advance','encode','restore')
        allrows = []
        for folder in sorted(base.glob('session*')):
            receipt = json.loads((folder/'receipt.json').read_text())
            assert receipt['exit_code'] == 0 and receipt['binary_sha256'] == conf['binary_sha256']
            rows, schedule = read(folder/('births.csv' if birth else 'contacts.csv')), read(folder/'schedule.csv')
            assert len(rows) == len(schedule) == receipt['rows']
            for row, planned in zip(rows,schedule):
                assert all(row[k] == v for k,v in planned.items())
                assert row['exact_restore' if birth else 'continuation_equal'] == '1'
                if birth:
                    assert row['mass_balanced'] == row['energy_balanced'] == '1'
                key = (birth,row['layout'],row['population'])
                fields = ('events','pending','checkpoint_bytes','state_hash','trace_hash') if birth else (
                    'events','pending','checkpoint_bytes','state_hash','trace_hash','decisions','candidates','bucket_queries','tree_visits','maximum_candidates')
                record = tuple(row[k] for k in fields)
                assert evidence.setdefault(key,record) == record, (name,key,'work or state changed')
                allrows.append(row)
                data.append(dict(batch=name,**row))
            for phase in read(folder/'phases.csv'):
                assert phase['start_processor'] == phase['end_processor'] == '0'
                r = rows[int(phase['sample'])]
                column = 'encode_ms' if phase['phase']=='checkpoint' else phase['phase']+'_ms'
                assert float(phase['wall_ms']) == float(r[column])
                phase_cpu.append(dict(batch=name,session=r['session'],population=r['population'],layout=r['layout'],warmup=r['warmup'],**phase))
            hw, os = read(folder/'hwinfo.csv'), read(folder/'telemetry.csv')
            times = [int(x['utc_ns']) for x in hw]
            assert times
            row = dict(batch=name,session=int(folder.name[7:]), hwinfo_rows=len(hw), os_rows=len(os),
                       maximum_sensor_gap_s=max(b-a for a,b in zip(times,times[1:]))/1e9 if len(times)>1 else 0,
                       start_bracket_s=(times[0]-receipt['started_utc_ns'])/1e9,
                       end_bracket_s=(receipt['ended_utc_ns']-times[-1])/1e9,
                       ac_values=';'.join(sorted({x['ac'] for x in os})),
                       saver_values=';'.join(sorted({x['battery_saver'] for x in os})))
            for field in ('package_temperature_c','p0_temperature_c','package_power_w','p0_clock_mhz',
                          'p0_t0_effective_clock_mhz','p0_thermal_throttling','package_thermal_throttling','package_power_limit'):
                values = [float(x[field]) for x in hw if x[field] != '']
                row.update({field+'_'+stat:val for stat,val in describe(values).items() if stat in ('p50','minimum','maximum')})
            for field in ('system_busy_pct','collector_ns'):
                values = [float(x[field]) for x in os if x[field] != '']
                row.update({field+'_'+stat:val for stat,val in describe(values).items() if stat in ('p50','p99','maximum')})
            sensors.append(row)
        measured = [r for r in allrows if r['warmup']=='0']
        for layout in layouts:
            for session in ('1','2','3','pooled'):
                for population in ('128','512','2048'):
                    subset = [r for r in measured if r['layout']==layout and r['population']==population and (session=='pooled' or r['session']==session)]
                    key = dict(batch=name,layout=layout,session=session,population=int(population))
                    for phase in phases:
                        latency.append(dict(**key,phase=phase,**describe([float(r[phase+'_ms']) for r in subset])))
                    for metric in (('rss_bytes','process_peak_bytes') if birth else ('resident_bytes','peak_resident_bytes'))+('events','pending','checkpoint_bytes'):
                        memory.append(dict(**key,metric=metric,**describe([int(r[metric]) for r in subset])))
            for phase in phases:
                blocks = defaultdict(list)
                for session in ('1','2','3'):
                    for block in range(1,13):
                        subset = [r for r in measured if r['layout']==layout and r['session']==session and int(r['block'])==block]
                        a,b = [st.median([float(r[phase+'_ms']) for r in subset if r['population']==n]) for n in ('512','2048')]
                        value = b/a
                        blocks[int(session)].append(value)
                        ratios.append(dict(batch=name,layout=layout,phase=phase,session=session,block=block,ratio=value,small_ms=a,large_ms=b))
                a,b = [st.median([float(r[phase+'_ms']) for r in measured if r['layout']==layout and r['population']==n]) for n in ('512','2048')]
                growth.append(dict(batch=name,layout=layout,phase=phase,p50_growth=b/a,**paired_interval(blocks)))
    outputs = {'latency.csv':latency,'growth.csv':growth,'paired_raw.csv':ratios,'memory.csv':memory,
               'telemetry_summary.csv':sensors,'phase_cpu.csv':phase_cpu}
    report = dict(raw_rows=len(data),measured_rows=sum(r['warmup']=='0' for r in data),
                  exact_work_state_and_trace=True, fixed_affinity=True,
                  note='4096 session/block bootstrap resamples, seed 6303. Host sensor samples bracket sessions, not every millisecond phase. Process peak memory is a process-lifetime high water mark, including warmups.')
    if args.check:
        for name, rows in outputs.items():
            assert read(args.out/name) == [{k:str(v) for k,v in r.items()} for r in rows], name
        assert json.loads((args.out/'audit.json').read_text()) == report
    else:
        for name,rows in outputs.items():
            emit(args.out/name,rows)
        (args.out/'audit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
    for row in growth:
        if row['layout']=='dense' and row['phase'] in ('advance','birth_advance','setup'):
            print(row)


if __name__ == '__main__':
    main()
