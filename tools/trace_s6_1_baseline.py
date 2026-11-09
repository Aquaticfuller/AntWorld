"""Decode and reconcile the complete retained S6 seed-7 durable fact stream."""
import argparse
import csv
import hashlib
import json
import sqlite3
import struct
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ('event_id world_high world_low time_ms source action revision payload random_value kind '
          'actor colony resource x_m y_m z_m carbs_ug protein_ug water_ug other_ug '
          'stage outcome mode reason deposited_units forgot_memory').split()
CODEC = struct.Struct('<QQQqQBQQQBQQQdddQQQQBBBBdB')
KINDS = ('Diagnostic ColonySeeded AntSeeded FoodSeeded Moved FoodCollected ActionRejected StageChanged '
         'AntDied SurfaceConfigured ForagingStarted ForagingDecision FoodDelivered Rested TrailMaintenance '
         'PhysiologyEnabled PhysiologyUpdated BehaviorChanged NutritionDecision CargoIngested NestIngested '
         'NutritionTransferred GeometryConfigured SoilExcavated SoilDropped SoilPickedUp SoilFilled '
         'ExcavationDecision FoodPlaced SocialConfigured AutonomyChanged AutonomyDecision').split()


def records(path):
    with sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True) as connection:
        return [bytes(row[0]) for row in connection.execute('SELECT payload FROM events ORDER BY id')]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--primary', type=Path, default=ROOT/'out/s6-primary/7-supplied-original-16.sqlite')
    p.add_argument('--long', type=Path, default=ROOT/'out/s6-long/7-supplied-original-16.sqlite')
    p.add_argument('--output', type=Path, default=ROOT/'experiments/s6_1/diagnosis')
    a = p.parse_args()
    assert CODEC.size == 159
    primary, full = records(a.primary), records(a.long)
    assert full[:len(primary)] == primary, '600 s and 1,800 s histories diverged'
    a.output.mkdir(parents=True, exist_ok=True)
    crop = defaultdict(lambda: [0]*4)
    tissue, behavior, changed = defaultdict(int), defaultdict(int), defaultdict(int)
    donors = defaultdict(Counter)
    brood, adults, dead, counts = set(), set(), set(), Counter()
    with (a.output/'seed7_complete_events.csv').open('w', encoding='utf-8', newline='') as f, \
            (a.output/'seed7_nursing_timeline.csv').open('w', encoding='utf-8', newline='') as t:
        events = csv.DictWriter(f, FIELDS+['kind_name']); events.writeheader()
        trace_fields = ['event_id', 'time_ms', 'actor', 'kind', 'source', 'payload', 'program_before',
                        'program_after', 'program_age_ms', 'crop_carbs_ug', 'crop_protein_ug',
                        'crop_water_ug', 'crop_other_ug', 'protein_transferred_ug', 'candidates']
        trace = csv.DictWriter(t, trace_fields); trace.writeheader()
        for index, raw in enumerate(full, 1):
            e = dict(zip(FIELDS, CODEC.unpack(raw), strict=True))
            assert e['event_id'] == index
            kind, actor, time = e['kind'], e['actor'], e['time_ms']
            counts[KINDS[kind]] += 1
            e['kind_name'] = KINDS[kind]; events.writerow(e)
            mass = [e[x] for x in ('carbs_ug', 'protein_ug', 'water_ug', 'other_ug')]
            old, age = behavior[actor], time-changed[actor]
            if kind == 2 and e['stage'] != 3:
                brood.add(actor)
                if e['stage'] == 2:
                    tissue[actor] = 100
            if kind in (15, 19, 20):
                crop[actor] = [x+y for x, y in zip(crop[actor], mass, strict=True)]
            if kind in (16, 21):
                crop[actor] = [x-y for x, y in zip(crop[actor], mass, strict=True)]
                assert min(crop[actor]) >= 0
                if kind == 16:
                    tissue[actor] += mass[1]
                else:
                    recipient = e['payload']
                    crop[recipient] = [x+y for x, y in zip(crop[recipient], mass, strict=True)]
                    donors[actor]['given_protein_ug'] += mass[1]
                    donors[actor]['gifts'] += 1
            if kind == 20:
                donors[actor]['nest_protein_ug'] += mass[1]
                donors[actor]['intakes'] += 1
            if kind == 17:
                behavior[actor], changed[actor] = e['payload'], time
                if old == 2 and e['payload'] == 3 and crop[actor][1]:
                    donors[actor]['nurse_to_forage_with_protein'] += 1
            if kind == 7 and e['stage'] == 3:
                adults.add(actor)
            if kind == 8:
                dead.add(actor); behavior[actor] = 0
            if kind in (17, 18, 19, 20, 21, 31, 8):
                trace.writerow(dict(zip(trace_fields, [index, time, actor, KINDS[kind], e['source'],
                    e['payload'], old, behavior[actor], age, *crop[actor], mass[1],
                    e['random_value'] if kind in (18, 31) else 0], strict=True)))
    final_crop = sum(v[1] for v in crop.values())
    assert final_crop == 1549 and sum(tissue.values()) == 651
    assert len(adults & brood) == 5 and len(brood-adults) == 7 and len(dead) == 45
    report = dict(scope='ENGINEERING_FIXTURE', baseline_source='2505f53e9ec8b6ba72828a651bd244934fde4431',
        seed=7, condition='supplied', mirror=0, primary_facts=len(primary), long_facts=len(full),
        primary_is_exact_prefix=True, fact_codec_bytes=159,
        primary_fact_sha256=hashlib.sha256(b''.join(primary)).hexdigest(),
        long_fact_sha256=hashlib.sha256(b''.join(full)).hexdigest(),
        cumulative_emergence=len(adults & brood), unemerged_ids=sorted(brood-adults),
        final_crop_protein_ug=final_crop, final_tissue_protein_ug=sum(tissue.values()), dead=45,
        donors={str(k): dict(v, retained_crop_protein_ug=crop[k][1]) for k, v in sorted(donors.items())},
        all_fact_counts=dict(sorted(counts.items())),
        caveat='Inventory and program history reconstructed from every actual fact. A selected action is not a successful transfer. Local perception itself is not fully encoded in S6 facts.')
    (a.output/'baseline_trace.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
