"""Reconcile retrieval and nursing endpoints against committed care-event records."""
import argparse
import csv
import gzip
import itertools
import math
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HISTORICAL = ROOT/'experiments/s6_3_3/raw'
STAGE = ROOT/'experiments/s6_3_3_1'
ZERO = (0., 0., 0.)
BEGIN, END = 180000, 780000
CONTACT_M = .002
ACTS = ('inactive', 'walk', 'approach', 'inspect', 'arrange', 'clean', 'transport', 'feed', 'worker_contact',
        'collect_food', 'deliver_food', 'ingest_food', 'transfer_nutrition', 'excavate', 'handle_soil', 'revisit')
OPPORTUNITY, SELECTED, STARTED, COMPLETED, INTERRUPTED = range(5)
MOVED, STAGE_CHANGED, DIED, OBSERVATION, BROOD_MOVED = 4, 7, 8, 42, 43
ACTIVE_CARE = {3, 4, 5}
HANDLING = {3, 4, 5, 6, 7}


def read(path):
    with path.open(encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream))


def write(path, rows):
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def events(path, wanted):
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rt', encoding='utf-8', newline='') as stream:
        for run, group in itertools.groupby(csv.DictReader(stream), key=lambda row: row['run']):
            if run not in wanted:
                continue
            rows = []
            for row in group:
                for key in ('event_id', 'time_ms', 'source', 'kind', 'actor', 'stage', 'target', 'phase', 'act', 'bout', 'began_ms', 'duration_known', 'outcome'):
                    row[key] = int(row[key])
                row['position'] = tuple(float(row[k]) for k in ('x_m', 'y_m', 'z_m'))
                rows.append(row)
            yield run, rows


def placement(layout):
    if layout == 'empty':
        return []
    if layout == 'sheltered':
        return [(-.0005, 0., (i % 5)*.00025) for i in range(6)]
    if layout == 'split':
        return [(.005+i*.002, 0., 0.) for i in range(3)] + [(0., 0., -(.005+i*.002)) for i in range(3)]
    start = .009 if layout == 'far' else .005
    sign = -1 if layout == 'mirror' else 1
    return [(sign*(start+i*.002), 0., 0.) for i in range(6)]


def trace_retrieval(run, info, rows, output):
    group = info['condition'] == 'three_workers'
    actors = (3, 4, 5) if group else (2,)
    locations = placement(info.get('layout', 'line'))
    brood = {3+3*group+i: p for i, p in enumerate(locations)}
    positions = {**dict.fromkeys(actors, ZERO), **brood}
    displaced = {ant for ant, p in brood.items() if math.dist(p, ZERO) > CONTACT_M}
    seen = dict.fromkeys(actors)
    seen_displaced = dict.fromkeys(actors)
    counts, observed, durations = Counter(), defaultdict(list), Counter()
    active, movement, trips = {}, {}, {}
    path, delivered = Counter(), {}
    decision_target = {}
    switches = Counter()
    key = dict(run=run, seed=int(info['seed']), policy=info.get('policy', 'legacy'),
               set=info.get('set', 'historical'), condition=info['condition'], layout=info.get('layout', 'line'))
    for row in rows:
        at, kind, actor, target, src = (row[k] for k in ('time_ms', 'kind', 'actor', 'target', 'source'))
        if kind in (STAGE_CHANGED, DIED) and actor in brood and row['stage'] >= 3:
            brood.pop(actor)
        if kind == MOVED and actor in actors:
            if BEGIN <= at <= END:
                path[actor] += math.dist(positions[actor], row['position'])
            positions[actor] = row['position']
        if kind == BROOD_MOVED and actor in brood:
            old, new = positions[actor], row['position']
            positions[actor] = new
            inside = math.dist(new, ZERO) <= CONTACT_M
            arrival = actor in displaced and actor not in delivered and inside and target in actors
            movement[src] = (actor, target, math.dist(old, new), arrival, row['event_id'])
            if arrival:
                delivered[actor] = (target, at, row['event_id'])
        if not BEGIN <= at <= END or kind != OBSERVATION or actor not in actors:
            continue
        phase, act, bout = row['phase'], row['act'], row['bout']
        counts[actor, act, phase] += 1
        if phase == SELECTED:
            local = [item for item in brood if math.dist(positions[actor], positions[item]) <= float(info['perception_m'])]
            away = [item for item in local if math.dist(positions[item], ZERO) > CONTACT_M]
            if local and seen[actor] is None:
                seen[actor] = at
            if away and seen_displaced[actor] is None:
                seen_displaced[actor] = at
            if target in brood:
                if actor in decision_target and target != decision_target[actor]:
                    switches[actor] += 1
                decision_target[actor] = target
            output['decisions'].append(dict(**key, actor=actor, event_id=row['event_id'], time_ms=at-BEGIN,
                                            act=ACTS[act], target=target, local_brood=len(local), local_displaced=len(away),
                                            local_sheltered=len(local)-len(away), target_displaced=int(target in away),
                                            x_m=positions[actor][0], y_m=positions[actor][1], z_m=positions[actor][2]))
        if phase == OPPORTUNITY and target in brood:
            observed[actor, 'opportunity'].append((at, target))
        if phase == STARTED:
            if row['duration_known']:
                active[bout] = (actor, act, at, target)
            if act in (1, 15):
                observed[actor, 'search'].append((at, target))
            if act == 2:
                observed[actor, 'approach'].append((at, target))
                if target in brood and math.dist(positions[target], ZERO) > CONTACT_M:
                    observed[actor, 'outside_approach'].append((at, target))
            if act in HANDLING:
                observed[actor, 'contact'].append((at, target))
                if target in brood and math.dist(positions[target], ZERO) > CONTACT_M:
                    observed[actor, 'displaced_contact'].append((at, target))
            if act == 6:
                trips.setdefault((actor, target), dict(start=at, end=None, distance=0., active_ms=0, segments=0))
        if phase in (COMPLETED, INTERRUPTED):
            start = active.pop(bout, None)
            span = at-start[2] if start else 0
            durations[actor, act] += span
            if phase == COMPLETED and act == 2:
                observed[actor, 'approach_completed'].append((at, target))
            if phase == COMPLETED and act in HANDLING:
                observed[actor, 'successful_contact'].append((at, target))
            if act == 6:
                moved = movement.get(src)
                if moved:
                    assert moved[:2] == (target, actor), (run, row['event_id'])
                trip = trips.get((actor, target))
                if trip and trip['end'] is None:
                    trip['distance'] += moved[2] if moved else 0.
                    trip['active_ms'] += span
                    trip['segments'] += 1
                    if moved and moved[3]:
                        trip['end'] = at
                output['transport_segments'].append(dict(**key, actor=actor, target=target, end_ms=at-BEGIN,
                    duration_ms=span, outcome=row['outcome'], completed=int(phase == COMPLETED),
                    observation_id=row['event_id'], movement_id=moved[4] if moved else '',
                    displacement_m=moved[2] if moved else 0., delivered=int(moved is not None and moved[3])))
    for actor, act, at, target in active.values():
        durations[actor, act] += END-at
        if act == 6:
            trips[actor, target]['active_ms'] += END-at
    for (actor, target), trip in trips.items():
        output['trips'].append(dict(**key, actor=actor, target=target, first_start_ms=trip['start']-BEGIN,
            delivered_ms=trip['end']-BEGIN if trip['end'] is not None else '',
            elapsed_or_censored_ms=(trip['end'] or END)-trip['start'], segment_terminal_count=trip['segments'],
            actual_segment_distance_m=trip['distance'], transport_active_ms=trip['active_ms'],
            status='DELIVERED' if trip['end'] is not None else 'UNDELIVERED_BY_ACTOR'))

    def relative(time):
        return time-BEGIN if time is not None else ''

    def first(actor, name):
        return relative(observed[actor, name][0][0]) if observed[actor, name] else ''

    for actor in actors:
        output['actors'].append(dict(**key, actor=actor, first_perception_ms=relative(seen[actor]),
            first_displaced_perception_ms=relative(seen_displaced[actor]), first_search_ms=first(actor, 'search'),
            first_opportunity_ms=first(actor, 'opportunity'), first_approach_ms=first(actor, 'approach'),
            first_completed_approach_ms=first(actor, 'approach_completed'), first_contact_ms=first(actor, 'contact'),
            first_successful_contact_ms=first(actor, 'successful_contact'), target_switches=switches[actor],
            deliveries=sum(v[0] == actor for v in delivered.values()), path_m=path[actor]))
        for act in range(len(ACTS)):
            if counts[actor, act, SELECTED] or durations[actor, act]:
                output['acts'].append(dict(**key, actor=actor, act=ACTS[act], selected=counts[actor, act, SELECTED],
                    started=counts[actor, act, STARTED], completed=counts[actor, act, COMPLETED],
                    interrupted=counts[actor, act, INTERRUPTED], observed_duration_ms=durations[actor, act]))
    for item, (actor, at, eid) in delivered.items():
        def next_act(act):
            return next((t-at for t, target in observed[actor, act] if t > at and target != item), '')

        remaining = sum(i != item and (i not in delivered or delivered[i][1] > at) for i in displaced)
        if not remaining:
            continue
        output['after_delivery'].append(dict(**key, actor=actor, delivered=item, event_id=eid, time_ms=at-BEGIN,
            initially_displaced_still_undelivered=remaining, followup_ms=END-at, next_search_ms=next_act('search'),
            next_outside_approach_ms=next_act('outside_approach'), next_displaced_contact_ms=next_act('displaced_contact'),
            next_delivery_ms=min((v[1]-at for v in delivered.values() if v[0] == actor and v[1] > at), default='')))
    group_first = min((observed[a, 'contact'][0][0]-BEGIN for a in actors if observed[a, 'contact']), default=-1)
    count = len(delivered)
    assert group_first == int(info['first_contact_ms']) and count == int(info['retrieved']), (run, group_first, count)
    output['runs'].append(dict(**key, retrieved=count, first_contact_ms=group_first, contact_observed=int(group_first >= 0),
        first_contact_capped_ms=group_first if group_first >= 0 else END-BEGIN, path_m=sum(path.values()),
        inactive_ms=sum(durations[a, 0] for a in actors), approach_ms=sum(durations[a, 2] for a in actors),
        handling_ms=sum(durations[a, act] for a in actors for act in ACTIVE_CARE), transport_ms=sum(durations[a, 6] for a in actors),
        started_contacts=sum(counts[a, act, STARTED] for a in actors for act in HANDLING),
        completed_contacts=sum(counts[a, act, COMPLETED] for a in actors for act in HANDLING),
        transport_interrupted=sum(counts[a, 6, INTERRUPTED] for a in actors)))


def nursing(rows, windows):
    queen = [r for r in rows if r['actor'] == 2 and r['kind'] == OBSERVATION]
    starts = {r['bout']: r for r in queen if r['phase'] == STARTED and r['duration_known']}
    terminals = {r['bout']: r['time_ms'] for r in queen if r['phase'] in (COMPLETED, INTERRUPTED) and r['duration_known']}
    bouts = [(r['time_ms'], terminals.get(bout, math.inf), r['act']) for bout, r in starts.items()]
    for w in windows:
        begin, end = int(w['begin_ms']), int(w['end_ms'])
        overlap, point = [], []
        care = [(a, b) for a, b, act in bouts if act in ACTIVE_CARE and a < end and b > begin]
        for minute in range(5, 56):
            t = begin + minute*60000
            overlap.append(any(a < t+10000 and b > t for a, b in care))
            point.append(any(a <= t < b for a, b in care))
        assert sum(overlap) == int(w['positive51']) and sum(overlap[:50]) == int(w['positive50']), w['run']
        count = Counter((r['act'], r['phase']) for r in queen if begin <= r['time_ms'] < end)
        durations = Counter()
        for a, b, act in bouts:
            durations[act] += max(0, min(b, end)-max(a, begin))
        yield dict(run=w['run'], seed=w['seed'], condition=w['condition'], age_days=w['context_age_days'], variant=w['variant'],
            assay=w['assay'], window_h=w['window_h'], overlap50=sum(overlap[:50])/50, overlap51=sum(overlap)/51,
            point50=sum(point[:50])/50, active_care_time_fraction=sum(durations[a] for a in ACTIVE_CARE)/(end-begin),
            inactive_fraction=durations[0]/(end-begin), program_fraction=int(w['program_ms'])/(end-begin),
            active_care_starts=sum(count[a, STARTED] for a in ACTIVE_CARE), worker_opportunities=count[8, OPPORTUNITY],
            worker_starts=count[8, STARTED], worker_completed=count[8, COMPLETED], worker_contact_ms=durations[8],
            worker_last_contact_ms=w['last_worker_contact_ms'], arrange_selected=count[4, SELECTED],
            arrange_completed=count[4, COMPLETED], arrange_interrupted=count[4, INTERRUPTED])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs', type=Path, help='Analyze a new flat runs.csv/events.csv pair instead of the archived baseline')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    output = defaultdict(list)
    if args.runs:
        info = {r['run']: r for r in read(args.runs)}
        for run, rows in events(args.runs.with_name('events.csv'), info):
            trace_retrieval(run, info[run], rows, output)
        assert len(output['runs']) == len(info)
    else:
        for directory in sorted(HISTORICAL.glob('*_*')):
            if not directory.is_dir():
                continue
            runs = {r['run']: r for r in read(directory/'runs.csv') if r['assay'] == 'retrieval'}
            windows = defaultdict(list)
            for row in read(directory/'windows.csv'):
                if int(row['context_age_days']) in (52, 55) or (row['seed'] == '7' and row['context_age_days'] == '932'):
                    windows[row['run']].append(row)
            for run, rows in events(directory/'events.csv.gz', set(runs) | set(windows)):
                if run in runs:
                    trace_retrieval(run, runs[run], rows, output)
                else:
                    output['b01_windows'].extend(nursing(rows, windows[run]))
        assert len(output['runs']) == 24 and len(output['actors']) == 48
    for table, rows in output.items():
        write(args.out/(table+'.csv'), rows)
    print({table: len(rows) for table, rows in output.items()})


if __name__ == '__main__':
    main()
