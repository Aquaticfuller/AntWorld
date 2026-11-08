#!/usr/bin/env python3
"""Audit S4 geometry experiments without third-party dependencies or seed filtering."""
import argparse
import csv
import hashlib
import io
import json
import random
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'experiments/s4'


def read(path):
    with path.open(encoding='utf-8', newline='') as stream:
        rows = list(csv.DictReader(stream))
    assert rows and all(None not in row and None not in row.values() for row in rows), path
    return rows


def render(rows):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def key(row):
    return tuple(row[name] for name in ('scenario', 'workers', 'reverse_order', 'seed'))


def interval(values):
    rng = random.Random(4004)
    count = len(values)
    draws = sorted(sum(values[rng.randrange(count)] for _ in values) / count for _ in range(4096))
    return statistics.mean(values), draws[102], draws[3992]


def analyze():
    configuration = json.loads((DATA/'raw/configuration.json').read_text(encoding='utf-8'))
    assert configuration['physics_version'] == 7 and configuration['seeds'] == 32
    assert configuration['scope'] == 'ENGINEERING_FIXTURE'
    rows, edits, trajectories = (read(DATA/'raw'/f'{name}.csv') for name in ('summary', 'edits', 'trajectories'))
    assert len(rows) == 160 and len(trajectories) == 3872
    grouped, edit_groups, positions, indexed = defaultdict(list), defaultdict(list), defaultdict(list), {}
    for row in edits:
        assert row['scope'] == 'ENGINEERING_FIXTURE'
        edit_groups[key(row)].append(row)
    for row in trajectories:
        assert row['scope'] == 'ENGINEERING_FIXTURE'
        positions[key(row)].append(row)
    for row in rows:
        assert row['scope'] == 'ENGINEERING_FIXTURE' and row['physics_version'] == '7'
        assert key(row) not in indexed
        indexed[key(row)] = row
        assert row['mass_balanced'] == row['energy_balanced'] == row['restore_equal'] == '1'
        assert int(row['initial_q3']) == sum(int(row[k]) for k in ('remaining_q3', 'carried_q3', 'deposited_q3'))
        assert int(row['initial_q3'])+int(row['filled_q3']) == int(row['remaining_q3'])+int(row['excavated_q3'])
        for place in ('excavated', 'deposited'):
            for material in ('dry', 'water'):
                assert int(row[f'{place}_{material}_ug']) == int(row[f'{place}_q3'])*int(row[f'{material}_ug_per_q3'])
        detail = edit_groups[key(row)]
        assert len(detail) == int(row['edits'])
        assert [int(e['edit_id']) for e in detail] == list(range(1, len(detail)+1))
        assert sum(int(e['volume_q3']) for e in detail if e['kind'] == '0') == int(row['excavated_q3'])
        assert all(e['kind'] == '0' and 0 < int(e['volume_q3']) <= 16 for e in detail)
        if row['scenario'] == 'overlap':
            assert row['workers'] == '2' and row['window_ms'] == '100' and row['excavated_q3'] == '24'
            assert [int(e['volume_q3']) for e in detail] == [16, 8]
        else:
            assert row['scenario'] == 'autonomous' and row['window_ms'] == '60000'
            samples = positions[key(row)]
            assert len(samples) == 13*int(row['workers'])
            assert {int(p['time_ms']) for p in samples} == set(range(0, 60001, 5000))
            final = [p for p in samples if p['time_ms'] == '60000']
            for metric in ('carrying_moves', 'deliveries'):
                assert sum(int(p[metric]) for p in final) == int(row[metric])
            assert sum(int(p['digs']) for p in final) == int(row['edits'])
            assert sum(int(p['carried_q3']) for p in final) == int(row['carried_q3'])
        grouped[key(row)[:-1]].append(row)
    assert len(grouped) == 5
    for values in grouped.values():
        assert {int(row['seed']) for row in values} == set(range(1,33))
    for row in rows:
        if row['reverse_order'] != '1':
            continue
        forward = list(key(row)); forward[2] = '0'; forward = tuple(forward)
        expected = indexed[forward]
        assert {k:v for k,v in row.items() if k != 'reverse_order'} == {k:v for k,v in expected.items() if k != 'reverse_order'}
        for left,right in zip(edit_groups[key(row)], edit_groups[forward]):
            fields = ('actor_id','time_ms','kind','min_x_q','min_y_q','min_z_q','max_x_q','max_y_q','max_z_q','volume_q3')
            assert all(left[k] == right[k] for k in fields)
        for left,right in zip(positions[key(row)], positions[forward]):
            assert {k:v for k,v in left.items() if k != 'reverse_order'} == {k:v for k,v in right.items() if k != 'reverse_order'}
    summary = []
    for group, values in sorted(grouped.items()):
        for metric in ('edits','excavated_q3','deposited_q3','carrying_moves','deliveries','rejections'):
            numbers = [int(row[metric]) for row in values]
            mean, low, high = interval(numbers)
            summary.append(dict(scenario=group[0],workers=group[1],reverse_order=group[2],metric=metric,
                                seeds=32,mean=mean,ci95_low=low,ci95_high=high,minimum=min(numbers),maximum=max(numbers)))
    hashes = {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_text(encoding='utf-8').encode()).hexdigest()
              for p in sorted((DATA/'raw').iterdir()) if p.is_file()}
    return rows, summary, dict(scope='ENGINEERING_FIXTURE', runs=len(rows), edits=len(edits), trajectory_rows=len(trajectories),
                              seed_range=[1,32], interval='4096 seed bootstrap draws; RNG 4004; paired reversals are controls',
                              hashes=hashes)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--check', action='store_true'); args = parser.parse_args()
    rows, summary, manifest = analyze()
    outputs = {ROOT/'S4_EXPERIMENTS.csv': render(rows), DATA/'summary.csv':render(summary),
               DATA/'manifest.json':json.dumps(manifest,indent=2)+'\n'}
    for path, content in outputs.items():
        if args.check:
            assert path.read_text(encoding='utf-8') == content, f'{path} is stale'
        else:
            path.write_text(content,encoding='utf-8',newline='\n')
    print(f"S4 audit passed: {manifest['runs']} runs, {manifest['edits']} edits, {manifest['trajectory_rows']} trajectory rows; all ledgers and paired reversals agree")


if __name__ == '__main__':
    main()
