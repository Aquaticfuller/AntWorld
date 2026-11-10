"""Read committed care facts and the published trial data without fitting any coefficient."""
import argparse
import math
import random
import statistics as st
from collections import Counter, defaultdict
from pathlib import Path

from analyze_s6_3_3 import q
from analyze_s6_3_3_2 import (
    APPROACH, ARRANGE, BASE as PREVIOUS, BROOD_MOVED, CARE_TICK, CARE_WAKE, CLEAN,
    COMPLETED, END, FEED, HORIZON, INSPECT, INTERRUPTED, LITERATURE, MOVED, OBSERVATION,
    OPPORTUNITY, PICKUP, PLACE, RELEASE, RETURN, REVISIT, SELECTED, STARTED, STAGES,
    TRANSPORT, WALK, WORKER_CONTACT, events, group, position, read, write,
)
from run_s6_3_3_3_assays import BASE, SEEDS


def estimates(x, y=()):
    rng = random.Random(63303)
    values = []
    for _ in range(4096):
        sample = st.fmean(rng.choices(x, k=len(x)))
        values.append(sample-st.fmean(rng.choices(y, k=len(y))) if y else sample)
    return dict(n=len(x), mean=st.fmean(x)-(st.fmean(y) if y else 0),
                ci_low=q(values, .025), ci_high=q(values, .975))


def first(values):
    return min((v for v in values if v is not None), default=None)


def b02_trace(run, profile, entities, trace):
    shelter = next((position(r) for r in entities if r['role']=='shelter'), (0., 0., 0.))
    ants = {r['entity']:r for r in entities if r['role']!='shelter'}
    positions = {i:position(r) for i,r in ants.items()}
    brood = {i for i,r in ants.items() if r['role']=='brood'}
    actors = {i:dict(wake=None, cue=None, search=None, approach=None, handling=None,
                     pickup=None, placement=None, path_mm=0., search_mm=0., interrupted=0)
              for i in ants if i not in brood}
    radius = float(run['perception_m'])
    wall = profile['layout']=='wall'

    def cue_count(actor):
        a = positions[actor]
        return sum(math.dist(a,positions[b])<=radius
                   and (not wall or not (min(a[0],positions[b][0])<.0005
                                         and max(a[0],positions[b][0])>.00075))
                   and (ants[actor]['colony']==ants[b]['colony']
                        or (profile['neutral_assay']=='1' and math.dist(positions[b],shelter)>.002))
                   for b in brood)

    initial_cues = {i:cue_count(i) for i in actors}
    began = {}
    activity = defaultdict(float)
    phase_counts = Counter()
    first_for_target = {}
    approach_ms = Counter()
    loads, trips, followups, latest_placement, placed = {}, [], [], {}, set()
    for e in trace:
        t = int(e['time_ms'])
        if not RELEASE<=t<=END:
            continue
        now = (t-RELEASE)/1000
        actor, target, kind = e['actor'], e['target'], int(e['kind'])
        if kind in (MOVED, BROOD_MOVED) and actor in positions:
            new = position(e)
            moved = 1000*math.dist(positions[actor], new)
            positions[actor] = new
            if actor in actors and kind==MOVED:
                actors[actor]['path_mm'] += moved
                if began.get(actor) in (WALK, REVISIT):
                    actors[actor]['search_mm'] += moved
                if actor in loads and began.get(actor)==TRANSPORT:
                    loads[actor]['load_path_mm'] += moved
        if actor not in actors:
            continue
        a = actors[actor]
        if kind==CARE_TICK and target==str(CARE_WAKE):
            if a['wake'] is None:
                a['wake'] = now
            if a['cue'] is None and cue_count(actor):
                a['cue'] = now
        if kind!=OBSERVATION:
            continue
        act, phase = int(e['act']), int(e['phase'])
        phase_counts[phase,act,int(e['outcome'])] += 1
        if phase==SELECTED and target in brood:
            first_for_target.setdefault((actor,target,'select'), now)
        if phase==STARTED:
            began[actor] = act
            if act in (WALK, REVISIT) and a['search'] is None:
                a['search'] = now
            if act==APPROACH and a['approach'] is None:
                a['approach'] = now
            if act in STAGES:
                first_for_target.setdefault((actor,target,'handling'), now)
                if a['handling'] is None:
                    a['handling'] = now
            if act in (APPROACH, PICKUP, WALK, REVISIT) and actor in latest_placement:
                prior = latest_placement[actor]
                if prior['restart_s'] is None:
                    prior.update(restart_s=now, restart_act=act, restart_delay_s=now-prior['placed_s'])
        if phase not in (COMPLETED, INTERRUPTED):
            continue
        began.pop(actor,None)
        duration = t-int(e['began_ms']) if e['duration_known']=='1' else 0
        activity[phase,act,int(e['outcome'])] += duration/1000
        if act==APPROACH:
            approach_ms[actor,target] += duration
        if phase==INTERRUPTED:
            a['interrupted'] += 1
            if actor in loads and act in (TRANSPORT, PLACE):
                load = loads.pop(actor)
                load.update(end_s=now, disposition='interrupted', outcome=e['outcome'])
                trips.append(load)
            if target in brood:
                for key in ('select','handling'):
                    first_for_target.pop((actor,target,key),None)
                approach_ms.pop((actor,target),None)
        elif act==PICKUP:
            assert actor not in loads
            if a['pickup'] is None:
                a['pickup'] = now
            loads[actor] = dict(run=run['run'], actor=actor, target=target, pickup_s=now,
                                target_selection_s=first_for_target.pop((actor,target,'select'),None),
                                target_handling_s=first_for_target.pop((actor,target,'handling'),None),
                                target_approach_s=approach_ms.pop((actor,target),0)/1000,
                                pickup_scheduled_s=duration/1000, load_path_mm=0., load_active_s=0.,
                                load_segments=0, placement_active_s=None, load_gap_s=None)
        elif act==TRANSPORT:
            loads[actor]['load_active_s'] += duration/1000
            loads[actor]['load_segments'] += 1
        elif act==PLACE:
            load = loads.pop(actor)
            assert load['target']==target
            gap = now-load['pickup_s']-load['load_active_s']-duration/1000
            load.update(end_s=now, disposition='placed', outcome=e['outcome'],
                        placement_active_s=duration/1000, load_gap_s=gap)
            trips.append(load)
            if actor in latest_placement:
                latest_placement[actor]['next_placement_s'] = now
            follow = dict(run=run['run'], actor=actor, target=target, placed_s=now, restart_s=None,
                          restart_act=None, restart_delay_s=None, next_placement_s=None,
                          available_s=HORIZON-now)
            followups.append(follow)
            latest_placement[actor] = follow
            placed.add(target)
            if a['placement'] is None:
                a['placement'] = now
    for load in loads.values():
        load.update(end_s=HORIZON, disposition='censored', outcome=None)
        trips.append(load)
    handling = first(a['handling'] for a in actors.values())
    placed_at = first(a['placement'] for a in actors.values())
    first_trip = min((r for r in trips if r['disposition']=='placed'), key=lambda r:r['end_s'], default={})
    assert len(placed)==int(run['retrieved']) and (handling is None)==(run['first_contact_ms']=='-1')
    if handling is not None:
        assert math.isclose(handling, int(run['first_contact_ms'])/1000)
    if placed_at is not None:
        assert math.isclose(placed_at, int(run['first_retrieval_ms'])/1000)
    row = dict(run=run['run'], seed=int(run['seed']), group=run['condition'], scenario=profile['scenario'],
               layout=profile['layout'], variant=profile['variant'], origin=profile['origin'],
               radius_mm=1000*radius, neutral=int(profile['neutral_assay']),
               caregivers=len(actors), initial_cue_actors=sum(x>0 for x in initial_cues.values()),
               cue_at_first_wake=sum(a['cue'] is not None and a['cue']==a['wake'] for a in actors.values()),
               first_wake_s=first(a['wake'] for a in actors.values()),
               first_geometric_cue_s=first(a['cue'] for a in actors.values()),
               first_approach_s=first(a['approach'] for a in actors.values()),
               first_handling_s=handling, first_pickup_s=first(a['pickup'] for a in actors.values()),
               first_place_s=placed_at, handling_capped_s=HORIZON if handling is None else handling,
               placement_capped_s=HORIZON if placed_at is None else placed_at,
               no_handling=int(handling is None), no_placement=int(placed_at is None), retrieved=len(placed),
               placements=sum(r['disposition']=='placed' for r in trips), pickups=len(trips),
               interrupted_loads=sum(r['disposition']=='interrupted' for r in trips),
               held_at_end=len(loads), interrupted_acts=sum(a['interrupted'] for a in actors.values()),
               repeated_trips=sum(r['next_placement_s'] is not None for r in followups),
               restarted=sum(r['restart_s'] is not None for r in followups),
               group_handling_to_first_place_s=None if placed_at is None else placed_at-handling,
               search_mm=sum(a['search_mm'] for a in actors.values()),
               body_path_mm=sum(a['path_mm'] for a in actors.values()))
    for field in ('actor','target','target_selection_s','target_handling_s','target_approach_s',
                  'pickup_s','pickup_scheduled_s','load_path_mm','load_active_s','load_gap_s','placement_active_s'):
        row['first_trip_'+field] = first_trip.get(field)
    actor_rows = [dict(run=run['run'], actor=i, initial_cues=initial_cues[i], **a) for i,a in actors.items()]
    act_rows = [dict(run=run['run'], phase=p, act=a, outcome=o, count=n, elapsed_s=activity[p,a,o])
                for (p,a,o),n in sorted(phase_counts.items())]
    return row, actor_rows, trips, followups, act_rows


def b02(raw, dest):
    previous = PREVIOUS/'raw'
    folders = [(previous/arm,'reviewed') for arm in ('b02','robustness','sensitivity')]
    folders += [(raw/'b02'/str(seed),'closure') for seed in SEEDS]
    table = [[], [], [], [], []]
    for folder, cohort in folders:
        runs = {r['run']:r for r in read(folder/'runs.csv')}
        profiles = {r['run']:r for r in read(folder/'profiles.csv')}
        entities = group(read(folder/'initial.csv'),lambda r:r['run'])
        for name, trace in events(folder):
            run, actors, trips, returns, acts = b02_trace(runs[name],profiles[name],entities[name],trace)
            table[0].append(dict(cohort=cohort, **run))
            for output, records in zip(table[1:],(actors,trips,returns,acts)):
                output.extend(dict(cohort=cohort, **r) for r in records)
    assert len(table[0])==756
    for label, rows in zip(('runs','caregivers','trips','restarts','acts'),table):
        write(dest/f'b02_{label}.csv',rows)

    metrics = ('retrieved','handling_capped_s','placement_capped_s','no_handling','no_placement',
               'cue_at_first_wake','interrupted_loads','repeated_trips','search_mm')
    cells = group((r for r in table[0] if r['cohort']=='closure'),
                  lambda r:(r['group'],r['origin'],r['layout'],r['radius_mm']))
    summary, contrasts = [], []
    for key, rows in sorted(cells.items()):
        role, origin, layout, radius = key
        ids = {r['seed']:r for r in rows}
        assert set(ids)==set(SEEDS)
        labels = dict(group=role,origin=origin,layout=layout,radius_mm=radius)
        for metric in metrics:
            x = [ids[s][metric] for s in SEEDS]
            summary.append(dict(**labels,metric=metric,**estimates(x)))
            alternatives = {'6 mm':(role,origin,layout,6.),'line':(role,origin,'line',radius),
                            'own':(role,'own',layout,radius)}
            for comparison, baseline in alternatives.items():
                if baseline==key:
                    continue
                other = {r['seed']:r[metric] for r in cells[baseline]}
                contrasts.append(dict(**labels,metric=metric,baseline=comparison,
                                      **estimates([x[i]-other[s] for i,s in enumerate(SEEDS)])))
    write(dest/'b02_uncertainty.csv',summary)
    write(dest/'b02_paired_contrasts.csv',contrasts)


def paper_b02(dest):
    rows = []
    for r in read(LITERATURE/'B02_retrieval.csv'):
        contact, retrieve, last = (float(r[f]) for f in ('first contact ',' first retrieving','last retrieving'))
        complete = contact<600 and retrieve<600 and retrieve>=contact
        rows.append(dict(group=r['qw'], colony=r['queen'], test=r['test'],
                         origin='own' if r['same']=='1' else 'foreign', contacted=int(contact<600),
                         first_contact_capped_s=contact, marker_recorded=int(retrieve<600),
                         first_retrieving_marker_capped_s=retrieve, ordered_complete_case=int(complete),
                         contact_to_marker_s=retrieve-contact if complete else None,
                         first_to_last_marker_s=last-retrieve if retrieve<=last<600 else None,
                         retrieved_600s=int(r[' brood items after 10min'])))
    assert len(rows)==398
    write(dest/'b02_paper_decomposition.csv',rows)


def b01(raw, dest):
    measures, scored, bouts = [], [], []
    phases = (0, 10, 20, 30, 40, 50)
    for seed in SEEDS:
        folder = raw/'b01'/str(seed)
        queens = {r['run']:r['entity'] for r in read(folder/'initial.csv') if r['role']=='queen'}
        meta = {r['run']:r for r in read(folder/'runs.csv')}
        windows = group(read(folder/'windows.csv'),lambda r:r['run'])
        scans = group(read(folder/'scans.csv'),lambda r:(r['run'],r['window_h']))
        for name, trace in events(folder):
            win = next(r for r in windows[name] if r['window_h']==('48' if r['condition']=='removed' else '24'))
            lo, hi = int(win['begin_ms']), int(win['end_ms'])
            contacts, opportunities, inactive_ms, program_ms = 0, 0, 0, int(win['program_ms'])
            last = None
            active, placements = [], []
            selected, started = Counter(), Counter()
            for e in trace:
                if int(e['kind'])!=OBSERVATION or e['actor']!=queens[name]:
                    continue
                t, start, act, phase = (int(e[k]) for k in ('time_ms','began_ms','act','phase'))
                if t>hi:
                    break
                if act==WORKER_CONTACT and phase==COMPLETED:
                    last = t
                    contacts += lo<=t<hi
                if act==WORKER_CONTACT and phase==OPPORTUNITY:
                    opportunities += lo<=t<hi
                if lo<=t<hi and phase in (SELECTED,STARTED):
                    (selected if phase==SELECTED else started)[act] += 1
                    if phase==SELECTED:
                        age = None if last is None else t-last
                        decay = 0 if age is None else max(0,1-age/int(meta[name]['memory_ms']))
                        bouts.append(dict(run=name, time_ms=t, act=act, minute_phase_ms=(t-lo)%60000,
                                          prior_committed_contact_age_ms=age, memory_proxy=decay))
                if lo<=t<hi and phase==COMPLETED and act==PLACE:
                    placements.append(t)
                gift = sum(int(e[field+'_ug']) for field in ('carbs','protein','water'))
                duration = e['duration_known']=='1' and phase in (COMPLETED,INTERRUPTED) and start<hi and t>lo
                if duration and (act in (INSPECT,ARRANGE,CLEAN) or (act==FEED and phase==COMPLETED and gift>0)):
                    active.append((start,t))
                if duration and act==0:
                    inactive_ms += min(t,hi)-max(start,lo)
            raw_scans = scans[name,win['window_h']]
            assert len(raw_scans)==51
            counts = Counter()
            for index, scan in enumerate(raw_scans):
                t = int(scan['begin_ms'])
                result = {}
                for offset in phases:
                    begin, end = t+offset*1000, t+(offset+10)*1000
                    hit = any(a<end and b>begin for a,b in active) or any(begin<=p<end for p in placements)
                    result[f'positive_offset_{offset}s'] = int(hit)
                    if index<50:
                        counts[offset] += hit
                scored.append(dict(run=name, scan=index, begin_ms=t, original_end_ms=t+10000, **result))
            measures.append(dict(run=name, seed=seed, condition=win['condition'], variant=win['variant'],
                                 window_h=int(win['window_h']), alive=int(win['alive']),
                                 window_ms=hi-lo, decision_ms=int(meta[name]['decision_ms']),
                                 memory_ms=int(meta[name]['memory_ms']), inhibition=float(meta[name]['inhibition']),
                                 contact_probability=float(meta[name]['worker_contact_probability']),
                                 active50=counts[0]/50,
                                 active51=(counts[0]+scored[-1]['positive_offset_0s'])/51,
                                 active_ms=sum(min(b,hi)-max(a,lo) for a,b in active),
                                 program_ms=program_ms, inactive_completed_ms=inactive_ms,
                                 worker_contact_opportunities=opportunities, worker_contacts=contacts,
                                 worker_contact_selected=selected[WORKER_CONTACT], worker_contact_started=started[WORKER_CONTACT],
                                 selected_total=sum(selected.values()),
                                 manipulations_started=sum(started[a] for a in (INSPECT,ARRANGE,CLEAN,FEED)),
                                 placed=len(placements), **{f'fraction_offset_{k}s':counts[k]/50 for k in phases}))
    assert len(measures)==108
    write(dest/'b01_windows.csv',measures)
    write(dest/'b01_scans.csv',scored)
    write(dest/'b01_decisions.csv',bouts)

    archived = read(PREVIOUS/'analysis/b01_window_diagnostics.csv')
    paper = read(LITERATURE/'Reversibility_of_worker_effect_3_days.csv')
    summary = []
    for condition,h,treatment in (('absent',24,'Without_workers'),('added',24,'With_workers'),
                                   ('removed',48,'Workers_removed')):
        refs = [r for r in archived if r['condition']==condition and r['window_h']==str(h)
                and r['age_days']=='55' and r['variant']=='base']
        base = {int(r['seed']):float(r['active_fraction50']) for r in refs}
        y = [int(r['Nursing'])/int(r['Scans']) for r in paper if r['Treatment']==treatment and r['Time']==str(h)]
        assert len(base)==12 and len(y)==16 and set(SEEDS)<=set(base)
        cells = group((r for r in measures if r['condition']==condition),lambda r:r['variant'])
        cells['reviewed_same_seeds'] = [dict(seed=int(r['seed']),active50=float(r['active_fraction50']),
                                            worker_contacts=int(r['worker_contacts']))
                                        for r in refs if int(r['seed']) in SEEDS]
        for variant, rows in sorted(cells.items()):
            x = [r['active50'] for r in rows]
            delta = estimates([r['active50']-base[r['seed']] for r in rows])
            error = estimates(x,y)
            summary.append(dict(condition=condition, window_h=h, variant=variant,
                                paper_n=len(y), paper_mean=st.fmean(y),
                                paired_delta=delta['mean'], paired_low=delta['ci_low'], paired_high=delta['ci_high'],
                                paper_error=error['mean'], error_low=error['ci_low'], error_high=error['ci_high'],
                                mean_worker_contacts=st.fmean(r['worker_contacts'] for r in rows),
                                **estimates(x)))
    write(dest/'b01_contrasts.csv',summary)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raw',type=Path,default=BASE/'assays')
    p.add_argument('--out',type=Path,default=BASE/'behavior')
    args = p.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    b02(args.raw,args.out)
    paper_b02(args.out)
    b01(args.raw,args.out)
    print('Derived 756 B02 runs, 398 animal trial records, and 108 B01 windows from raw evidence.')


if __name__=='__main__':
    main()
