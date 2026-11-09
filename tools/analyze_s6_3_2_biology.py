"""Verify unchanged-model probes and reanalyze every predeclared queen contrast."""
import argparse
import statistics as st
from pathlib import Path
from analyze_s6_3_1 import read,emit,wilson

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'experiments/s6_3_2'

def probe_analysis(folder):
    care=read(folder/'eligibility.csv');checks=read(folder/'checks.csv');series=read(folder/'time_series.csv');events=read(folder/'events.csv')
    seeds=sorted({int(r['seed']) for r in checks});assert seeds==list(range(1,len(seeds)+1))
    assert len(care)==3*len(seeds) and len(checks)==5*len(seeds)
    for r in care:
        assert r['queen_nurse_rejected']==r['queen_autonomy_rejected']==r['exact_rollback']=='1'
        assert r['worker_nurse_accepted']==('1' if int(r['workers']) else 'NOT_APPLICABLE')
    for r in checks:assert r['exact_restore']==r['exact_single_advance']==r['conserved']=='1'
    for r in series:
        assert int(r['total_energy_input_nj'])==int(r['total_body_energy_nj'])+int(r['total_dissipated_nj'])
        assert 1500000000+int(r['oxidized_carbs_ug'])*1000000==int(r['body_energy_nj'])+int(r['actor_dissipated_nj'])+int(r['exported_nj'])
    for r in events:assert len(bytes.fromhex(r['canonical_event_hex']))==159
    result=[]
    for check in checks:
        name=check['probe'];seed=check['seed'];rows=[r for r in series if r['probe']==name and r['seed']==seed]
        assert len({r['actor'] for r in rows})==1
        selected=[r for r in events if r['probe']==name and r['seed']==seed]
        assert [int(r['event_id']) for r in selected]==list(range(1,len(selected)+1))
        assert len(selected)==int(rows[-1]['events'])
        death=next((r for r in selected if r['kind']=='8' and r['actor']==rows[0]['actor']),None)
        if name.startswith('rest_'):assert rows[-1]['body_energy_nj']=='1413600000' and rows[-1]['hydration_ug']=='1576'
        if name=='supplied_tissue_clock':
            assert [(int(r['time_ms'])//86400000,int(r['stage'])) for r in rows]==[(0,0),(1,0),(2,1),(3,1),(4,1),(5,2),(6,2),(7,3),(8,3)]
        result.append(dict(probe=name,seed=seed,observed_days=int(rows[-1]['time_ms'])/86400000,lifetime_days=int(death['time_ms'])/86400000 if death else '',censored=0 if death else 1,final_stage=rows[-1]['stage'],births=rows[-1]['births'],final_body_energy_nj=rows[-1]['body_energy_nj'],final_hydration_ug=rows[-1]['hydration_ug'],final_population=rows[-1]['living'],events=len(selected),exact_restore=1,exact_single_advance=1,conserved=1,status='ENGINEERING_DIAGNOSTIC_NOT_EMPIRICAL_FIT'))
    return result

def queen_contrasts():
    rows=[]
    for group in ('historical','positive'):
        source=ROOT/f'experiments/s6_3_1/ecology/corrected/{group}/diagnosis.csv'
        for r in read(source):
            if group=='historical' and not(r['workers']=='32' and r['supply']=='balanced' and r['cyclic']=='0'):continue
            assert r['status']=='complete' and r['reserve_mode']=='1'
            balanced=1500000000+int(r['final_absorbed_carbs_ug'])*1000000-int(r['final_basal_cost_nj'])-int(r['final_egg_energy_nj'])-int(r['final_reproductive_dissipation_nj'])==int(r['final_body_energy_nj'])
            assert balanced
            rows.append(dict(source=source.relative_to(ROOT).as_posix(),condition='ordinary32' if group=='historical' else 'adequate_access'+r['workers'],**r,queen_energy_reconciled=1))
    assert len(rows)==18
    for condition in ('ordinary32','adequate_access8','adequate_access32'):
        assert {int(r['seed']) for r in rows if r['condition']==condition}==set(range(1,7))
    return rows

def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');p.add_argument('--probes',type=Path,default=BASE/'probes');p.add_argument('--verify-only',action='store_true');args=p.parse_args()
    results=probe_analysis(args.probes)
    if args.verify_only:
        print(f'PASS: {len(results)} probe runs; exact restore/advance, canonical facts, nutrient and energy budgets');return
    emit(BASE/'analysis/probes.csv',results,args.check)
    contrasts=queen_contrasts();emit(BASE/'analysis/queen_contrasts.csv',contrasts,args.check)
    summaries=[]
    for condition in ('ordinary32','adequate_access8','adequate_access32'):
        chosen=[r for r in contrasts if r['condition']==condition]
        alive=sum(int(r['queen_alive']) for r in chosen);lo,hi=wilson(alive,len(chosen))
        summary=dict(condition=condition,seeds=len(chosen),survivors=alive,simulation_seed_survival_wilson_low=lo,simulation_seed_survival_wilson_high=hi,observed_lifetime_or_censor_p50=st.median(float(r['queen_lifetime_days']) for r in chosen),deaths_with_external_or_depot_carbs=sum(r['queen_alive']=='0' and int(r['death_available_carbs_ug'])+int(r['death_nest_carbs_ug'])>0 for r in chosen))
        for key in ('last48_physical_contacts','last48_queen_sampled','last48_matching_donors','last48_selected_queen','last48_gifts','final_received_carbs_ug','final_received_protein_ug','final_egg_energy_nj','final_reproductive_dissipation_nj','final_basal_cost_nj'):
            summary[key+'_p50']=st.median(float(r[key]) for r in chosen)
        summaries.append(summary)
        print(condition,'alive',sum(int(r['queen_alive']) for r in chosen),'/6; lifetimes',[r['queen_lifetime_days'] for r in chosen])
    emit(BASE/'analysis/queen_contrast_summary.csv',summaries,args.check)
    print(f'PASS: {len(results)} new unchanged-model probes and all 18 frozen historical contrasts reconcile')
if __name__=='__main__':main()
