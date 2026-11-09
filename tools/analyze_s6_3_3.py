"""Reproduce clustered source comparisons without fitting a model coefficient."""
import argparse,csv,hashlib,io,json,math,random,statistics as st
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'experiments/s6_3_3'
def rows(path):
    with path.open(newline='',encoding='utf-8') as f: return list(csv.DictReader(f))
def csv_text(data):
    out=io.StringIO(newline=''); w=csv.DictWriter(out,list(data[0]),lineterminator='\n');w.writeheader();w.writerows(data);return out.getvalue()
def q(values,p):
    x=sorted(values);t=(len(x)-1)*p;i=int(t);return x[i]+(x[min(i+1,len(x)-1)]-x[i])*(t-i)
def interval(x,y=None):
    rng=random.Random(633);boot=[]
    for _ in range(4000):
        v=st.mean(rng.choices(x,k=len(x)))
        if y is not None:v-=st.mean(rng.choices(y,k=len(y)))
        boot.append(v)
    return q(boot,.025),q(boot,.975)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');p.add_argument('--figures',action='store_true');a=p.parse_args()
    runs=[];windows=[]
    for manifest in ('primary','sensitivity'):
        config=json.loads((BASE/'raw'/f'{manifest}_manifest.json').read_text())
        for seed in config['seeds']:
            path=BASE/'raw'/f'{manifest}_{seed}'; receipt=json.loads((path/'receipt.json').read_text()); assert receipt['returncode']==0
            for name,digest in receipt['files'].items():assert hashlib.sha256((path/name).read_bytes()).hexdigest()==digest,name
            runs+=rows(path/'runs.csv');windows+=rows(path/'windows.csv')
    assert len(runs)==384 and len({r['run'] for r in runs})==384
    assert all(r['conserved']==r['continuation_equal']=='1' for r in runs)
    literature=BASE/'literature'; groups=defaultdict(list);sim=defaultdict(list);details=[]
    for name in ['manifest.json','B02_manifest.json']:
        for table in json.loads((literature/name).read_text())['tables']:
            assert hashlib.sha256((literature/table['csv']).read_bytes()).hexdigest()==table['csv_sha256'],table['csv']
    # B01 Methods2.2.4 adds workers at setup in With_workers; only removal has prior3-day exposure.
    mapping={'Without_workers':'absent','With_workers':'added','Workers_removed':'removed'}
    for age,name in [(55,'Reversibility_of_worker_effect_3_days'),(932,'Reversibility_of_worker_effect_2.5_years')]:
        table=rows(literature/(name+'.csv'));complete={r['Box_label'] for r in table}-{r['Box_label'] for r in table if r['Nursing']=='NA'}
        for i,r in enumerate(table,2):
            key=('reversal',age,mapping[r['Treatment']] if age==55 else 'removed',int(r['Time']),'care_fraction')
            value='MISSING' if r['Nursing']=='NA' else float(r['Nursing'])/float(r['Scans'])
            if value!='MISSING':groups[key].append(value)
            if age==932 and r['Box_label'] in complete:groups[('reversal_complete12',*key[1:])].append(value)
            details.append(dict(source='B01',file=name+'.csv',csv_line=i,unit_id=r['Box_label'],assay=key[0],age=age,condition=key[2],window_h=key[3],metric=key[4],value=value,denominator=r['Scans'],locator='Methods2.1.4/2.2.4-5; Fig1c-d'))
    design={r['Box_label']:r for r in rows(literature/'Effect_of_worker_cues_wire_mesh_design_info.csv')}
    mesh=defaultdict(list)
    for r in rows(literature/'Effect_of_worker_cues_wire_mesh_BORIS_output.csv'):mesh[r['Box_label'],int(r['Time_since_setup_h'])].append(int(r['Behavior']))
    mapping={'No_callows':'absent','Callows_separated':'barrier','Callows_with_Q':'present'}
    for (queen,h),values in mesh.items():
        key=('mesh',52,mapping[design[queen]['Treatment']],h,'care_fraction');v=st.mean(values);groups[key].append(v)
        details.append(dict(source='B01',file='Effect_of_worker_cues_wire_mesh_BORIS_output.csv',csv_line='GROUP_BY Box_label AND Time_since_setup_h',unit_id=queen,assay='mesh',age=52,condition=key[2],window_h=h,metric=key[4],value=v,denominator=len(values),locator='Methods2.2.12; Fig2c; partial/unequal scan counts retained'))
    b02=defaultdict(list)
    for i,r in enumerate(rows(literature/'B02_retrieval.csv'),2):
        for metric,field in [('retrieved',' brood items after 10min'),('first_contact_capped_s','first contact ')]:
            b02[r['qw'],r['queen'],metric].append(float(r[field]))
    ids={c:{queen for caste,queen,_ in b02 if caste==c} for c in ['q','w','w2']}
    paired_ids=ids['q']&ids['w'];productivity_ids={r['colony'] for r in rows(literature/'B02_productivity.csv')}
    author_ids=(paired_ids|ids['w2'])&productivity_ids
    assert len(paired_ids)==67 and len(author_ids)==61
    for (caste,queen,metric),values in b02.items():
        condition={'q':'queen','w':'three_workers','w2':'later_workers'}[caste];key=('retrieval',0,condition,0,metric);v=st.mean(values);groups[key].append(v)
        details.append(dict(source='B02',file='B02_retrieval.csv',csv_line='GROUP_BY qw AND queen; mean of both trials',unit_id=queen,assay='retrieval',age=0,condition=condition,window_h=0,metric=metric,value=v,denominator=len(values),locator='pp10411-10412; Methods2.2-2.3; Fig1-2; 600s noncontacts retained'))
        for cohort,eligible in [('retrieval_matched67',paired_ids),('retrieval_author61',author_ids)]:
            if queen in eligible:groups[cohort,0,condition,0,metric].append(v)
    for r in windows:
        if r['variant']!='base':continue
        key=(r['assay'],int(r['context_age_days']),r['condition'],int(r['window_h']),'care_fraction')
        sim[key].append(int(r['positive50'])/50 if r['assay']=='reversal' else int(r['positive51'])/51)
    for r in runs:
        if r['assay']=='retrieval':
            sim['retrieval',0,r['condition'],0,'retrieved'].append(int(r['retrieved']))
            t=float(r['first_contact_ms']);sim['retrieval',0,r['condition'],0,'first_contact_capped_s'].append(600 if t<0 else t/1000)
    comparisons=[]
    for key,observed in sorted(groups.items()):
        simkey=('retrieval',*key[1:]) if key[0].startswith('retrieval_') else ('reversal',*key[1:]) if key[0].startswith('reversal_') else key
        predicted=sim.get(simkey,[]); lo,hi=interval(observed)
        item=dict(assay=key[0],age_days=key[1],condition=key[2],window_h=key[3],metric=key[4],paper_units=len(observed),paper_mean=st.mean(observed),paper_ci_low=lo,paper_ci_high=hi,simulation_units=len(predicted),simulation_mean='',simulation_ci_low='',simulation_ci_high='',signed_error='',error_ci_low='',error_ci_high='',status='NOT_IMPLEMENTED')
        if predicted:
            pl,ph=interval(predicted);dl,dh=interval(predicted,observed)
            item.update(simulation_mean=st.mean(predicted),simulation_ci_low=pl,simulation_ci_high=ph,signed_error=st.mean(predicted)-st.mean(observed),error_ci_low=dl,error_ci_high=dh,status='APPROXIMATE_CONDITIONS; no equivalence claim')
        comparisons.append(item)
    aggregate=[];wg=defaultdict(list)
    for r in windows:wg[r['assay'],r['context_age_days'],r['condition'],r['variant'],r['window_h']].append(r)
    for key,data in sorted(wg.items()):
        x=[int(r['positive51'])/51 for r in data];lo,hi=interval(x)
        aggregate.append(dict(assay=key[0],age_days=key[1],condition=key[2],variant=key[3],window_h=key[4],seeds=len(x),care_fraction51=st.mean(x),ci_low=lo,ci_high=hi,care_fraction50=st.mean(int(r['positive50'])/50 for r in data),active_fraction=st.mean(int(r['active_ms'])/3600000 for r in data),contacts=st.mean(int(r['contacts']) for r in data),protein_ug=st.mean(int(r['protein_ug']) for r in data),dead_windows=sum(r['alive']!='1' for r in data)))
    contrasts=[]
    for age in [35,55,932]:
        for hour in [24,48]:
            for left,right in [('present','absent'),('removed','present'),('removed','absent'),('added','absent'),('sham','present')]:
                def get(c):return {r['seed']:int(r['positive51'])/51 for r in windows if r['variant']=='base' and r['context_age_days']==str(age) and r['condition']==c and r['window_h']==str(hour)}
                x,y=get(left),get(right);d=[x[s]-y[s] for s in sorted(x)];lo,hi=interval(d)
                contrasts.append(dict(age_days=age,window_h=hour,contrast=left+' minus '+right,seeds=len(d),difference=st.mean(d),ci_low=lo,ci_high=hi))
    sensitivity=[]
    for variant in ['base','memory1h','memory24h','inhibition0','inhibition0_4','decision15s','decision240s']:
        for condition in ['absent','present','removed']:
            for hour in [24,48]:
                data=[r for r in windows if r['context_age_days']=='55' and r['variant']==variant and r['condition']==condition and r['window_h']==str(hour) and int(r['seed']) in [7,19,43,71,101,137]]
                assert len(data)==6
                values=[int(r['positive51'])/51 for r in data];lo,hi=interval(values)
                sensitivity.append(dict(variant=variant,condition=condition,window_h=hour,seeds=6,mean=st.mean(values),ci_low=lo,ci_high=hi))
    summary=dict(runs=len(runs),windows=len(windows),conservation_and_restore='384/384',paper_clusters=len(details),quantitative_comparisons=sum(bool(x['simulation_units']) for x in comparisons),all_parameters_fitted=0,
        raw_discrepancies=['B01 reversibility: raw50 versus text51 scans; older queens14 labels with3 NA rows;13 measured units per hour versus text12','B01 mesh:60 raw queens;175 observed queen-hours; varying scan counts 1-52; no deletion','B02 author R script explains70 raw first-worker groups ->67 queen-worker pairs ->61 productivity cohort; all398 trials retained'],
        missing_source_observations=sum(r['value']=='MISSING' for r in details),
        interpretation='Bootstrap seed/queen cluster intervals; no biological equivalence margin; approximate geometry and passive-worker cue controls; no calibration')
    outputs={'source_endpoints.csv':csv_text(details),'comparisons.csv':csv_text(comparisons),'window_summary.csv':csv_text(aggregate),'paired_contrasts.csv':csv_text(contrasts),'matched_sensitivity.csv':csv_text(sensitivity),'summary.json':json.dumps(summary,indent=2)+'\n'}
    target=BASE/'analysis';target.mkdir(exist_ok=True)
    for name,text in outputs.items():
        path=target/name
        if a.check:assert path.read_text(encoding='utf-8')==text,name+' drift'
        else:path.write_text(text,encoding='utf-8',newline='\n')
    if a.figures:
        import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
        fig,ax=plt.subplots(1,2,figsize=(11,4),layout='constrained')
        for c in ['absent','present','removed','added']:
            g=sorted([r for r in aggregate if r['assay']=='reversal' and r['age_days']=='55' and r['variant']=='base' and r['condition']==c],key=lambda r:int(r['window_h']))
            y=[r['care_fraction51'] for r in g];ax[0].errorbar([int(r['window_h']) for r in g],y,yerr=[[v-r['ci_low'] for r,v in zip(g,y)],[r['ci_high']-v for r,v in zip(g,y)]],label=c,marker='o',capsize=3)
        ax[0].set(xlabel='Hours after intervention (0: preceding hour)',ylabel='Active-care scan fraction (51 scans)',ylim=(0,1),title='Founding55 fixture; 12 seeds, 95% bootstrap CI');ax[0].legend()
        g=[r for r in comparisons if r['assay']=='retrieval' and r['metric']=='retrieved' and r['condition']!='later_workers']
        for i,r in enumerate(g):
            for shift,pre,col in [(-.15,'paper','gray'),(.15,'simulation','teal')]:
                m=r[pre+'_mean'];lo=r[pre+'_ci_low'];hi=r[pre+'_ci_high'];ax[1].bar(i+shift,m,.28,color=col,label=('Dryad (all units)' if pre=='paper' else 'Simulation') if i==0 else None);ax[1].errorbar(i+shift,m,yerr=[[m-lo],[hi-m]],color='black',capsize=3)
        ax[1].set(xticks=range(len(g)),xticklabels=[r['condition'].replace('_',' ').capitalize() for r in g],ylabel='Brood retrieved within 600 s',ylim=(0,6),title='B02 holdout: approximate assay, no fitting');ax[1].legend();fig.savefig(target/'care_and_retrieval.png',dpi=180);plt.close(fig)
        fig,axes=plt.subplots(1,3,figsize=(12,3.7),layout='constrained')
        for ax,variants,ticks,label in zip(axes,[['memory1h','base','memory24h'],['inhibition0','inhibition0_4','base'],['decision15s','base','decision240s']],[[1,6,24],[0,.4,.8],[15,60,240]],['Memory horizon (h)','Maximum inhibition','Decision interval (s)']):
            for condition in ['absent','present','removed']:
                g=[next(r for r in sensitivity if r['variant']==v and r['condition']==condition and r['window_h']==24) for v in variants]
                means=[r['mean'] for r in g];ax.errorbar(ticks,means,yerr=[[m-r['ci_low'] for r,m in zip(g,means)],[r['ci_high']-m for r,m in zip(g,means)]],label=condition,marker='o',capsize=3)
            ax.set(xlabel=label,ylabel='Care scan fraction at 24 h',ylim=(0,1));ax.legend(fontsize=8)
        fig.suptitle('ENGINEERING_FIXTURE sensitivity; same six seeds; 95% bootstrap intervals');fig.savefig(target/'sensitivity.png',dpi=180);plt.close(fig)
    print(json.dumps(summary))
if __name__=='__main__':main()
