"""Compare the frozen paired assays and audit the original retained CSVs."""
import argparse
from collections import defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import random
import statistics as st

from analyze_s6_3_2_performance import describe, quantile
from analyze_s6_3_3_1_performance import emit
from diagnose_s6_3_3_1 import STAGE, events, nursing, read, trace_retrieval

REFERENCE = STAGE.parent/'s6_3_3'
HISTORICAL = (7,19,43,71,101,137,181,223,269,313,367,421)
HOLDOUT = (1009,1013,1019,1021,1031,1033,1039,1049,1051,1061,1063,1069)
LAYOUTS = ('line','mirror','split','far','empty','sheltered')
POLICIES = ('legacy','local')


def sha(path, unpack=False):
    opener = gzip.open if unpack else open
    with opener(path,'rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def paired(legacy, local):
    assert len(legacy) == len(local) and legacy
    rng = random.Random(63301)
    draws = [rng.choices(range(len(legacy)), k=len(legacy)) for _ in range(4096)]
    a = [st.mean(legacy[i] for i in indices) for indices in draws]
    b = [st.mean(local[i] for i in indices) for indices in draws]
    delta = [y-x for x,y in zip(a,b)]
    return dict(seeds=len(legacy),legacy_mean=st.mean(legacy),local_mean=st.mean(local),
                legacy_ci_low=quantile(a,.025),legacy_ci_high=quantile(a,.975),
                local_ci_low=quantile(b,.025),local_ci_high=quantile(b,.975),
                paired_delta=st.mean(y-x for x,y in zip(legacy,local)),
                paired_ci_low=quantile(delta,.025),paired_ci_high=quantile(delta,.975))


def followup_and_episodes(output):
    first = {}
    for row in output['after_delivery']:
        key = (row['set'],row['policy'],row['run'],row['actor'])
        if key not in first or row['time_ms'] < first[key]['time_ms']:
            first[key] = row
    output['first_delivery_followup'] = list(first.values())
    # CareEnd -> CareWake -> CareBegin takes two 1 ms scheduler boundaries.
    # A larger gap, target change, or unsuccessful terminal separates loaded episodes.
    episodes = []
    pending = {}
    for row in output['transport_segments']:
        key = (row['set'],row['policy'],row['run'],row['actor'])
        old = pending.get(key)
        start = row['end_ms']-row['duration_ms']
        if not old or old['target'] != row['target'] or start-old['end_ms'] > 2 or not row['completed']:
            episode = {k:row[k] for k in ('run','seed','policy','set','condition','layout','actor','target')}
            episode.update(start_ms=start,end_ms=start,active_ms=0,segment_terminals=0,completed_segments=0,
                           distance_m=0.,shelter_entries=0,first_terminal_id=row['observation_id'],last_terminal_id=0)
            pending[key] = episode
            episodes.append(episode)
        episode = pending[key]
        episode['end_ms'] = row['end_ms']
        episode['active_ms'] += row['duration_ms']
        episode['segment_terminals'] += 1
        episode['completed_segments'] += row['completed']
        episode['distance_m'] += row['displacement_m']
        episode['shelter_entries'] += row['delivered']
        episode['last_terminal_id'] = row['observation_id']
        if not row['completed'] or row['delivered']:
            del pending[key]
    output['continuous_loaded_episodes'] = episodes


def collect(root):
    manifest = json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    output = defaultdict(list)
    seen = set()
    for batch in manifest['batches']:
        policy, mode = batch['policy'], batch['mode']
        assert (policy,mode) not in seen
        seen.add((policy,mode))
        folder = root/policy/mode
        for file, info in batch['files'].items():
            path = folder/file
            assert path.stat().st_size == info['bytes'] and sha(path) == info['sha256'], path
            assert sha(path,file.endswith('.gz')) == info['csv_sha256'], path
        all_runs = read(folder/'runs.csv')
        assert len(all_runs) == batch['runs']
        assert all(r['continuation_equal'] == r['conserved'] == '1' for r in all_runs)
        if mode == 'b01':
            assert len(all_runs) == 40
            windows = defaultdict(list)
            for row in read(folder/'windows.csv'):
                windows[row['run']].append(row)
            assert len(windows) == len(all_runs)
            decoded = set()
            for run, rows in events(folder/'events.csv.gz', windows):
                assert run not in decoded
                decoded.add(run)
                output['b01_windows'].extend(dict(policy=policy,**r) for r in nursing(rows,windows[run]))
            assert decoded == set(windows)
            continue
        layout = mode.split('-',1)[1]
        sample = 'historical' if mode == 'retrieval-line' else 'holdout'
        seeds = HISTORICAL if sample == 'historical' else HOLDOUT
        assert {(int(r['seed']),r['condition']) for r in all_runs} == {
            (seed,group) for seed in seeds for group in ('queen','three_workers')}
        info = {r['run']:dict(r,layout=layout,policy=policy,set=sample) for r in all_runs}
        count = len(output['runs'])
        for run, rows in events(folder/'events.csv.gz', info):
            trace_retrieval(run,info[run],rows,output)
        assert len(output['runs'])-count == 24
    assert seen == {(policy,mode) for policy in POLICIES for mode in
                    ('b01','retrieval-line',*(f'holdout-{layout}' for layout in LAYOUTS))}
    assert len(output['runs']) == 336 and len(output['b01_windows']) == 240
    assert [{k:str(v) for k,v in r.items()} for r in output['runs']
            if r['policy'] == 'legacy' and r['set'] == 'historical'] == sorted(
                read(STAGE/'diagnosis/runs.csv'), key=lambda r:(HISTORICAL.index(int(r['seed'])),r['condition']))
    followup_and_episodes(output)
    return output


def retrieval(output):
    runs = defaultdict(dict)
    for row in output['runs']:
        runs[row['set'],row['layout'],row['condition']][row['policy'],row['seed']] = row
    metrics = ('retrieved','first_contact_capped_ms','contact_observed','path_m','inactive_ms','approach_ms',
               'handling_ms','transport_ms','started_contacts','completed_contacts','transport_interrupted')
    comparison = []
    for (sample,layout,group),rows in sorted(runs.items()):
        seeds = HISTORICAL if sample == 'historical' else HOLDOUT
        for metric in metrics:
            values = [[rows[policy,seed][metric] for seed in seeds] for policy in POLICIES]
            comparison.append(dict(set=sample,layout=layout,condition=group,metric=metric,**paired(*values)))
    output['paired_retrieval'] = comparison
    # Published per-colony experimental endpoints, independently resampled from simulator seed pairs.
    source = read(REFERENCE/'analysis/source_endpoints.csv')
    observed_units = {group: {r['unit_id'] for r in source if r['assay'] == 'retrieval' and r['condition'] == group}
                      for group in ('queen','three_workers','later_workers')}
    paired_ids = observed_units['queen'] & observed_units['three_workers']
    productivity_ids = {r['colony'] for r in read(REFERENCE/'literature/B02_productivity.csv')}
    author_ids = (paired_ids | observed_units['later_workers']) & productivity_ids
    assert len(paired_ids) == 67 and len(author_ids) == 61
    cohorts = dict(all_units=observed_units['queen'] | observed_units['three_workers'],
                   matched67=paired_ids,productivity61=author_ids)
    papers = []
    for cohort,ids in cohorts.items():
        for group in ('queen','three_workers'):
            for metric in ('retrieved','first_contact_capped_s'):
                published = [float(r['value']) for r in source if r['assay'] == 'retrieval' and
                             r['condition'] == group and r['metric'] == metric and r['unit_id'] in ids]
                rows = runs['historical','line',group]
                for policy in POLICIES:
                    simulated = [rows[policy,s]['retrieved' if metric == 'retrieved' else 'first_contact_capped_ms']
                                 /(1 if metric == 'retrieved' else 1000) for s in HISTORICAL]
                    papers.append(dict(cohort=cohort,condition=group,metric=metric,policy=policy,
                                       **external_comparison(published,simulated)))
    output['b02_literature_comparison'] = papers


def external_comparison(observed, simulated):
    rng = random.Random(63301)
    pairs = [(st.mean(rng.choices(observed,k=len(observed))),st.mean(rng.choices(simulated,k=len(simulated))))
             for _ in range(4096)]
    diff = [b-a for a,b in pairs]
    return dict(observed_units=len(observed),simulation_seeds=len(simulated),
                observed_mean=st.mean(observed),simulated_mean=st.mean(simulated),
                observed_ci_low=quantile([a for a,_ in pairs],.025),observed_ci_high=quantile([a for a,_ in pairs],.975),
                simulated_ci_low=quantile([b for _,b in pairs],.025),simulated_ci_high=quantile([b for _,b in pairs],.975),
                signed_error=st.mean(simulated)-st.mean(observed),error_ci_low=quantile(diff,.025),error_ci_high=quantile(diff,.975))


def care(output):
    rows = output['b01_windows']
    source = read(REFERENCE/'analysis/source_endpoints.csv')
    results = []
    for condition,window in (('absent','24'),('added','24'),('removed','48')):
        expected = [float(r['value']) for r in source if r['assay'] == 'reversal' and r['age'] == '55' and
                    r['condition'] == condition and r['window_h'] == window]
        assert len(expected) == 16
        for policy in POLICIES:
            sample = [r for r in rows if r['age_days'] == '55' and r['condition'] == condition and
                      r['window_h'] == window and r['policy'] == policy]
            assert len(sample) == 12
            results.append(dict(condition=condition,window_h=window,policy=policy,
                **external_comparison(expected,[r['overlap50'] for r in sample]),
                overlap51=st.mean(r['overlap51'] for r in sample),
                point50=st.mean(r['point50'] for r in sample),active_time=st.mean(r['active_care_time_fraction'] for r in sample),
                inactive_time=st.mean(r['inactive_fraction'] for r in sample),program_time=st.mean(r['program_fraction'] for r in sample),
                worker_opportunities=st.mean(r['worker_opportunities'] for r in sample),
                worker_contacts=st.mean(r['worker_completed'] for r in sample),
                worker_contact_ms=st.mean(r['worker_contact_ms'] for r in sample)))
    output['b01_literature_comparison'] = results


def density(path):
    tables = defaultdict(list)
    for row in read(path):
        tables[row['layout'],row['policy'],row['caregivers'],row['brood_per_caregiver']].append(row)
    assert len(tables) == 32
    result = []
    for (layout,policy,caregivers,brood),rows in sorted(tables.items()):
        assert [r['replicate'] for r in rows] == ['0','1','2','3'] and all(r['restore_equal'] == '1' for r in rows)
        assert len({r['trace_hash'] for r in rows}) == 1 and rows[0]['trace_hash'] != '0'
        c,b = int(caregivers),int(brood)
        initial = c*(c-1+c*b) if layout == 'dense' else c*b
        assert all(int(r['initial_opportunities']) == initial for r in rows)
        for key in ('advance_ms','checkpoint_ms','restore_ms','candidates_examined','opportunities','selected',
                    'started','completed','interrupted','completed_brood_handling','nutrition_transfers',
                    'advance_facts','journal_facts','encoded_history_bytes','checkpoint_bytes'):
            result.append(dict(layout=layout,policy=policy,caregivers=c,brood_per_caregiver=b,metric=key,
                               **describe([float(r[key]) for r in rows if r['warmup']=='0'])))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw', type=Path, default=STAGE/'raw')
    parser.add_argument('--out', type=Path, default=STAGE/'analysis')
    parser.add_argument('--density', type=Path)
    parser.add_argument('--density-only', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result = {}
    if args.density_only:
        assert args.density, '--density is required'
    else:
        result = collect(args.raw)
        retrieval(result)
        care(result)
    if args.density:
        result['density_summary'] = density(args.density)
    if not args.check:
        args.out.mkdir(parents=True,exist_ok=True)
    for name,rows in result.items():
        if rows:
            emit(args.out/(name+'.csv'),rows,args.check)
    print({name:len(rows) for name,rows in result.items()})


if __name__ == '__main__':
    main()
