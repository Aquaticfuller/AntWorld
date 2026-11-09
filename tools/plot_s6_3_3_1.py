"""Plot paired retrieval, B01 observation, TD-11 density and formal timing results."""
import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]/'experiments/s6_3_3_1'
BLUE, GREEN, GRAY, RED = '#2470a0', '#147960', '#545963', '#a54332'


def read(path):
    with path.open(encoding='utf-8',newline='') as f:
        return list(csv.DictReader(f))


def value(row, field):
    return float(row[field])


def point(ax, x, mean, low, high, color, label=None, horizontal=False):
    error = [[mean-low], [high-mean]]
    if horizontal:
        ax.errorbar(mean,x,xerr=error,fmt='o',capsize=3,color=color,label=label)
    else:
        ax.errorbar(x,mean,yerr=error,fmt='o',capsize=3,color=color,label=label)


def retrieval_and_care(root):
    fig, axes = plt.subplots(1,3,figsize=(12.4,4.3),layout='constrained')
    rows = [r for r in read(root/'analysis/b02_literature_comparison.csv') if r['cohort']=='all_units']
    for ax, metric, label in zip(axes,('retrieved','first_contact_capped_s'),
                                 ('Brood retrieved in 600 s','Mean capped first contact (s)')):
        for i,group in enumerate(('queen','three_workers')):
            a,b = [r for r in rows if r['condition']==group and r['metric']==metric]
            for offset,row,prefix,color,key in ((-.2,a,'simulated',GRAY,'Legacy'),(0,b,'simulated',BLUE,'Local episode'),
                                               (.2,a,'observed',GREEN,'Measured')):
                point(ax,i+offset,value(row,prefix+'_mean'),value(row,prefix+'_ci_low'),value(row,prefix+'_ci_high'),
                      color,key if i==0 else None)
        ax.set(xticks=[0,1],xticklabels=['Queen','Three workers'],ylabel=label,ylim=(0,None))
        ax.grid(axis='y',alpha=.24)
    axes[0].legend(loc='upper left',frameon=False,fontsize=8)
    axes[0].set_title('A   B02 counts')
    axes[1].set_title('B   B02 contact')
    ax = axes[2]
    rows = [r for r in read(root/'analysis/b01_literature_comparison.csv') if r['policy']=='local']
    for i,row in enumerate(rows):
        for offset,prefix,color,key in ((-.23,'observed',GREEN,'Measured 50-scan'),(0,'simulated',BLUE,'Simulated 50-scan')):
            point(ax,i+offset,100*value(row,prefix+'_mean'),100*value(row,prefix+'_ci_low'),
                  100*value(row,prefix+'_ci_high'),color,key if i==0 else None)
        ax.scatter(i+.23,100*value(row,'active_time'),color=GRAY,marker='s',label='Active-care time' if i==0 else None)
    ax.set(xticks=[0,1,2],xticklabels=['Absent','Added','Removed'],ylabel='Percentage',ylim=(0,34))
    ax.set_title('C   B01 scoring definitions')
    ax.legend(loc='upper right',frameon=False,fontsize=8)
    ax.grid(axis='y',alpha=.24)
    fig.suptitle('Exploratory brood retrieval and separate care-fidelity check',weight='bold')
    return fig


def heldout(root):
    fig, axes = plt.subplots(1,2,figsize=(9.5,4.4),layout='constrained',sharey=True)
    rows = read(root/'analysis/paired_retrieval.csv')
    layouts = ('line','mirror','split','far','sheltered','empty')
    for ax,metric,unit,label in zip(axes,('retrieved','first_contact_capped_ms'),(1,1000),
                                   ('Change in retrieved brood','Change in capped first contact (s)')):
        ax.axvline(0,color=GRAY,linewidth=1)
        for i,layout in enumerate(layouts):
            for group,offset,color,key in (('queen',-.13,BLUE,'Queen'),('three_workers',.13,GREEN,'Three workers')):
                row = next(r for r in rows if r['set']=='holdout' and r['metric']==metric and
                           r['layout']==layout and r['condition']==group)
                point(ax,i+offset,value(row,'paired_delta')/unit,value(row,'paired_ci_low')/unit,
                      value(row,'paired_ci_high')/unit,color,key if i==0 else None,horizontal=True)
        ax.set(xlabel=label,yticks=range(len(layouts)),yticklabels=[s.capitalize() for s in layouts])
        ax.grid(axis='x',alpha=.24)
    axes[0].invert_yaxis()
    axes[1].legend(loc='lower left',frameon=False)
    fig.suptitle('Prospective simulator holdout, 12 paired seeds per layout',weight='bold')
    return fig


def density(root):
    rows = [r for r in read(root/'analysis/density_summary.csv') if r['policy']=='local']
    fig, axes = plt.subplots(1,3,figsize=(12.6,4.1),layout='constrained')
    for ax,metric,label in zip(axes,('advance_ms','opportunities','encoded_history_bytes'),
                               ('Advance p50 (ms)','Committed opportunities','Encoded history (MiB)')):
        for layout,color in (('dense',RED),('dispersed',BLUE)):
            for brood,line in (('1','--'),('4','-')):
                chosen = sorted((r for r in rows if r['layout']==layout and r['brood_per_caregiver']==brood and
                                 r['metric']==metric),key=lambda r:int(r['caregivers']))
                scale = 2**20 if metric=='encoded_history_bytes' else 1
                x = [int(r['caregivers']) for r in chosen]
                y = [value(r,'p50')/scale for r in chosen]
                ax.plot(x,y,marker='o',color=color,linestyle=line,label=f'{layout}, {brood} brood per caregiver')
        ax.set(xscale='log',yscale='log',xlabel='Simultaneous caregivers',ylabel=label,xticks=(1,8,32,128),
               xticklabels=('1','8','32','128'))
        ax.grid(which='major',alpha=.22)
    axes[0].legend(loc='upper left',fontsize=8,frameon=False)
    fig.suptitle('TD-11, 60 s of care with every opportunity retained',weight='bold')
    return fig


def performance(root):
    paths = [root/'performance/analysis/growth.csv',root/'performance_reserve/analysis/growth.csv']
    rows = [r for p in paths if p.exists() for r in read(p) if r['target'] and r['status'] in ('PASS','FAIL')]
    fig, ax = plt.subplots(figsize=(7.1,3.25),layout='constrained')
    labels = {'contacts':'Dense contacts','births':'Reserve births'}
    for i,row in enumerate(rows):
        point(ax,i,value(row,'ratio_of_p50'),value(row,'pooled_ci_low'),value(row,'pooled_ci_high'),
              BLUE if row['status']=='PASS' else RED,horizontal=True)
    ax.axvline(6,color=RED,linestyle='--',label='Frozen limit')
    ax.set(xlabel='2,048 / 512 advance p50 ratio',yticks=range(len(rows)),yticklabels=[labels[r['kind']] for r in rows],
           xlim=(0,max([7,*(value(r,'pooled_ci_high')+1 for r in rows)])))
    ax.invert_yaxis()
    ax.legend(loc='lower left',frameon=False)
    ax.grid(axis='x',alpha=.24)
    fig.suptitle('Formal Windows Release timing with hierarchical 95% intervals',weight='bold')
    return fig


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=ROOT)
    p.add_argument('--out',type=Path,default=ROOT/'figures')
    args = p.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'svg.hashsalt':'antworld-s6331','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    for name,plot in (('b02_b01',retrieval_and_care),('holdout',heldout),('td11',density),('performance',performance)):
        figure = plot(args.root)
        path = args.out/(name+'.svg')
        figure.savefig(path,metadata={'Date':None})
        source = path.read_text(encoding='utf-8')
        path.write_text('\n'.join(line.rstrip() for line in source.splitlines())+'\n',encoding='utf-8',newline='\n')
        plt.close(figure)


if __name__ == '__main__':
    main()
