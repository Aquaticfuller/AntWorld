"""Standalone audit figures; empirical measurements are never labelled simulations."""
from pathlib import Path
import statistics as st
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analyze_s6_3_1 import read

ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'experiments/s6_3_2';OUT=BASE/'figures'
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':120,'savefig.dpi':180,'svg.hashsalt':'AntWorld-S632'})
def save(fig,name,note):
    fig.text(.5,.015,note,ha='center',fontsize=8,color='#555555')
    fig.tight_layout(rect=(0,.045,1,.97));OUT.mkdir(exist_ok=True)
    for ext in ('png','svg'):fig.savefig(OUT/f'{name}.{ext}',metadata={'Date':None} if ext=='svg' else None)
    plt.close(fig)
    svg=OUT/f'{name}.svg';svg.write_text('\n'.join(x.rstrip() for x in svg.read_text().splitlines())+'\n',encoding='utf-8')
def main():
    measurements=read(BASE/'literature_measurements.csv')
    fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    for population,color in [('Borisovka','#226b89'),('St_Petersburg','#bd652a')]:
        rows=[r for r in measurements if r['population']==population and r['endpoint']=='total' and r['mean']]
        axes[0].errorbar([float(r['temperature_c']) for r in rows],[float(r['mean']) for r in rows],yerr=[float(r['dispersion']) for r in rows],marker='o',capsize=3,color=color,label=population.replace('_',' '))
    axes[0].set(title='Published first-worker development (B06 Table 2)',xlabel='Measured temperature (C)',ylabel='Egg to worker (days)',ylim=(0,80));axes[0].legend();axes[0].grid(alpha=.15)
    clock=[r for r in read(BASE/'probes/time_series.csv') if r['probe']=='supplied_tissue_clock' and r['seed']=='1']
    transitions=[0.,*[min(int(r['time_ms']) for r in clock if r['stage']==str(stage))/86400000 for stage in (1,2,3)]]
    model=[b-a for a,b in zip(transitions,transitions[1:])]
    empirical=[[float(min((r for r in measurements if r['population']==population and r['endpoint']==stage and r['mean']),key=lambda r:abs(float(r['temperature_c'])-25))['mean']) for stage in ('egg','larva','prepupa_pupa')] for population in ('Borisovka','St_Petersburg')]
    names=['Model supplied tissue','Borisovka near 25 C','St Petersburg near 25 C'];values=[model,*empirical]
    left=[0.,0.,0.]
    for index,(stage,color) in enumerate([('Egg','#d6a456'),('Larva','#629785'),('Pupa / empirical prepupa+pupa','#697eae')]):
        x=[v[index] for v in values];axes[1].barh(names,x,left=left,label=stage,color=color);left=[a+b for a,b in zip(left,x)]
    axes[1].set(title='Stage-clock magnitude only; conditions differ',xlabel='Sum of stage means (days)');axes[1].legend(fontsize=8,loc='lower right')
    save(fig,'development_mismatch','Empirical errors are reported errors, not inferred CIs. Model has no temperature. Stage sums need not equal observed first-worker totals.')

    contrasts=read(BASE/'analysis/queen_contrasts.csv');fig,axes=plt.subplots(1,3,figsize=(12,4.2),sharey=True)
    for ax,condition,title,horizon in zip(axes,['ordinary32','adequate_access8','adequate_access32'],['32 workers: ordinary access','8 workers: depot food','32 workers: depot food'],[90,180,180]):
        rows=[r for r in contrasts if r['condition']==condition];times=[float(r['queen_lifetime_days']) for r in rows if r['queen_alive']=='0'];grid=sorted(set([0.,*times,float(horizon)]));ys=[sum(float(r['queen_lifetime_days'])>t or r['queen_alive']=='1' for r in rows)/6 for t in grid]
        ax.step(grid,ys,where='post',color='#226b89');ax.scatter(times,[0]*len(times),marker='|',color='#b34b3c');ax.set(title=title,xlabel='Game days',ylim=(-.05,1.05));ax.grid(alpha=.15)
        if condition=='adequate_access32':ax.scatter([horizon],[1],marker='+',color='#226b89',label='6 right-censored');ax.legend(fontsize=8)
    axes[0].set_ylabel('Queen survival fraction');save(fig,'retained_queen_survival','All six frozen S6.3.1 corrected seeds per condition; unchanged data. ENGINEERING_FIXTURE, not measured Lasius niger survival.')

    fig,axes=plt.subplots(1,2,figsize=(11,4.7));colors={'ordinary32':'#b34b3c','adequate_access8':'#bd8735','adequate_access32':'#226b89'}
    for condition,color in colors.items():
        rows=[r for r in contrasts if r['condition']==condition]
        axes[0].scatter([float(r['final_absorbed_carbs_ug'])/1000 for r in rows],[float(r['queen_lifetime_days']) for r in rows],color=color,label=condition)
        dead=[r for r in rows if r['queen_alive']=='0']
        axes[1].scatter([int(r['last48_physical_contacts']) for r in dead],[int(r['last48_gifts']) for r in dead],color=color,label=condition)
    axes[0].set(xlabel='Queen absorbed carbohydrate (mg)',ylabel='Lifetime / observation limit (days)',title='Actual uptake; living endpoints are censored');axes[0].legend(fontsize=8)
    axes[1].set(xlabel='Physical opportunities in final 48 h',ylabel='Committed queen gifts in final 48 h',title='Opportunity is not successful provisioning')
    for ax in axes:ax.grid(alpha=.15)
    save(fig,'queen_supply_diagnosis','Same 18 predeclared historical runs. Correlations do not identify a calibrated energy demand or a causal worker-count rule.')

    ratios=read(BASE/'performance_analysis/paired_ratios.csv');growth=read(BASE/'performance_analysis/growth.csv');fig,axes=plt.subplots(1,2,figsize=(11,4.3))
    for ax,layout in zip(axes,['dense','dispersed']):
        rows=[r for r in ratios if r['layout']==layout and r['phase']=='advance'];g=next(r for r in growth if r['layout']==layout and r['phase']=='advance')
        for s,color in [('1','#226b89'),('2','#bd8735'),('3','#629785')]:
            selected=[r for r in rows if r['session']==s];ax.scatter([int(r['block']) for r in selected],[float(r['ratio']) for r in selected],label='Session '+s,color=color,s=22)
        ax.axhline(6,color='#b34b3c',linestyle='--',label='Frozen target (dense)');ax.axhline(float(g['ratio_of_p50']),color='black',linewidth=.9,label='Pooled p50 ratio')
        ax.set(title=layout.capitalize()+' contacts: all paired blocks',xlabel='Balanced block',ylabel='2048 / 512 advance ratio');ax.grid(alpha=.15)
    axes[0].legend(fontsize=7);save(fig,'contact_requalification','Same binaries, decisions and history. Birth registration remains unqualified; contact evidence cannot substitute for its missing batch.')
if __name__=='__main__':main()
