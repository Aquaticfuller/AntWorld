"""Retain event-level long-term reproductive, scarcity and death endpoints."""
import argparse
from pathlib import Path
from analyze_s6_3 import ROOT, read, emit


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=ROOT/'experiments/s6_3/ecology')
    p.add_argument('--out',type=Path,default=ROOT/'experiments/s6_3/analysis/diagnosis.csv')
    args = p.parse_args()
    result = []
    for group in ('primary-v1','primary-v2','controls-v2','sensitivity-v2','factorial-v2','spatial-v2'):
        for r in read(args.root/group/'summary.csv'):
            base = args.root/group/r['run']
            people,events,series = read(base/'individuals.csv'),read(base/'life_events.csv'),read(base/'daily.csv')
            queen = next(x['id'] for x in people if x['day']=='0' and x['caste']=='1')
            final = [x for x in people if x['day']==r['completed_days']]
            q = next(x for x in final if x['id']==queen)
            born = [x for x in events if x['kind']=='35']
            dead = [x for x in events if x['kind']=='8']
            gifts = [x for x in events if x['kind']=='21']
            children = {x['actor'] for x in born}
            row = dict(group=group,run=r['run'],seed=r['seed'],workers=r['workers'],supply=r['supply'],cyclic=r['cyclic'],arm=r['arm'],
                       pulse_hours=r['pulse_hours'],observed_days=r['completed_days'],status=r['status'],
                       queen_alive=int(q['stage']!='4'),queen_death_cause=q['death_cause'],
                       queen_death_ms=next((x['time_ms'] for x in dead if x['actor']==queen),''),
                       first_birth_ms=born[0]['time_ms'] if born else '',last_birth_ms=born[-1]['time_ms'] if born else '',
                       births=len(born),emerged=r['emerged'],deaths=len(dead),
                       first_observed_extinction_day=next((x['day'] for x in series if sum(int(x[k]) for k in ('egg','larva','pupa','adult'))==0),''),
                       queen_gifts=sum(x['payload']==queen for x in gifts),
                       queen_gift_carbs_ug=sum(int(x['carbs_ug']) for x in gifts if x['payload']==queen),
                       queen_gift_protein_ug=sum(int(x['protein_ug']) for x in gifts if x['payload']==queen),
                       child_gifts=sum(x['payload'] in children for x in gifts),
                       child_gift_protein_ug=sum(int(x['protein_ug']) for x in gifts if x['payload'] in children),
                       final_child_tissue_ug=sum(int(x['tissue_protein_ug']) for x in final if x['id'] in children),
                       final_living_child_unmet_protein_ug=sum(max(0,100-int(x['tissue_protein_ug'])-int(x['protein_ug'])) for x in final if x['stage']=='1'),
                       final_dead_crop_protein_ug=sum(int(x['protein_ug']) for x in final if x['stage']=='4'),
                       energy_deaths=sum(x['death_cause']=='1' for x in final),water_deaths=sum(x['death_cause']=='2' for x in final),
                       final_nest_protein_ug=series[-1]['nest_protein_ug'],final_worker_crop_protein_ug=series[-1]['living_worker_crop_protein_ug'])
            row['queen_reproductive_export_and_cost_nj'] = sum(int(x['energy_or_candidates'])+10000000 for x in born)
            row['queen_energy_input_nj'] = 1500000000+(200+row['queen_gift_carbs_ug']-int(q['carbs_ug']))*1000000
            queen_lifetime = int(row['queen_death_ms']) if row['queen_death_ms'] else int(r['completed_days'])*86400000
            row['queen_basal_cost_nj'] = queen_lifetime
            row['queen_body_energy_nj'] = int(q['body_energy_nj'])
            assert row['queen_energy_input_nj'] == row['queen_basal_cost_nj']+row['queen_reproductive_export_and_cost_nj']+row['queen_body_energy_nj']
            result.append(row)
    emit(args.out,result)
    print('Diagnosed',len(result),'complete retained run histories')


if __name__ == '__main__':
    main()
