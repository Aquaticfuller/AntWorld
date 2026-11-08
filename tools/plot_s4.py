#!/usr/bin/env python3
"""Export scientific figures from the complete S4 archive; never filter successful seeds."""
import csv
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'out/matplotlib'))
sys.path.insert(0,str(ROOT/'.tools/s2_1-python'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

DATA = ROOT/'experiments/s4'
FIGURES = DATA/'figures'


def read(name):
    with (DATA/name).open(encoding='utf-8',newline='') as stream:
        return list(csv.DictReader(stream))


def save(fig,name):
    fig.savefig(FIGURES/f'{name}.png',dpi=170,metadata={'Software':'AntWorld S4 scientific validation'})
    fig.savefig(FIGURES/f'{name}.svg',metadata={'Date':None,'Creator':'AntWorld S4 scientific validation'})
    svg = FIGURES/f'{name}.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8',newline='\n')
    plt.close(fig)


def main():
    FIGURES.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'svg.hashsalt':'AntWorld-S4','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    raw,summary = read('raw/summary.csv'),read('summary.csv')
    fig,axes = plt.subplots(1,3,figsize=(12,4.2),layout='constrained')
    for ax,metric,label in zip(axes,('excavated_q3','deposited_q3','carrying_moves'),('Excavated volume (q cubed)','Deposited volume (q cubed)','Loaded movement actions')):
        for x,count in enumerate(('1','4')):
            rows = [r for r in raw if r['scenario']=='autonomous' and r['workers']==count and r['reverse_order']=='0']
            values = [int(r[metric]) for r in rows]
            jitter = [(int(r['seed'])%8-3.5)*.026 for r in rows]
            ax.scatter([x+j for j in jitter],values,color='#326d91',alpha=.65,s=20)
            s = next(r for r in summary if r['scenario']=='autonomous' and r['workers']==count and r['reverse_order']=='0' and r['metric']==metric)
            mean,lo,hi = (float(s[k]) for k in ('mean','ci95_low','ci95_high'))
            ax.errorbar(x,mean,yerr=[[mean-lo],[hi-mean]],fmt='D',color='#b35d24',capsize=6,markersize=7)
        ax.set_xticks([0,1],['1 worker','4 workers']); ax.set_ylabel(label); ax.grid(axis='y',alpha=.15)
    fig.suptitle('S4 autonomous excavation: every seed 1-32, 60 simulated seconds\nDots: individual runs; diamonds: means and 95% seed-bootstrap intervals',fontsize=12)
    fig.supxlabel('ENGINEERING_FIXTURE | q = 0.5 mm | Reversed activation duplicates are paired controls, excluded from sample size',fontsize=9)
    save(fig,'excavation_outcomes')

    edits = [r for r in read('raw/edits.csv') if r['seed']=='1' and r['scenario']=='autonomous' and r['workers']=='4' and r['reverse_order']=='0']
    points = [r for r in read('raw/trajectories.csv') if r['seed']=='1' and r['scenario']=='autonomous' and r['workers']=='4' and r['reverse_order']=='0' and r['time_ms']=='60000']
    fig,axes = plt.subplots(1,2,figsize=(10.8,5.8))
    fig.subplots_adjust(top=.79,bottom=.20,wspace=.25)
    for ax,axis,cut in ((axes[0],'y','z'),(axes[1],'z','y')):
        offset = -12 if axis=='y' else 0
        ax.add_patch(Rectangle((0,offset),16,12,facecolor='#c3ad91',edgecolor='#66513d'))
        for row in edits:
            if int(row[f'min_{cut}_q']) <= 12 < int(row[f'max_{cut}_q']):
                x,y = int(row['min_x_q'])*.5,int(row[f'min_{axis}_q'])*.5+offset
                width = (int(row['max_x_q'])-int(row['min_x_q']))*.5
                height = (int(row[f'max_{axis}_q'])-int(row[f'min_{axis}_q']))*.5
                ax.add_patch(Rectangle((x,y),width,height,facecolor='#81b8c9',edgecolor='#4b8295',linewidth=.45))
        # All experiment edits excavate. Cover their already-empty initial overlap.
        ax.add_patch(Rectangle((1,1+offset),6,10,facecolor='#f7f8f8',edgecolor='#87949c',linestyle='--'))
        for point in points:
            if abs(int(point[f'{cut}_q'])-12)<=1:
                ax.scatter(int(point['x_q'])*.5,int(point[f'{axis}_q'])*.5+offset,color='#ae4e28',s=22,zorder=3)
        ax.set(xlim=(0,16),ylim=(offset,12+offset),xlabel='X east (mm)',ylabel=f'{axis.upper()} '+('up' if axis=='y' else 'north')+' (mm)',aspect='equal')
        ax.set_title(f'Exact box section: {cut.upper()} quantum coordinate = 12')
    fig.suptitle('Predeclared example: seed 1, four workers, 60 s\nWhite: seeded void; blue: removed initial soil in this section',fontsize=12,y=.98)
    fig.text(.5,.05,'ENGINEERING_FIXTURE | Orange: workers within 0.5 mm of the section\n3D authority is the ordered box log; projected crossings do not imply connectivity',ha='center',fontsize=9)
    save(fig,'geometry_sections')
    print('Wrote S4 outcome and geometry figures (PNG and SVG)')


if __name__ == '__main__':
    main()
