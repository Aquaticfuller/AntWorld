#!/usr/bin/env python3
"""Audit all S2.1 trials and reproduce the combined CSV and uncertainty tables (stdlib only)."""
import argparse
import csv
import hashlib
import io
import json
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'experiments/s2_1'
MODELS = ('s2-baseline', 's2.1')
DELAYS = (0, 180000, 600000)
TREATMENTS = ('absent', 'blind', 'present')
BOOTSTRAPS = 4096


def read(path):
    with path.open(newline='', encoding='utf-8') as stream:
        rows = list(csv.DictReader(stream))
    assert all(None not in row and all(v is not None for v in row.values()) for row in rows), path
    return rows


def render(rows, columns=None):
    if columns is None:
        columns = list(rows[0])
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=columns, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def bootstrap(values):
    rng = random.Random(2101)
    n = len(values)
    draws = sorted(sum(values[rng.randrange(n)] for _ in range(n)) / n for _ in range(BOOTSTRAPS))
    return draws[int(0.025 * (BOOTSTRAPS-1))], draws[int(0.975 * (BOOTSTRAPS-1))]


def clusters(rows, value):
    grouped = defaultdict(list)
    for row in rows:
        grouped[int(row['seed'])].append(value(row))
    return [statistics.mean(grouped[key]) for key in sorted(grouped)]


def wilson(successes, count):
    z = 1.959963984540054
    p = successes / count
    middle = (p + z*z/(2*count)) / (1 + z*z/count)
    half = z * math.sqrt(p*(1-p)/count + z*z/(4*count*count)) / (1 + z*z/count)
    return middle-half, middle+half


def config(row):
    result = dict(row)
    if row['experiment'] == 'social':
        result.update(workers='2', novice_workers='1', initial_food_ug='4000000', carrying_capacity_ug='1000',
                      surface_width='21', surface_height='15', nest_x='10', nest_z='7', max_trip_moves='192',
                      memory_lifetime_ms='300000', field_interval_ms='5000',
                      trails_enabled='0' if row['treatment'] == 'absent' else '1')
    elif row['experiment'] in ('bias', 'response'):
        result.update(actor_id='7', current_x='2', current_z='2', heading='North', decision_count='0',
                      path_cells='1', trail_cap_units='16', trail_cutoff_units='0.001', explore_weight='10', persistence_weight='20')
    return result


def analyze():
    combined, social_rows, field_rows, hashes = [], [], [], {}
    for directory, model, physics in (('baseline', 's2-baseline', 3), ('fixed', 's2.1', 4)):
        social = read(DATA / directory / 'social.csv')
        choices = read(DATA / directory / 'choices.csv')
        fields = read(DATA / directory / 'fields.csv')
        assert len(social) == 64*2*3*3 and len(choices) == 4096*6
        index = {}
        for row in social:
            assert row['scope'] == 'ENGINEERING_FIXTURE' and row['model'] == model and int(row['physics_version']) == physics
            key = (int(row['seed']), row['orientation'], int(row['release_delay_ms']), row['treatment'])
            assert key not in index
            index[key] = row
            assert row['initial_memory_cells'] == '0' and row['memory_enabled'] == '0'
            assert row['cell_size_m'] == '0.01' and row['sensing_radius'] == '2' and row['route_capacity'] == '48'
            assert row['step_ms'] == '1100' and row['half_life_s'] == '60' and row['deposit_units'] == '1'
            assert row['trail_weight'] == ('0' if row['treatment'] == 'blind' else '180')
            for name in ('trained', 'discovery_observed', 'release_continuous'):
                assert row[name] in ('0', '1')
            discovered = row['discovery_observed'] == '1'
            assert discovered == (int(row['first_discovery_ms']) >= 0)
            assert 0 <= int(row['followup_ms']) <= 180000
            if row['trained'] == '1':
                assert int(row['followup_ms']) == (int(row['first_discovery_ms']) if discovered else 180000)
                if discovered:
                    assert int(row['first_discovery_ms']) >= 6600 and int(row['steps_before_discovery']) >= 6
            else:
                assert not discovered and row['followup_ms'] == '0'
            if int(row['collections']):
                assert discovered and int(row['first_collection_ms']) > int(row['first_discovery_ms'])
            if int(row['deliveries']):
                assert int(row['first_delivery_ms']) > int(row['first_collection_ms']) >= 0
            assert 0 <= int(row['delivered_ug']) <= int(row['collected_ug']) <= 3999000
            assert 0 <= float(row['route_overlap_fraction']) <= 1
            assert abs(float(row['path_before_discovery_m']) - int(row['steps_before_discovery'])*0.01) < 1e-10
            if row['trained'] == '1' and row['treatment'] != 'absent':
                if key[2] == 0:
                    assert row['release_continuous'] == '1' and float(row['release_trace_coverage']) == 1
                if key[2] == 600000:
                    assert float(row['release_trail_units']) == 0
        expected = {(seed, orientation, delay, treatment) for seed in range(1, 65)
                    for orientation in ('east', 'west') for delay in DELAYS for treatment in TREATMENTS}
        assert set(index) == expected
        physical_metrics = ('discovery_observed', 'first_discovery_ms', 'followup_ms', 'first_collection_ms', 'first_delivery_ms',
                            'path_before_discovery_m', 'path_window_m', 'route_overlap_fraction', 'collections', 'deliveries',
                            'collected_ug', 'delivered_ug')
        for seed in range(1, 65):
            for orientation in ('east', 'west'):
                reference = index[seed, orientation, 0, 'absent']
                for delay in DELAYS:
                    absent = index[seed, orientation, delay, 'absent']
                    blind = index[seed, orientation, delay, 'blind']
                    present = index[seed, orientation, delay, 'present']
                    assert all(absent[k] == blind[k] == reference[k] for k in physical_metrics)
                    assert all(r['training_delivery_ms'] == reference['training_delivery_ms'] and r['trace_edges'] == reference['trace_edges']
                               for r in (absent, blind, present))
                    assert present['release_trail_units'] == blind['release_trail_units']
                    if delay == 180000:
                        assert abs(float(present['release_trail_units']) - float(index[seed, orientation, 0, 'present']['release_trail_units'])/8) < 1e-9
                    if delay == 600000:
                        assert all(absent[k] == present[k] for k in ('discovery_observed', 'first_discovery_ms', 'path_before_discovery_m'))
        bias = [r for r in choices if r['experiment'] == 'bias']
        assert len(bias) == 8192 and all(r['cue_order_invariant'] == '1' for r in bias)
        assert all(r['id_swap_invariant'] == ('1' if model == 's2.1' else '0') for r in bias)
        responses = {(r['seed'], r['treatment']): r for r in choices if r['experiment'] == 'response'}
        for seed in range(1, 4097):
            a, b = responses[str(seed), 'absent'], responses[str(seed), 'blind']
            assert (a['selected_x'], a['selected_z']) == (b['selected_x'], b['selected_z'])
        field_groups = defaultdict(list)
        for row in fields:
            assert row['model'] == model
            units = float(row['units']); x, z = int(row['cell_x']), int(row['cell_z'])
            assert math.isfinite(units) and 0 <= units <= 16
            assert (x == -1 and z == -1 and units == 0) or (0 <= x < 21 and 0 <= z < 15 and units > 0)
            key = (int(row['seed']), row['orientation'], int(row['release_delay_ms']), row['treatment'], int(row['elapsed_ms']))
            field_groups[key].append((x, z, units))
        for key, row in index.items():
            if row['trained'] == '1':
                for elapsed in range(0, 180001, 30000):
                    samples = field_groups[key + (elapsed,)]
                    assert samples and len({(x, z) for x, z, _ in samples}) == len(samples)
                    if elapsed == 0:
                        assert abs(sum(v for _, _, v in samples)-float(row['release_trail_units'])) < 1e-9
        social_rows.extend(social); field_rows.extend(fields)
        combined.extend(config(r) for r in choices + social)
        for name in ('choices.csv', 'social.csv', 'fields.csv'):
            path = DATA / directory / name
            hashes[str(path.relative_to(ROOT)).replace('\\', '/')] = hashlib.sha256(path.read_text(encoding='utf-8').encode()).hexdigest()
    # S2 ablations remain independent evidence; the historical data is unchanged.
    ablations = []
    for path, model, physics in ((ROOT / 'experiments/s2/summary.csv', 's2-baseline', 3),
                                  (DATA / 'ablations/summary.csv', 's2.1', 4)):
        rows = read(path); assert len(rows) == 128
        for row in rows:
            row.update(experiment='ablation', model=model, physics_version=str(physics), window_ms=row['simulated_ms'],
                       initial_food_ug='8000000', carrying_capacity_ug='1000', cell_size_m='0.01', surface_width='31', surface_height='21',
                       nest_x='3', nest_z='10', sensing_radius='2', route_capacity='48', max_trip_moves='192', step_ms='1100',
                       decision_delay_ms='1', memory_lifetime_ms='300000', field_interval_ms='5000', half_life_s='60', deposit_units='1',
                       trail_cap_units='16', trail_cutoff_units='0.001', explore_weight='10', persistence_weight='20', trail_weight='180')
            assert sum(int(row[k]) for k in ('available_ug', 'carried_ug', 'stored_ug')) == 8000000
        ablations.extend(rows); combined.extend(rows)
    old_ablations = {(r['layout'], r['seed'], r['treatment']): r for r in ablations if r['model'] == 's2-baseline'}
    for row in ablations:
        if row['model'] == 's2.1' and row['treatment'] in ('none', 'memory'):
            old = old_ablations[row['layout'], row['seed'], row['treatment']]
            assert all(row[key] == old[key] for key in row if key not in ('model', 'physics_version'))
    # Same dormant and training states across model versions are a pairing invariant.
    social_index = {(r['model'], r['seed'], r['orientation'], r['release_delay_ms'], r['treatment']): r for r in social_rows}
    for row in social_rows:
        if row['model'] == 's2.1':
            old = social_index['s2-baseline', row['seed'], row['orientation'], row['release_delay_ms'], row['treatment']]
            assert all(row[k] == old[k] for k in ('trained', 'training_delivery_ms', 'release_time_ms', 'trace_edges', 'release_trail_units'))
    summaries, orientation_rates, paired, survival, ablation_summary = [], [], [], [], []
    for model in MODELS:
        for delay in DELAYS:
            for treatment in TREATMENTS:
                all_rows = [r for r in social_rows if r['model'] == model and int(r['release_delay_ms']) == delay and r['treatment'] == treatment]
                rows = [r for r in all_rows if r['trained'] == '1']
                success = sum(int(r['discovery_observed']) for r in rows)
                ci = bootstrap(clusters(rows, lambda r: int(r['discovery_observed'])))
                summaries.append(dict(model=model, release_delay_ms=delay, treatment=treatment, runs=len(all_rows), trained=len(rows),
                                      discovered=success, discovery_rate=success/len(rows), pipeline_rate=success/len(all_rows),
                                      cluster_ci_low=ci[0], cluster_ci_high=ci[1],
                                      rmst_s=statistics.mean(float(r['followup_ms'])/1000 for r in rows),
                                      path_m=statistics.mean(float(r['path_before_discovery_m']) for r in rows),
                                      route_overlap=statistics.mean(float(r['route_overlap_fraction']) for r in rows),
                                      collected_ug=statistics.mean(float(r['collected_ug']) for r in rows),
                                      delivered_ug=statistics.mean(float(r['delivered_ug']) for r in rows),
                                      release_trail_units=statistics.mean(float(r['release_trail_units']) for r in rows)))
                for orientation in ('east', 'west'):
                    group = [r for r in rows if r['orientation'] == orientation]
                    successes = sum(int(r['discovery_observed']) for r in group); lo, hi = wilson(successes, len(group))
                    orientation_rates.append(dict(model=model, release_delay_ms=delay, treatment=treatment, orientation=orientation,
                                                  runs=len(group), discovered=successes, rate=successes/len(group), wilson_low=lo, wilson_high=hi))
                for t in range(0, 180001, 1000):
                    events = sum(r['discovery_observed'] == '1' and int(r['first_discovery_ms']) <= t for r in rows)
                    survival.append(dict(model=model, release_delay_ms=delay, treatment=treatment, time_ms=t, runs=len(rows),
                                         discovered=events, undiscovered_fraction=1-events/len(rows),
                                         censored_at_end=len(rows)-success if t == 180000 else 0))
            rows = [r for r in social_rows if r['model'] == model and int(r['release_delay_ms']) == delay and r['treatment'] == 'present' and r['trained'] == '1']
            for source, metric, divisor, unit in (
                ('discovery_observed', 'discovery_rate', 1, 'probability'),
                ('followup_ms', 'restricted_mean_discovery_s', 1000, 's'),
                ('route_overlap_fraction', 'route_overlap_fraction', 1, 'fraction'),
                ('path_before_discovery_m', 'path_until_discovery_or_censor_m', 1, 'm'),
                ('delivered_ug', 'delivered_ug', 1, 'ug'),
            ):
                def difference(row):
                    other = social_index[model, row['seed'], row['orientation'], row['release_delay_ms'], 'absent']
                    return (float(row[source])-float(other[source]))/divisor
                values = clusters(rows, difference); lo, hi = bootstrap(values)
                paired.append(dict(model=model, release_delay_ms=delay, contrast='present-minus-absent', metric=metric, unit=unit,
                                   seed_clusters=len(values), mean_difference=statistics.mean(values), ci_low=lo, ci_high=hi,
                                   bootstrap_replicates=BOOTSTRAPS, bootstrap_seed=2101))
    for model in MODELS:
        for layout in ('open', 'barrier'):
            for treatment in ('none', 'trails', 'memory', 'both'):
                rows = [r for r in ablations if r['model'] == model and r['layout'] == layout and r['treatment'] == treatment]
                for metric in ('coverage', 'deliveries', 'delivery_per_started_trip', 'revisits', 'trail_moves', 'memory_moves', 'trail_units'):
                    values = [float(r[metric]) for r in rows]
                    ablation_summary.append(dict(model=model, layout=layout, treatment=treatment, metric=metric, seeds=len(values),
                                                 mean=statistics.mean(values), sample_sd=statistics.stdev(values), min=min(values), max=max(values)))
    prefix = ['scope', 'experiment', 'model', 'physics_version', 'seed', 'orientation', 'layout', 'treatment']
    columns = prefix + sorted(set().union(*(r.keys() for r in combined)) - set(prefix))
    outputs = {ROOT / 'S2_1_EXPERIMENTS.csv': render(combined, columns),
               DATA / 'social_summary.csv': render(summaries), DATA / 'orientation_rates.csv': render(orientation_rates),
               DATA / 'paired_effects.csv': render(paired), DATA / 'survival.csv': render(survival),
               DATA / 'ablation_summary.csv': render(ablation_summary),
               DATA / 'input_hashes.json': json.dumps(dict(normalization='UTF-8 with LF newlines', sha256=hashes), indent=2, sort_keys=True)+'\n'}
    return outputs, len(combined), len(field_rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    outputs, trials, field_samples = analyze()
    for path, content in outputs.items():
        if args.check:
            assert path.read_text(encoding='utf-8') == content, f'stale generated evidence: {path}'
        else:
            path.write_text(content, encoding='utf-8', newline='\n')
    print(f'PASS S2.1 audit: {trials} raw trial rows, {field_samples} sparse field samples; matched controls, censoring, physics and conservation checked')


if __name__ == '__main__':
    main()
