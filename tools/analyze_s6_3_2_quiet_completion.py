"""Verify the predeclared quiet-interval extension without changing old evidence."""
import argparse
import hashlib
import json
import statistics as st
from pathlib import Path
from analyze_s6_3_1 import read, emit, quantile
from analyze_s6_3_2_performance import describe, uncertainty

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'experiments/s6_3_2'
OLD = BASE/'performance/births'
NEW = BASE/'performance_quiet_1/births'
OUT = BASE/'completion_analysis'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--check', action='store_true')
    args = p.parse_args()
    old_config = json.loads((OLD/'configuration.json').read_text())
    new_config = json.loads((NEW/'configuration.json').read_text())
    for key in ('binary_sha256', 'selected_logical', 'affinity_mask', 'observer_affinity_mask', 'runner_sha256', 'topology'):
        assert new_config[key] == old_config[key], key
    assert new_config['source_commit'].startswith('7badade'), 'addendum must precede new timing'
    assert not (OLD/'session1/receipt.json').exists() and not (OLD/'session1/births.csv').exists()
    old_failures = sorted((OLD/'session1').glob('admission*_receipt.json'))
    assert len(old_failures) == 3 and all(not json.loads(x.read_text())['admitted'] for x in old_failures)
    assert (NEW/'session1/schedule.csv').read_text() == (OLD/'session1/schedule.csv').read_text()
    keys = ('events', 'pending', 'checkpoint_bytes', 'state_hash', 'trace_hash')
    original = read(ROOT/'experiments/s6_3_1/performance/births-reserve/session1/births.csv')
    baseline = {r['population']: tuple(r[k] for k in keys) for r in original}
    allrows, phases, admissions, telemetry, sources = [], [], [], [], []
    selected = [NEW/'session1', OLD/'session2', OLD/'session3']
    for folder in selected:
        receipt = json.loads((folder/'receipt.json').read_text())
        assert receipt['exit_code'] == 0 and receipt['binary_sha256'] == old_config['binary_sha256']
        admission = json.loads((folder/f"admission{receipt['admission_attempt']}_receipt.json").read_text())
        samples = read(folder/f"admission{receipt['admission_attempt']}.csv")
        assert len(samples) == 60 and admission['admitted']
        for field in ('system_busy_pct', 'processor_busy_pct'):
            values = [float(r[field]) for r in samples]
            assert st.median(values) <= 10 and quantile(values, .95) <= 20
        assert all(r['processor_busy_pct_status'] in ('0', '1') and r['ac'] == '1' and r['battery_saver'] == '0'
                   and -2 <= float(r['sensor_age_s']) <= 10 and r['package_temperature_c'] and r['package_power_w'] for r in samples)
        assert receipt['started_utc_ns'] >= admission['ended_utc_ns']
        rows, plan = read(folder/'births.csv'), read(folder/'schedule.csv')
        assert len(rows) == len(plan) == receipt['rows'] == 56
        for row, scheduled in zip(rows, plan):
            assert all(row[k] == v for k, v in scheduled.items())
            assert row['session'] == folder.name[-1]
            assert row['births'] == row['population']
            assert row['exact_restore'] == row['mass_balanced'] == row['energy_balanced'] == '1'
            assert tuple(row[k] for k in keys) == baseline[row['population']]
        allrows.extend(rows)
        for phase in read(folder/'phases.csv'):
            row = rows[int(phase['sample'])]
            assert phase['start_processor'] == phase['end_processor'] == str(old_config['selected_logical'])
            if phase['phase'] == 'checkpoint':
                phase['phase'] = 'encode'
            phases.append(dict(session=row['session'], population=row['population'], warmup=row['warmup'], **phase))
        admissions.append(dict(session=folder.name, source=folder.relative_to(ROOT).as_posix(), **admission['checks']))
        os, hw = read(folder/'telemetry.csv'), read(folder/'hwinfo.csv')
        telemetry.append(dict(session=folder.name, os_samples=len(os), invalid_core_samples=sum(not r['processor_busy_pct'] for r in os),
                              system_busy_p50=st.median(float(r['system_busy_pct']) for r in os if r['system_busy_pct']),
                              system_busy_p95=quantile([float(r['system_busy_pct']) for r in os if r['system_busy_pct']], .95),
                              temperature_min_c=min(float(r['package_temperature_c']) for r in hw),
                              temperature_max_c=max(float(r['package_temperature_c']) for r in hw),
                              power_min_w=min(float(r['package_power_w']) for r in hw),
                              power_max_w=max(float(r['package_power_w']) for r in hw),
                              p0_effective_mhz_p50=st.median(float(r['p0_t0_effective_clock_mhz']) for r in hw),
                              thermal_flag_max=max(float(r['package_thermal_throttling']) for r in hw),
                              power_limit_flag_max=max(float(r['package_power_limit']) for r in hw),
                              maximum_sensor_gap_s=max((int(b['utc_ns'])-int(a['utc_ns']))/1e9 for a, b in zip(hw, hw[1:]))))
        for path in sorted(folder.iterdir()):
            if path.suffix in ('.csv', '.json', '.log'):
                data = path.read_bytes().replace(b'\r\n', b'\n')
                sources.append(dict(path=path.relative_to(ROOT).as_posix(), lf_bytes=len(data), lf_sha256=hashlib.sha256(data).hexdigest()))
    assert len(allrows) == 168
    measured = [r for r in allrows if r['warmup'] == '0']
    latency, growth, pairs, work, cpu = [], [], [], [], []
    for population in ('128', '512', '2048'):
        chosen = [r for r in measured if r['population'] == population]
        for phase in ('setup', 'birth_advance', 'encode', 'restore'):
            for session in ('pooled', '1', '2', '3'):
                values = [float(r[phase+'_ms']) for r in chosen if session == 'pooled' or r['session'] == session]
                latency.append(dict(population=population, phase=phase, session=session, **describe(values)))
            ps = [r for r in phases if r['warmup'] == '0' and r['population'] == population and r['phase'] == phase]
            cpu.append(dict(population=population, phase=phase, cpu_ms_p50=st.median(float(r['cpu_ms']) for r in ps),
                            cycles_p50=st.median(int(r['cycles']) for r in ps),
                            cpu_wall_fraction=sum(float(r['cpu_ms']) for r in ps)/sum(float(r['wall_ms']) for r in ps)))
        for metric in ('events', 'pending', 'checkpoint_bytes', 'rss_bytes', 'process_peak_bytes', 'births'):
            work.append(dict(population=population, metric=metric, **describe([int(r[metric]) for r in chosen])))
    rows = [r for r in measured if r['population'] != '128']
    for phase in ('setup', 'birth_advance', 'encode', 'restore'):
        ratio = st.median(float(r[phase+'_ms']) for r in rows if r['population'] == '2048')/st.median(float(r[phase+'_ms']) for r in rows if r['population'] == '512')
        interval, blocks = uncertainty(rows, phase)
        growth.append(dict(phase=phase, ratio_of_p50=ratio, **interval,
                           status=('PASS' if ratio <= 6 else 'FAIL') if phase == 'birth_advance' else 'DESCRIPTIVE',
                           target=6 if phase == 'birth_advance' else ''))
        pairs.extend(dict(phase=phase, session=session, block=block, ratio=value) for (session, block), value in blocks.items())
    diagnostic = read(BASE/'quiet_1_diagnostic/raw_counters.csv')
    assert len(diagnostic) == 60
    failed = [r for r in diagnostic if not r['processor_busy_pct']]
    diagnostics = [dict(samples=60, primary_invalid=len(failed), legacy_invalid=sum(not r['legacy_busy_pct'] for r in diagnostic),
                        coincident_invalid=sum(not r['legacy_busy_pct'] for r in failed),
                        primary_nonpositive_second_deltas=sum(int(r['processor_busy_pct_second_delta']) <= 0 for r in diagnostic),
                        failed_first_delta_exceeds_second=sum(int(r['processor_busy_pct_first_delta']) > int(r['processor_busy_pct_second_delta']) for r in failed),
                        system_busy_p50=st.median(float(r['system_busy_pct']) for r in diagnostic),
                        hwinfo_thread_usage_p50=st.median(float(r['p0_t0_usage_pct']) for r in diagnostic))]
    for path in [OLD/'configuration.json', NEW/'configuration.json', *sorted((BASE/'quiet_1_diagnostic').iterdir())]:
        data = path.read_bytes().replace(b'\r\n', b'\n')
        sources.append(dict(path=path.relative_to(ROOT).as_posix(), lf_bytes=len(data), lf_sha256=hashlib.sha256(data).hexdigest()))
    for name, data in [('latency', latency), ('growth', growth), ('paired_ratios', pairs), ('work', work),
                       ('admissions', admissions), ('telemetry', telemetry), ('cpu_cycles', cpu), ('sources', sources), ('diagnostic', diagnostics)]:
        emit(OUT/f'{name}.csv', data, args.check)
    print('PASS: all 168 predeclared rows, original workload/hash/continuation and admission equality; old incomplete series unchanged')
    print(json.dumps(next(r for r in growth if r['phase'] == 'birth_advance')))


if __name__ == '__main__':
    main()
