"""Independently reconcile queen budgets with canonical facts and actual decisions.

Observer records are joined to committed source IDs, never treated as fact events.
The byte codec is the documented 159-byte Core event codec. All numeric physiology
is ENGINEERING_FIXTURE. This script neither changes Core nor selects outcomes.
"""
import argparse
import bisect
import copy
import csv
import json
import struct
from pathlib import Path

DAY = 86400000
HOUR = 3600000
U64 = struct.Struct('<Q')
MASS = struct.Struct('<4Q')


def read(path):
    with path.open(newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def emit(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def vecadd(a, b, sign=1):
    return [x + sign*y for x, y in zip(a, b)]


def settle(q, at, rate):
    if not q['alive']:
        return
    dt = at-q['time_ms']
    assert dt >= 0
    cost = min(q['body_energy_nj'], dt*rate)
    q['body_energy_nj'] -= cost
    q['basal_cost_nj'] += cost
    water, q['water_remainder'] = divmod(dt+q['water_remainder'], HOUR)
    water = min(water, q['hydration_ug'])
    q['hydration_ug'] -= water
    q['lost_water_ug'] += water
    q['time_ms'] = at


def check(q):
    assert q['body_energy_nj'] == 1500000000+q['absorbed_carbs_ug']*1000000-q['basal_cost_nj']-q['egg_energy_nj']-q['reproductive_dissipation_nj']
    assert q['crop_carbs_ug'] == 200+q['received_carbs_ug']-q['absorbed_carbs_ug']
    assert q['crop_protein_ug'] == 100+q['received_protein_ug']-q['egg_protein_ug']
    assert q['crop_water_ug'] == 200+q['received_water_ug']-q['absorbed_water_ug']
    assert q['hydration_ug'] == 1600+q['absorbed_water_ug']-q['lost_water_ug']-q['egg_water_ug']
    assert min(q.values()) >= 0


def diagnose(folder, summary):
    config = read(folder/'configuration.csv')[0]
    config.setdefault('reserve_mode','0')
    config.setdefault('maintenance_horizon_ms','0')
    rate = int(config['lineage_basal'])
    obs = [{k:int(v) for k,v in r.items()} for r in read(folder/'decisions.csv')]
    pending = {}
    for o in obs:
        key = (o['source'], o['context'])
        assert key not in pending
        pending[key] = o
    q = dict(time_ms=0,alive=1,body_energy_nj=1500000000,hydration_ug=1600,
             crop_carbs_ug=200,crop_protein_ug=100,crop_water_ug=200,
             received_carbs_ug=0,received_protein_ug=0,received_water_ug=0,
             absorbed_carbs_ug=0,absorbed_water_ug=0,basal_cost_nj=0,lost_water_ug=0,
             egg_energy_nj=0,egg_protein_ug=0,egg_water_ug=0,reproductive_dissipation_nj=0,water_remainder=0)
    qrows = []
    timeline = [(0,copy.copy(q))]
    deaths = 0
    gifts = []
    births = []
    seen = 0
    stock, available, cargo = [0]*4,[0]*4,[0]*4
    crops, stages = {}, {}
    death_resources = {}
    death_time = None
    with (folder/'events.bin').open('rb') as f:
        while block := f.read(159*4096):
            assert len(block)%159 == 0
            for off in range(0,len(block),159):
                b = memoryview(block)[off:off+159]
                event, time, source = U64.unpack_from(b,0)[0],U64.unpack_from(b,24)[0],U64.unpack_from(b,32)[0]
                payload, random, kind, actor = U64.unpack_from(b,49)[0],U64.unpack_from(b,57)[0],b[65],U64.unpack_from(b,66)[0]
                mass = MASS.unpack_from(b,114)
                stage = b[146]
                context = {18:0,31:1,20:2,6:2}.get(kind)
                if (source,context) in pending:
                    o = pending.pop((source,context))
                    settle(q,time,rate)
                    for actual, expected in [('queen_energy_nj','body_energy_nj'),('queen_water_ug','hydration_ug'),('queen_crop_carbs_ug','crop_carbs_ug'),('queen_crop_protein_ug','crop_protein_ug'),('queen_crop_water_ug','crop_water_ug'),('queen_alive','alive')]:
                        assert o[actual] == q[expected], (folder.name,event,actual,o[actual],q[expected])
                    assert o['time_ms']==time
                    seen += 1
                relevant = actor==2 or (kind in (21,35) and payload==2)
                if relevant:
                    settle(q,time,rate)
                    before = copy.copy(q)
                    if kind==16:
                        q['crop_carbs_ug']-=mass[0]; q['absorbed_carbs_ug']+=mass[0]
                        q['body_energy_nj']+=mass[0]*1000000
                        q['crop_water_ug']-=mass[2]; q['absorbed_water_ug']+=mass[2]; q['hydration_ug']+=mass[2]
                    if kind==21:
                        for i,nutrient in enumerate(('carbs','protein','water')):
                            q[f'crop_{nutrient}_ug']+=mass[i]; q[f'received_{nutrient}_ug']+=mass[i]
                        gifts.append((time,mass))
                    if kind==35:
                        q['crop_protein_ug']-=mass[1]; q['egg_protein_ug']+=mass[1]
                        q['hydration_ug']-=mass[2]; q['egg_water_ug']+=mass[2]
                        q['body_energy_nj']-=random+10000000; q['egg_energy_nj']+=random; q['reproductive_dissipation_nj']+=10000000
                        births.append(time)
                    if kind==8:
                        q['alive']=0; death_time=time; deaths+=1
                    check(q)
                    row = dict(event=event,time_ms=time,kind=kind,source=source,actor=actor,payload=payload,energy_payload_nj=random)
                    row.update({f'fact_{n}_ug':mass[i] for i,n in enumerate(('carbs','protein','water','other'))})
                    row.update({f'pre_{k}':v for k,v in before.items() if k!='time_ms'})
                    row.update({f'post_{k}':v for k,v in q.items() if k!='time_ms'})
                    row['post_maintenance_hours']=q['body_energy_nj']/(rate*HOUR)
                    absorption_period=int(config['absorption_hours'])*HOUR
                    until_absorption=absorption_period-time%absorption_period
                    row['until_next_absorption_ms']=until_absorption
                    row['post_energy_covers_next_absorption']=int(q['body_energy_nj']>rate*until_absorption)
                    row['post_water_covers_next_absorption']=int(q['hydration_ug']>(until_absorption+q['water_remainder'])//HOUR)
                    qrows.append(row)
                    timeline.append((time,copy.copy(q)))
                if kind in (2,35):
                    stages[actor]=stage; crops[actor]=[0]*4
                if kind in (7,8): stages[actor]=stage
                if kind==15: crops[actor]=list(mass)
                if kind in (19,20): crops[actor]=vecadd(crops[actor],mass)
                if kind==16: crops[actor]=vecadd(crops[actor],mass,-1)
                if kind==21:
                    crops[actor]=vecadd(crops[actor],mass,-1); crops[payload]=vecadd(crops[payload],mass)
                if kind==35: crops[payload][1]-=mass[1]
                if kind==38: crops[actor]=vecadd(crops[actor],mass,-1)
                if kind in (3,28,37): available=vecadd(available,mass)
                if kind==5: available=vecadd(available,mass,-1);cargo=vecadd(cargo,mass)
                if kind in (12,19): cargo=vecadd(cargo,mass,-1)
                if kind in (12,38): stock=vecadd(stock,mass)
                if kind==20: stock=vecadd(stock,mass,-1)
                if kind==8 and actor==2:
                    for name,m in [('nest',stock),('available',available),('cargo',cargo),('living_worker_crop',[sum(c[i] for a,c in crops.items() if a!=2 and stages[a]==3) for i in range(4)])]:
                        death_resources.update({f'death_{name}_{n}_ug':m[i] for i,n in enumerate(('carbs','protein','water','other'))})
    assert not pending, (folder.name,len(pending))
    assert seen==len(obs) and deaths<=1
    times=[t for t,_ in timeline]
    daily=[]
    for r in read(folder/'individuals.csv'):
        if r['id']!='2': continue
        t=int(r['day'])*DAY
        state=copy.copy(timeline[bisect.bisect_right(times,t)-1][1]);settle(state,t,rate);check(state)
        for col,key in [('body_energy_nj','body_energy_nj'),('hydration_ug','hydration_ug'),('carbs_ug','crop_carbs_ug'),('protein_ug','crop_protein_ug'),('water_ug','crop_water_ug')]:
            assert int(r[col])==state[key], (folder.name,t,col)
        assert (r['stage']!='4')==bool(state['alive'])
        daily.append(dict(day=r['day'],observed_time_ms=t,**state))
    last=daily[-1]
    end=int(summary['completed_days'])*DAY
    lifetime=death_time if death_time is not None else end
    recent=[o for o in obs if o['queen_alive'] and max(0,lifetime-2*DAY)<=o['time_ms']<=lifetime]
    nutrition=[o for o in recent if o['context']==0]
    matching=[o for o in nutrition if o['sampled_queen'] and not o['donor_urgent'] and any(o['signal_'+n+'_ug'] and o['donor_crop_'+n+'_ug'] for n in ('carbs','protein','water'))]
    row=dict(**config,run=summary['run'],status=summary['status'],observed_days=summary['completed_days'],queen_alive=last['alive'],queen_lifetime_days=lifetime/DAY,queen_death_ms='' if death_time is None else death_time,
             births=summary['births'],emerged=summary['emerged'],final_population=summary['alive'],last_birth_day=births[-1]/DAY if births else '',late_births_120_180=sum(120*DAY<=t<=180*DAY for t in births),queen_gifts=len(gifts),verified_observations=seen,
             last48_decisions=len(recent),last48_physical_contacts=sum(o['reachable_queen'] for o in recent),last48_nutrition_decisions=len(nutrition),last48_queen_sampled=sum(o['sampled_queen'] for o in nutrition),last48_matching_donors=len(matching),last48_selected_queen=sum(o['recipient']==2 for o in nutrition),last48_gifts=sum(lifetime-2*DAY<=t<=lifetime for t,_ in gifts),
             minimum_post_lay_maintenance_hours=min((r['post_maintenance_hours'] for r in qrows if r['kind']==35),default=''))
    row['unsafe_post_lay_energy']=sum(r['kind']==35 and not r['post_energy_covers_next_absorption'] for r in qrows)
    row['unsafe_post_lay_water']=sum(r['kind']==35 and not r['post_water_covers_next_absorption'] for r in qrows)
    row['deferred_attempts']=sum(r['kind']==34 and not r['payload'] for r in qrows)
    row.update({f'final_{k}':v for k,v in last.items() if k not in ('day','time_ms','observed_time_ms')})
    for name in ('nest','available','cargo','living_worker_crop'):
        for n in ('carbs','protein','water','other'):
            key=f'death_{name}_{n}_ug';row[key]=death_resources.get(key,'')
    emit(folder/'queen_events.csv',qrows)
    emit(folder/'queen_daily.csv',daily)
    return row


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path)
    args=p.parse_args()
    rows=[]
    for r in read(args.source/'summary.csv'):
        row=diagnose(args.source/r['run'],r);rows.append(row)
        print(r['run'],'queen_days',round(row['queen_lifetime_days'],3),'gifts',row['queen_gifts'],flush=True)
    emit(args.source/'diagnosis.csv',rows)
    (args.source/'audit.json').write_text(json.dumps(dict(runs=len(rows),verified_observations=sum(r['verified_observations'] for r in rows),all_queen_accounts_exact=True),indent=2)+'\n')


if __name__=='__main__':main()
