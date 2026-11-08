#!/usr/bin/env python3
"""Audit the frozen S3 matrix and derive seed-cluster intervals using only the standard library."""
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
DATA = ROOT / 'experiments/s3'


def read(path):
    with path.open(encoding='utf-8', newline='') as stream:
        rows = list(csv.DictReader(stream))
    assert rows and all(None not in r and None not in r.values() for r in rows), path
    return rows


def render(rows):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def interval(values):
    if len(set(values)) == 1:
        return values[0], values[0], values[0]
    rng = random.Random(3003)
    n = len(values)
    draws = sorted(sum(values[rng.randrange(n)] for _ in range(n))/n for _ in range(4096))
    return statistics.mean(values), draws[102], draws[3992]


def key(row):
    return tuple(row[k] for k in ('scenario', 'supplied', 'pulse_ms', 'receiver_capacity_ug', 'reverse_order', 'seed'))


def analyze():
    configuration = json.loads((DATA/'raw/configuration.json').read_text(encoding='utf-8'))
    assert configuration['scope'] == 'ENGINEERING_FIXTURE' and configuration['physics_version'] == 6 and configuration['seeds'] == 64
    rows = read(DATA/'raw/summary.csv')
    individuals = read(DATA/'raw/individuals.csv')
    assert len(rows) == 1536 and len(individuals) == 5376
    indexed, grouped, detail = {}, defaultdict(list), defaultdict(list)
    for r in individuals:
        assert r['scope'] == 'ENGINEERING_FIXTURE'
        detail[key(r)].append(r)
    for r in rows:
        assert r['scope'] == 'ENGINEERING_FIXTURE' and r['physics_version'] == '6'
        assert key(r) not in indexed
        indexed[key(r)] = r
        assert 1 <= int(r['seed']) <= 64
        assert r['mass_balanced'] == r['energy_balanced'] == r['partition_equal'] == '1'
        for ingredient in ('carbs', 'protein', 'water', 'other'):
            assert r[f'initial_{ingredient}_ug'] == r[f'accounted_{ingredient}_ug']
        assert int(r['energy_input_nj']) == int(r['body_energy_nj'])+int(r['dissipated_energy_nj'])
        parts = detail[key(r)]
        assert len(parts) == int(r['focal_count']) and len({p['entity_id'] for p in parts}) == len(parts)
        assert sum(int(p['emergence_observed']) for p in parts) == int(r['emerged'])
        assert sum(max(0, int(p['adult_at_ms'])) for p in parts) == int(r['emergence_sum_ms'])
        for i, name in enumerate(('eggs', 'larvae', 'pupae', 'adults', 'dead')):
            assert sum(p['final_stage'] == str(i) for p in parts) == int(r[name])
        if r['scenario'] == 'N2':
            assert r['pulse_ms'] == '1000' and r['window_ms'] == '500'
            expected = min(int(r['receiver_capacity_ug']), 400) if r['supplied'] == '1' else 0
            assert int(r['transferred_ug']) == expected
            assert sum(sum(int(p[f'received_{s}_ug']) for s in ('carbs', 'protein', 'water', 'other')) for p in parts) == expected
        else:
            assert r['scenario'] in ('N1', 'development') and r['window_ms'] == '180000'
            assert r['pulse_ms'] in ('250','1000','2000') and r['receiver_capacity_ug'] == '1000' and r['reverse_order'] == '0'
            for p in parts:
                assert int(p['tissue_protein_ug']) <= int(p['received_protein_ug'])
                if r['supplied'] == '0':
                    assert p['final_stage'] == '1'
                else:
                    assert p['final_stage'] in ('1','2','3','4')  # Retain stalls and deaths, if observed.
                if p['emergence_observed'] == '1':
                    assert 0 <= int(p['pupa_at_ms']) < int(p['adult_at_ms']) <= 180000
                else:
                    assert p['adult_at_ms'] == '-1' and p['pupa_at_ms'] == '-1'
        grouped[key(r)[:-1]].append(r)
    assert len(grouped) == 24
    for group in grouped.values():
        assert {int(r['seed']) for r in group} == set(range(1,65))
    # Submission reversal changes source sequence IDs, not actual donor/recipient outcomes.
    for r in rows:
        if r['scenario'] != 'N2' or r['reverse_order'] != '0':
            continue
        reverse = list(key(r)); reverse[4] = '1'; counterpart = indexed[tuple(reverse)]
        for field in ('transferred_ug', 'transfers', 'rejections', 'crop_carbs_ug', 'crop_protein_ug', 'crop_water_ug', 'crop_other_ug'):
            assert r[field] == counterpart[field]
        left = {p['entity_id']: p for p in detail[key(r)]}
        right = {p['entity_id']: p for p in detail[tuple(reverse)]}
        for entity in left:
            for field in ('crop_carbs_ug','crop_protein_ug','crop_water_ug','crop_other_ug'):
                assert left[entity][field] == right[entity][field]
    metrics = {
        'emergence_fraction': lambda r: int(r['emerged'])/int(r['focal_count']),
        # Unobserved individuals contribute the entire observation window (restricted mean).
        'restricted_emergence_ms': lambda r: (int(r['emergence_sum_ms'])+(int(r['focal_count'])-int(r['emerged']))*int(r['window_ms']))/int(r['focal_count']),
        'transferred_ug': lambda r: float(r['transferred_ug']),
        'tissue_protein_ug': lambda r: float(r['tissue_protein_ug']),
        'body_energy_j': lambda r: int(r['body_energy_nj'])/1e9,
        'deaths': lambda r: float(r['dead']),
    }
    summary, pairs, sensitivity = [], [], []
    for group, values in sorted(grouped.items()):
        for metric, value in metrics.items():
            if group[0] == 'N2' and metric in ('emergence_fraction','restricted_emergence_ms'):
                continue
            mean, low, high = interval([value(r) for r in sorted(values,key=lambda r:int(r['seed']))])
            summary.append(dict(zip(('scenario','supplied','pulse_ms','receiver_capacity_ug','reverse_order'),group)) |
                           {'metric':metric,'seeds':64,'mean':mean,'ci95_low':low,'ci95_high':high})
    for scenario in ('N1','development'):
        for pulse in ('250','1000','2000'):
            for metric, value in metrics.items():
                differences = [value(indexed[(scenario,'1',pulse,'1000','0',str(seed))])-value(indexed[(scenario,'0',pulse,'1000','0',str(seed))]) for seed in range(1,65)]
                mean, low, high = interval(differences)
                pairs.append({'scenario':scenario,'pulse_ms':pulse,'comparison':'protein_minus_zero_protein','metric':metric,
                              'seeds':64,'mean':mean,'ci95_low':low,'ci95_high':high})
        for supplied in ('0','1'):
            for pulse in ('250','2000'):
                for metric in ('restricted_emergence_ms','body_energy_j','transferred_ug'):
                    value = metrics[metric]
                    differences = [value(indexed[(scenario,supplied,pulse,'1000','0',str(seed))])-value(indexed[(scenario,supplied,'1000','1000','0',str(seed))]) for seed in range(1,65)]
                    mean,low,high = interval(differences)
                    sensitivity.append({'scenario':scenario,'supplied':supplied,'pulse_ms':pulse,'reference_pulse_ms':1000,'metric':metric,
                                        'seeds':64,'mean':mean,'ci95_low':low,'ci95_high':high})
    hashes = {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_text(encoding='utf-8').encode()).hexdigest()
              for path in (DATA/'raw/summary.csv', DATA/'raw/individuals.csv', DATA/'raw/configuration.json')}
    return {ROOT/'S3_EXPERIMENTS.csv':render(rows), DATA/'summary.csv':render(summary), DATA/'paired.csv':render(pairs),
            DATA/'sensitivity.csv':render(sensitivity), DATA/'input_hashes.json':json.dumps(hashes,indent=2)+'\n'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check',action='store_true')
    args = parser.parse_args()
    for path, content in analyze().items():
        if args.check:
            assert path.read_text(encoding='utf-8') == content, f'stale artifact: {path}'
        else:
            path.write_text(content,encoding='utf-8',newline='\n')
    print('PASS S3: 1536 runs, 5376 individual rows, complete seeds, ingredient/energy budgets, order and partition checks')
