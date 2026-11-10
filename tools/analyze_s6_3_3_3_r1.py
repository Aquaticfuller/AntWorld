"""Verify R1 evidence and pair completed 21-day outcomes without imputing failed cases."""
import argparse
from collections import Counter, defaultdict
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import random
import statistics

from analyze_s6_3_3_2 import q
from analyze_s6_3_3_3_ecology import DAY, case, facts
from run_s6_3_3_3_assays import BASE, read, sha
from run_s6_3_3_3_r1 import planned

RAW = BASE.with_name('s6_3_3_3_r1')
NUTRIENTS = ('carbs', 'protein', 'water', 'other')
MOTION = (1, 2, 6, 15, 18)
HANDLING = (3, 4, 5, 7, 16, 17)
OUTCOMES = (
    'queen_received_carbs_ug', 'queen_received_protein_ug', 'queen_received_water_ug',
    'queen_absorbed_carbs_ug', 'queen_absorbed_protein_ug', 'queen_absorbed_water_ug',
    'queen_alive_days', 'queen_alive', 'queen_actual_care_ms', 'worker_actual_care_ms',
    'actual_worker_task_switches', 'actual_worker_switches_per_adult_day', 'food_deliveries',
    'underground_deliveries', 'placements', 'transfers_to_brood', 'born_eggs', 'emerged', 'events',
)
DENSITY_PHASES = ('setup_ms', 'advance_ms', 'checkpoint_ms', 'restore_ms', 'journal_encode_ms',
                  'rss_bytes', 'process_peak_bytes')


def value(row, key):
    return float(row.get(key) or 0)


def encode_table(rows):
    rows = list(rows)
    assert rows
    buffer = io.StringIO(newline='')
    columns = dict.fromkeys(key for row in rows for key in row)
    writer = csv.DictWriter(buffer, columns, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode('utf-8')


def audit_archive(folder, deep):
    entry = json.loads((folder / 'attempt.json').read_text(encoding='utf-8'))
    assert entry['run'] == folder.name
    for name, digest in entry['files'].items():
        assert sha(folder / name) == digest, folder / name
    if 'facts' in entry:
        for key, name, digest_key in (('facts', 'events.csv.gz', 'csv_sha256'),
                                      ('canonical', 'events.facts.gz', 'raw_sha256')):
            info = entry[key]
            path = folder / name
            assert info['sha256'] == entry['files'][name] and info['bytes'] == path.stat().st_size
            if deep:
                with gzip.open(path, 'rb') as stream:
                    assert hashlib.file_digest(stream, 'sha256').hexdigest() == info[digest_key], path
        assert entry['facts']['rows'] == entry['canonical']['rows']
    return entry


def ledgers(days):
    for row in days:
        for nutrient in NUTRIENTS:
            assert row[f'introduced_{nutrient}_ug'] == row[f'accounted_{nutrient}_ug']
        assert int(row['energy_input_nj']) == int(row['body_energy_nj']) + int(row['dissipated_energy_nj'])
        assert int(row['soil_initial_q3']) == sum(int(row[k]) for k in (
            'soil_remaining_q3', 'soil_carried_q3', 'soil_deposited_q3'))


def endpoints(path, row):
    queen = int(row['queen'])
    stats = Counter()
    underground_collections, below_starts = {}, {}
    deliveries, placements, feeds, births, emerged = {}, {}, {}, {}, {}
    later_feeds, later_placements, later_tactile = {}, {}, {}
    stages = {}
    for f in facts(path):
        event, time, kind, actor = map(int, f[1:5])
        related = int(f[8])
        if kind in (2, 7, 8, 35):
            stages[actor] = int(f[6])
        if kind == 10 and float(f[16]) < 0:
            below_starts.setdefault(actor, (event, time))
        if kind == 5 and float(f[16]) > 0:
            underground_collections.setdefault(actor, (event, time))
        if kind == 12 and float(f[16]) < 0:
            stats['underground_deliveries'] += 1
            assert actor in below_starts and actor in underground_collections
            assert below_starts[actor][0] < underground_collections[actor][0] < event
            deliveries.setdefault(actor, (event, time))
        if kind == 21 and related == queen:
            stream = 'received'
        elif kind == 16 and actor == queen:
            stream = 'absorbed'
        elif kind in (19, 20) and actor == queen:
            stream = 'self_ingested'
        else:
            stream = None
        if stream:
            for name, amount in zip(NUTRIENTS, f[18:22]):
                stats[f'queen_{stream}_{name}_ug'] += int(amount)
        if kind == 21 and stages[related] < 3 and int(f[19]):
            feeds.setdefault(actor, (event, time))
            if actor in deliveries:
                later_feeds.setdefault(actor, (event, time))
        if kind == 35:
            births.setdefault(actor, (event, time))
        if kind == 7 and f[6] == '3':
            emerged.setdefault(actor, (event, time))
        if kind == 42 and f[9] in ('3', '4'):
            act = int(f[10])
            if f[9] == '3' and act == 17:
                placements.setdefault(actor, (event, time))
                if actor in deliveries:
                    later_placements.setdefault(actor, (event, time))
            if f[9] == '3' and f[13] == '1' and act in (3, 4, 5) and actor in deliveries:
                later_tactile.setdefault(actor, (event, time))
            # The generic Move observer also uses Walk, with unknown duration.
            if act not in MOTION + HANDLING or (act == 1 and f[13] != '1'):
                continue
            caste = 'queen' if actor == queen else 'worker'
            if f[13] == '1':
                elapsed = time - int(f[12])
                assert elapsed >= 0
                stats[f'{caste}_actual_care_ms'] += elapsed
                if act in (3, 4, 5) or (act == 7 and f[9] == '3' and any(map(int, f[18:22]))):
                    stats[f'{caste}_tactile_care_ms'] += elapsed
            else:
                stats[f'{caste}_unknown_duration_care_facts'] += 1
    stats['queen_alive_days'] = int(row.get('queen_death_ms') or row['end_ms']) / DAY
    stats['workers_with_underground_return_feed_place'] = len(deliveries.keys() & placements.keys() & feeds.keys())
    stats['workers_with_post_return_feed_and_place'] = len(later_feeds.keys() & later_placements.keys())
    stats['workers_with_post_return_feed_and_tactile_care'] = len(later_feeds.keys() & later_tactile.keys())
    stats['same_world_chain'] = int(bool(deliveries and placements and feeds and births and emerged))
    witness = []
    for worker in sorted((deliveries.keys() & placements.keys() & feeds.keys()) |
                         (later_feeds.keys() & later_tactile.keys())):
        chain = (('starts_below', below_starts), ('collects_above', underground_collections),
                 ('delivers_below', deliveries), ('places_brood', placements), ('feeds_brood_protein', feeds),
                 ('places_after_return', later_placements), ('feeds_after_return', later_feeds),
                 ('active_care_after_return', later_tactile))
        for label, events in chain:
            if worker in events:
                event, time = events[worker]
                witness.append(dict(run=row['run'], actor=worker, event=event, time_ms=time, evidence=label))
    return stats, witness


def ecology(root, deep):
    completed, attempts, witnesses = {}, [], []
    old_rows = {r['run']: r for r in read(BASE / 'ecology_cases.csv')}
    cases = dict(planned())
    assert len(cases) == 96 and {p.name for p in (root / 'ecology').iterdir()} == set(cases)
    for name, space in cases.items():
        seed, workers, _, food, policy = name.split('_')
        folder = root / 'ecology' / name
        entry = audit_archive(folder, deep)
        days = read(folder / 'days.csv')
        ledgers(days)
        attempt = dict(run=name, seed=seed, workers=workers, space=space, food=food, policy=policy,
                       origin=entry['origin'], status=entry['status'], observed_facts=entry.get('facts', {}).get('rows', 0))
        if entry['status'] == 'FAILED':
            abort, = read(folder / 'abort.csv')
            assert int(abort['committed_events']) == attempt['observed_facts']
            assert int(abort['last_full_day']) == int(days[-1]['day']) < 21
            attempt.update(abort, reason=(folder / 'console.log').read_text(encoding='utf-8').strip())
        else:
            run, = read(folder / 'runs.csv')
            timing, = read(folder / 'timings.csv')
            assert entry['status'] == 'COMPLETE' and len(days) == 22
            assert all(run[key] == timing[key] for key in ('events', 'state_hash', 'trace_hash'))
            assert run['direct_equal'] == run['restored_equal'] == run['all_ledgers_equal'] == '1'
            assert int(run['events']) == int(run['sql_fact_count']) == attempt['observed_facts']
            final = {int(r['id']): r for r in read(folder / 'individuals.csv') if r['day'] == '21'}
            path = folder / 'events.csv.gz'
            result = case(folder, run, days[-1], final, [], event_path=path)
            new, witness = endpoints(path, result)
            completed[name] = dict(result, **new)
            witnesses.extend(witness)
        attempts.append(attempt)
    legacy = {}
    for name, row in old_rows.items():
        extra, _ = endpoints(BASE / 'ecology/events' / f'{name}.csv.gz', row)
        legacy[name] = dict(row, **extra)
    assert len(legacy) == 72
    assert any(r['workers_with_post_return_feed_and_tactile_care'] for r in completed.values())
    return completed, legacy, attempts, witnesses


def compare(complete, legacy):
    rows = []
    for model, cases in (('reviewed', legacy), ('continuous', complete)):
        for name, on in cases.items():
            if not name.endswith('_care'):
                continue
            off = cases.get(name.removesuffix('_care') + '_control')
            if off:
                rows.append(dict(contrast='care_minus_control', model=model, seed=on['seed'],
                                 workers=on['workers'], space=on['space'], food=on['food'],
                                 **{key: value(on, key) - value(off, key) for key in OUTCOMES}))
    for name in sorted(complete.keys() & legacy.keys()):
        after, before = complete[name], legacy[name]
        rows.append(dict(contrast='continuous_minus_reviewed', model=name.split('_')[-1], seed=after['seed'],
                         workers=after['workers'], space=after['space'], food=after['food'],
                         **{key: value(after, key) - value(before, key) for key in OUTCOMES}))
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(row[k] for k in ('contrast', 'model', 'workers', 'space', 'food'))].append(row)
    summaries = []
    for (contrast, model, workers, space, food), group in sorted(groups.items()):
        assert len({r['seed'] for r in group}) == len(group)
        rng = random.Random(63331)
        picks = [rng.choices(group, k=len(group)) for _ in range(4096)]
        for key in OUTCOMES:
            estimates = sorted(statistics.fmean(row[key] for row in draw) for draw in picks)
            summaries.append(dict(contrast=contrast, model=model, workers=workers, space=space, food=food,
                                  seeds=len(group), metric=key, mean=statistics.fmean(r[key] for r in group),
                                  low95=q(estimates, .025) if len(group) > 1 else '',
                                  high95=q(estimates, .975) if len(group) > 1 else ''))
    return rows, summaries


def density(root):
    out = []
    old = {(r['mode'], r['layout'], r['workers']): r for r in read(BASE / 'density/summary.csv')
           if r['build'] == 'unprofiled'}
    for motor in ('legacy', 'continuous'):
        groups = defaultdict(list)
        for row in read(root / f'density/{motor}/samples.csv'):
            groups[row['mode'], row['layout'], row['workers']].append(row)
        assert set(groups) == set(old)
        for (mode, layout, workers), group in sorted(groups.items()):
            assert {r['replicate'] for r in group} == {'0', '1', '2', '3'}
            assert all(r['restore_equal'] == r['conserved'] == '1' for r in group)
            assert all(r['sqlite_save_ms'] == r['sqlite_load_ms'] == '-1' for r in group)
            keys = ('opportunities', 'started', 'completed', 'transfers', 'placements', 'switches', 'facts',
                    'journal_bytes', 'checkpoint_bytes', 'state_hash', 'trace_hash')
            for key in keys:
                assert len({r[key] for r in group}) == 1
                if motor == 'legacy':
                    assert group[0][key] == old[mode, layout, workers][key], (mode, layout, workers, key)
            row = dict(motor=motor, mode=mode, layout=layout, workers=workers,
                       **{key: group[0][key] for key in keys})
            for key in DENSITY_PHASES:
                measured = sorted(value(r, key) for r in group if r['warmup'] == '0')
                assert len(measured) == 3
                for p in (50, 95, 99):
                    row[f'{key}_p{p}'] = q(measured, p / 100)
            out.append(row)
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raw', default=RAW, type=Path)
    p.add_argument('--check', action='store_true')
    p.add_argument('--deep', action='store_true')
    a = p.parse_args()
    complete, old, attempts, witnesses = ecology(a.raw, a.deep)
    differences, intervals = compare(complete, old)
    outputs = dict(ecology_attempts=attempts, ecology_cases=complete.values(), reviewed_endpoints=old.values(),
                   ecology_paired=differences, ecology_intervals=intervals, underground_witnesses=witnesses,
                   density_summary=density(a.raw))
    for name, rows in outputs.items():
        path = a.raw / f'{name}.csv'
        payload = encode_table(rows)
        if a.check:
            assert path.read_bytes() == payload, path.name
        else:
            path.write_bytes(payload)
    print(f'Verified {len(attempts)} attempts, {len(complete)} completed worlds and {len(differences)} paired comparisons.')


if __name__ == '__main__':
    main()
