"""Audit the frozen balanced experiment; never select runs by timing or sensor values."""
import argparse
import csv
import hashlib
import json
import math
import random
import statistics as st
from collections import defaultdict
from pathlib import Path

from analyze_s6 import quantile, read, emit

ROOT = Path(__file__).resolve().parents[1]
WORK = ('events', 'pending', 'decisions', 'candidates', 'bucket_queries',
        'tree_visits', 'maximum_candidates')


def describe(values):
    assert values
    return dict(n=len(values), mean=st.mean(values), p50=st.median(values),
                p95=quantile(values, .95), p99=quantile(values, .99),
                minimum=min(values), maximum=max(values))


def hierarchical(blocks):
    assert set(blocks) == {1, 2, 3} and all(len(v) == 12 for v in blocks.values())
    rng = random.Random(6206)
    medians, geometric = [], []
    for _ in range(4096):
        sample = [rng.choice(blocks[s]) for s in rng.choices([1, 2, 3], k=3)
                  for _ in range(12)]
        medians.append(st.median(sample))
        geometric.append(math.exp(st.mean(map(math.log, sample))))
    values = [v for group in blocks.values() for v in group]
    return dict(n_blocks=len(values), median=st.median(values),
                median_ci_low=quantile(medians, .025), median_ci_high=quantile(medians, .975),
                geometric_mean=math.exp(st.mean(map(math.log, values))),
                geometric_ci_low=quantile(geometric, .025), geometric_ci_high=quantile(geometric, .975))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=ROOT/'experiments/s6_2')
    p.add_argument('--check', action='store_true')
    args = p.parse_args()
    baseline = {(r['population'], r['layout'], r['policy']): r
                for r in read(ROOT/'experiments/s6_1/performance_final/states.csv')}
    baseline_work = {(r['population'], r['layout'], r['policy']): r
                     for r in read(ROOT/'experiments/s6_1/performance_final/contacts.csv')}
    collected, phase_rows, sensor_rows, os_rows, profiles = [], [], [], [], []
    hardware, receipts = {}, {}
    for mode in ('smoke', 'primary', 'overhead', 'exhaustive', 'attribution'):
        base = args.root/'performance'/mode
        for name, digest in json.loads((base/'files.json').read_text()).items():
            assert hashlib.sha256((base/name).read_bytes()).hexdigest() == digest, name
        conf = json.loads((base/'configuration.json').read_text())
        assert conf['selected_logical'] == 0 and conf['affinity_mask'] == 1
        assert conf['observer_affinity_mask'] == 65532
        assert conf['before']['power_plan'] == conf['after']['power_plan']
        assert conf['source_commit'].startswith('cc9004e')
        hardware[mode] = conf
        for folder in sorted(base.glob('session*')):
            session = int(folder.name[7:])
            receipt = json.loads((folder/'receipt.json').read_text())
            assert receipt['exit_code'] == 0 and receipt['binary_sha256'] == conf['binary_sha256']
            receipts[mode, session] = receipt
            raw, plan = read(folder/'contacts.csv'), read(folder/'schedule.csv')
            assert len(raw) == len(plan) == receipt['rows']
            for r, order in zip(raw, plan):
                assert all(r[k] == v for k, v in order.items())
                assert r['seed'] == '42' and r['simulation_ms'] == '10000'
                assert r['continuation_equal'] == '1' and r['affinity_mask'] == '1'
                assert r['instrumented'] == ('1' if mode == 'attribution' else '0')
                key = r['population'], r['layout'], r['policy']
                assert all(r[k] == baseline[key][k] for k in ('state_hash', 'trace_hash'))
                assert all(r[k] == baseline_work[key][k] for k in WORK), (mode, key)
                collected.append(dict(mode=mode, **r))
            phases = read(folder/'phases.csv')
            assert len(phases) == len(raw)*4
            for r in phases:
                assert r['start_processor'] == r['end_processor'] == '0'
                source = raw[int(r['sample'])]
                assert float(r['wall_ms']) == float(source[r['phase']+'_ms'])
                phase_rows.append(dict(mode=mode, session=session, population=source['population'],
                                       layout=source['layout'], warmup=source['warmup'], **r))
            profile = read(folder/'profile.csv')
            assert len(profile) == len(raw)*4*9
            if mode == 'attribution':
                for sample in range(len(raw)):
                    group = [r for r in profile if int(r['sample']) == sample and r['phase'] == 'advance']
                    total = next(int(r['inclusive_ns']) for r in group if r['category'] == 'advance')
                    assert sum(int(r['exclusive_ns']) for r in group) == total
                profiles.extend(dict(session=session, population=raw[int(r['sample'])]['population'],
                                     layout=raw[int(r['sample'])]['layout'], **r) for r in profile)
            else:
                assert all(r['inclusive_ns'] == r['exclusive_ns'] == r['calls'] == '0' for r in profile)
            sensors = read(folder/'hwinfo_corrected.csv')
            provenance = json.loads((folder/'hwinfo_corrected_provenance.json').read_text())
            assert len(sensors) == provenance['retained_rows']
            receipt['sensor_incomplete_prefix_rows'] = provenance['incomplete_rows']
            sensor_rows.extend(dict(mode=mode, session=session, **r) for r in sensors)
            if (folder/'telemetry.csv').exists():
                os_rows.extend(dict(mode=mode, session=session, **r) for r in read(folder/'telemetry.csv'))
    assert {m: sum(r['mode'] == m for r in collected) for m in hardware} == dict(
        smoke=4, primary=312, overhead=32, exhaustive=16, attribution=32)
    assert len({hardware[m]['binary_sha256'] for m in hardware if m != 'attribution'}) == 1
    primary = [r for r in collected if r['mode'] == 'primary' and r['warmup'] == '0']
    assert len(primary) == 288
    groups = defaultdict(list)
    for r in collected:
        if r['warmup'] == '0':
            for session in (r['session'], 'pooled'):
                groups[r['mode'], session, r['layout'], r['population'], r['policy']].append(r)
    latency, memory = [], []
    for (mode, session, layout, population, policy), rows in sorted(groups.items()):
        key = dict(mode=mode, session=session, layout=layout, population=int(population), policy=policy)
        for phase in ('setup', 'advance', 'encode', 'restore'):
            latency.append(dict(**key, phase=phase, **describe([float(r[phase+'_ms']) for r in rows])))
        for metric in ('resident_bytes', 'peak_resident_bytes', 'checkpoint_bytes', *WORK):
            memory.append(dict(**key, metric=metric, **describe([int(r[metric]) for r in rows])))
    paired, growth, block_environment = [], [], []
    for layout in ('dense', 'dispersed'):
        blocks = defaultdict(list)
        session_ratios = []
        for session in range(1, 4):
            rows = [r for r in primary if r['layout'] == layout and int(r['session']) == session]
            assert len(rows) == 96//2
            for block in range(1, 13):
                block_rows = [r for r in rows if int(r['block']) == block]
                expected = ['512', '2048', '2048', '512'] if block % 2 else ['2048', '512', '512', '2048']
                assert [r['population'] for r in block_rows] == expected
                a, b = ([float(r['advance_ms']) for r in block_rows if r['population'] == n] for n in ('512', '2048'))
                ratio = st.mean(b)/st.mean(a)
                blocks[session].append(ratio)
                phase_block = [r for r in phase_rows if r['mode'] == 'primary' and r['session'] == session
                               and r['phase'] == 'advance' and r['sample'] in {x['sample'] for x in block_rows}]
                detail = {}
                for metric in ('cpu_ms', 'cycles'):
                    av = st.mean(float(r[metric]) for r in phase_block if r['population'] == '512')
                    bv = st.mean(float(r[metric]) for r in phase_block if r['population'] == '2048')
                    detail[metric+'_ratio'] = bv/av
                paired.append(dict(layout=layout, session=session, block=block, ratio=ratio, **detail))
                start = min(int(r['start_utc_ns']) for r in phase_block)
                end = max(int(r['end_utc_ns']) for r in phase_block)
                # Coarse sensor window means are explanatory context. They do
                # not assert instantaneous temperature during subsecond phases.
                context = dict(layout=layout, session=session, block=block, start_utc_ns=start, end_utc_ns=end)
                for source, metrics in ((sensor_rows, ('p0_temperature_c', 'package_power_w', 'p0_clock_mhz', 'p0_t0_effective_clock_mhz')),
                                        (os_rows, ('system_busy_pct', 'processor_busy_pct', 'performance_pct'))):
                    window = [r for r in source if r['mode'] == 'primary' and r['session'] == session
                              and start-2000000000 <= int(r['utc_ns']) <= end+2000000000]
                    for metric in metrics:
                        vals = [float(r[metric]) for r in window if r[metric] != '']
                        context[metric] = st.mean(vals) if vals else ''
                block_environment.append(context)
            ratio = st.median(float(r['advance_ms']) for r in rows if r['population'] == '2048') / st.median(float(r['advance_ms']) for r in rows if r['population'] == '512')
            session_ratios.append(ratio)
            growth.append(dict(layout=layout, session=str(session), p50_ratio=ratio))
        all_rows = [r for r in primary if r['layout'] == layout]
        ratio = st.median(float(r['advance_ms']) for r in all_rows if r['population'] == '2048') / st.median(float(r['advance_ms']) for r in all_rows if r['population'] == '512')
        growth.append(dict(layout=layout, session='pooled', p50_ratio=ratio))
        stats = hierarchical(blocks)
        growth.append(dict(layout=layout, session='paired', p50_ratio='', **stats,
                           session_max_min=max(session_ratios)/min(session_ratios),
                           original_gate_pass=ratio <= 6,
                           uncertainty_gate_pass=max(session_ratios) <= 6 and stats['median_ci_high'] <= 6
                           and stats['geometric_ci_high'] <= 6 and max(session_ratios)/min(session_ratios) <= 1.25))
    attribution = []
    pg = defaultdict(list)
    for r in profiles:
        pg[r['layout'], r['population'], r['phase'], r['category']].append(r)
    for (layout, population, phase, category), rows in sorted(pg.items()):
        attribution.append(dict(layout=layout, population=int(population), phase=phase, category=category,
                                n=len(rows), calls_mean=st.mean(int(r['calls']) for r in rows),
                                inclusive_ms=st.mean(int(r['inclusive_ns']) for r in rows)/1e6,
                                exclusive_ms=st.mean(int(r['exclusive_ns']) for r in rows)/1e6))
    telemetry, coverage, background, correlations = [], [], [], []
    for mode, conf in hardware.items():
        before = {r['Id']: r for r in conf['before']['processes']}
        seconds = (conf['ended_utc_ns']-conf['started_utc_ns'])/1e9
        for process in conf['after']['processes']:
            prev = before.get(process['Id'])
            if prev and prev['ProcessName'] == process['ProcessName']:
                available = prev['CPU'] is not None and process['CPU'] is not None
                delta = process['CPU']-prev['CPU'] if available else ''
                background.append(dict(mode=mode, pid=process['Id'], process=process['ProcessName'],
                                       cpu_seconds_delta=delta, elapsed_seconds=seconds,
                                       one_logical_cpu_pct=delta/seconds*100 if available else '',
                                       working_set_before=prev['WorkingSet'], working_set_after=process['WorkingSet']))
    for layout in ('dense', 'dispersed'):
        contexts = [r for r in block_environment if r['layout'] == layout]
        ratios = [r['ratio'] for r in paired if r['layout'] == layout]
        for metric in ('p0_temperature_c', 'package_power_w', 'p0_clock_mhz', 'p0_t0_effective_clock_mhz', 'system_busy_pct'):
            values = [r[metric] for r in contexts]
            correlation = st.correlation(ratios, values) if len(set(values)) > 1 else ''
            correlations.append(dict(layout=layout, metric=metric, blocks=len(contexts), pearson_r=correlation))
    for (mode, session), receipt in receipts.items():
        sensors = [r for r in sensor_rows if r['mode'] == mode and r['session'] == session]
        times = [int(r['utc_ns']) for r in sensors]
        gaps = [(b-a)/1e9 for a, b in zip(times, times[1:])]
        coverage.append(dict(mode=mode, session=session, sensor_rows=len(sensors),
                             incomplete_prefix_rows=receipt['sensor_incomplete_prefix_rows'],
                             first_utc_ns=min(times), last_utc_ns=max(times),
                             median_gap_s=st.median(gaps), max_gap_s=max(gaps),
                             brackets_session=min(times) <= receipt['started_utc_ns'] and max(times) >= receipt['ended_utc_ns']))
        for k in sensors[0]:
            if k in ('mode', 'session', 'utc_ns', 'source_line'):
                continue
            values = [float(r[k]) for r in sensors if r[k] != '']
            telemetry.append(dict(mode=mode, session=session, source='HWiNFO', metric=k, **describe(values)))
        os = [r for r in os_rows if r['mode'] == mode and r['session'] == session]
        if os:
            for k in ('system_busy_pct', 'frequency_mhz', 'performance_pct', 'processor_busy_pct',
                      'utility_pct', 'performance_limit_pct', 'collector_ns', 'ac', 'battery_saver'):
                values = [float(r[k]) for r in os if r[k] != '']
                if values:
                    telemetry.append(dict(mode=mode, session=session, source='Windows', metric=k, **describe(values)))
    exhaustive = [r for r in collected if r['mode'] == 'exhaustive']
    speedup = st.median(float(r['advance_ms']) for r in exhaustive if r['policy'] == 'exhaustive')/st.median(float(r['advance_ms']) for r in exhaustive if r['policy'] == 'bounded')
    gates = dict(paired=growth, matched_exhaustive_speedup=speedup, matched_speedup_pass=speedup >= 4,
                 candidate_cap_pass=all(int(r['maximum_candidates']) <= 16 for r in collected if r['policy'] == 'bounded'),
                 canonical_parity=True, restored_continuation=True, raw_rows=len(collected),
                 primary_measured_rows=len(primary), source_commit=hardware['primary']['source_commit'],
                 hardware_sensor_coverage=all(r['brackets_session'] for r in coverage))
    output = args.root/'analysis'
    output.mkdir(exist_ok=True)
    for name, rows in [('latency', latency), ('memory_work', memory), ('paired_blocks', paired),
                       ('profile', attribution), ('hardware_summary', telemetry), ('sensor_coverage', coverage),
                       ('background_processes', background), ('block_environment', block_environment),
                       ('environment_correlations', correlations)]:
        emit(output/(name+'.csv'), rows, args.check)
    target = output/'performance.json'
    if args.check:
        assert json.loads(target.read_text()) == gates, 'stale performance gates'
    else:
        target.write_text(json.dumps(gates, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(gates, indent=2))


if __name__ == '__main__':
    main()
