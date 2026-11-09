"""Reconcile ordered scarcity evidence with every declared S6.1 case and equal-demand choice."""
import argparse
import hashlib
import json
import random
import statistics as st
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

from archive_s6_1 import rows, verify
from analyze_s6 import emit, quantile, read

ROOT = Path(__file__).resolve().parents[1]
KEY = ('seed', 'workers', 'source_protein_ug', 'policy')


def key(r):
    return tuple(r[k] for k in KEY)


@lru_cache(None)
def resamples(n):
    rng = random.Random(6206)
    return [[rng.randrange(n) for _ in range(n)] for _ in range(4096)]


def interval(values):
    sampled = [sum(values[i] for i in sample)/len(sample) for sample in resamples(len(values))]
    return dict(n_seeds=len(values), mean=st.mean(values),
                ci_low=quantile(sampled, .025), ci_high=quantile(sampled, .975))


def analyze(root, check, pilot=None):
    base = pilot or root/'nutrition'
    if not pilot:
        verify(base)
    raw = {key(r): r for r in rows(base, 'summary')}
    seeds = {int(k[0]) for k in raw}
    expected = {(str(s), str(w), str(p), arm) for s in (seeds if pilot else range(1, 17))
                for w in (8, 32, 128) for p in (500, 2000) for arm in ('legacy', 'combined')}
    assert set(raw) == expected
    old = {key(r): r for r in rows(ROOT/'experiments/s6_1/matrix', 'summary') if key(r) in raw}
    assert set(old) == set(raw)
    for k, r in raw.items():
        assert all(r[f] == old[k][f] for f in ('events', 'state_hash', 'trace_hash', 'gift_attempts'))
        assert r['protein_given_ug'] == old[k]['given_protein_ug']
        assert r['continuation_equal'] == '1'
    people, gifts, decisions = (defaultdict(list) for _ in range(3))
    intake, allocation_events = defaultdict(Counter), defaultdict(list)
    for r in rows(ROOT/'experiments/s6_1/matrix', 'events'):
        if key(r) in raw and r['kind'] in ('19', '20'):
            intake[key(r)][r['actor']] += int(r['protein_ug'])
        if key(r) in raw and r['kind'] in ('17', '19', '20', '21'):
            allocation_events[key(r)].append(r)
    for name, groups in [('individuals', people), ('gifts', gifts), ('decisions', decisions)]:
        for r in rows(base, name):
            assert key(r) in raw
            groups[key(r)].append(r)
    case_rows, classified, event_rows, transitions = [], [], [], []
    for k in sorted(raw, key=lambda k: (int(k[0]), int(k[1]), int(k[2]), k[3])):
        header = dict(zip(KEY, k))
        ps, gs, ds = people[k], gifts[k], decisions[k]
        assert len(ps) == int(k[1])+13
        assert len(gs) == int(raw[k]['gift_attempts']) and len(ds) == int(raw[k]['nutrition_decisions'])
        assert len({int(r['event_id']) for r in ds}) == len(ds)
        assert sum(int(r['protein_ug']) for r in gs) == int(raw[k]['protein_given_ug'])
        brood = [r for r in ps if r['seed_stage'] in ('0', '1')]
        pupae = [r for r in ps if r['seed_stage'] == '2']
        assert len(brood) == 10 and len(pupae) == 2
        assert all(r['threshold_ms'] == r['tissue_threshold_ms'] == '0' for r in pupae)
        received, given = Counter(), Counter()
        for r in gs:
            received[r['recipient']] += int(r['protein_ug'])
            given[r['donor']] += int(r['protein_ug'])
        for r in ps:
            assert int(r['received_protein_ug']) == received[r['entity_id']]
            assert int(r['given_protein_ug']) == given[r['entity_id']]
            retained = int(r['crop_protein_ug'])+int(r['tissue_protein_ug'])
            initial = 100 if r['seed_stage'] == '2' else 0
            assert initial+intake[k][r['entity_id']]+received[r['entity_id']]-given[r['entity_id']] == retained
            if r['seed_stage'] in ('0', '1'):
                assert received[r['entity_id']] == min(100, retained)
                if int(r['adult_ms']) >= 0:
                    assert int(r['adult_ms']) == int(r['tissue_threshold_ms'])+90000
                elif int(r['tissue_threshold_ms']) >= 0 and r['death_ms'] == '-1':
                    assert int(r['tissue_threshold_ms'])+90000 > 180000
        statuses, dstatus = Counter(), Counter()
        for r in gs:
            if r['committed'] == '1':
                status = 'protein_transferred' if int(r['protein_ug']) else 'other_ingredients_only'
            elif int(r['donor_crop_mass_before_ug']) == 0:
                status = 'donor_empty_at_resolution'
            elif int(r['recipient_capacity_before_ug']) == 0:
                status = 'recipient_full_at_resolution'
            elif int(r['compatible_mass_before_ug']) == 0:
                status = 'no_compatible_demand_at_resolution'
            else:
                status = 'other_actual_failure'
            statuses[status] += 1
            event_rows.append(dict(**header, event_id=r['event_id'], time_ms=r['time_ms'],
                                   donor=r['donor'], recipient=r['recipient'], classification=status,
                                   actual_outcome=r['outcome'], protein_ug=r['protein_ug']))
        for r in ds:
            # A decision classification is exclusive; complementary counts below
            # retain missed local protein and cancellation as separate predicates.
            if r['program'] != '2':
                status = 'not_nursing'
            elif r['canceled_by_timestamp_end'] == '1':
                status = 'action_canceled_by_program_change'
            elif r['urgent'] == '1' and r['actual_candidates'] == '0':
                status = 'urgent_self_before_gift'
            elif r['crop_mass_ug'] == '0':
                status = 'empty_crop'
            elif r['actual_candidates'] == '0':
                status = 'no_sample_refill_precedence' if r['action_kind'] in ('10', '11') else 'no_sample_other'
            elif r['chosen_recipient'] != '0':
                status = 'selected_eligible_recipient'
            elif int(r['reachable_protein_larvae']) and not int(r['sampled_protein_larvae']):
                status = 'sample_missed_local_protein_demand'
            elif int(r['reachable_eligible']):
                status = 'sample_missed_other_compatible_demand'
            else:
                status = 'no_reachable_compatible_demand'
            dstatus[status] += 1
        for scope, counts in [('resolution', statuses), ('decision', dstatus)]:
            for status, count in sorted(counts.items()):
                classified.append(dict(**header, scope=scope, classification=status, count=count))
        # Newly emerged identities may later ingest their own crop. Allocation
        # to development excludes that adult intake and retains actual gifts.
        retained = [received[r['entity_id']] for r in brood]
        total = sum(retained)
        # Initial workers never absorb protein. Their exact crop and program
        # residence can be reconstructed from archived real intake/gift facts.
        stores = {str(i): [0, 0, 0] for i in range(3, int(k[1])+3)}
        exposure, exits, foraging = Counter(), 0, 0
        def settle_worker(actor, at):
            crop, program, last = stores[actor]
            exposure[program] += crop*(at-last)/1000
            stores[actor][2] = at
        for event in allocation_events[k]:
            actor, at, kind = event['actor'], int(event['time_ms']), event['kind']
            if actor in stores:
                settle_worker(actor, at)
                before, program, _ = stores[actor]
                if kind == '17':
                    after_program = int(event['payload'])
                    exits += program == 2 and after_program != 2 and before > 0
                    foraging += after_program == 3 and program != 3 and before > 0
                    stores[actor][1] = after_program
                elif kind in ('19', '20'):
                    stores[actor][0] += int(event['protein_ug'])
                else:
                    stores[actor][0] -= int(event['protein_ug'])
                assert stores[actor][0] >= 0
                transitions.append(dict(**header, event_id=event['event_id'], time_ms=at,
                                        actor=actor, fact_kind=kind, protein_before_ug=before,
                                        protein_after_ug=stores[actor][0], program_before=program,
                                        program_after=stores[actor][1]))
            if kind == '21' and event['payload'] in stores:
                recipient = event['payload']
                settle_worker(recipient, at)
                stores[recipient][0] += int(event['protein_ug'])
        for actor in stores:
            settle_worker(actor, 180000)
            assert stores[actor][0] == int(next(r['crop_protein_ug'] for r in ps if r['entity_id'] == actor))
        nurses = [r for r in ds if r['program'] == '2']
        protein_decisions = [r for r in nurses if int(r['crop_protein_ug']) > 0]
        local_opportunities = [r for r in protein_decisions if int(r['reachable_protein_larvae']) > 0]
        sampled_opportunities = [r for r in local_opportunities if int(r['actual_candidates']) > 0]
        hits = [r for r in sampled_opportunities if int(r['sampled_protein_larvae']) > 0]
        metric = dict(new_brood_protein_ug=total, new_brood_full=sum(x >= 100 for x in retained),
                      new_brood_partial=sum(0 < x < 100 for x in retained), new_brood_unfed=sum(x == 0 for x in retained),
                      new_brood_emerged=sum(int(r['adult_ms']) >= 0 for r in brood),
                      new_full_late=sum(int(r['tissue_threshold_ms']) > 90000 for r in brood),
                      protein_hhi=sum((x/total)**2 for x in retained) if total else 0.,
                      nursing_decisions=len(nurses), donor_protein_decisions=len(protein_decisions),
                      reachable_protein_opportunities=len(local_opportunities),
                      sampled_protein_opportunities=len(sampled_opportunities), sampled_protein_hits=len(hits),
                      sample_misses=len(sampled_opportunities)-len(hits),
                      selected_protein_opportunities=sum(int(r['chosen_recipient']) > 0 for r in hits),
                      canceled_protein_choices=sum(r['canceled_by_timestamp_end'] == '1' for r in hits),
                      no_sample_refill=dstatus['no_sample_refill_precedence'],
                      failed_gifts=sum(r['committed'] == '0' for r in gs),
                      failed_incompatible=statuses['no_compatible_demand_at_resolution'],
                      failed_donor_empty=statuses['donor_empty_at_resolution'],
                      failed_recipient_full=statuses['recipient_full_at_resolution'],
                      protein_gifts=statuses['protein_transferred'],
                      protein_before_egg_hatch_ug=sum(int(r['protein_ug']) for r in gs if int(r['time_ms']) < 30000),
                      nurse_exits_holding_protein=exits, forage_entries_holding_protein=foraging,
                      protein_nurse_exposure_ug_s=exposure[2], protein_forage_exposure_ug_s=exposure[3],
                      protein_rest_exposure_ug_s=exposure[1], protein_excavate_exposure_ug_s=exposure[4],
                      protein_success_fraction=statuses['protein_transferred']/len(gs) if gs else 0.)
        for field in ('emerged', 'unmet_integral_ug_s', 'given_protein_ug', 'program_switches',
                      'adult_crop_protein_ug', 'dead_crop_protein_ug', 'gift_attempts',
                      'gift_success', 'gift_partial', 'gift_failed'):
            metric[field] = int(old[k][field])
        case_rows.append(dict(**header, **metric))
    if pilot:
        print(f'PASS {len(raw)} exact S6.1 states, traces, ordered transfers, identities and observer continuations')
        return
    paired, means = [], []
    for workers in ('8', '32', '128'):
        for protein in ('500', '2000'):
            cells = [r for r in case_rows if r['workers'] == workers and r['source_protein_ug'] == protein]
            for metric in list(case_rows[0])[4:]:
                arms = {arm: sorted([r for r in cells if r['policy'] == arm], key=lambda r: int(r['seed']))
                        for arm in ('legacy', 'combined')}
                for arm, data in arms.items():
                    means.append(dict(workers=workers, source_protein_ug=protein, policy=arm, metric=metric,
                                      **interval([r[metric] for r in data])))
                deltas = [b[metric]-a[metric] for a, b in zip(arms['legacy'], arms['combined'])]
                paired.append(dict(workers=workers, source_protein_ug=protein, metric=metric, **interval(deltas)))
    output = root/'analysis'
    for name, data in [('nutrition_cases', case_rows), ('nutrition_means', means), ('nutrition_paired', paired),
                       ('nutrition_classifications', classified), ('gift_classifications', event_rows)]:
        emit(output/(name+'.csv'), data, check)
    emit(output/'worker_protein_transitions.csv', transitions, check)
    print('PASS 192 exact S6.1 scarcity states/traces; all protein gifts and recipient thresholds reconciled')


def choices(root, check):
    base = root/'choice'
    verify(base)
    summary = list(rows(base, 'summary'))
    assert {(int(r['seed']), int(r['permutation'])) for r in summary} == {(s, p) for s in range(1, 65) for p in range(4)}
    assert all(r['decisions'] == r['gifts'] == '64' and r['continuation_equal'] == '1' for r in summary)
    counts, events, seen = defaultdict(Counter), defaultdict(Counter), set()
    for r in rows(base, 'choices'):
        seed, perm, decision = int(r['seed']), int(r['permutation']), int(r['decision'])
        assert (seed, perm, decision, r['entity_id']) not in seen
        seen.add((seed, perm, decision, r['entity_id']))
        assert int(r['chosen']) <= int(r['included']) and r['protein_ug'] == r['chosen']
        events[seed, perm, decision]['rows'] += 1
        events[seed, perm, decision]['chosen'] += int(r['chosen'])
        events[seed, perm, decision]['included'] += int(r['included'])
        for axis in ('id_rank', 'logical_slot'):
            counts[seed, perm, axis, int(r[axis])]['chosen'] += int(r['chosen'])
            counts[seed, perm, axis, int(r[axis])]['included'] += int(r['included'])
    assert len(seen) == 64*4*64*16 and len(events) == 64*4*64
    assert all(r['rows'] == 16 and r['chosen'] == 1 and r['included'] in (15, 16) for r in events.values())
    output = []
    for perm in range(4):
        for axis in ('id_rank', 'logical_slot'):
            for rank in range(16):
                for metric in ('chosen', 'included'):
                    values = [counts[s, perm, axis, rank][metric]/64 for s in range(1, 65)]
                    output.append(dict(permutation=perm, axis=axis, rank=rank, metric=metric, **interval(values)))
    contrasts = []
    for perm in range(4):
        for axis in ('id_rank', 'logical_slot'):
            values = [(sum(counts[s, perm, axis, i]['chosen'] for i in range(8))-
                       sum(counts[s, perm, axis, i]['chosen'] for i in range(8, 16)))/64 for s in range(1, 65)]
            contrasts.append(dict(permutation=perm, axis=axis, contrast='lower_half_minus_upper_half', **interval(values)))
    emit(root/'analysis/choice_distribution.csv', output, check)
    emit(root/'analysis/choice_contrasts.csv', contrasts, check)
    print('PASS 256 equal-demand cases; 16384 committed choices and 262144 inclusion records')


def archived_controls(root, check):
    """All original ablation arms are retained; these are archived, not new runs."""
    groups = defaultdict(list)
    for r in rows(ROOT/'experiments/s6_1/matrix', 'summary'):
        groups[r['workers'], r['source_protein_ug'], r['policy']].append(r)
    metrics = ('given_protein_ug', 'emerged', 'unmet_integral_ug_s', 'program_switches', 'adult_crop_protein_ug')
    data = []
    for (workers, protein, arm), group in sorted(groups.items()):
        assert len(group) == 16
        ordered = sorted(group, key=lambda r: int(r['seed']))
        legacy = sorted(groups[workers, protein, 'legacy'], key=lambda r: int(r['seed']))
        for metric in metrics:
            for comparison in ('endpoint', 'minus_legacy'):
                values = [int(r[metric])-(int(a[metric]) if comparison == 'minus_legacy' else 0)
                          for r, a in zip(ordered, legacy)]
                data.append(dict(source='immutable_S6.1_archive', workers=workers, source_protein_ug=protein,
                                 policy=arm, metric=metric, comparison=comparison, **interval(values)))
    streams = defaultdict(list)
    fields = ('time_ms', 'actor', 'payload', 'outcome', 'carbs_ug', 'protein_ug', 'water_ug', 'other_ug')
    for r in rows(ROOT/'experiments/s6_1/matrix', 'events'):
        if r['workers'] == '128' and r['source_protein_ug'] == '500' and r['kind'] == '21':
            streams[int(r['seed']), r['policy']].append(tuple(r[f] for f in fields))
    comparison = []
    for seed in range(1, 17):
        for a, b in (('legacy', 'local_continuation'), ('gift_first', 'combined')):
            left, right = streams[seed, a], streams[seed, b]
            comparison.append(dict(seed=seed, workers=128, source_protein_ug=500, first=a, second=b,
                                   gifts_first=len(left), gifts_second=len(right), exact_gift_sequence_equal=left == right,
                                   first_sha256=hashlib.sha256(json.dumps(left).encode()).hexdigest(),
                                   second_sha256=hashlib.sha256(json.dumps(right).encode()).hexdigest()))
    emit(root/'analysis/archived_ablations.csv', data, check)
    emit(root/'analysis/dense_gift_sequence_comparison.csv', comparison, check)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=ROOT/'experiments/s6_2')
    p.add_argument('--check', action='store_true')
    p.add_argument('--pilot', type=Path)
    args = p.parse_args()
    analyze(args.root, args.check, args.pilot)
    if not args.pilot:
        choices(args.root, args.check)
        archived_controls(args.root, args.check)


if __name__ == '__main__':
    main()
