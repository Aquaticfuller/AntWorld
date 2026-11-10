"""Render the frozen comparison and density figures from tracked analysis tables."""
import csv
from pathlib import Path
import statistics as st

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


BASE = Path(__file__).resolve().parents[1]/'experiments/s6_3_3_2'
matplotlib.rcParams.update({'svg.hashsalt':'s6.3.3.2', 'font.size':9, 'axes.spines.top':False,
                            'axes.spines.right':False, 'axes.grid':True, 'grid.alpha':.22})


def read(path):
    with path.open(newline='',encoding='utf-8') as stream:
        return list(csv.DictReader(stream))


def save(fig, name):
    path = BASE/'figures'/f'{name}.svg'
    path.parent.mkdir(exist_ok=True)
    fig.savefig(path, metadata={'Date':None}, bbox_inches='tight')
    content = path.read_text(encoding='utf-8')
    path.write_text('\n'.join(line.rstrip() for line in content.splitlines())+'\n', encoding='utf-8', newline='\n')
    plt.close(fig)


def interval(ax, x, row, prefix, color, scale=1, label=None):
    mean = float(row[prefix+'mean'])*scale
    lower,upper = (float(row[prefix+'ci_'+end])*scale for end in ('low','high'))
    ax.errorbar(x, mean, yerr=[[max(0,mean-lower)],[max(0,upper-mean)]], fmt='o',
                capsize=3, color=color, label=label)


def biology():
    b01 = read(BASE/'analysis/b01_paper_errors.csv')
    b02 = read(BASE/'analysis/b02_paper_errors.csv')
    controls = read(BASE/'analysis/b02_run_diagnostics.csv')
    fig, axes = plt.subplots(2,2,figsize=(10.1,7.0),layout='constrained')
    ax = axes[0,0]
    for i,condition in enumerate(('absent','added','removed')):
        old,new = (next(r for r in b01 if r['condition']==condition and r['variant']==v)
                   for v in ('S6.3.3.1','base'))
        for offset,row,prefix,color,label in ((-.15,new,'paper_','#2d693a','Measured'),
                (0,old,'','#777777','Prior model'),(.15,new,'','#075b84','Timed model')):
            interval(ax,i+offset,row,prefix,color,100,label if i==0 else None)
    ax.set(xticks=range(3),xticklabels=['Absent 24 h','Added 24 h','Removed 48 h'],
           ylabel='Active-care scans (%)',title='A   B01 first 10 s of each minute')
    ax.legend(frameon=False,loc='upper center')
    for ax,metric,label,panel in ((axes[0,1],'retrieved','Brood items at 10 min','B'),
                                  (axes[1,0],'first_contact_capped_s','Time to contact (s)','C')):
        for i,caste in enumerate(('q','w')):
            row = next(r for r in b02 if r['metric']==metric and r['caste']==caste)
            interval(ax,i-.12,row,'paper_','#2d693a',label='Measured' if i==0 else None)
            interval(ax,i+.12,row,'','#075b84',label='Timed model' if i==0 else None)
        ax.set(xticks=range(2),xticklabels=['Queen','Three workers'],ylabel=label,
               title=f'{panel}   B02 paired-origin units')
        ax.legend(frameon=False)
    ax=axes[1,1]
    for caste,color,label in (('queen','#aa641d','Queen'),('three_workers','#075b84','Three workers')):
        layouts=('line','mirror','split','far','empty','sheltered')
        sets=[[int(r['retrieved']) for r in controls if r['scenario']=='B02_robustness'
               and r['layout']==layout and r['condition']==caste] for layout in layouts]
        ax.plot(range(len(layouts)),[st.fmean(v) for v in sets],'-o',color=color,label=label)
        for x,data in enumerate(sets):
            ax.scatter([x]*len(data),data,s=14,color=color,alpha=.18)
    ax.set(xticks=range(len(layouts)),xticklabels=layouts,ylabel='Completed placements',
           ylim=(-.2,6.2),title='D   Simulator spatial robustness')
    ax.legend(frameon=False)
    save(fig,'b01_b02')


def density():
    rows = read(BASE/'td11/summary.csv')
    fig, axes = plt.subplots(1,3,figsize=(11.2,3.7),layout='constrained')
    cases=(('reference','dense','#aa641d','--'),('indexed','dense','#aa641d','-'),
           ('reference','dispersed','#075b84','--'),('indexed','dispersed','#075b84','-'))
    for mode,layout,color,style in cases:
        for ax,metric,scale,title,y in (
                (axes[0],'neighborhood_work',1,'A   Spatial candidate work','Candidates'),
                (axes[1],'advance_ms',1,'B   Simulation advance','Wall time (ms)'),
                (axes[2],'checkpoint_bytes',1e6,'C   Complete history retained','Checkpoint (MB)')):
            selected = [r for r in rows if r['mode']==mode and r['layout']==layout and
                        r['brood_per_caregiver']=='4' and r['metric']==metric]
            ax.plot([int(r['caregivers']) for r in selected],[float(r['p50'])/scale for r in selected],
                    linestyle=style,marker='o',color=color,label=f'{layout}, {mode}')
            ax.set(xscale='log',yscale='log',xticks=[1,8,32,128],xticklabels=[1,8,32,128],
                   xlabel='Caregivers',ylabel=y,title=title)
    axes[1].legend(frameon=False,fontsize=7)
    save(fig,'td11_density')


if __name__=='__main__':
    biology()
    density()
