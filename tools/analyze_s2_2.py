#!/usr/bin/env python3
"""Audit frozen S2.2 local assays and derive clustered comparisons (standard library only)."""
import argparse
import csv
import hashlib
import io
import json
import math
import random
import statistics as stats
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'experiments/s2_2'
CONTEXTS = ('y_symmetric', 'y_conflict', 'straight', 'bend', 'lost', 'visited')
METRICS = ('selected_marked', 'occupancy', 'near_occupancy', 'initial_streak', 'max_streak', 'streak3',
           'restricted_first_deviation_step', 'deviations', 'reacquisitions', 'uturns', 'net_displacement_m', 'mean_distance_m')
PRIMARY_BOOT = {('y_symmetric', 'selected_marked'), ('straight', 'occupancy'), ('straight', 'streak3'),
                ('bend', 'occupancy'), ('bend', 'streak3'), ('lost', 'selected_marked')}


def read(path):
    with path.open(newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    assert all(None not in r and None not in r.values() for r in rows), path
    return rows


def render(rows):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
    writer.writeheader(); writer.writerows(rows)
    return stream.getvalue()


def cluster(rows, value):
    groups = defaultdict(list)
    for row in rows:
        groups[int(row['seed'])].append(value(row))
    assert all(len(v) == 2 for v in groups.values())
    return [stats.mean(groups[k]) for k in sorted(groups)]


def interval(values, bootstrap=False):
    mean = stats.mean(values)
    if bootstrap:
        rng = random.Random(2202); n = len(values)
        draws = sorted(sum(values[rng.randrange(n)] for _ in range(n))/n for _ in range(4096))
        return mean, draws[102], draws[3992]
    error = 1.96*stats.stdev(values)/math.sqrt(len(values))
    return mean, mean-error, mean+error


def analyze(baseline_only):
    summaries, pairs, mirrors, survival, hashes, combined = [], [], [], [], {}, []
    versions = [('baseline', 's2.1', '4')]
    if not baseline_only:
        versions.append(('fixed', 's2.2', '5'))
    for folder, model, physics in versions:
        path = DATA / folder / 'local.csv'; rows = read(path); assert len(rows) == 55296
        hashes[folder] = hashlib.sha256(path.read_text(encoding='utf-8').encode()).hexdigest()
        combined.extend(rows); indexed, groups = {}, defaultdict(list)
        for r in rows:
            assert r['scope'] == 'ENGINEERING_FIXTURE' and r['model'] == model and r['physics_version'] == physics
            context, age, inertia, seed, mirror, treatment = r['context'], int(r['age_ms']), int(r['persistence_weight']), int(r['seed']), int(r['mirror']), r['treatment']
            assert context in CONTEXTS and age in (0, 60000, 180000) and inertia in (0, 20, 40) and mirror in (0, 1)
            assert treatment in ('present', 'absent', 'blind')
            primary = age == 0 and inertia == 20
            assert r['primary'] == str(int(primary)) and 1 <= seed <= (512 if primary else 128)
            assert r['trail_weight'] == ('0' if treatment == 'blind' else '180') and r['memory_enabled'] == '0'
            assert r['explore_weight'] == '10' and r['cell_size_m'] == '0.01' and r['half_life_s'] == '60'
            key = (context, age, inertia, seed, mirror, treatment); assert key not in indexed; indexed[key] = r
            n = 24 if context in ('straight', 'bend') else 1
            positions = [tuple(map(int, p.split(':'))) for p in r['trajectory'].split(';')]
            assert len(positions) == n+1 and int(r['moves']) == n
            assert all(0 <= v <= 80 for p in positions for v in p)
            assert all(abs(a[0]-b[0])+abs(a[1]-b[1]) == 1 for a, b in zip(positions, positions[1:]))
            assert math.isclose(float(r['path_m']), n*.01)
            assert int(r['streak3']) == (int(r['max_streak']) >= 3)
            assert 0 <= float(r['occupancy']) <= float(r['near_occupancy']) <= 1
            assert r['deviation_observed'] == str(int(int(r['first_deviation_step']) >= 0))
            assert int(r['restricted_first_deviation_step']) == (int(r['first_deviation_step']) if r['deviation_observed'] == '1' else n)
            expected = 0 if treatment == 'absent' else 2**(-age/60000)
            assert math.isclose(float(r['release_units']), expected, abs_tol=1e-12)
            assert math.isclose(float(r['end_units']), expected*2**(-n*1101/60000), abs_tol=1e-12)
            groups[context, age, inertia, treatment].append(r)
        assert len(groups) == 6*3*3*3
        for key, r in indexed.items():
            if key[-1] == 'blind':
                a = indexed[key[:-1]+('absent',)]
                assert all(r[k] == a[k] for k in METRICS+('trajectory',)), (model, key)
        for (context, age, inertia, treatment), group in sorted(groups.items()):
            assert len(group) == (1024 if age == 0 and inertia == 20 else 256)
            for metric in METRICS:
                values = cluster(group, lambda r: float(r[metric])); mean, low, high = interval(values)
                summaries.append(dict(model=model, context=context, age_ms=age, persistence_weight=inertia, treatment=treatment,
                                      metric=metric, seed_clusters=len(values), mean=mean, ci_low=low, ci_high=high, method='cluster-normal-95'))
                if treatment == 'present':
                    def difference(r):
                        other = indexed[context, age, inertia, int(r['seed']), int(r['mirror']), 'absent']
                        return float(r[metric])-float(other[metric])
                    values = cluster(group, difference)
                    boot = age == 0 and inertia == 20 and (context, metric) in PRIMARY_BOOT
                    mean, low, high = interval(values, boot)
                    pairs.append(dict(model=model, context=context, age_ms=age, persistence_weight=inertia, metric=metric,
                                      seed_clusters=len(values), difference=mean, ci_low=low, ci_high=high,
                                      method='cluster-bootstrap-4096-seed2202' if boot else 'cluster-normal-95'))
            if age == 0 and inertia == 20:
                for side in (0, 1):
                    selected = [r for r in group if int(r['mirror']) == side]
                    for metric in ('selected_marked', 'occupancy', 'streak3'):
                        mirrors.append(dict(model=model, context=context, treatment=treatment, mirror=side, seeds=len(selected), metric=metric,
                                            mean=stats.mean(float(r[metric]) for r in selected)))
                if context in ('straight', 'bend'):
                    for step in range(25):
                        survival.append(dict(model=model, context=context, treatment=treatment, step=step, trials=len(group),
                                             not_yet_departed=stats.mean(int(r['first_deviation_step']) < 0 or int(r['first_deviation_step']) > step for r in group),
                                             censored=sum(r['deviation_observed'] == '0' for r in group) if step == 24 else 0))
    target = DATA / 'baseline' if baseline_only else DATA
    outputs = {target/'summary.csv': render(summaries), target/'paired.csv': render(pairs), target/'mirrors.csv': render(mirrors),
               target/'departure_survival.csv': render(survival), target/'input_hashes.json': json.dumps(hashes, indent=2, sort_keys=True)+'\n'}
    if not baseline_only:
        outputs[ROOT/'S2_2_EXPERIMENTS.csv'] = render(combined)
    for model in (v[1] for v in versions):
        for r in pairs:
            if r['model'] == model and r['age_ms'] == 0 and r['persistence_weight'] == 20 and (r['context'], r['metric']) in PRIMARY_BOOT:
                print(f"{model} {r['context']} {r['metric']}: delta={r['difference']:.6f}, 95%=[{r['ci_low']:.6f},{r['ci_high']:.6f}]")
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--baseline-only', action='store_true'); parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    for path, content in analyze(args.baseline_only).items():
        if args.check:
            assert path.read_text(encoding='utf-8') == content, f'stale evidence: {path}'
        else:
            path.write_text(content, encoding='utf-8', newline='\n')
    print('PASS S2.2 local evidence, controls, trajectories, censoring and clustered analysis')


if __name__ == '__main__':
    main()
