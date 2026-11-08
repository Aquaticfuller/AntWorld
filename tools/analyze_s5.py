"""Audit raw S5 evidence and produce reproducible statistical/performance summaries."""
import argparse
import csv
import hashlib
import json
import random
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
S4_SOURCE = '214fce398a29d26507e21c75f4f78f1485527e6b'
INITIAL_S5_SOURCE = '8f3f5ec7caf868dd76c9704411be9134ca24dd2c'

def rows(path):
    with path.open(encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream))

def quantile(values, p):
    values = sorted(values)
    at = (len(values) - 1) * p
    low = int(at)
    return values[low] + (values[min(low + 1, len(values) - 1)] - values[low]) * (at - low)

def write_csv(path, fields, data):
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(data)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=ROOT / 'experiments/s5')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--source-commit', default='UNRECORDED')
    args = parser.parse_args()
    root = args.root
    raw = rows(root / 'raw/summary.csv')
    assert len(raw) == 128
    key = lambda r: (r['scenario'], int(r['seed']), int(r['save_interval_ms']))
    indexed = {key(r): r for r in raw}
    assert len(indexed) == 128
    assert set(indexed) == {(case, seed, interval) for case in ('physiology', 'excavation')
                            for seed in range(1, 33) for interval in (5000, 30000)}
    for row in raw:
        assert row['scope'] == 'ENGINEERING_FIXTURE' and row['exact_continuation'] == '1'
        assert all(int(row[name]) == 0 for name in ('carb_residual_ug', 'protein_residual_ug',
                                                   'water_residual_ug', 'energy_residual_nj'))
        expected_time = 180000 if row['scenario'] == 'physiology' else 60000
        assert int(row['simulation_ms']) == expected_time
        assert int(row['generations']) == 1 + expected_time // int(row['save_interval_ms'])
    ignore = {'save_interval_ms', 'generations', 'database_bytes'}
    for scenario in ('physiology', 'excavation'):
        for seed in range(1, 33):
            a, b = indexed[(scenario, seed, 5000)], indexed[(scenario, seed, 30000)]
            assert {k: v for k, v in a.items() if k not in ignore} == {k: v for k, v in b.items() if k not in ignore}
    summaries = []
    for scenario in ('physiology', 'excavation'):
        data = [indexed[(scenario, seed, 30000)] for seed in range(1, 33)]
        for metric in ('adult_workers', 'larvae', 'deaths', 'emergences', 'internal_transfer_ug',
                       'geometry_edits', 'excavated_q3', 'deposited_q3'):
            values = [int(r[metric]) for r in data]
            rng = random.Random(5005)
            means = [sum(values[rng.randrange(32)] for _ in range(32)) / 32 for _ in range(4096)]
            summaries.append(dict(scenario=scenario, metric=metric, independent_seeds=32,
                                  mean=statistics.mean(values), ci95_low=quantile(means, .025),
                                  ci95_high=quantile(means, .975)))
    performance = []
    for condition in ('repeated', 'interleaved'):
        for edits in (1000, 5000, 10000):
            samples = rows(root / f'performance/{condition}-{edits}.csv')
            assert len(samples) == 60
            operations = {r['operation'] for r in samples}
            assert operations == {'checkpoint_encode', 'checkpoint_restore', 'durable_save',
                                  'durable_load_validate', 'indexed_history_and_flow_query', 'post_wal_checkpoint_size'}
            assert {int(r['iteration']) for r in samples} == set(range(10))
            assert all(int(r['edits']) == edits and r['condition'] == condition and int(r['events']) == edits + 4 for r in samples)
            assert all(int(r['peak_resident_bytes']) >= int(r['resident_bytes']) > 0 for r in samples)
            assert all(int(r['checkpoint_bytes']) > 0 for r in samples)
            assert all(r['scope'] == 'ENGINEERING_FIXTURE' and
                       int(r['index_entries']) == (1 if condition == 'repeated' else 2) for r in samples)
            for operation in sorted(operations):
                data = [r for r in samples if r['operation'] == operation]
                assert {int(r['iteration']) for r in data} == set(range(10)) and len(data) == 10
                times = [float(r['elapsed_us']) for r in data]
                assert all(value >= 0 for value in times)
                performance.append(dict(condition=condition, edits=edits, operation=operation, samples=len(data),
                    p50_us=statistics.median(times), p95_us=quantile(times, .95), p99_us=quantile(times, .99),
                    max_us=max(times), checkpoint_bytes=int(data[0]['checkpoint_bytes']),
                    max_database_bytes=max(int(r['database_bytes']) for r in data),
                    max_peak_resident_bytes=max(int(r['peak_resident_bytes']) for r in data)))
    long = rows(root / 'performance/long-history.csv')
    assert len(long) == 365
    for day, row in enumerate(long, 1):
        assert row['scope'] == 'ENGINEERING_STORAGE_CLOCK'
        assert int(row['day']) == day and int(row['events']) == 100 * day + 2
        assert int(row['simulation_ms']) == day * 86400000 and int(row['generation']) == day + 1
        assert (float(row['load_validate_us']) >= 0) == (day % 30 == 0 or day == 365)
    before = rows(root / 'performance/long-history-before-query-index.csv')
    fields = ('scope', 'day', 'simulation_ms', 'events', 'generation', 'checkpoint_bytes', 'database_bytes')
    assert [{k:r[k] for k in fields} for r in before] == [{k:r[k] for k in fields} for r in long]
    old = rows(root / 'performance/s4_reference.csv')
    new = rows(root / 'performance/s4_same_fixture_s5.csv')
    # Query candidate counts intentionally improve. All fixture identities, counts and volumes remain.
    fields = ('scope', 'case', 'population', 'lifetime_edits', 'iteration', 'operation', 'nodes', 'cached_bricks')
    assert [{k:r[k] for k in fields} for r in old] == [{k:r[k] for k in fields} for r in new]
    # Commit/contact rows deliberately report 0 (not measured), not an empty checkpoint.
    assert all(int(b['checkpoint_bytes']) == (int(a['checkpoint_bytes']) + 8 if int(a['checkpoint_bytes']) else 0)
               for a,b in zip(old,new,strict=True))
    paths = [root/'raw/summary.csv']
    paths += sorted(p for p in (root/'performance').iterdir() if p.suffix in ('.csv','.json') and p.name != 'summary.csv')
    hashes = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_text(encoding='utf-8').encode()).hexdigest() for p in paths}
    verification = json.loads((root/'verification.json').read_text(encoding='utf-8'))
    executions = rows(root/'executed_tests.csv')
    assert len(executions) == 522 and all(row['result'] == 'Passed' for row in executions)
    for build in verification['local_builds']:
        tests = [r for r in executions if r['configuration'] == build['configuration']]
        assert len(tests) == build['tests'] == build['passed'] and build['failed'] == 0
        assert len({r['test'] for r in tests}) == len(tests)
        assert all(r['source_commit'] == build['source_commit'] for r in tests)
    test_hash = hashlib.sha256((root/'executed_tests.csv').read_text(encoding='utf-8').encode()).hexdigest()
    assert verification['test_rows_sha256'] == test_hash
    if args.check:
        manifest = json.loads((root/'manifest.json').read_text(encoding='utf-8'))
        assert manifest['normalized_lf_sha256'] == hashes
        # Recompute summary values, not just file presence.
        for expected, actual in zip(summaries, rows(root/'summary.csv'), strict=True):
            assert {k: str(v) for k,v in expected.items()} == actual
        for expected, actual in zip(performance, rows(root/'performance/summary.csv'), strict=True):
            assert {k: str(v) for k,v in expected.items()} == actual
    else:
        write_csv(root/'summary.csv', list(summaries[0]), summaries)
        write_csv(root/'performance/summary.csv', list(performance[0]), performance)
        assert args.source_commit != 'UNRECORDED'
        sources = {name: args.source_commit for name in hashes}
        for name in ('raw/summary.csv', 'performance/long-history-before-query-index.csv',
                     'performance/s4_same_fixture_s5.csv', 'performance/s0.json',
                     'performance/scheduler.csv', 'performance/s1.csv', 'performance/s2.csv', 'performance/s3.csv'):
            sources[name] = INITIAL_S5_SOURCE
        sources['performance/s4_reference.csv'] = S4_SOURCE
        (root/'manifest.json').write_text(json.dumps(dict(source_commit=args.source_commit,
            runs=128, independent_seeds=32, performance_samples=360, diagnostic_days=365,
            source_by_file=sources, normalized_lf_sha256=hashes), indent=2)+'\n', encoding='utf-8', newline='\n')
    print('PASS S5: 128 exact-continuation runs, 360 performance samples, 365 diagnostic days; complete seeds and zero nutrient/energy residuals')

if __name__ == '__main__':
    main()
