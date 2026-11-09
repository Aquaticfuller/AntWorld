"""Verify the frozen Windows batch, retaining incomplete admissions and timed rows."""
import argparse
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import statistics as st

from analyze_s6_3_2_performance import describe, uncertainty
ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'experiments/s6_3_3_1/performance'
BASELINE = ROOT/'experiments/s6_3_1/performance'
SENSORS = ('package_temperature_c', 'package_power_w', 'p0_t0_effective_clock_mhz')


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def read(path):
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rt', newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def emit(path, rows, check):
    import io
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, list(rows[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    encoded = stream.getvalue().encode()
    if check:
        assert path.read_bytes() == encoded, path.name
    else:
        path.write_bytes(encoded)


def finite(value):
    try:
        return math.isfinite(float(value))
    except (ValueError, TypeError):
        return False


def telemetry(folder, receipt):
    path = folder/'telemetry.csv.gz'
    if not path.exists():
        return {}, False
    with gzip.open(path, 'rb') as f:
        assert hashlib.sha256(f.read()).hexdigest() == receipt['telemetry_uncompressed_sha256']
    os = read(path)
    assert len(os) == receipt['telemetry_rows']
    counts = dict(os_samples=len(os), native_invalid=sum(r['nonidle_wall_all_valid'] != 'True' for r in os),
                  missing_process_time=sum(not finite(r['benchmark_cpu_ns']) for r in os))
    pdh = next(key for key in os[0] if key.startswith('pdh') and key.endswith('_processor_busy_pct')) if os else ''
    if pdh:
        counts['pdh_invalid'] = sum(not finite(r[pdh]) for r in os)
    def stats(name, rows, field):
        values = [float(r[field]) for r in rows if finite(r.get(field))]
        if values:
            counts.update({name+'_'+k:v for k,v in describe(values).items()})
    stats('collector_ns', os, 'collector_ns')
    stats('system_pct', os, 'system_busy_pct')
    stats('selected_pct', os, 'processor_busy_pct')
    stats('sample_delta_ms', [dict(interval=int(b['monotonic_ns'])/1e6-int(a['monotonic_ns'])/1e6)
                             for a,b in zip(os,os[1:])], 'interval')
    path = folder/'hwinfo.csv'
    hw = read(path) if path.exists() else []
    if hw:
        provenance = load(folder/'hwinfo_provenance.json')
        assert provenance['source_prefix_sha256'] == receipt['hwinfo_after_sha256']
        assert provenance['retained_rows'] == len(hw)
    times = [int(r['utc_ns']) for r in hw]
    gaps = [(b-a)/1e9 for a,b in zip(times,times[1:])]
    counts.update(sensor_rows=len(hw), maximum_sensor_gap_s=max(gaps, default=''),
                  bracketed=bool(times and times[0] <= receipt['started_utc_ns'] <=
                                 receipt['ended_utc_ns'] <= times[-1]),
                  saver_intervals=sum(r['battery_saver'] != '0' for r in os),
                  off_ac_intervals=sum(r['ac'] != '1' for r in os),
                  thermal_flags=sum(r['package_thermal_throttling'] == '1' for r in hw),
                  power_limit_flags=sum(r['package_power_limit'] == '1' for r in hw))
    for key in SENSORS:
        stats(key, hw, key)
    return counts, (len(os) > 1 and counts['bracketed'] and all(0 < g <= 10 for g in gaps) and
                    all(finite(row[k]) for row in hw for k in SENSORS) and
                    all(counts.get(key+'_n', 0) > 0 for key in ('system_pct', 'selected_pct', 'collector_ns')) and
                    counts['missing_process_time'] < len(os) and not receipt['collector_error'] and
                    not receipt.get('sensor_error'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw', type=Path, default=BASE)
    parser.add_argument('--out', type=Path, default=BASE/'analysis')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    raw = args.raw
    freeze = load(raw/'freeze.json')
    confirmation = ROOT/freeze['confirmation'] if 'confirmation' in freeze else raw/'instrument_v2_confirmation/receipt.json'
    assert digest(confirmation) == freeze['confirmation_sha256']
    assert load(raw/'batch_start.json')['freeze_sha256'] == digest(raw/'freeze.json')
    batch = load(raw/'batch_result.json')
    assert batch['started_utc_ns'] > freeze['created_utc_ns']
    tables = {key: [] for key in ('admissions', 'sessions', 'latency', 'growth', 'paired_ratios',
                                  'work', 'telemetry', 'cpu_cycles', 'profile', 'status', 'workload_mismatches')}
    for kind in freeze['executables']:
        birth = kind == 'births'
        filename = kind+'.csv'
        frozen = freeze['executables'][kind]
        base = raw/kind
        conf = load(base/'configuration.json') if (base/'configuration.json').exists() else {}
        if conf:
            assert conf['binary_sha256'] == frozen['sha256'] and conf['source_commit'] == freeze['source_commit']
        keys = ('events', 'pending', 'checkpoint_bytes', 'state_hash', 'trace_hash')
        reserved = frozen['name'] == 'antworld_s6_3_1_birth_benchmark.exe'
        if birth:
            keys += ('births','exact_restore','mass_balanced','energy_balanced')
        else:
            keys += ('decisions', 'candidates', 'bucket_queries', 'tree_visits', 'maximum_candidates')
        historical = read(BASELINE/('births-reserve' if birth else 'contacts')/'session1'/filename)
        identities = {(r['layout'],r['population']):tuple(r[k] for k in keys) for r in historical}
        assert all(tuple(r[k] for k in keys) == identities[r['layout'],r['population']] for r in historical)
        allrows, phases, profiles, complete = [], [], [], []
        native_rows = 0
        all_work_identical = True
        for number in (1,2,3):
            label = f'session{number}'
            folder = base/label
            plan_file = folder/'schedule.csv'
            assert digest(plan_file) == frozen['schedule_sha256'][label]
            plan = read(plan_file)
            assert len(plan) == (56 if birth else 112) and all(r['session'] == str(number) for r in plan)
            attempts = []
            for path in sorted(folder.glob('admission*_receipt.json')):
                receipt = load(path)
                assert receipt['attempt'] == len(attempts)+1
                if attempts:
                    assert not attempts[-1]['admitted'] and receipt['started_utc_ns']-attempts[-1]['ended_utc_ns'] >= 300*10**9
                rows = read(folder/path.name.replace('_receipt.json','.csv'))
                assert len(rows) == 60
                checks = receipt['checks']
                admitted = all(checks[k] for k in ('power_valid','sensors_valid','native_intervals_valid')) and all(
                    checks[k+'_complete'] and checks[k+'_p50'] <= 10 and checks[k+'_p95'] <= 20
                    for k in ('system_busy_pct','processor_busy_pct'))
                assert receipt['admitted'] == admitted
                tables['admissions'].append(dict(kind=kind,session=label,attempt=receipt['attempt'],admitted=admitted,
                                                 pdh_invalid=sum(not r[f"pdh{conf['selected_logical']}_processor_busy_pct"] for r in rows),
                                                 **checks))
                attempts.append(receipt)
            assert len(attempts) <= 3
            rows_path = folder/filename
            rows = read(rows_path) if rows_path.exists() else []
            native_rows += len(rows)
            assert len(rows) <= len(plan)
            work_identical = not birth or reserved
            for r,s in zip(rows,plan):
                assert all(r[k] == v for k,v in s.items())
                assert r['exact_restore' if birth else 'continuation_equal'] == '1'
                if birth:
                    assert r['mass_balanced'] == r['energy_balanced'] == '1' and r['births'] == r['population']
                historical = dict(zip(keys,identities[r['layout'],r['population']]))
                for key in keys:
                    if r[key] != historical[key]:
                        work_identical = False
                        tables['workload_mismatches'].append(dict(kind=kind,session=label,sample=r['sample'],layout=r['layout'],
                            population=r['population'],metric=key,measured=r[key],required=historical[key]))
            all_work_identical = all_work_identical and work_identical
            receipt_path = folder/'receipt.json'
            receipt = load(receipt_path) if receipt_path.exists() else None
            if receipt:
                assert attempts and attempts[-1]['admitted'] and receipt['admission_attempt'] == attempts[-1]['attempt']
                assert receipt['binary_sha256'] == frozen['sha256'] and receipt['rows'] == len(plan)
            if (folder/'phases.csv').exists():
                for row in read(folder/'phases.csv'):
                    item = plan[int(row['sample'])]
                    assert row['start_processor'] == row['end_processor'] == str(conf['selected_logical'])
                    if row['phase'] == 'checkpoint':
                        row['phase'] = 'encode'
                    phases.append(dict(session=item['session'],layout=item['layout'],population=item['population'],warmup=item['warmup'],**row))
            if (folder/'profile.csv').exists():
                for row in read(folder/'profile.csv'):
                    item = plan[int(row['sample'])]
                    profiles.append(dict(session=item['session'],layout=item['layout'],population=item['population'],warmup=item['warmup'],**row))
            observed, qualified = telemetry(folder,receipt) if receipt else ({},False)
            qualified = qualified and receipt['exit_code'] == 0 and len(rows) == len(plan) and work_identical
            if len(rows) == len(plan):
                allrows.extend(rows)
            if qualified:
                complete.append(label)
            if observed:
                tables['telemetry'].append(dict(kind=kind,session=label,**observed))
            tables['sessions'].append(dict(kind=kind,session=label,admission_attempts=len(attempts),
                                           measured_rows=len(rows),planned_rows=len(plan),qualified=qualified,
                                           historical_workload_match=work_identical,native_exit=receipt['exit_code'] if receipt else ''))
        verdict = 'INCONCLUSIVE' if all_work_identical else 'WORKLOAD_MISMATCH'
        measured = [r for r in allrows if r['warmup'] == '0']
        for layout in (('dense',) if birth else ('dense','dispersed')):
            layout_rows = [r for r in measured if r['layout'] == layout]
            if not layout_rows:
                continue
            phase_names = ('setup','birth_advance' if birth else 'advance','encode','restore')
            for population in ('128','512','2048'):
                selected = [r for r in layout_rows if r['population'] == population]
                for phase in phase_names:
                    for session in ('pooled',*sorted({r['session'] for r in selected})):
                        times = [float(r[phase+'_ms']) for r in selected if session == 'pooled' or r['session'] == session]
                        tables['latency'].append(dict(kind=kind,layout=layout,population=population,
                                                      phase=phase,session=session,**describe(times)))
                    ps = [r for r in phases if r['warmup'] == '0' and r['layout'] == layout and
                          r['population'] == population and r['phase'] == phase]
                    if ps:
                        tables['cpu_cycles'].append(dict(kind=kind,layout=layout,population=population,phase=phase,
                            cpu_ms_p50=st.median(float(r['cpu_ms']) for r in ps),
                            cycles_p50=st.median(int(r['cycles']) for r in ps),
                            cpu_wall_fraction=sum(float(r['cpu_ms']) for r in ps)/sum(float(r['wall_ms']) for r in ps)))
                memory = ('rss_bytes','process_peak_bytes','births') if birth else ('resident_bytes','peak_resident_bytes')
                for metric in dict.fromkeys((*(k for k in keys if not k.endswith('_hash')),*memory)):
                    tables['work'].append(dict(kind=kind,layout=layout,population=population,metric=metric,
                                               **describe([int(r[metric]) for r in selected])))
            for phase in phase_names:
                rows = [r for r in layout_rows if r['population'] != '128']
                ci,pairs = uncertainty(rows,phase)
                ratio = st.median(float(r[phase+'_ms']) for r in rows if r['population'] == '2048')/st.median(
                    float(r[phase+'_ms']) for r in rows if r['population'] == '512')
                primary = layout == 'dense' and phase in ('advance','birth_advance')
                if primary and len(complete) == 3:
                    verdict = 'PASS' if ratio <= 6 else 'FAIL'
                tables['growth'].append(dict(kind=kind,layout=layout,phase=phase,ratio_of_p50=ratio,**ci,
                                             status=verdict if primary else 'DESCRIPTIVE',target=6 if primary else ''))
                tables['paired_ratios'].extend(dict(kind=kind,layout=layout,phase=phase,session=s,block=b,ratio=v)
                                               for (s,b),v in pairs.items())
        groups = {}
        for row in profiles:
            if row['warmup'] == '0':
                key = (row['layout'],row['population'],row['phase'],row['category'])
                groups.setdefault(key,[]).append(row)
        for (layout,population,phase,category),rows in sorted(groups.items()):
            tables['profile'].append(dict(kind=kind,layout=layout,population=population,phase=phase,category=category,
                n=len(rows),calls_p50=st.median(int(r['calls']) for r in rows),
                inclusive_ns_p50=st.median(int(r['inclusive_ns']) for r in rows),
                exclusive_ns_p50=st.median(int(r['exclusive_ns']) for r in rows)))
        tables['status'].append(dict(kind=kind,status=verdict,qualified_sessions=len(complete),required_sessions=3,
                                     raw_rows=native_rows,planned_rows=168 if birth else 336,batch=batch['outcome']))
    if not args.check:
        args.out.mkdir(parents=True,exist_ok=True)
    for name,rows in tables.items():
        if rows:
            # Additional telemetry fields on a partial session are represented by blanks.
            columns = dict.fromkeys(k for row in rows for k in row)
            emit(args.out/(name+'.csv'), [{k:row.get(k,'') for k in columns} for row in rows], args.check)
    print(json.dumps(tables['status']))
    print(json.dumps([r for r in tables['growth'] if r['target']]))


if __name__ == '__main__':
    main()
