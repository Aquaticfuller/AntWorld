"""Render standalone S6.3 scientific figures from the complete archived observations."""
import argparse
from collections import defaultdict
from pathlib import Path
import statistics as st
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analyze_s6_3 import ROOT, read


def save(fig, directory, name):
    fig.tight_layout()
    for extension in ('png','svg'):
        path = directory/(name+'.'+extension)
        fig.savefig(path, dpi=160)
        if extension == 'svg':
            path.write_text('\n'.join(line.rstrip() for line in path.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8',newline='\n')
    plt.close(fig)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=ROOT/'experiments/s6_3')
    args = p.parse_args()
    out = args.root/'figures'
    out.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    colors = {'balanced':'#177e89','scarce':'#d08124','empty':'#a33c47','cyclic':'#7657a6'}
    fig,axes = plt.subplots(2,2,figsize=(11,7),sharex=True)
    for column,population in enumerate(('8','32')):
        rows = [r for r in read(args.root/'ecology/primary-v2/summary.csv') if r['workers']==population]
        grouped = defaultdict(list)
        for r in rows:
            group = 'cyclic' if r['cyclic']=='1' else r['supply']
            grouped[group].append(read(args.root/'ecology/primary-v2'/r['run']/'daily.csv'))
        for group,series in grouped.items():
            for axis,metric in zip(axes[:,column],('living','available_carbs_ug')):
                observations = [[sum(int(row[k]) for k in ('egg','larva','pupa','adult')) if metric=='living' else int(row[metric])/1000 for row in s] for s in series]
                mean = [st.mean(x) for x in zip(*observations)]
                low,high = [min(x) for x in zip(*observations)],[max(x) for x in zip(*observations)]
                axis.plot(range(91),mean,label=group,color=colors[group])
                axis.fill_between(range(91),low,high,color=colors[group],alpha=.11)
            axes[0,column].set_title(population+' initial workers + one queen')
            axes[1,column].set_xlabel('Game day (86,400,000 ms)')
    axes[0,0].set_ylabel('Living individuals')
    axes[1,0].set_ylabel('Accessible carbohydrate (mg)')
    axes[0,1].legend(loc='upper right')
    fig.suptitle('90-day finite-source ecology | mean and seed range, all six seeds | ENGINEERING_FIXTURE')
    save(fig,out,'population_resources')

    contrasts = read(args.root/'analysis/paired.csv')
    fig,axes = plt.subplots(1,3,figsize=(12,4))
    for axis,metric,label in zip(axes,('emerged','sampled_unmet_protein_ug_days','active_program_pct'),
                                ('Cumulative emergence','Sampled unmet protein (ug days)','Active program ownership (percentage points)')):
        rows = [r for r in contrasts if r['group']=='controls-v2' and r['metric']==metric]
        values = [float(r['mean']) for r in rows]
        errors = [[float(r['mean'])-float(r['low']) for r in rows],[float(r['high'])-float(r['mean']) for r in rows]]
        axis.errorbar(values,range(len(rows)),xerr=errors,fmt='o',color='#177e89',capsize=4)
        axis.set_yticks(range(len(rows)),[r['contrast'].replace(' minus full','') for r in rows])
        axis.axvline(0,color='gray',linewidth=.7)
        axis.set_xlabel(label)
    fig.suptitle('14-day scarcity controls minus full model | paired seed mean and 95% bootstrap CI')
    save(fig,out,'nutrition_activity_controls')

    growth = read(args.root/'performance_analysis/growth.csv')
    fig,axes = plt.subplots(1,2,figsize=(11,4))
    for axis,phase,batches,title in (
            (axes[0],'advance',('contacts-baseline-final','contacts-final'),'TD-01 stationary dense advance'),
            (axes[1],'birth_advance',('birth-before-index','birth-after-index'),'TD-08 dynamic births with pending actions')):
        rows = [next(r for r in growth if r['batch']==batch and r['layout']=='dense' and r['phase']==phase) for batch in batches]
        y = [float(r['paired_median']) for r in rows]
        axis.errorbar(range(2),y,yerr=[[float(r['paired_median'])-float(r['ci_low']) for r in rows],
                                     [float(r['ci_high'])-float(r['paired_median']) for r in rows]],fmt='o',capsize=5)
        axis.axhline(6,color='#a33c47',linestyle='--',label='6x gate / proposed registration target')
        axis.set_xticks(range(2),('Before','After'))
        axis.set_ylabel('2048 / 512 paired block growth')
        axis.set_title(title)
        axis.legend(fontsize=7)
    fig.suptitle('Three balanced sessions | hierarchical 95% CI | actual actions and full history retained')
    save(fig,out,'performance_growth')


if __name__ == '__main__':
    main()
