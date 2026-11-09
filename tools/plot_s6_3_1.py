"""Export standalone S6.3.1 science figures; no outcome or seed filtering."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analyze_s6_3_1 import BASE,ROOT,read

COLORS={'baseline':'#b65243','corrected':'#147d92'}
LABELS={'baseline':'S6.3 rules','corrected':'Local reserve rule'}
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':120,'savefig.dpi':180})
OUT=BASE/'figures';OUT.mkdir(parents=True,exist_ok=True)


def save(fig,name):
    fig.text(.5,-.015,'All numeric physiology and behavior are ENGINEERING_FIXTURE; not calibrated species data.',ha='center',fontsize=8,color='#555555')
    fig.tight_layout();fig.savefig(OUT/(name+'.png'),bbox_inches='tight');fig.savefig(OUT/(name+'.svg'),bbox_inches='tight');plt.close(fig)
    svg=OUT/(name+'.svg');svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n',encoding='utf-8',newline='\n')


def folder(model,matrix,seed,workers,arm='laying'):
    return BASE/'ecology'/model/matrix/f'{seed}_{workers}_balanced_constant_{arm}_6'


def main():
    conditions=read(BASE/'analysis/conditions.csv');survival=read(BASE/'analysis/survival.csv')
    fig,axes=plt.subplots(2,2,figsize=(11,7),sharey=True)
    for row,matrix in enumerate(('causal','positive')):
        for col,workers in enumerate(('8','32')):
            ax=axes[row,col]
            for model in COLORS:
                rs=[r for r in survival if r['model']==model and r['matrix']==matrix and r['workers']==workers and r['supply']=='balanced' and r['arm']==('laying' if matrix=='causal' else 'positive')]
                ax.step([float(r['day']) for r in rs],[float(r['survival_fraction']) for r in rs],where='post',color=COLORS[model],label=LABELS[model])
            ax.set(title=f'{workers} workers: '+('ordinary access, 90 days' if matrix=='causal' else 'depot food, 180 days'),xlabel='Game days',ylabel='Queen survival fraction',ylim=(-.03,1.05));ax.grid(alpha=.18)
    axes[0,0].legend();fig.suptitle('All six frozen seeds per condition; living endpoints are right-censored',y=1.02)
    save(fig,'queen_survival')

    fig,axes=plt.subplots(2,2,figsize=(12,7))
    for col,model in enumerate(COLORS):
        events=read(folder(model,'causal',1,8)/'queen_events.csv')
        x=[float(r['time_ms'])/86400000 for r in events]
        continuous_x=[t for t in x for _ in range(2)]
        axes[0,col].plot(continuous_x,[float(r[side+'_body_energy_nj'])/1e9 for r in events for side in ('pre','post')],label='Body energy (usable)',color=COLORS[model])
        axes[0,col].step(x,[float(r['post_crop_carbs_ug'])/1000 for r in events],where='post',label='Crop carbohydrate potential*',color='#7a5d9b',alpha=.75)
        for r in events:
            if r['kind']=='35':axes[0,col].axvline(float(r['time_ms'])/86400000,color='#7b8768',alpha=.25,lw=.8)
        axes[0,col].set(title=LABELS[model]+' (seed 1, eight workers)',ylabel='Energy (J)',xlabel='Game days')
        for key,label,color in [('basal_cost_nj','Basal expenditure','#a87936'),('egg_energy_nj','Egg export','#147d92'),('reproductive_dissipation_nj','Reproductive dissipation','#b65243')]:
            axes[1,col].plot(continuous_x,[float(r[side+'_'+key])/1e9 for r in events for side in ('pre','post')],label=label,color=color)
        axes[1,col].step(x,[(1500000000+float(r['post_absorbed_carbs_ug'])*1000000)/1e9 for r in events],where='post',label='Initial body + absorbed input',color='#252b35',ls='--')
        axes[1,col].set(xlabel='Game days',ylabel='Cumulative energy (J)')
    axes[0,0].legend(fontsize=8);axes[1,0].legend(fontsize=8)
    fig.suptitle('Event-derived maternal account; vertical lines mark actual births\n*Crop carbohydrate is not body energy before absorption',y=1.05)
    save(fig,'queen_energy_account')

    fig,axes=plt.subplots(1,2,figsize=(12,7),sharex=True)
    for ax,workers in zip(axes,('8','32')):
        labels=[]
        for m,model in enumerate(COLORS):
            for seed in range(1,7):
                y=m*7+seed;labels.append((y,f'{model}, seed {seed}'))
                events=read(folder(model,'positive',seed,workers,'positive')/'queen_events.csv')
                births=[float(r['time_ms'])/86400000 for r in events if r['kind']=='35']
                death=next((float(r['time_ms'])/86400000 for r in events if r['kind']=='8'),180)
                ax.hlines(y,0,death,color=COLORS[model],alpha=.4,lw=3)
                ax.plot(births,[y]*len(births),'|',color=COLORS[model],ms=9)
                ax.plot([death],[y],'x' if death<180 else 'o',color=COLORS[model],ms=5)
        ax.axvspan(120,180,color='#e9d6a9',alpha=.4)
        ax.set(yticks=[y for y,_ in labels],yticklabels=[s for _,s in labels],xlabel='Game days',title=f'Depot-food positive control: {workers} initial workers',xlim=(0,183));ax.invert_yaxis()
    fig.suptitle('Actual births (ticks), death (x), alive at endpoint (circle); late window shaded',y=1.01)
    save(fig,'reproductive_timeline')

    fig,axes=plt.subplots(1,2,figsize=(12,5))
    for ax,workers in zip(axes,('8','32')):
        for m,model in enumerate(COLORS):
            rs=[next(r for r in conditions if r['model']==model and r['matrix']=='causal' and r['workers']==workers and r['supply']==s and r['arm']=='laying') for s in ('balanced','scarce','empty')]
            means=[float(r['queen_lifetime_days_mean']) for r in rs]
            err=[[v-float(r['queen_lifetime_days_ci_low']) for v,r in zip(means,rs)],[float(r['queen_lifetime_days_ci_high'])-v for v,r in zip(means,rs)]]
            ax.bar([i+(m-.5)*.35 for i in range(3)],means,.35,color=COLORS[model],yerr=err,capsize=4,label=LABELS[model])
        ax.set(xticks=range(3),xticklabels=['Balanced','Scarce protein','No external food'],ylabel='Restricted mean queen lifetime (days)',title=f'{workers} initial workers',ylim=(0,100))
    axes[0].legend(fontsize=8);fig.suptitle('Fixed 90-day window; 95% seed-bootstrap intervals, six seeds',y=1.02)
    save(fig,'supply_controls')

    fig,axes=plt.subplots(2,2,figsize=(12,7))
    for col,workers in enumerate(('8','32')):
        for model in COLORS:
            curves=[read(folder(model,'positive',seed,workers,'positive')/'daily.csv') for seed in range(1,7)]
            for row,metric in enumerate(('population','nest_carbs_ug')):
                values=[[sum(float(r[k]) for k in ('egg','larva','pupa','adult')) if metric=='population' else float(r[metric]) for r in curve] for curve in curves]
                x=range(181);mean=[sum(v[d] for v in values)/6 for d in x]
                axes[row,col].plot(x,mean,color=COLORS[model],label=LABELS[model]);axes[row,col].fill_between(x,[min(v[d] for v in values) for d in x],[max(v[d] for v in values) for d in x],color=COLORS[model],alpha=.12)
                axes[row,col].set(xlabel='Game days',ylabel='Living individuals' if metric=='population' else 'Depot carbohydrate (ug)',title=f'{workers} initial workers')
    axes[0,0].legend(fontsize=8);fig.suptitle('Finite depot-food control: mean and full seed range (not a confidence band)',y=1.02)
    save(fig,'population_and_resources')
    fig,axes=plt.subplots(1,2,figsize=(12,4.8))
    ratios=read(BASE/'performance_analysis/paired_ratios.csv')
    for name,label,color in [('contacts','Dense contact advance','#147d92'),('births-reserve','Birth registration','#b65243')]:
        rs=[r for r in ratios if r['batch']==name and r['layout']=='dense' and r['phase'] in ('advance','birth_advance')]
        axes[0].plot([12*(int(r['session'])-1)+int(r['block']) for r in rs],[float(r['ratio']) for r in rs],'.-',label=label,color=color,lw=.8)
    axes[0].axhline(6,ls='--',color='#333333',label='Frozen threshold');axes[0].set(xlabel='Paired block (all three sessions)',ylabel='2048 / 512 wall-time ratio',yscale='log');axes[0].legend(fontsize=8)
    latency=read(BASE/'performance_analysis/latency.csv');cpu=read(BASE/'performance_analysis/cpu_and_cycles.csv')
    for i,n in enumerate(('128','512','2048')):
        wall=next(r for r in latency if r['batch']=='contacts' and r['layout']=='dense' and r['session']=='pooled' and r['population']==n and r['phase']=='advance')
        process=next(r for r in cpu if r['batch']=='contacts' and r['layout']=='dense' and r['population']==n and r['phase']=='advance')
        axes[1].bar(i-.18,float(wall['p50']),.36,color='#147d92',label='Wall p50' if i==0 else None)
        axes[1].bar(i+.18,float(process['cpu_ms_p50']),.36,color='#aa8741',label='Process CPU p50' if i==0 else None)
    axes[1].set(xticks=range(3),xticklabels=['128','512','2048'],xlabel='Workers',ylabel='Advance time (ms)',yscale='log');axes[1].legend(fontsize=8)
    fig.suptitle('Pooled wall-time gate NOT PASSED: contacts 6.315x, births 8.154x\nPaired ratios and CPU counters do not replace the frozen wall-time criterion',y=1.07)
    save(fig,'performance_uncertainty')
    print('Wrote six PNG/SVG figures')


if __name__=='__main__':main()
