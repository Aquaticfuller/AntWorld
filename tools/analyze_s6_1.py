"""Independently reconcile S6.1 evidence and compute frozen paired-seed intervals."""
import argparse
import csv
import hashlib
import itertools
import json
import math
import random
import statistics
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

import analyze_s6 as previous
from archive_s6_1 import rows, verify

ROOT = Path(__file__).resolve().parents[1]
KEY = ('suite', 'seed', 'policy', 'workers', 'source_protein_ug', 'budget',
       'minimum_ms', 'condition', 'mirror')
ARMS = ('legacy', 'gift_first', 'local_continuation', 'combined')
METRICS = ('emerged', 'unemerged_brood', 'unmet_integral_ug_s',
           'accessible_demand_integral_ug_s', 'accessible_supply_integral_ug_s',
           'adult_crop_protein_ug', 'dead_crop_protein_ug', 'given_protein_ug',
           'gift_attempts', 'gift_completion_fraction', 'gift_failed',
           'program_switches', 'nurse_exits_with_sampled_work', 'nest_intakes',
           'active_fraction', 'away_fraction', 'blocked_fraction', 'moves',
           'excavated_q3', 'living')


def key(row):
    return tuple(row[f] for f in KEY)


def integer(row, field):
    return int(row[field])


class Groups:
    """The native exporter writes complete cases consecutively; keep one in RAM."""
    def __init__(self, base, name):
        self.iterator = iter(itertools.groupby(rows(base, name), key))
        self.current = next(self.iterator, None)

    def take(self, case):
        if self.current is None or self.current[0] != case:
            return []
        result = list(self.current[1])
        self.current = next(self.iterator, None)
        return result


@lru_cache(maxsize=None)
def resamples(n):
    rng = random.Random(6106)
    return tuple(tuple(rng.randrange(n) for _ in range(n)) for _ in range(4096))


def interval(values):
    values = list(values)
    defined = [v for v in values if math.isfinite(v)]
    if not defined:
        return dict(independent_seeds=len(values), defined_seeds=0, mean='NA',
                    ci95_low='NA', ci95_high='NA', minimum='NA', maximum='NA')
    means = [math.fsum(defined[i] for i in sample)/len(defined) for sample in resamples(len(defined))]
    return dict(independent_seeds=len(values), defined_seeds=len(defined), mean=statistics.mean(defined),
                ci95_low=previous.quantile(means, .025), ci95_high=previous.quantile(means, .975),
                minimum=min(defined), maximum=max(defined))


def expected(suite, seeds):
    settings = ([(p, w, n, 16, 10000, 'supplied', 0) for p in ARMS
                 for w in (8, 32, 128) for n in (0, 500, 2000)] if suite == 'matrix' else
                [(p, 32, 2000, b, m, 'supplied', 0) for p in ('legacy', 'combined')
                 for b, m in ((8, 10000), (16, 5000), (16, 20000), (32, 10000))]
                if suite == 'sensitivity' else
                [(p, 32, 2000, 16, 10000, c, m) for p in ('legacy', 'combined')
                 for m in (0, 1) for c in previous.CONDITIONS])
    return {(suite, str(s), *(str(v) for v in setting)) for s in range(1, seeds+1) for setting in settings}


def audit_observer(base, suite, seeds, shape):
    if (base/'archive.json').exists():
        verify(base)
    config = json.loads((base/'configuration.json').read_text(encoding='utf-8'))
    assert config['scope'] == 'ENGINEERING_FIXTURE' and config['seeds'] == seeds
    assert config['suite'] == suite and config['schema'] == 8 and config['physics'] == 9
    summaries = list(rows(base, 'summary'))
    assert len(summaries) == len(expected(suite, seeds))
    assert {key(r) for r in summaries} == expected(suite, seeds)
    cursors = {name: Groups(base, name) for name in
               ('time_series', 'events', 'decisions', 'individuals', 'event_counts', 'geometry')}
    duration = 600000 if suite == 'integrated' else 180000
    results, causes = [], []
    for r in summaries:
        case = key(r)
        data = {name: cursor.take(case) for name, cursor in cursors.items()}
        series, events, decisions = (data[name] for name in ('time_series', 'events', 'decisions'))
        people, counts, geom = (data[name] for name in ('individuals', 'event_counts', 'geometry'))
        assert integer(r, 'duration_ms') == duration
        previous.zero_residuals(r)
        workers = integer(r, 'workers')
        assert len(people) == workers+13
        assert {integer(p, 'entity_id') for p in people} == set(range(2, workers+15))
        assert sum(p['final_stage'] != '4' for p in people) == integer(r, 'living')
        assert sum(p['adult_ms'] != '-1' for p in people) == integer(r, 'emerged')
        assert sum(p['seed_stage'] != '3' and p['adult_ms'] == '-1' for p in people) == integer(r, 'unemerged_brood')
        assert sum(integer(p, 'crop_protein_ug') for p in people if p['final_stage'] == '4') == integer(r, 'dead_crop_protein_ug')
        assert sum(integer(p, 'crop_protein_ug') for p in people if p['final_stage'] == '3') == integer(r, 'adult_crop_protein_ug')
        by_kind = {integer(c, 'kind'): integer(c, 'count') for c in counts}
        assert len(by_kind) == len(counts) and sum(by_kind.values()) == integer(r, 'events')
        assert by_kind[2] == workers+13
        selected = Counter(integer(e, 'kind') for e in events)
        for kind in (5, 6, 7, 8, 12, 17, 20, 21, 23, 24, 25, 26):
            assert selected[kind] == by_kind.get(kind, 0), (case, kind)
        ids = [integer(e, 'event_id') for e in events]
        assert ids == sorted(set(ids))
        assert all(0 <= integer(e, 'time_ms') <= duration and 2 <= integer(e, 'actor') < workers+15 for e in events)
        gifts = [e for e in events if e['scheduled_kind'] == '12']
        assert len(gifts) == integer(r, 'gift_attempts')
        assert sum(e['kind'] != '21' for e in gifts) == integer(r, 'gift_failed')
        assert sum(e['kind'] == '21' for e in gifts) == integer(r, 'gift_success')+integer(r, 'gift_partial')
        assert sum(integer(e, 'protein_ug') for e in gifts if e['kind'] == '21') == integer(r, 'given_protein_ug')
        assert selected[20] == integer(r, 'nest_intakes') and selected[17] == integer(r, 'program_switches')
        assert by_kind.get(4, 0) == integer(r, 'moves')
        assert by_kind.get(31, 0) == len(decisions) == integer(r, 'autonomy_decisions')
        assert sum(d['can_switch'] == '0' for d in decisions) == integer(r, 'blocked_travel_decisions')
        assert sum(d['can_switch'] == '1' and d['ready'] == '0' for d in decisions) == integer(r, 'minimum_time_decisions')
        exits = [d for d in decisions if d['program_before'] == '2' and d['program_after'] != '2' and d['crop_compatible_work'] == '1']
        assert len(exits) == integer(r, 'nurse_exits_with_sampled_work')
        for d in decisions:
            assert integer(d, 'actual_contacts') <= integer(d, 'actual_candidates') <= integer(r, 'budget')
            if r['policy'] in ('local_continuation', 'combined') and d['program_before'] == '2' and d['crop_compatible_work'] == '1' and d['urgent'] == '0':
                assert d['program_after'] == '2', (case, 'compatible work abandoned')
        by_actor = defaultdict(list)
        for event in events:
            by_actor[event['actor']].append(event)
        for p in people:
            actor = p['entity_id']
            transitions = by_actor[actor]
            adult = [integer(e, 'time_ms') for e in transitions if e['kind'] == '7' and e['stage'] == '3']
            death = [integer(e, 'time_ms') for e in transitions if e['kind'] == '8']
            assert adult == ([] if p['adult_ms'] == '-1' else [integer(p, 'adult_ms')])
            assert death == ([] if p['death_ms'] == '-1' else [integer(p, 'death_ms')])
            assert (p['final_stage'] == '4') == bool(death)
        # Rebuild initial-worker task residence from facts, independently of the
        # observer's event-boundary duration counter.
        living_ms, active_ms = 0, 0
        for actor in range(3, workers+3):
            p = next(p for p in people if integer(p, 'entity_id') == actor)
            end = integer(p, 'death_ms') if p['death_ms'] != '-1' else duration
            living_ms += end
            changed, program = 0, 0
            for e in by_actor[str(actor)]:
                if e['kind'] in ('17', '8'):
                    t = integer(e, 'time_ms')
                    if program >= 2:
                        active_ms += t-changed
                    changed, program = t, (0 if e['kind'] == '8' else integer(e, 'payload'))
            if program >= 2:
                active_ms += end-changed
        assert living_ms == integer(r, 'initial_worker_living_ms')
        assert active_ms == integer(r, 'initial_worker_active_ms')
        assert 0 <= integer(r, 'initial_worker_away_ms') <= living_ms
        assert [integer(t, 'time_ms') for t in series] == list(range(0, duration+1, 1000))
        assert sum(integer(t, 'unmet_protein_ug') for t in series[:-1]) == integer(r, 'unmet_integral_ug_s')
        contact = [t for t in series if t['accessible_sample'] == '1']
        assert len(contact) == duration//10000+1
        for field in ('demand', 'supply'):
            assert 10*sum(integer(t, 'accessible_'+field+'_ug') for t in contact[:-1]) == integer(r, 'accessible_'+field+'_integral_ug_s')
        for t in series:
            for ingredient, singular in (('carbs', 'carb'), ('protein', 'protein'), ('water', 'water'), ('other', 'other')):
                inventory = sum(integer(t, location+'_'+ingredient+'_ug') for location in ('available', 'stored', 'carried', 'crop'))
                inventory += (integer(t, 'oxidized_carbs_ug') if ingredient == 'carbs' else
                              integer(t, 'tissue_protein_ug') if ingredient == 'protein' else
                              integer(t, 'hydration_ug')+integer(t, 'lost_water_ug') if ingredient == 'water' else 0)
                assert inventory == integer(t, singular+'_introduced_ug') == integer(t, singular+'_accounted_ug')
            assert integer(t, 'energy_input_nj') == (workers+13)*1000000000+integer(t, 'oxidized_carbs_ug')*1000000
            assert integer(t, 'energy_input_nj') == integer(t, 'body_energy_nj')+integer(t, 'dissipated_energy_nj')
            assert integer(t, 'soil_initial_q3') == sum(integer(t, 'soil_'+name+'_q3') for name in ('remaining', 'carried', 'deposited'))
            assert integer(t, 'soil_initial_q3')+integer(t, 'soil_filled_q3') == integer(t, 'soil_remaining_q3')+integer(t, 'excavated_q3')
        final = series[-1]
        for f in ('living', 'emerged', 'unmet_protein_ug', 'adult_crop_protein_ug', 'dead_crop_protein_ug',
                  'gift_attempts', 'gift_success', 'gift_partial', 'gift_failed', 'given_protein_ug', 'program_switches', 'moves', 'excavated_q3'):
            assert r[f] == final[f], (case, f)
        for ingredient in ('carbs', 'protein', 'water', 'other'):
            assert sum(integer(p, 'crop_'+ingredient+'_ug') for p in people) == integer(final, 'crop_'+ingredient+'_ug')
        for f, g in (('body_energy_nj', 'body_energy_nj'), ('hydration_ug', 'hydration_ug'), ('tissue_protein_ug', 'tissue_protein_ug')):
            assert sum(integer(p, f) for p in people) == integer(final, g)
        # Reconstruct authoritative ordered edits on this finite integer fixture.
        rocks = set().union(*(previous.box_cells(b) for b in shape['sealed_rocks_q'])) if r['condition'] == 'sealed' else set()
        soil = previous.box_cells(shape['initial_solid_q'])-previous.box_cells(shape['chamber_q'])-rocks
        if r['condition'] != 'sealed':
            soil -= previous.box_cells(shape['passage_q'])
        assert len(soil) == integer(final, 'soil_initial_q3')
        facts = {integer(e, 'event_id'): e for e in events}
        for index, g in enumerate(geom, 1):
            assert integer(g, 'edit_id') == index and g['kind'] in ('0', '3')
            e = facts[integer(g, 'event_id')]
            assert e['actor'] == g['actor_id'] and e['source_id'] == g['source_id'] and e['time_ms'] == g['time_ms']
            assert integer(e, 'kind') == (23 if g['kind'] == '0' else 26)
            patch = previous.box_cells([[integer(g, side+'_'+a+'_q') for a in 'xyz'] for side in ('min', 'max')])
            assert not patch & rocks
            assert len(patch & soil if g['kind'] == '0' else patch-soil) == integer(g, 'volume_q3') > 0
            soil = soil-patch if g['kind'] == '0' else soil|patch
        assert len(soil) == integer(final, 'soil_remaining_q3')
        assert sum(integer(g, 'volume_q3') for g in geom if g['kind'] == '0') == integer(r, 'excavated_q3')
        assert sum(integer(g, 'volume_q3') for g in geom if g['kind'] == '3') == integer(final, 'soil_filled_q3')
        n = integer(r, 'gift_attempts')
        results.append(dict(r, gift_completion_fraction=(integer(r, 'gift_success')+integer(r, 'gift_partial'))/n if n else math.nan,
                            active_fraction=active_ms/living_ms, away_fraction=integer(r, 'initial_worker_away_ms')/living_ms,
                            blocked_fraction=integer(r, 'blocked_travel_decisions')/max(1, len(decisions))))
        digs = [e for e in events if e['kind'] == '23']
        delivered = [integer(e, 'time_ms') for e in events if e['kind'] == '12']
        early_digs = sum(integer(e, 'time_ms') < min(delivered, default=duration+1) for e in digs)
        causes.append(dict(zip(KEY, case), first_delivery_ms=min(delivered, default=-1),
                           first_dig_ms=min((integer(e, 'time_ms') for e in digs), default=-1),
                           last_dig_ms=max((integer(e, 'time_ms') for e in digs), default=-1),
                           dig_events=len(digs), dig_events_before_first_delivery=early_digs,
                           eligible_decisions=sum(d['can_switch'] == d['ready'] == '1' for d in decisions),
                           nurse_decisions_with_compatible_work=sum(d['program_before'] == '2' and d['crop_compatible_work'] == '1' for d in decisions),
                           reachable_soil_decisions=sum(d['reachable_soil'] == '1' for d in decisions)))
    assert all(c.current is None for c in cursors.values()), 'unmatched trailing evidence'
    print(f'PASS observer {suite}: {len(results)} cases, complete row/ledger/identity/geometry reconciliation')
    return results, causes


def statistics_rows(data):
    groups = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for r in data:
        group = tuple(r[f] for f in ('suite', 'workers', 'source_protein_ug', 'budget', 'minimum_ms', 'condition'))
        groups[group][r['policy']][int(r['seed'])].append(r)
    result = []
    for group, arms in sorted(groups.items()):
        for metric in METRICS:
            values = {a: {s: statistics.mean(float(r[metric]) for r in records) for s, records in seeds.items()}
                      for a, seeds in arms.items()}
            for arm, by_seed in values.items():
                value = [by_seed[s] for s in sorted(by_seed)]
                result.append(dict(zip(('suite', 'workers', 'source_protein_ug', 'budget', 'minimum_ms', 'condition'), group),
                                   policy=arm, comparison='endpoint', metric=metric, **interval(value)))
                if arm != 'legacy':
                    assert set(by_seed) == set(values['legacy'])
                    delta = [by_seed[s]-values['legacy'][s] for s in sorted(by_seed)]
                    result.append(dict(zip(('suite', 'workers', 'source_protein_ug', 'budget', 'minimum_ms', 'condition'), group),
                                       policy=arm, comparison='minus_legacy', metric=metric, **interval(delta)))
    return result


def emit(path, data, check):
    previous.emit(path, data, check)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT/'experiments/s6_1')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--pilot', type=Path, help='audit a complete one-seed matrix without producing statistics')
    args = parser.parse_args()
    shape = json.loads((ROOT/'experiments/s6/integrated/configuration.json').read_text(encoding='utf-8'))['geometry']
    if args.pilot:
        audit_observer(args.pilot, 'matrix', 1, shape)
        return
    root = args.root
    data, causes = [], []
    for directory, suite, seeds in [('matrix', 'matrix', 16), ('sensitivity', 'sensitivity', 16),
                                     ('observer_integrated', 'integrated', 32)]:
        a, b = audit_observer(root/directory, suite, seeds, shape)
        data.extend(a)
        causes.extend(b)
    # Reuse the full S6 60-metric durable audit with explicit format versions;
    # historical S6 validation retains its original version defaults.
    durable = []
    for directory, suite, seeds, duration in [('integrated', 'primary', 32, 600000), ('long', 'long', 8, 1800000)]:
        a, _ = previous.audit_integration(root, directory, suite, seeds, duration, schema=8, physics=9)
        durable.extend(a)
    old = {tuple(r[f] for f in ('seed', 'condition', 'mirror')): r
           for r in previous.read(ROOT/'experiments/s6/integrated/summary.csv') if r['mode'] == 'normal'}
    new = {tuple(r[f] for f in ('seed', 'condition', 'mirror')): r for r in durable if r['suite'] == 'primary'}
    pairs = 0
    for r in data:
        if r['suite'] != 'integrated':
            continue
        k = tuple(r[f] for f in ('seed', 'condition', 'mirror'))
        reference = old[k] if r['policy'] == 'legacy' else new[k]
        for field, other in [('trace_hash', 'trace_hash'), ('events', 'events'), ('living', 'population.alive'),
                             ('emerged', 'life.emerged'), ('excavated_q3', 'excavated_q3'),
                             ('program_switches', 'behavior.changes'), ('moves', 'movement.moves')]:
            if other in reference:
                assert r[field] == reference[other], (k, r['policy'], field)
        if r['policy'] == 'combined':
            assert r['state_hash'] == reference['state_hash'], (k, 'observer versus durable state')
        pairs += 1
    assert pairs == 512
    output = root/'analysis'
    if not args.check:
        output.mkdir(exist_ok=True, parents=True)
    emit(output/'ecology.csv', statistics_rows(data), args.check)
    emit(output/'behavior_diagnosis.csv', causes, args.check)
    emit(output/'cases.csv', data, args.check)
    report = dict(scope='ENGINEERING_FIXTURE', matrix_cases=576, sensitivity_cases=128,
                  integrated_observer_cases=512, durable_cases=272, durable_execution_modes=816,
                  observer_durable_or_original_exact_trace_pairs=pairs, independent_integrated_seeds=32,
                  bootstrap_resamples=4096, analysis_seed=6106, conservation_identity_history_geometry='PASS',
                  confidence='95% paired seed percentile bootstrap; mirrors averaged within seed; modes are verification replicas',
                  accessible_integral='Unique reachable recipient demand and adult crop supply; coexistence diagnostic, not maximum feasible flow',
                  gift_completion_fraction='Successful plus partial committed transfers / resolved attempts; undefined with zero attempts. Conditional intervals show defined seed counts; every raw case and attempt count is retained.')
    text = json.dumps(report, indent=2)+'\n'
    if args.check:
        assert (output/'audit.json').read_text(encoding='utf-8') == text
    else:
        (output/'audit.json').write_text(text, encoding='utf-8', newline='\n')
    print(text)


if __name__ == '__main__':
    main()
