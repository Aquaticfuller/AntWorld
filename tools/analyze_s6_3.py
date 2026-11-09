"""Audit complete long-term series and summarize frozen outcomes without selecting seeds."""
import argparse
import csv
import gzip
import hashlib
import json
import random
import statistics as st
import struct
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GROUPS = {'primary-v1': 48, 'primary-v2': 48, 'controls-v2': 18,
          'sensitivity-v2': 6, 'factorial-v2': 24, 'spatial-v2': 6}


def read(path):
    if path.exists():
        stream = path.open(encoding='utf-8', newline='')
    else:
        stream = gzip.open(str(path)+'.gz', 'rt', encoding='utf-8', newline='')
    with stream:
        return list(csv.DictReader(stream))


def emit(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as out:
        writer = csv.DictWriter(out, list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def quantile(values, fraction):
    values = sorted(values)
    at = (len(values)-1)*fraction
    left = int(at)
    return values[left]+(values[min(left+1, len(values)-1)]-values[left])*(at-left)


def interval(values):
    rng = random.Random(6303)
    boot = [st.mean(rng.choices(values, k=len(values))) for _ in range(4096)]
    return dict(n=len(values), mean=st.mean(values), low=quantile(boot, .025), high=quantile(boot, .975),
                minimum=min(values), maximum=max(values))


def verify_archive(base, deep=False):
    for name, item in json.loads((base/'archive.json').read_text()).items():
        if 'archive' not in item:
            continue
        path = base/item['archive']
        h = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1048576), b''):
                h.update(block)
        assert h.hexdigest() == item['archive_sha256'], path
        if deep:
            h, size = hashlib.sha256(), 0
            with (gzip.open(path, 'rb') if path.suffix == '.gz' else path.open('rb')) as stream:
                for block in iter(lambda: stream.read(1048576), b''):
                    size += len(block)
                    h.update(block)
            assert size == item['bytes'] and h.hexdigest() == item['sha256'], name


def verify_facts(folder, summary):
    """Independent codec projection: ID continuity, stages and every readable event."""
    path = folder/'events.bin'
    stream = path.open('rb') if path.exists() else gzip.open(str(path)+'.gz','rb')
    life_path = folder/'life_events.csv'
    life = life_path.open(encoding='utf-8',newline='') if life_path.exists() else gzip.open(str(life_path)+'.gz','rt',encoding='utf-8',newline='')
    selected = {7,8,17,20,21,34,35,37,38}
    stages, count, previous_time = {}, 0, 0
    births = emerged = deaths = protein = recycled = 0
    with stream, life:
        projection = iter(csv.DictReader(life))
        while chunk := stream.read(159*4096):
            assert len(chunk)%159 == 0
            for offset in range(0,len(chunk),159):
                count += 1
                event = struct.unpack_from('<Q',chunk,offset)[0]
                time,source = struct.unpack_from('<qQ',chunk,offset+24)
                payload, value = struct.unpack_from('<QQ',chunk,offset+49)
                kind = chunk[offset+65]
                actor = struct.unpack_from('<Q',chunk,offset+66)[0]
                amounts = struct.unpack_from('<QQQQ',chunk,offset+114)
                stage = chunk[offset+146]
                assert event == count and time >= previous_time
                previous_time = time
                if kind in (2,35):
                    assert actor not in stages
                    if kind == 35:
                        assert stages[payload] == 3 and stage == 0 and time > 0
                        births += 1
                    stages[actor] = stage
                if kind in (7,8):
                    assert actor in stages and stages[actor] != 4
                    assert stage == 4 or stage == stages[actor]+1
                    stages[actor] = stage
                    emerged += int(stage == 3)
                    deaths += int(stage == 4)
                if kind == 21:
                    protein += amounts[1]
                if kind == 38:
                    recycled += amounts[1]
                if kind in selected:
                    observed = next(projection)
                    expected = [event,time,kind,actor,payload,value,*amounts,stage,source]
                    assert [int(v) for v in observed.values()] == expected, (folder,event)
        assert next(projection,None) is None
    assert count == int(summary['events'])
    assert (births,emerged,deaths,protein,recycled) == tuple(int(summary[k]) for k in (
        'births','emerged','deaths','protein_transferred_ug','recycled_protein_ug'))
    assert sum(v != 4 for v in stages.values()) == int(summary['alive'])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=ROOT/'experiments/s6_3/ecology')
    p.add_argument('--out', type=Path, default=ROOT/'experiments/s6_3/analysis')
    p.add_argument('--check', action='store_true')
    p.add_argument('--deep', action='store_true')
    args = p.parse_args()
    results, grouped, lookup = [], defaultdict(list), {}
    for group, expected in GROUPS.items():
        base = args.root/group
        if (base/'archive.json').exists():
            verify_archive(base, args.deep)
        summary = read(base/'summary.csv')
        assert len(summary) == expected
        for r in summary:
            folder = base/r['run']
            if args.deep:
                verify_facts(folder,r)
            series = [{k:int(v) for k,v in row.items()} for row in read(folder/'daily.csv')]
            final = series[-1]
            assert len(series) == int(r['completed_days'])+1
            for day, row in enumerate(series):
                assert row['day'] == day and row['time_ms'] == day*86400000
                assert row['egg']+row['larva']+row['pupa']+row['adult']+row['dead'] == int(r['workers'])+1+row['births']
                for kind in ('carbs','protein','water','other'):
                    assert row['input_'+kind+'_ug'] == series[0]['input_'+kind+'_ug'] == row['accounted_'+kind+'_ug']
                assert row['energy_input_nj'] == row['body_energy_nj']+row['dissipated_energy_nj']
                assert row['soil_initial_q3'] == row['soil_remaining_q3']+row['soil_carried_q3']+row['soil_deposited_q3']
                assert row['mass_balanced'] == row['energy_balanced'] == 1
            assert final['events'] == int(r['events'])
            assert final['dead'] == int(r['deaths'])
            assert final['egg']+final['larva']+final['pupa']+final['adult'] == int(r['alive'])
            assert all(final[k] == int(r[k]) for k in ('births','emerged','geometry_edits'))
            if r['status'] == 'complete':
                assert r['exact_continuation'] == '1'
                assert r['requested_days'] == r['completed_days']
            auc = sum((a['unmet_larval_protein_ug']+b['unmet_larval_protein_ug'])/2 for a,b in zip(series,series[1:]))
            owned = sum(final[k+'_ms'] for k in ('paused','rest','nurse','forage','excavate'))
            activity = 100*sum(final[k+'_ms'] for k in ('nurse','forage','excavate'))/owned if owned else 0
            addition = dict(group=group, **r, sampled_unmet_protein_ug_days=auc, active_program_pct=activity,
                            terminal_nest_protein_ug=final['nest_protein_ug'], terminal_crop_protein_ug=final['crop_protein_ug'],
                            terminal_available_protein_ug=final['available_protein_ug'], terminal_reserve_protein_ug=final['reserve_protein_ug'],
                            minimum_alive=min(x['egg']+x['larva']+x['pupa']+x['adult'] for x in series))
            results.append(addition)
            grouped[group,r['workers'],r['supply'],r['cyclic'],r['arm'],r['pulse_hours']].append(addition)
            lookup[group,r['seed'],r['workers'],r['supply'],r['cyclic'],r['arm'],r['pulse_hours']] = addition
    metrics = ('births','emerged','alive','deaths','protein_transferred_ug','recycled_protein_ug',
               'geometry_edits','events','sampled_unmet_protein_ug_days','active_program_pct')
    estimates = []
    for key, rows in sorted(grouped.items()):
        for metric in metrics:
            estimates.append(dict(group=key[0], workers=key[1], supply=key[2], cyclic=key[3], arm=key[4], pulse_hours=key[5],
                                  censored=sum(r['status'] != 'complete' for r in rows), metric=metric,
                                  **interval([float(r[metric]) for r in rows])))
    paired = []
    for group, arm, basegroup, basearm in (
            ('controls-v2','no_recycling','controls-v2','full'),
            ('controls-v2','no_feedback','controls-v2','full'),
            ('spatial-v2','compact','primary-v2','full')):
        rows = [r for r in results if r['group'] == group and r['arm'] == arm]
        for metric in metrics:
            differences = [float(r[metric])-float(lookup[basegroup,r['seed'],r['workers'],r['supply'],r['cyclic'],basearm,r['pulse_hours']][metric]) for r in rows]
            paired.append(dict(contrast=arm+' minus '+basearm, group=group, metric=metric, **interval(differences)))
    report = dict(runs=len(results), daily_snapshots=sum(int(r['completed_days'])+1 for r in results),
                  completed=sum(r['status']=='complete' for r in results), censored=sum(r['status']!='complete' for r in results),
                  primary_v2_complete=sum(r['group']=='primary-v2' and r['status']=='complete' for r in results),
                  exact_completed_continuations=sum(r['exact_continuation']=='1' for r in results),
                  durable_checks=sum(r['durable_checked']=='1' for r in results),
                  uncertainty='4096 seed-bootstrap resamples, seed 6303; six or three independent seeds; descriptive, unadjusted multiple endpoints. Censored rows are last observed outcomes, not 90-day outcomes.')
    outputs = {'runs.csv': results, 'estimates.csv': estimates, 'paired.csv': paired}
    if args.check:
        for name, rows in outputs.items():
            old = read(args.out/name)
            assert old == [{k:str(v) for k,v in row.items()} for row in rows], name
        assert json.loads((args.out/'audit.json').read_text()) == report
    else:
        for name, rows in outputs.items():
            emit(args.out/name, rows)
        (args.out/'audit.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
