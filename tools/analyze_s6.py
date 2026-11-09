"""Audit S6 raw evidence and regenerate seed-paired summaries without filtering runs."""
import argparse
import csv
import hashlib
import json
import math
import random
import statistics
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEY = ('suite', 'seed', 'condition', 'mirror', 'encounter_budget')
INGREDIENTS = ('carbs', 'protein', 'water', 'other')
MODES = ('normal', 'accelerated', 'recovered')
CONDITIONS = ('supplied', 'protein_absent', 'food_absent', 'sealed')
RESIDENCE = ('paused_ms', 'rest_ms', 'nurse_ms', 'forage_ms', 'excavate_ms')
METRICS = ('population.alive', 'population.worker_alive', 'population.larva',
           'life.emerged', 'life.deaths', 'food_collections', 'food_deliveries',
           'explored_cells', 'discovered_sources', 'nutrition.internal_transfer',
           'body.tissue_protein', 'body.energy', 'body.water', 'crop.protein',
           'sink.dissipated_energy', 'sink.oxidized_carbs', 'sink.lost_water',
           'environment_food.carbs', 'environment_food.protein', 'environment_food.water',
           'nest_food.protein', 'food.delivered_carbs', 'food.delivered_protein',
           'food.delivered_water', 'excavated_q3', 'filled_q3', 'soil.carried',
           'soil.deposited', 'geometry.edit_count', 'behavior.changes',
           'events', 'checkpoint_bytes', 'database_bytes', 'save_ms', 'load_ms')
DERIVED_METRICS = ('initial_worker_active_fraction', 'initial_worker_observed_survival_s',
                   'deaths_energy', 'deaths_water', 'unemerged_brood', 'brood_unmet_protein_ug',
                   'dead_crop_protein_ug')


def read(path):
    with path.open(encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream))


def key(row):
    return tuple(row[k] for k in KEY)


def grouped(path):
    result = defaultdict(list)
    for row in read(path):
        result[key(row)].append(row)
    return result


def number(row, field):
    return int(row[field])


def quantile(values, p):
    values = sorted(values)
    at = (len(values) - 1) * p
    low = int(at)
    return values[low] + (values[min(low + 1, len(values) - 1)] - values[low]) * (at - low)


@lru_cache(maxsize=None)
def resamples(n):
    rng = random.Random(6006)
    return [[rng.randrange(n) for _ in range(n)] for _ in range(4096)]


def interval(values):
    means = [math.fsum(values[i] for i in sample) / len(values)
             for sample in resamples(len(values))]
    return dict(independent_seeds=len(values), mean=statistics.mean(values),
                ci95_low=quantile(means, .025), ci95_high=quantile(means, .975),
                minimum=min(values), maximum=max(values))


def wilson(successes, n):
    z = 1.959963984540054
    p = successes / n
    center = (p + z*z/(2*n)) / (1 + z*z/n)
    radius = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / (1 + z*z/n)
    return max(0., center-radius), min(1., center+radius)


def zero_residuals(row):
    residuals = [v for k, v in row.items() if '_residual_' in k]
    assert residuals and all(int(v) == 0 for v in residuals), row


def box_cells(bounds):
    low, high = bounds
    return {(x, y, z) for x in range(low[0], high[0]) for y in range(low[1], high[1])
            for z in range(low[2], high[2])}


def audit_integration(root, directory, suite, seeds, duration):
    base = root / directory
    raw = read(base / 'summary.csv')
    configuration = json.loads((base / 'configuration.json').read_text(encoding='utf-8'))
    assert configuration['scope'] == 'ENGINEERING_FIXTURE'
    assert configuration['suite'] == suite and configuration['seeds'] == seeds
    treatments = ([(c, m, 16) for m in (0, 1) for c in CONDITIONS] if suite == 'primary'
                  else [('supplied', 0, b) for b in (8, 16, 32)] if suite == 'sensitivity'
                  else [(c, 0, 16) for c in ('supplied', 'food_absent')])
    expected = {(suite, str(s), c, str(m), str(b)) for s in range(1, seeds+1)
                for c, m, b in treatments}
    cases = defaultdict(dict)
    for row in raw:
        assert row['mode'] not in cases[key(row)], 'duplicate mode'
        cases[key(row)][row['mode']] = row
    assert set(cases) == expected and len(raw) == len(expected)*3
    evidence = {name: grouped(base / f'{name}.csv') for name in
                ('individuals', 'events', 'geometry', 'foods', 'event_counts', 'time_series')}
    analyzed = []
    for name, entries in evidence.items():
        assert set(entries) <= expected, f'unmatched {name} case'
    for case, replicas in cases.items():
        assert set(replicas) == set(MODES)
        r = replicas['normal']
        for mode in MODES:
            assert {k: v for k, v in r.items() if k not in ('mode', 'advance_ms')} == {
                k: v for k, v in replicas[mode].items() if k not in ('mode', 'advance_ms')}
        assert r['scope'] == 'ENGINEERING_FIXTURE' and r['exact_continuation'] == '1'
        assert number(r, 'schema_version') == 7 and number(r, 'physics_version') == 8
        assert number(r, 'simulation_ms') == duration
        assert number(r, 'maximum_candidates') <= number(r, 'encounter_budget')
        zero_residuals(r)
        people = evidence['individuals'][case]
        assert len(people) == 45 and {number(p, 'entity_id') for p in people} == set(range(2, 47))
        counts = Counter(number(p, 'final_stage') for p in people)
        assert 45-counts[4] == number(r, 'population.alive')
        assert counts[4] == number(r, 'population.dead_retained') == number(r, 'life.deaths')
        for stage, metric in ((0, 'population.egg'), (1, 'population.larva'), (2, 'population.pupa')):
            assert counts[stage] == number(r, metric)
        assert sum(number(p, 'caste') == 0 and number(p, 'final_stage') == 3 for p in people) == number(r, 'population.worker_alive')
        for p in people:
            dead = number(p, 'death_ms') >= 0
            assert dead == (number(p, 'final_stage') == 4)
            assert sum(number(p, k) for k in RESIDENCE) == (number(p, 'death_ms') if dead else duration)
            transitions = [number(p, k) for k in ('larva_ms', 'pupa_ms', 'adult_ms', 'death_ms') if number(p, k) >= 0]
            assert transitions == sorted(transitions) and all(t <= duration for t in transitions)
        for pfield, metric in [('body_energy_nj', 'body.energy'), ('hydration_ug', 'body.water'),
                               ('tissue_protein_ug', 'body.tissue_protein')]:
            assert sum(number(p, pfield) for p in people) == number(r, metric)
        for ingredient in INGREDIENTS:
            assert sum(number(p, f'crop_{ingredient}_ug') for p in people) == number(r, 'crop.'+ingredient)
        assert sum(number(p, 'adult_ms') >= 0 for p in people) == number(r, 'life.emerged')
        events = evidence['events'][case]
        ids = [number(e, 'event_id') for e in events]
        assert ids == sorted(set(ids)) and all(0 <= number(e, 'time_ms') <= duration for e in events)
        events_by_id = {number(e, 'event_id'): e for e in events}
        event_counts = evidence['event_counts'][case]
        by_kind = {number(e, 'kind'): number(e, 'events') for e in event_counts}
        assert len(by_kind) == len(event_counts) and sum(by_kind.values()) == number(r, 'events')
        assert by_kind[2] == 45 and by_kind.get(8, 0) == counts[4]
        selected_counts = Counter(number(e, 'kind') for e in events)
        for kind in (5, 7, 8, 12, 17, 19, 20, 21, 23, 24, 25, 26):
            assert selected_counts[kind] == by_kind.get(kind, 0)
        transfers = [e for e in events if e['kind'] == '21']
        protein = sum(number(e, 'protein_ug') for e in transfers)
        assert protein == sum(number(p, 'received_protein_ug') for p in people) == sum(number(p, 'given_protein_ug') for p in people)
        assert sum(sum(number(e, i+'_ug') for i in INGREDIENTS) for e in transfers) == number(r, 'nutrition.internal_transfer')
        for p in people:
            actor = p['entity_id']
            assert sum(number(e, 'protein_ug') for e in transfers if e['actor_id'] == actor) == number(p, 'given_protein_ug')
            assert sum(number(e, 'protein_ug') for e in transfers if e['payload'] == actor) == number(p, 'received_protein_ug')
            for stage, field in ((1, 'larva_ms'), (2, 'pupa_ms'), (3, 'adult_ms')):
                observed = [number(e, 'time_ms') for e in events if e['actor_id'] == actor and e['kind'] == '7' and number(e, 'stage') == stage]
                assert observed == ([] if number(p, field) < 0 else [number(p, field)])
            death = [number(e, 'time_ms') for e in events if e['actor_id'] == actor and e['kind'] == '8']
            assert death == ([] if number(p, 'death_ms') < 0 else [number(p, 'death_ms')])
        for kind, flow in ((5, 'collected'), (12, 'delivered')):
            for ingredient in INGREDIENTS[:3]:
                assert sum(number(e, ingredient+'_ug') for e in events if number(e, 'kind') == kind) == number(r, 'food.'+flow+'_'+ingredient)
        geom = evidence['geometry'][case]
        assert len(geom) == number(r, 'geometry.edit_count')
        assert [number(g, 'edit_id') for g in geom] == list(range(1, len(geom)+1))
        # Independent finite-fixture audit, not a replacement geometry authority.
        # An edit box can overlap existing void: volume is actual material, not
        # the raw bounding-box volume. Reconstruct every ordered cut/fill.
        shape = configuration['geometry']
        rocks = set().union(*(box_cells(b) for b in shape['sealed_rocks_q'])) if r['condition'] == 'sealed' else set()
        soil = box_cells(shape['initial_solid_q'])-box_cells(shape['chamber_q'])-rocks
        if r['condition'] != 'sealed':
            soil -= box_cells(shape['passage_q'])
        assert len(soil) == number(r, 'soil_initial_q3')
        for g in geom:
            e = events_by_id[number(g, 'event_id')]
            assert all(e[k] == g[k] for k in ('source_id', 'actor_id', 'time_ms'))
            assert number(e, 'kind') == (23 if g['kind'] == '0' else 26)
            patch = box_cells([[number(g, side+'_'+a+'_q') for a in 'xyz'] for side in ('min', 'max')])
            assert not (patch & rocks), 'edit intersects immutable rock'
            actual = patch & soil if g['kind'] == '0' else patch-soil
            assert len(actual) == number(g, 'volume_q3') > 0
            if g['kind'] == '0':
                soil -= patch
            else:
                soil |= patch
        assert len(soil) == number(r, 'soil_remaining_q3')
        assert sum(number(g, 'volume_q3') for g in geom if g['kind'] == '0') == number(r, 'excavated_q3')
        assert sum(number(g, 'volume_q3') for g in geom if g['kind'] == '1') == number(r, 'filled_q3')
        foods = evidence['foods'][case]
        assert len(foods) == (0 if r['condition'] == 'food_absent' else 2)
        for ingredient in INGREDIENTS:
            assert sum(number(f, 'remaining_'+ingredient+'_ug') for f in foods) == number(r, 'environment_food.'+ingredient)
            introduced = sum(number(f, 'initial_'+ingredient+'_ug') for f in foods)
            introduced += {'carbs': 0, 'protein': 200, 'water': 45000, 'other': 0}[ingredient]
            assert introduced == number(r, ingredient+'_introduced_ug')
            inventory = sum(number(r, prefix+ingredient) for prefix in ('environment_food.', 'cargo.', 'nest_food.', 'crop.'))
            inventory += (number(r, 'sink.oxidized_carbs') if ingredient == 'carbs' else
                          number(r, 'body.tissue_protein') if ingredient == 'protein' else
                          number(r, 'body.water')+number(r, 'sink.lost_water') if ingredient == 'water' else 0)
            assert inventory == introduced
        assert number(r, 'energy_input_nj') == 45000000000+number(r, 'sink.oxidized_carbs')*1000000
        assert number(r, 'energy_input_nj') == number(r, 'body.energy')+number(r, 'sink.dissipated_energy')
        assert number(r, 'soil_initial_q3') == sum(number(r, 'soil_'+s+'_q3') for s in ('remaining', 'carried', 'deposited'))
        assert number(r, 'soil_initial_q3')+number(r, 'filled_q3') == number(r, 'soil_remaining_q3')+number(r, 'excavated_q3')
        series = evidence['time_series'][case]
        assert [number(t, 'time_ms') for t in series] == list(range(0, duration+1, 10000))
        assert series[-1]['event_cursor'] == r['events']
        for field in r:
            if '.' in field:
                assert series[-1][field] == r[field]
        for t in series:
            assert number(t, 'population.alive')+number(t, 'population.dead_retained') == 45
            assert sum(number(t, 'population.'+s) for s in ('worker_alive', 'queen_alive', 'male_alive', 'egg', 'larva', 'pupa')) == number(t, 'population.alive')
            for ingredient in INGREDIENTS:
                inventory = sum(number(t, prefix+ingredient) for prefix in ('environment_food.', 'cargo.', 'nest_food.', 'crop.'))
                inventory += (number(t, 'sink.oxidized_carbs') if ingredient == 'carbs' else
                              number(t, 'body.tissue_protein') if ingredient == 'protein' else
                              number(t, 'body.water')+number(t, 'sink.lost_water') if ingredient == 'water' else 0)
                assert inventory == number(r, ingredient+'_introduced_ug'), 'intermediate nutrition imbalance'
            assert number(t, 'body.energy')+number(t, 'sink.dissipated_energy') == 45000000000+number(t, 'sink.oxidized_carbs')*1000000
            assert sum(number(t, 'soil.'+s) for s in ('remaining', 'carried', 'deposited')) == number(r, 'soil_initial_q3')
            assert number(t, 'excavation.dry') == 4*number(t, 'excavation.water')
            assert number(t, 'fill.dry') == 4*number(t, 'fill.water')
            assert number(t, 'nest.void_volume') == number(series[0], 'nest.void_volume')+(number(t, 'excavation.dry')-number(t, 'fill.dry'))//100
        if r['condition'] in ('sealed', 'food_absent'):
            assert number(r, 'food_collections') == number(r, 'food_deliveries') == 0
        if r['condition'] == 'sealed':
            assert number(r, 'excavated_q3') == 0
        initial_workers = [p for p in people if p['caste'] == '0' and p['seed_stage'] == '3']
        assert len(initial_workers) == 32
        lived = sum(sum(number(p, f) for f in RESIDENCE) for p in initial_workers)
        active = sum(sum(number(p, f) for f in ('nurse_ms', 'forage_ms', 'excavate_ms')) for p in initial_workers)
        analyzed.append(dict(r, initial_worker_active_fraction=active/lived,
                             initial_worker_observed_survival_s=lived/32000,
                             deaths_energy=sum(p['death_cause'] == '1' for p in people),
                             deaths_water=sum(p['death_cause'] == '2' for p in people),
                             unemerged_brood=sum(p['seed_stage'] != '3' and p['adult_ms'] == '-1' for p in people),
                             brood_unmet_protein_ug=sum(max(0, 100-number(p, 'crop_protein_ug')-number(p, 'tissue_protein_ug'))
                                                        for p in people if p['final_stage'] == '1'),
                             dead_crop_protein_ug=sum(number(p, 'crop_protein_ug') for p in people if p['final_stage'] == '4')))
    print(f'PASS S6 {suite}: {len(cases)} cases / {len(raw)} modes; identity, event, geometry and integer ledger reconciliation')
    return analyzed, evidence['time_series']


def integration_statistics(data):
    results = []
    groups = defaultdict(lambda: defaultdict(list))
    for row in data:
        groups[(row['suite'], row['condition'], row['encounter_budget'])][int(row['seed'])].append(row)
    seed_values = {}
    for (suite, condition, budget), per_seed in sorted(groups.items()):
        for metric in METRICS+DERIVED_METRICS:
            values = [statistics.mean(float(r[metric]) for r in per_seed[s]) for s in sorted(per_seed)]
            seed_values[(suite, condition, budget, metric)] = values
            results.append(dict(suite=suite, condition=condition, encounter_budget=budget,
                                comparison='endpoint', metric=metric, **interval(values)))
    for condition in CONDITIONS[1:]:
        for metric in METRICS+DERIVED_METRICS:
            a = seed_values[('primary', 'supplied', '16', metric)]
            b = seed_values[('primary', condition, '16', metric)]
            results.append(dict(suite='primary', condition='supplied-minus-'+condition, encounter_budget='16',
                                comparison='paired_difference', metric=metric,
                                **interval([x-y for x, y in zip(a, b, strict=True)])))
    for budget in ('8', '32'):
        for metric in METRICS+DERIVED_METRICS:
            a = seed_values[('sensitivity', 'supplied', budget, metric)]
            b = seed_values[('sensitivity', 'supplied', '16', metric)]
            results.append(dict(suite='sensitivity', condition='supplied', encounter_budget=budget+'-minus-16',
                                comparison='paired_difference', metric=metric,
                                **interval([x-y for x, y in zip(a, b, strict=True)])))
    for metric in METRICS+DERIVED_METRICS:
        a = seed_values[('long', 'supplied', '16', metric)]
        b = seed_values[('long', 'food_absent', '16', metric)]
        results.append(dict(suite='long', condition='supplied-minus-food_absent', encounter_budget='16',
                            comparison='paired_difference', metric=metric,
                            **interval([x-y for x, y in zip(a, b, strict=True)])))
    return results


def nutrition_statistics(root, case_rows=None):
    result = []
    for archive in ('nutrition', 'nutrition_final'):
        data = read(root/archive/'summary.csv')
        assert len(data) == 768
        keys = {(r['seed'], r['policy'], r['seed_stage'], r['protein_per_nurse_ug']) for r in data}
        assert keys == {(str(s), p, stage, str(protein)) for s in range(1, 65)
                        for p in ('legacy', 'local_demand') for stage in ('egg', 'larva') for protein in (0, 100, 400)}
        people = read(root/archive/'individuals.csv')
        assert len(people) == 3072
        by_case = defaultdict(list)
        for p in people:
            by_case[(p['seed'], p['policy'], p['seed_stage'], p['protein_per_nurse_ug'])].append(p)
        for r in data:
            assert r['scope'] == 'ENGINEERING_FIXTURE'
            zero_residuals(r)
            group = by_case[(r['seed'], r['policy'], r['seed_stage'], r['protein_per_nurse_ug'])]
            assert len(group) == 4 and len({p['id'] for p in group}) == 4
            assert sum(number(p, 'stage') == 3 for p in group) == number(r, 'adult_brood')
            assert sum(number(p, 'received_protein_ug') for p in group) == number(r, 'protein_transfer_ug')
            unmet = sum(max(0, 100-number(p, 'crop_protein_ug')-number(p, 'tissue_protein_ug'))
                        for p in group if p['stage'] == '1')
            surplus = number(r, 'nurse_protein_ug') + sum(
                max(0, number(p, 'crop_protein_ug')+number(p, 'tissue_protein_ug')-100) for p in group)
            assert number(r, 'deaths') == 0, 'surplus audit assumes all matched colocated donors remain living'
            if case_rows is not None:
                case_rows.append(dict(archive=archive, seed=r['seed'], policy=r['policy'], seed_stage=r['seed_stage'],
                                      protein_per_nurse_ug=r['protein_per_nurse_ug'], adult_brood=r['adult_brood'],
                                      unmet_larval_protein_ug=unmet, locally_accessible_surplus_ug=surplus,
                                      shortfall_with_surplus=int(unmet > 0 and surplus > 0)))
            if r['policy'] == 'local_demand':
                assert r['oversupplied_brood'] == '0'
                assert all(number(p, 'received_protein_ug') <= 100 for p in group)
        for stage in ('egg', 'larva'):
            for protein in (0, 100, 400):
                for policy in ('legacy', 'local_demand'):
                    selected = [r for r in data if r['seed_stage'] == stage and r['protein_per_nurse_ug'] == str(protein) and r['policy'] == policy]
                    for metric in ('adult_brood', 'oversupplied_brood', 'protein_transfer_ug', 'nurse_protein_ug'):
                        result.append(dict(archive=archive, stage=stage, protein_per_nurse_ug=protein,
                                           policy=policy, metric=metric, **interval([number(r, metric) for r in selected])))
                for metric in ('adult_brood', 'oversupplied_brood', 'protein_transfer_ug', 'nurse_protein_ug'):
                    pairs = {policy: {int(r['seed']): number(r, metric) for r in data
                                      if r['seed_stage'] == stage and int(r['protein_per_nurse_ug']) == protein and r['policy'] == policy}
                             for policy in ('legacy', 'local_demand')}
                    values = [pairs['local_demand'][s]-pairs['legacy'][s] for s in range(1, 65)]
                    result.append(dict(archive=archive, stage=stage, protein_per_nurse_ug=protein,
                                       policy='local-minus-legacy', metric=metric, **interval(values)))
        legacy43 = next(r for r in data if (r['seed'], r['policy'], r['seed_stage'], r['protein_per_nurse_ug']) == ('43', 'legacy', 'egg', '400'))
        assert legacy43['adult_brood'] == '3', 'preserve seed-43 baseline failure'
    return result


def surplus_statistics(root):
    result = []
    for archive in ('surplus', 'surplus_sensitivity'):
        data = read(root/archive/'summary.csv')
        n = 64 if archive == 'surplus' else 16
        conditions = ('contact', 'wall', 'range', 'no_response', 'no_protein') if n == 64 else ('contact',)
        budgets = (16,) if n == 64 else (8, 16, 32)
        keys = {(int(r['seed']), r['condition'], r['initial_donor_stage'], int(r['encounter_budget'])) for r in data}
        assert len(keys) == len(data) and keys == {(s, c, stage, b) for s in range(1, n+1)
                                                  for c in conditions for stage in ('adult', 'pupa') for b in budgets}
        transferred = defaultdict(int)
        for e in read(root/archive/'events.csv'):
            if e['kind'] == '21':
                transferred[(int(e['seed']), e['condition'], e['initial_donor_stage'], int(e['encounter_budget']))] += int(e['protein_ug'])
        for r in data:
            zero_residuals(r)
            assert r['scope'] == 'ENGINEERING_FIXTURE' and r['donor_id'] == '2'
            k = (int(r['seed']), r['condition'], r['initial_donor_stage'], int(r['encounter_budget']))
            assert transferred[k] == int(r['protein_transferred_ug'])
            if r['condition'] != 'contact':
                assert r['protein_transferred_ug'] == '0' and r['adult_recipients'] == '0'
        for c in conditions:
            for stage in ('adult', 'pupa'):
                for b in budgets:
                    group = [r for r in data if r['condition'] == c and r['initial_donor_stage'] == stage and int(r['encounter_budget']) == b]
                    successes = sum(r['adult_recipients'] == '2' for r in group)
                    low, high = wilson(successes, n)
                    for metric in ('adult_recipients', 'protein_transferred_ug', 'total_transferred_ug'):
                        result.append(dict(archive=archive, condition=c, initial_donor_stage=stage, encounter_budget=b,
                                           metric=metric, **interval([number(r, metric) for r in group]),
                                           all_recipient_emergence_cases=successes,
                                           success_rate=successes/n, success_wilson95_low=low, success_wilson95_high=high))
    return result


def contact_statistics(root, archives=('contact_initial', 'performance')):
    result, acceptance = [], {}
    for archive in archives:
        data = read(root/archive/'contacts.csv')
        expected = {(n, layout, policy, rep) for n in (128, 512, 2048) for layout in ('dense', 'dispersed')
                    for policy in ('exhaustive', 'bounded') for rep in range(10)}
        assert len(data) == 120 and {(int(r['population']), r['layout'], r['policy'], int(r['repetition'])) for r in data} == expected
        indexed = {(int(r['population']), r['layout'], r['policy'], int(r['repetition'])): r for r in data}
        for n in (128, 512, 2048):
            for layout in ('dense', 'dispersed'):
                for rep in range(10):
                    a, b = (indexed[(n, layout, policy, rep)] for policy in ('exhaustive', 'bounded'))
                    for field in ('events', 'pending', 'decisions', 'checkpoint_bytes'):
                        assert a[field] == b[field], 'contact speedup removed physical work or history'
                    assert int(a['candidates']) == int(a['decisions'])*n
                    assert int(b['bucket_queries']) == int(b['decisions'])*27
        medians = {}
        for n in (128, 512, 2048):
            for layout in ('dense', 'dispersed'):
                for policy in ('exhaustive', 'bounded'):
                    group = [r for r in data if int(r['population']) == n and r['layout'] == layout and r['policy'] == policy]
                    for r in group:
                        assert r['scope'] == 'ENGINEERING_FIXTURE' and r['simulation_ms'] == '10000'
                        assert int(r['peak_resident_bytes']) >= int(r['resident_bytes']) > 0
                        if policy == 'bounded':
                            assert int(r['maximum_candidates']) <= 16 and int(r['candidates']) <= 16*int(r['decisions'])
                    for metric in ('setup_ms', 'advance_ms', 'encode_ms', 'restore_ms', 'checkpoint_bytes',
                                   'resident_bytes', 'peak_resident_bytes', 'events', 'decisions', 'candidates', 'tree_visits'):
                        values = [float(r[metric]) for r in group]
                        result.append(dict(archive=archive, population=n, layout=layout, policy=policy, metric=metric,
                                           samples=10, p50=statistics.median(values), p95=quantile(values, .95),
                                           p99=quantile(values, .99), maximum=max(values)))
                        if metric == 'advance_ms':
                            medians[(n, layout, policy)] = statistics.median(values)
        speedup = medians[(2048, 'dense', 'exhaustive')]/medians[(2048, 'dense', 'bounded')]
        growth = medians[(2048, 'dense', 'bounded')]/medians[(512, 'dense', 'bounded')]
        acceptance[archive] = dict(bounded_candidates='PASS', dense_2048_speedup=speedup,
                                  speedup_at_least_4x='PASS' if speedup >= 4 else 'FAIL',
                                  dense_512_to_2048_growth=growth,
                                  growth_at_most_6x='PASS' if growth <= 6 else 'FAIL')
    return result, acceptance


def emit(path, data, check):
    if check:
        expected = [{k: str(v) for k, v in row.items()} for row in data]
        assert read(path) == expected, f'stale derived evidence: {path}'
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, list(data[0]), lineterminator='\n')
            writer.writeheader()
            writer.writerows(data)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=ROOT/'experiments/s6')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    root = args.root
    data = []
    for directory, suite, seeds, duration in [('integrated', 'primary', 32, 600000),
                                             ('sensitivity', 'sensitivity', 16, 600000), ('long', 'long', 8, 1800000)]:
        rows, _ = audit_integration(root, directory, suite, seeds, duration)
        data.extend(rows)
    primary_reference = {r['seed']: r for r in data if r['suite'] == 'primary' and r['condition'] == 'supplied' and r['mirror'] == '0'}
    excluded = {'suite', 'setup_ms', 'advance_ms', 'save_ms', 'load_ms', 'database_bytes'}
    for row in data:
        if row['suite'] == 'sensitivity' and row['encounter_budget'] == '16':
            expected = primary_reference[row['seed']]
            assert {k: v for k, v in row.items() if k not in excluded} == {
                k: v for k, v in expected.items() if k not in excluded}, 'default-budget sensitivity changed the primary fixture'
    nutrition_cases = []
    nutrition = nutrition_statistics(root, nutrition_cases)
    surplus = surplus_statistics(root)
    performance, acceptance = contact_statistics(root)
    verification = json.loads((root/'verification.json').read_text(encoding='utf-8'))
    executions = read(root/'executed_tests.csv')
    assert len(executions) == verification['test_rows'] == 601
    assert all(r['result'] == 'Passed' for r in executions)
    for build in verification['local_builds']:
        tests = [r for r in executions if r['configuration'] == build['configuration']]
        assert len(tests) == build['tests'] == build['passed'] and build['failed'] == 0
        assert len({r['test'] for r in tests}) == len(tests)
        assert all(r['source_commit'] == build['source_commit'] for r in tests)
    assert hashlib.sha256((root/'executed_tests.csv').read_text(encoding='utf-8').encode()).hexdigest() == verification['test_rows_sha256']
    assert len(verification['github_source_ci']['jobs']) == 5
    assert all(j['conclusion'] == 'success' for j in verification['github_source_ci']['jobs'])
    emit(root/'analysis/ecology.csv', integration_statistics(data), args.check)
    emit(root/'analysis/nutrition.csv', nutrition, args.check)
    emit(root/'analysis/nutrition_cases.csv', nutrition_cases, args.check)
    emit(root/'analysis/surplus.csv', surplus, args.check)
    emit(root/'analysis/contact_quantiles.csv', performance, args.check)
    directories = ('baseline', 'nutrition', 'nutrition_final', 'surplus', 'surplus_sensitivity',
                   'integrated', 'sensitivity', 'long', 'contact_initial', 'performance')
    paths = sorted(p for d in directories for p in (root/d).glob('*') if p.suffix in ('.csv', '.json'))
    hashes = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_text(encoding='utf-8').encode()).hexdigest() for p in paths}
    report = dict(scope='ENGINEERING_FIXTURE', primary_cases=256, sensitivity_cases=48, long_cases=16,
                  paired_execution_modes=960, nutrition_cases_per_archive=768, surplus_cases=640,
                  exact_primary_sensitivity_baseline_pairs=16,
                  surplus_sensitivity_cases=96, independent_primary_seeds=32, bootstrap_resamples=4096,
                  analysis_seed=6006, confidence='95% percentile bootstrap; mirrors averaged within seed; modes paired',
                  conservation_identity_history_continuation='PASS', contact_acceptance=acceptance,
                  normalized_lf_sha256=hashes)
    path = root/'analysis/audit.json'
    if args.check:
        assert json.loads(path.read_text(encoding='utf-8')) == report
    else:
        path.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'normalized_lf_sha256'}, indent=2))


if __name__ == '__main__':
    main()
