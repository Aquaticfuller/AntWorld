"""Archive and audit day-scale ecology, physical controls and committed interaction chains."""
import argparse
import gzip
import hashlib
import itertools
import json
from collections import Counter
from pathlib import Path
import shutil

from analyze_s6_3_3_2 import (
    BIRTH, BROOD_MOVED, CARE_PROGRAM, COMPLETED, DELIVERED, FEED, INTERRUPTED, OBSERVATION,
    PICKUP, PLACE, PROGRAM, TRANSFERRED, read, write,
)
from run_s6_3_3_3_assays import BASE, save, sha

DAY = 86_400_000


def split_facts(source, dest, expected):
    files = {}
    with source.open('rb') as stream:
        header = next(stream)
        for key, lines in itertools.groupby(stream, lambda line:line.split(b',',1)[0]):
            run = key.decode('ascii')
            path = dest/f'{run}.csv.gz'
            digest = hashlib.sha256(header)
            count = 0
            with path.open('xb') as file, gzip.GzipFile(filename='',mode='wb',fileobj=file,mtime=0,compresslevel=4) as out:
                out.write(header)
                for line in lines:
                    out.write(line)
                    digest.update(line)
                    count += 1
            assert run not in files and (run not in expected or expected[run]==count)
            files[run] = dict(csv_sha256=digest.hexdigest(), sha256=sha(path), rows=count, bytes=path.stat().st_size)
    assert not expected or set(expected)==set(files)
    return files


def archive(matrix, probes, dest):
    dest.mkdir(parents=True)
    for name in ('runs','days','individuals'):
        shutil.copyfile(matrix/f'{name}.csv',dest/f'{name}.csv')
    shutil.copyfile(probes/'probes.csv',dest/'probes.csv')
    expected = {r['run']:int(r['events']) for r in read(dest/'runs.csv')}
    assert len(expected)==72
    (dest/'events').mkdir()
    (dest/'probe_events').mkdir()
    data = split_facts(matrix/'events.csv',dest/'events',expected)
    controls = split_facts(probes/'events.csv',dest/'probe_events',{})
    assert len(controls)==5
    csvs = {p.name:sha(p) for p in dest.glob('*.csv')}
    save(dest/'manifest.json',dict(csv_sha256=csvs, events=data, probe_events=controls))


def verify(dest):
    manifest = json.loads((dest/'manifest.json').read_text(encoding='utf-8'))
    for name,digest in manifest['csv_sha256'].items():
        assert sha(dest/name)==digest, name
    for folder, count in (('events',72),('probe_events',5)):
        assert len(manifest[folder])==count
        for name,info in manifest[folder].items():
            path = dest/folder/f'{name}.csv.gz'
            assert path.stat().st_size==info['bytes'] and sha(path)==info['sha256'], path


def facts(path):
    # This native exporter emits numeric cells with no quoting.
    with gzip.open(path,'rt',encoding='utf-8') as stream:
        header = next(stream).strip().split(',')
        assert header[:12]==['run','event','time_ms','kind','actor','colony','stage','source','related','phase','act','bout']
        for line in stream:
            yield line.rstrip().split(',')


def case(dest, run, end, individuals, sequences):
    name = run['run']
    queen = int(run['queen'])
    displaced = int(run['displaced_brood'])
    counts, amounts, placed, emerged = Counter(), Counter(), set(), set()
    born, last_mode, worker_events, life = set(), {}, {}, {}
    transfer_sources, care_feed_bouts = {}, set()
    depths = []
    timeline, development = [], {}
    for f in facts(dest/'events'/f'{name}.csv.gz'):
        fact, now, kind, actor = map(int,f[1:5])
        if kind==8:
            counts['deaths'] += 1
            counts['death_cause_'+f[8]] += 1
            if actor==queen:
                counts['queen_death_ms'] = now
        if kind==BIRTH:
            assert int(f[8])==queen and actor not in born
            born.add(actor)
            timeline.append(('queen_birth',fact,now,actor))
            development[actor] = [(fact,now,0)]
        if kind in (7,8) and actor in development:
            development[actor].append((fact,now,int(f[6])))
        if kind==7 and f[6]=='3':
            emerged.add(actor)
        if kind in (PROGRAM, TRANSFERRED, DELIVERED, CARE_PROGRAM, OBSERVATION, BROOD_MOVED):
            work = worker_events.setdefault(actor,{})
            if kind==PROGRAM:
                mode = int(f[8])
                if mode!=last_mode.get(actor,0):
                    counts['actual_worker_task_switches'] += actor!=queen
                    last_mode[actor] = mode
                if mode in (1,3,4):
                    work.setdefault('other_work',(fact,now,mode))
            elif kind==DELIVERED:
                work.setdefault('food_return',(fact,now,int(f[18])))
                counts['food_deliveries'] += 1
                amounts['delivered_carbs_ug'] += int(f[18])
            elif kind==TRANSFERRED:
                recipient = int(f[8])
                gain = [int(x) for x in f[18:22]]
                assert sum(gain)>0
                counts['transfers'] += 1
                if f[6]=='3' and actor!=queen and recipient!=queen:
                    counts['worker_to_worker_or_brood'] += 1
                if recipient==queen:
                    counts['queen_transfers'] += 1
                # Event stage is the donor. The recipient's stage is reconstructed below.
                work.setdefault('first_transfer',(fact,now,recipient))
                for nutrient, qty in zip(('carbs','protein','water','other'),gain):
                    amounts['transferred_'+nutrient+'_ug'] += qty
                transfer_sources[int(f[7]),actor,recipient] = gain
                if life[recipient]<3:
                    counts['transfers_to_brood'] += 1
                    amounts['protein_to_brood_ug'] += gain[1]
                    work.setdefault('brood_feed',(fact,now,recipient))
            elif kind==CARE_PROGRAM:
                if f[8]=='1':
                    counts['care_starts'] += 1
                    if actor==queen:
                        counts['queen_care_starts'] += 1
                        timeline.append(('queen_care_start',fact,now,actor))
                else:
                    counts['care_exits'] += 1
            elif kind==BROOD_MOVED:
                counts['brood_moved_facts'] += 1
                if actor==displaced:
                    counts['displaced_moved_facts'] += 1
                    depths.append(float(f[16]))
            elif kind==OBSERVATION:
                phase, act, outcome = int(f[9]), int(f[10]), int(f[14])
                if phase==0:
                    counts['care_opportunities'] += 1
                if phase==2 and act==FEED:
                    care_feed_bouts.add(int(f[11]))
                if phase==COMPLETED and act==FEED:
                    gain = transfer_sources[int(f[7]),actor,int(f[8])]
                    assert int(f[11]) in care_feed_bouts and gain==[int(v) for v in f[18:22]]
                    counts['feed_observations'] += 1
                    counts['timed_feed_observations' if f[13]=='1' else 'instant_feed_observations'] += 1
                if phase==COMPLETED and act==PICKUP:
                    counts['pickups'] += 1
                if phase==COMPLETED and act==PLACE:
                    placed.add(int(f[8]))
                    counts['placements'] += 1
                    work.setdefault('brood_placement',(fact,now,int(f[8])))
                if phase==INTERRUPTED:
                    counts['care_interruptions'] += 1
                    counts['care_outcome_'+str(outcome)] += 1
        if kind in (2,BIRTH,7,8):
            life[actor] = int(f[6])
    assert fact==int(run['events'])
    assert counts['feed_observations']<=counts['transfers']
    for worker, work in worker_events.items():
        if worker!=queen and {'brood_placement','brood_feed','other_work'}<=work.keys():
            counts['workers_with_placement_feed_other'] += 1
            if 'food_return' in work:
                counts['workers_with_placement_feed_and_food_return'] += 1
            for label, (fact, now, detail) in sorted(work.items(),key=lambda kv:kv[1][0]):
                sequences.append(dict(run=name, actor=worker, event=fact, time_ms=now, evidence=label, detail=detail))
    for label,fact,now,actor in timeline:
        sequences.append(dict(run=name, actor=queen, event=fact, time_ms=now, evidence=label, detail=actor))
    for child in sorted(born&emerged):
        for fact,now,stage in development[child]:
            sequences.append(dict(run=name, actor=child, event=fact, time_ms=now, evidence='offspring_stage', detail=stage))
    adult_days = int(end['adult_worker_ms'])/DAY
    counts['actual_worker_switches_per_adult_day'] = counts['actual_worker_task_switches']/adult_days
    return dict(**run, **{k:end[k] for k in ('egg','larva','pupa','adult','dead','geometry_edits')},
                adult_worker_days=adult_days, born_eggs=len(born), emerged=len(emerged), born_then_emerged=len(born&emerged),
                distinct_brood_placed=len(placed), displaced_placed=int(displaced in placed),
                carried_min_depth_m=min(depths,default=None), carried_max_depth_m=max(depths,default=None),
                queen_alive=int(individuals[queen]['stage']!='4'), **counts, **amounts)


def analyze(dest):
    runs = read(dest/'runs.csv')
    days = {(r['run'],int(r['day'])):r for r in read(dest/'days.csv')}
    assert len(runs)==72 and len(days)==72*22
    final = {}
    for r in read(dest/'individuals.csv'):
        if r['day']=='21':
            final.setdefault(r['run'],{})[int(r['id'])] = r
    for r in days.values():
        for nutrient in ('carbs','protein','water','other'):
            assert r[f'introduced_{nutrient}_ug']==r[f'accounted_{nutrient}_ug']
        assert int(r['energy_input_nj'])==int(r['body_energy_nj'])+int(r['dissipated_energy_nj'])
        assert int(r['soil_initial_q3'])==sum(int(r[k]) for k in ('soil_remaining_q3','soil_carried_q3','soil_deposited_q3'))
    cases,sequences = [],[]
    for r in runs:
        assert r['direct_equal']==r['restored_equal']==r['all_ledgers_equal']=='1'
        assert r['events']==r['sql_fact_count']
        cases.append(case(dest,r,days[r['run'],21],final[r['run']],sequences))
    write(dest.parent/'ecology_cases.csv',cases)
    write(dest.parent/'ecology_sequences.csv',sequences)
    print('Verified 72 ecological histories and five representation/interruption controls.')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raw',type=Path,default=BASE/'ecology')
    p.add_argument('--matrix',type=Path)
    p.add_argument('--probes',type=Path)
    p.add_argument('--verify-only',action='store_true')
    a = p.parse_args()
    if a.matrix:
        assert a.probes
        archive(a.matrix,a.probes,a.raw)
    verify(a.raw)
    if not a.verify_only:
        analyze(a.raw)


if __name__=='__main__':
    main()
