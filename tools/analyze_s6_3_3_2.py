"""Reconstruct physical episodes, align B01/B02 endpoints and retain censored runs."""
import argparse
import csv
import gzip
import itertools
import json
import math
import random
import statistics as st
from collections import Counter, defaultdict
from pathlib import Path

from analyze_s6_3_3 import q
from run_s6_3_3_2_assays import ARMS, ROOT, save, sha
from verify_s6_3_3_reproduction import read


BASE = ROOT/'experiments/s6_3_3_2'
PREVIOUS = ROOT/'experiments/s6_3_3_1/raw/local'
LITERATURE = ROOT/'experiments/s6_3_3/literature'
MOVED, COLLECTED, FORAGING, DELIVERED, PROGRAM, TRANSFERRED = 4, 5, 11, 12, 17, 21
AUTONOMY, BIRTH, CARE_PROGRAM, CARE_TICK, OBSERVATION, BROOD_MOVED = 31, 35, 40, 41, 42, 43
OPPORTUNITY, SELECTED, STARTED, COMPLETED, INTERRUPTED = range(5)
WALK, APPROACH, INSPECT, ARRANGE, CLEAN, TRANSPORT, FEED, WORKER_CONTACT = range(1, 9)
REVISIT, PICKUP, PLACE, RETURN = range(15, 19)
CARE_WAKE = 19
RELEASE, END = 180000, 780000
HORIZON = (END-RELEASE)/1000
STAGES = (INSPECT, ARRANGE, CLEAN, TRANSPORT, FEED, PICKUP, PLACE)


def write(path, rows):
    rows = list(rows)
    assert rows, path
    columns = dict.fromkeys(k for row in rows for k in row)
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, columns, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def events(folder):
    with gzip.open(folder/'events.csv.gz', 'rt', newline='', encoding='utf-8') as stream:
        yield from itertools.groupby(csv.DictReader(stream), key=lambda r: r['run'])


def group(rows, key):
    output = defaultdict(list)
    for row in rows:
        output[key(row)].append(row)
    return output


def ci(values, reference=None):
    rng = random.Random(63302)
    samples = []
    for _ in range(4096):
        value = st.fmean(rng.choices(values, k=len(values)))
        if reference is not None:
            value -= st.fmean(rng.choices(reference, k=len(reference)))
        samples.append(value)
    return q(samples, .025), q(samples, .975)


def stats(values):
    lo, hi = ci(values)
    return dict(n=len(values), mean=st.fmean(values), ci_low=lo, ci_high=hi)


def position(row):
    return tuple(float(row[f'{axis}_m']) for axis in 'xyz')


def b02_trace(run, profile, entities, trace):
    metadata = {r['entity']:r for r in entities}
    places = {r['entity']:position(r) for r in entities}
    caregivers = {r['entity'] for r in entities if r['role'] != 'brood'}
    brood = {r['entity'] for r in entities if r['role'] == 'brood'}
    actors = {k:dict(first_decision_s=None, first_visible_s=None, first_target_s=None,
                     first_search_s=None, first_approach_s=None, first_contact_s=None,
                     first_pickup_s=None, first_place_s=None, loaded_m=0., path_m=0.,
                     loaded_s=0., placements=0, interrupted=0) for k in sorted(caregivers, key=int)}
    pending, loads, trips, followups, entries, all_placed = {}, {}, [], [], set(), set()
    first_full = None
    counts, seconds = Counter(), Counter()
    for e in trace:
        t, actor, target, kind = int(e['time_ms']), e['actor'], e['target'], int(e['kind'])
        if not RELEASE <= t <= END:
            continue
        time_s = (t-RELEASE)/1000
        if kind in (MOVED, BROOD_MOVED) and actor in places:
            new = position(e)
            distance = math.dist(places[actor], new)
            places[actor] = new
            if kind == BROOD_MOVED and actor in brood and actor in {x['target'] for x in loads.values()}:
                if math.dist(new, (0., 0., 0.)) <= .002:
                    entries.add(actor)
            if actor in caregivers and kind == MOVED:
                actors[actor]['path_m'] += distance
                if actor in pending and pending[actor] == TRANSPORT:
                    actors[actor]['loaded_m'] += distance
                    loads[actor]['loaded_m'] += distance
        if actor not in caregivers:
            continue
        a = actors[actor]
        if kind == CARE_TICK and target == str(CARE_WAKE):
            if a['first_decision_s'] is None:
                a['first_decision_s'] = time_s
            visible = any(math.dist(places[actor], places[b]) <= float(run['perception_m']) and
                          (metadata[b]['colony'] == metadata[actor]['colony'] or
                           (profile['neutral_assay'] == '1' and math.dist(places[b], (0., 0., 0.)) > .002))
                          for b in brood)
            if visible and a['first_visible_s'] is None:
                a['first_visible_s'] = time_s
        if kind != OBSERVATION:
            continue
        phase, act = int(e['phase']), int(e['act'])
        counts[phase, act] += 1
        if phase == SELECTED and target in brood and a['first_target_s'] is None:
            a['first_target_s'] = time_s
        if phase == STARTED:
            pending[actor] = act
            if act in (WALK, REVISIT) and a['first_search_s'] is None:
                a['first_search_s'] = time_s
            if act == APPROACH and a['first_approach_s'] is None:
                a['first_approach_s'] = time_s
            if act in STAGES and a['first_contact_s'] is None:
                assert target in brood and math.dist(places[actor], places[target]) <= .002+1e-12, e
                a['first_contact_s'] = time_s
            if act in (WALK, REVISIT, APPROACH, PICKUP):
                waiting = next((r for r in reversed(followups) if r['actor']==actor), None)
                if waiting is not None and waiting['next_search_s'] is None:
                    waiting['next_search_s'] = time_s
                    waiting['search_delay_s'] = time_s-waiting['placed_s']
        if phase in (COMPLETED, INTERRUPTED):
            pending.pop(actor, None)
            duration = (t-int(e['began_ms']))/1000 if e['duration_known']=='1' else 0.
            seconds[phase, act] += duration
            if phase == INTERRUPTED:
                a['interrupted'] += 1
                if act in (TRANSPORT, PLACE) and actor in loads:
                    load = loads.pop(actor)
                    load.update(end_s=time_s, outcome='interrupted', interruption_code=e['outcome'])
                    trips.append(load)
            elif act == PICKUP:
                assert actor not in loads
                loads[actor] = dict(run=run['run'], actor=actor, target=target, pickup_s=time_s,
                                    pickup_handling_s=duration, loaded_m=0., loaded_s=0.)
                if a['first_pickup_s'] is None:
                    a['first_pickup_s'] = time_s
            elif act == TRANSPORT:
                a['loaded_s'] += duration
                loads[actor]['loaded_s'] += duration
            elif act == PLACE:
                load = loads.pop(actor)
                assert load['target'] == target
                load.update(end_s=time_s, outcome='placed', placement_handling_s=duration)
                trips.append(load)
                prior = next((r for r in reversed(followups) if r['actor']==actor), None)
                if prior is not None:
                    prior['next_place_s'] = time_s
                followups.append(dict(run=run['run'], actor=actor, target=target, placed_s=time_s,
                                      next_search_s=None, next_place_s=None, search_delay_s=None,
                                      observation_remaining_s=HORIZON-time_s))
                a['placements'] += 1
                if a['first_place_s'] is None:
                    a['first_place_s'] = time_s
                all_placed.add(target)
                if len(all_placed)==6 and first_full is None:
                    first_full = time_s
    for load in loads.values():
        load.update(end_s=HORIZON, outcome='window_censored')
        trips.append(load)
    assert len(all_placed) == int(run['retrieved']), run['run']
    if profile['layout'] in ('empty', 'sheltered'):
        assert not trips and not all_placed
    metrics = {k:min((a[k] for a in actors.values() if a[k] is not None), default=None)
               for k in next(iter(actors.values())) if k.startswith('first_')}
    contact = metrics['first_contact_s']
    assert abs(contact - int(run['first_contact_ms'])/1000) < 1e-9 if contact is not None else run['first_contact_ms']=='-1'
    assert (metrics['first_place_s'] is None) == (run['first_retrieval_ms']=='-1')
    metrics.update(
        run=run['run'], seed=int(run['seed']), condition=run['condition'], scenario=profile['scenario'],
        layout=profile['layout'], variant=profile['variant'], origin=profile['origin'],
        neutral_assay=profile['neutral_assay'], items=len(brood), retrieved=len(all_placed),
        shelter_entry=len(entries), first_contact_capped_s=HORIZON if contact is None else contact,
        contact_censored=int(contact is None), first_place_censored=int(not all_placed),
        full_completion_s=first_full, full_censored=int(first_full is None),
        first_decision_visible=sum(a['first_visible_s'] is not None and a['first_visible_s']==a['first_decision_s']
                                   for a in actors.values()),
        detected_caregivers=sum(a['first_visible_s'] is not None for a in actors.values()),
        caregivers=len(actors), path_m=sum(a['path_m'] for a in actors.values()),
        loaded_m=sum(a['loaded_m'] for a in actors.values()), loaded_s=sum(a['loaded_s'] for a in actors.values()),
        pickups=sum(t['outcome'] in ('placed', 'interrupted', 'window_censored') for t in trips),
        completed_trips=sum(t['outcome']=='placed' for t in trips),
        restarted=sum(r['next_search_s'] is not None for r in followups),
        repeats=sum(r['next_place_s'] is not None for r in followups))
    actor_rows = [dict(run=run['run'], actor=actor, **values) for actor,values in actors.items()]
    act_rows = [dict(run=run['run'], phase=phase, act=act, events=n, elapsed_s=seconds[phase, act])
                for (phase, act), n in sorted(counts.items())]
    return metrics, actor_rows, trips, followups, act_rows


def b02(root):
    output = [[], [], [], [], []]
    for arm in ('b02','robustness','sensitivity'):
        folder = root/arm
        runs = {r['run']:r for r in read(folder/'runs.csv')}
        profiles = {r['run']:r for r in read(folder/'profiles.csv')}
        entities = group(read(folder/'initial.csv'), lambda r:r['run'])
        for name, trace in events(folder):
            assert runs[name]['conserved']==runs[name]['continuation_equal']=='1'
            result = b02_trace(runs[name], profiles[name], entities[name], trace)
            output[0].append(result[0])
            for dest, source in zip(output[1:], result[1:]):
                dest.extend(source)
    assert len(output[0])==396
    return output


def b02_comparison(simulation):
    units = defaultdict(dict)
    for r in read(LITERATURE/'B02_retrieval.csv'):
        units[r['qw'],r['queen']][r['same']] = r
    assert len(units)==199 and all(len(r)==2 for r in units.values())
    matched = {unit for caste,unit in units if caste=='q'} & {unit for caste,unit in units if caste=='w'}
    productivity = {r['colony'] for r in read(LITERATURE/'B02_productivity.csv')}
    author = (matched | {unit for caste,unit in units if caste=='w2'}) & productivity
    assert len(matched)==67 and len(author)==61
    published_pairs, observed_summary, model_error, changes = [], [], [], []
    fields = {'retrieved':' brood items after 10min', 'first_contact_capped_s':'first contact ',
              'first_retrieval_capped_s':' first retrieving', 'reported_rate_items_s':'b10t'}
    for (caste,unit), pair in units.items():
        source = dict(caste=caste, unit=unit, matched67=int(unit in matched), productivity61=int(unit in author))
        for metric,field in fields.items():
            for origin,key in (('own','1'),('foreign','0')):
                source[metric+'_'+origin] = float(pair[key][field])
        for origin,key in (('own','1'),('foreign','0')):
            source['raw_task_duration_s_'+origin] = float(pair[key]['time task'])
            source['last_retrieval_s_'+origin] = float(pair[key]['last retrieving'])
            source['contact_censored_'+origin] = int(source['first_contact_capped_s_'+origin]>=HORIZON)
            source['retrieval_censored_'+origin] = int(source['first_retrieval_capped_s_'+origin]>=HORIZON)
            source['full_censored_'+origin] = int(source['retrieved_'+origin]<6)
            source['full_capped_s_'+origin] = HORIZON if source['full_censored_'+origin] else source['last_retrieval_s_'+origin]
        published_pairs.append(source)
    for (caste, rows) in sorted(group(published_pairs, lambda r:r['caste']).items()):
        for scope, allowed in (('all', rows), ('matched67', [r for r in rows if r['matched67']]),
                               ('productivity61', [r for r in rows if r['productivity61']])):
            for metric in (*fields, 'contact_censored', 'retrieval_censored', 'full_censored', 'full_capped_s'):
                if allowed:
                    x = [r[metric+'_own'] for r in allowed]
                    y = [r[metric+'_foreign'] for r in allowed]
                    observed_summary.append(dict(caste=caste, scope=scope, metric=metric,
                        own_mean=st.fmean(x), foreign_mean=st.fmean(y),
                        contrast='foreign minus own', **stats([b-a for a,b in zip(x,y)])))
    primary = [r for r in simulation if r['scenario']=='B02_line' and r['neutral_assay']=='1']
    old = {(int(r['seed']),r['condition']):r for r in read(PREVIOUS/'retrieval-line/runs.csv')}
    for caste,condition in (('q','queen'),('w','three_workers')):
        pairs = group([r for r in primary if r['condition']==condition], lambda r:r['seed'])
        measured = [r for r in published_pairs if r['caste']==caste]
        for metric in ('retrieved','first_contact_capped_s','contact_censored','first_retrieval_capped_s',
                       'retrieval_censored','full_censored','full_capped_s'):
            def value(r):
                if metric == 'first_retrieval_capped_s':
                    return HORIZON if r['first_place_s'] is None else r['first_place_s']
                if metric == 'retrieval_censored':
                    return r['first_place_censored']
                if metric == 'full_capped_s':
                    return HORIZON if r['full_completion_s'] is None else r['full_completion_s']
                return r[metric]
            x = [st.fmean(value(r) for r in pair) for pair in pairs.values()]
            y = [st.fmean((r[metric+'_own'],r[metric+'_foreign'])) for r in measured]
            lo, hi = ci(x,y)
            pl,ph = ci(y)
            model_error.append(dict(caste=caste, condition=condition, metric=metric, paper_n=len(y),
                paper_mean=st.fmean(y), paper_ci_low=pl, paper_ci_high=ph, **stats(x),
                error=st.fmean(x)-st.fmean(y), error_ci_low=lo, error_ci_high=hi))
            differences = [value(pair[1])-value(pair[0]) for pair in pairs.values()
                           if pair[0]['origin']=='own' and pair[1]['origin']=='foreign']
            assert len(differences)==12
            changes.append(dict(condition=condition, metric=metric, contrast='neutral foreign minus own',
                                **stats(differences)))
            if metric not in ('retrieved','first_contact_capped_s'):
                continue
            baseline = [old[seed,condition] for seed in pairs]
            b = [int(r['retrieved']) if metric=='retrieved' else (
                HORIZON if int(r['first_contact_ms'])<0 else int(r['first_contact_ms'])/1000) for r in baseline]
            x = [value(next(r for r in pair if r['origin']=='own')) for pair in pairs.values()]
            changes.append(dict(condition=condition, metric=metric, contrast='timed own minus S6.3.3.1 local',
                                old_mean=st.fmean(b), new_mean=st.fmean(x), **stats([a-c for a,c in zip(x,b)])))
    for condition,items in sorted(group(simulation, lambda r:r['condition']).items()):
        named = {(r['scenario'],r['layout'],r['variant'],r['neutral_assay'],r['seed']):r for r in items if r['origin']=='own'}
        for name in ('mirror','split','far','empty','sheltered'):
            robustness = [(r,named['B02_robustness','line','base','1',r['seed']]) for r in items
                          if r['scenario']=='B02_robustness' and r['layout']==name]
            for metric in ('retrieved','first_contact_capped_s','contact_censored'):
                changes.append(dict(condition=condition, metric=metric, contrast=name+' minus robustness line',
                                    **stats([a[metric]-b[metric] for a,b in robustness])))
        for layout in ('line','far'):
            perturbations = [r for r in items if r['scenario']=='B02_sensitivity' and r['layout']==layout and r['variant']!='base']
            for variant, rows in sorted(group(perturbations, lambda r:r['variant']).items()):
                family = 'B02_line' if layout=='line' else 'B02_sensitivity'
                for metric in ('retrieved','first_contact_capped_s','contact_censored'):
                    values = [r[metric]-named[family,layout,'base','1',r['seed']][metric] for r in rows]
                    changes.append(dict(condition=condition, metric=metric, contrast=layout+' '+variant+' minus base',
                                        **stats(values)))
    return published_pairs, observed_summary, model_error, changes


def b01(root):
    samples, scans_out = [], []
    for arm in ('b01','b01-sensitivity'):
        folder = root/arm
        windows = group(read(folder/'windows.csv'), lambda r:r['run'])
        scans = group(read(folder/'scans.csv'), lambda r:(r['run'],r['window_h']))
        queen = {r['run']:r['entity'] for r in read(folder/'initial.csv') if r['role']=='queen'}
        for name, trace in events(folder):
            measures = []
            for win in windows[name]:
                data = scans[name,win['window_h']]
                assert len(data)==51
                measures.append(dict(window=win, low=int(win['begin_ms']), high=int(win['end_ms']),
                                     scans=data, intervals=[], placements=[], contacts=0, opportunities=0))
            for e in trace:
                if int(e['kind'])!=OBSERVATION or e['actor']!=queen[name]:
                    continue
                end,start = int(e['time_ms']),int(e['began_ms'])
                act,phase = int(e['act']),int(e['phase'])
                for m in measures:
                    if m['low']<=end<m['high'] and act==WORKER_CONTACT:
                        if phase==COMPLETED:
                            m['contacts']+=1
                        elif phase==OPPORTUNITY:
                            m['opportunities']+=1
                    if m['low']<=end<m['high'] and phase==COMPLETED and act==PLACE:
                        m['placements'].append(end)
                    mass = sum(int(e[field+'_ug']) for field in ('carbs','protein','water'))
                    tactile = (act in (INSPECT,ARRANGE,CLEAN) or
                               (act==FEED and phase==COMPLETED and mass>0))
                    if (tactile and phase in (COMPLETED,INTERRUPTED) and e['duration_known']=='1'
                            and start<m['high'] and end>m['low']):
                        m['intervals'].append((start,end,act))
            for m in measures:
                win = m['window']
                local_scans = []
                for scan in m['scans']:
                    start, end = int(scan['begin_ms']),int(scan['end_ms'])
                    manipulation = any(lo<end and hi>start for lo,hi,_ in m['intervals'])
                    placement = any(start<=t<end for t in m['placements'])
                    point = any(lo<=start<hi for lo,hi,_ in m['intervals']) or start in m['placements']
                    local_scans.append(dict(run=name, window_h=win['window_h'], scan=scan['scan'],
                        begin_ms=start, end_ms=end, scored_active=int(manipulation or placement),
                        point_active=int(point), manipulation=int(manipulation), placement=int(placement),
                        inherited_act_only=int(scan['active_care']), alive=int(scan['alive'])))
                scans_out.extend(local_scans)
                counts = {k:sum(r[k] for r in local_scans[:50]) for k in ('scored_active','point_active','inherited_act_only')}
                minutes = m['high']-m['low']
                tactile_ms = sum(min(hi,m['high'])-max(lo,m['low']) for lo,hi,_ in m['intervals'])
                samples.append(dict(run=name,seed=int(win['seed']),variant=win['variant'],assay=win['assay'],
                    condition=win['condition'],age_days=int(win['context_age_days']),window_h=int(win['window_h']),
                    alive=int(win['alive']),active_fraction50=counts['scored_active']/50,
                    active_fraction51=sum(r['scored_active'] for r in local_scans)/51,
                    legacy_definition50=counts['inherited_act_only']/50,point_fraction50=counts['point_active']/50,
                    tactile_fraction=tactile_ms/minutes,care_program_fraction=int(win['program_ms'])/minutes,
                    known_active_fraction=int(win['active_ms'])/minutes,worker_contacts=m['contacts'],
                    worker_opportunities=m['opportunities'],placements=len(m['placements']),
                    feeding_protein_ug=int(win['protein_ug']),feeding_carbs_ug=int(win['carbs_ug']),
                    feeding_water_ug=int(win['water_ug'])))
    assert len(samples)==228
    return samples,scans_out


def b01_comparison(samples):
    mapping = {'Without_workers':'absent','With_workers':'added','Workers_removed':'removed'}
    source = read(LITERATURE/'Reversibility_of_worker_effect_3_days.csv')
    old = read(PREVIOUS/'b01/windows.csv')
    error, controls = [], []
    for treatment, h in (('absent',24),('added',24),('removed',48)):
        y = [int(r['Nursing'])/int(r['Scans']) for r in source if mapping[r['Treatment']]==treatment and int(r['Time'])==h]
        selected = [r for r in samples if r['condition']==treatment and r['window_h']==h and r['age_days']==55]
        base = {r['seed']:r['active_fraction50'] for r in selected if r['variant']=='base'}
        assert len(base)==12 and len(y)==16
        for variant, rows in sorted(group(selected, lambda r:r['variant']).items()):
            x = [r['active_fraction50'] for r in rows]
            a, b = ci(x,y)
            pl,ph = ci(y)
            contrast = [r['active_fraction50']-base[r['seed']] for r in rows]
            cl,ch = ci(contrast)
            error.append(dict(condition=treatment,window_h=h,variant=variant,paper_n=len(y),paper_mean=st.fmean(y),
                paper_ci_low=pl,paper_ci_high=ph, **stats(x), error=st.fmean(x)-st.fmean(y),error_ci_low=a,error_ci_high=b,
                paired_change_from_timed_base=st.fmean(contrast), paired_ci_low=cl,paired_ci_high=ch))
        prior = {int(r['seed']):int(r['positive50'])/50 for r in old if r['condition']==treatment and
                 int(r['window_h'])==h and r['context_age_days']=='55'}
        x = [prior[s] for s in base]
        a,b = ci(x,y)
        cl,ch = ci([prior[s]-base[s] for s in base])
        error.append(dict(condition=treatment,window_h=h,variant='S6.3.3.1',paper_n=len(y),paper_mean=st.fmean(y),
            paper_ci_low=pl,paper_ci_high=ph, **stats(x), error=st.fmean(x)-st.fmean(y), error_ci_low=a,error_ci_high=b,
            paired_change_from_timed_base=st.fmean(prior[s]-base[s] for s in base), paired_ci_low=cl,paired_ci_high=ch))
    for key, rows in sorted(group(samples, lambda r:(r['assay'],r['condition'],r['age_days'],r['window_h'],r['variant'])).items()):
        a,c,age,h,v = key
        values = ['active_fraction50','active_fraction51','point_fraction50','tactile_fraction','known_active_fraction',
                  'care_program_fraction','worker_contacts','worker_opportunities','placements','feeding_protein_ug']
        controls.append(dict(assay=a,condition=c,age_days=age,window_h=h,variant=v,
                             **stats([r['active_fraction50'] for r in rows]),
                             **{field:st.fmean(r[field] for r in rows) for field in values}))
    return error, controls


def integration(root):
    folder = root/'integration'
    runs = {r['run']:r for r in read(folder/'ecology.csv')}
    entities = group(read(folder/'initial.csv'), lambda r:r['run'])
    rows = []
    for name,trace in events(folder):
        row = runs[name]
        assert row['exact_restore']==row['conserved']=='1'
        roles = {r['entity']:r['role'] for r in entities[name]}
        care_end = set()
        changes, after, actions = Counter(), set(), Counter()
        for e in trace:
            actor, kind = e['actor'], int(e['kind'])
            role = roles.get(actor, '')
            if kind == CARE_PROGRAM and e['target']=='0':
                care_end.add(actor)
            if kind == FORAGING and actor in care_end:
                after.add(actor)
            if kind == PROGRAM:
                changes[role] += 1
            if kind in (COLLECTED, DELIVERED, TRANSFERRED, FORAGING, BIRTH, AUTONOMY):
                actions[kind] += 1
            if kind==OBSERVATION and int(e['phase'])==COMPLETED and int(e['act']) in (*STAGES,RETURN):
                actions[role,int(e['act'])] += 1
        assert actions[BIRTH]==int(row['births'])
        rows.append(dict(**row,worker_program_changes=changes['worker'],worker_foraged_after_care=len(after),
            forage_decisions=actions[FORAGING],food_collections=actions[COLLECTED],food_deliveries=actions[DELIVERED],
            nutrition_transfers=actions[TRANSFERRED],autonomy_decisions=actions[AUTONOMY],
            **{f'{role}_{act}_completed':actions[role,act] for role in ('queen','worker') for act in (*STAGES,RETURN)}))
    assert len(rows)==12
    return rows


def carthy():
    rows = []
    for row in read(BASE/'literature/carthy_loaded_returns.csv'):
        # The inch is exactly 25.4 mm. The printed speed column is preserved separately.
        distance = 25.4*float(row['distance_in']) if row['distance_in'] else None
        speed = distance/float(row['time_s']) if distance is not None and row['time_s'] else None
        rows.append(dict(**row,path_mm=distance,derived_path_rate_mm_s=speed,
                         normal_reference=int(row['status']=='TIMED' and row['condition']=='normal')))
    summary = []
    for (ant,condition), data in sorted(group([r for r in rows if r['status']=='TIMED'],
                                               lambda r:(r['individual'],r['condition'])).items()):
        rates = [r['derived_path_rate_mm_s'] for r in data]
        summary.append(dict(individual=ant,condition=condition,paths=len(rates),
                            minimum_mm_s=min(rates),median_mm_s=st.median(rates),maximum_mm_s=max(rates),
                            biological_units=1))
    return rows, summary


def verify_archive(root, deep=False):
    manifest = json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    assert {r['arm']:r['runs'] for r in manifest['arms']}==ARMS
    for item in manifest['arms']:
        for name, receipt in item['files'].items():
            path = root/item['arm']/name
            assert sha(path)==receipt['sha256'] and path.stat().st_size==receipt['bytes'], path
            if deep and path.suffix=='.gz':
                import hashlib
                with gzip.open(path,'rb') as stream:
                    assert hashlib.file_digest(stream,'sha256').hexdigest()==receipt['csv_sha256'], path
    print('Verified frozen archive of 484 fidelity and integration runs.', flush=True)


def analyze(root, dest):
    dest.mkdir(parents=True,exist_ok=True)
    retrieval, actors, trips, followups, acts = b02(root)
    b02_pairs, b02_paper, b02_error, b02_changes = b02_comparison(retrieval)
    care, scans = b01(root)
    b01_error, b01_controls = b01_comparison(care)
    integrated = integration(root)
    motion, motion_summary = carthy()
    outputs = {
        'b02_run_diagnostics':retrieval, 'b02_caregivers':actors, 'b02_physical_trips':trips,
        'b02_after_placement':followups, 'b02_observed_acts':acts, 'b02_published_pairs':b02_pairs,
        'b02_origin_contrasts':b02_paper, 'b02_paper_errors':b02_error, 'b02_paired_model_contrasts':b02_changes,
        'b01_window_diagnostics':care, 'b01_scans':scans, 'b01_paper_errors':b01_error,
        'b01_control_diagnostics':b01_controls, 'integration_diagnostics':integrated,
        'carthy_converted_paths':motion, 'carthy_individual_summary':motion_summary,
    }
    for name, rows in outputs.items():
        write(dest/(name+'.csv'), rows)
    save(dest/'summary.json', dict(retrieval_runs=len(retrieval), b01_runs=len({r['run'] for r in care}),
        b01_windows=len(care), b01_scans=len(scans), ecological_runs=len(integrated),
        complete_placements=sum(r['retrieved'] for r in retrieval), loaded_episodes=len(trips),
        retrospective_B01_B02=True, biological_parameters_fitted=0,
        bootstrap_draws=4096, bootstrap_seed=63302,
        source_bootstrap_unit='queen or group/colony, origins paired', model_bootstrap_unit='simulator seed',
        censored_latency_s=HORIZON))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raw', type=Path, default=BASE/'raw')
    p.add_argument('--out', type=Path, default=BASE/'analysis')
    p.add_argument('--verify-only', action='store_true')
    p.add_argument('--deep', action='store_true')
    args = p.parse_args()
    verify_archive(args.raw,args.deep)
    if not args.verify_only:
        analyze(args.raw,args.out)


if __name__=='__main__':
    main()
