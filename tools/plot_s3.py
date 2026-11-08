#!/usr/bin/env python3
"""Create exportable S3 engineering validation figures from audited aggregates."""
import argparse
import csv
import os
import sys
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--packages',type=Path)
args = parser.parse_args()
if args.packages:
    sys.path.insert(0,str(args.packages.resolve()))
ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR', str(ROOT/'out/matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

DATA = ROOT/'experiments/s3'
with (DATA/'summary.csv').open(encoding='utf-8',newline='') as stream:
    rows = list(csv.DictReader(stream))
with (DATA/'raw/individuals.csv').open(encoding='utf-8',newline='') as stream:
    individual = list(csv.DictReader(stream))
plt.rcParams.update({'font.size':10,'svg.hashsalt':'AntWorld-S3'})


def select(scenario, supplied, pulse, metric, capacity='1000'):
    return next(r for r in rows if r['scenario']==scenario and r['supplied']==str(supplied) and r['pulse_ms']==str(pulse)
                and r['metric']==metric and r['receiver_capacity_ug']==capacity and r['reverse_order']=='0')


fig, axes = plt.subplots(2,2,figsize=(12,8.5),layout='constrained')
fig.suptitle('S3 nutrition and lifecycle validation — ENGINEERING_FIXTURE',fontsize=15)
ax = axes[0,0]
for supplied, color, label in ((0,'#a9b4bd','Zero protein'),(1,'#267f8e','Protein supplied')):
    r = select('development',supplied,1000,'emergence_fraction')
    ax.bar(supplied,float(r['mean'])*100,color=color,width=.6,label=label)
ax.set(xticks=[0,1],xticklabels=['Zero protein','Protein supplied'],ylabel='Brood emerged by 180 s (%)',ylim=(0,110),title='N1 / continuous identity: 64 seeds × 4 eggs')
ax.text(.5,.84,'Engineering protein gate; not species growth validation',transform=ax.transAxes,ha='center',fontsize=9)
ax = axes[0,1]
for supplied,color,label in ((0,'#b86c48','Zero protein (censored)'),(1,'#267f8e','Protein supplied')):
    sample = [int(r['adult_at_ms'])/1000 for r in individual if r['scenario']=='development' and r['supplied']==str(supplied) and r['pulse_ms']=='1000']
    times = sorted(v for v in sample if v>=0)
    x = [0]+times+[180]; y = [0]+[(i+1)/len(sample) for i in range(len(times))]+[len(times)/len(sample)]
    ax.step(x,y,where='post',label=label,color=color)
ax.set(xlabel='Simulation time (s)',ylabel='Cumulative emergence fraction',ylim=(-.02,1.05),title='All non-emergers retained at the 180 s horizon')
ax.legend(loc='upper left',fontsize=9)
ax = axes[1,0]
capacities = ['0','100','1000']
values = [float(select('N2',1,1000,'transferred_ug',c)['mean']) for c in capacities]
ax.bar(range(3),values,color='#526dab',width=.6)
ax.set(xticks=range(3),xticklabels=capacities,xlabel='Receiver crop capacity (ug)',ylabel='Actual total received (ug)',ylim=(0,450),title='N2: two 200 ug donors; both submission orders')
ax.text(.5,.86,'Donor loss = recipient gain; empty donors transfer 0',transform=ax.transAxes,ha='center',fontsize=9)
ax = axes[1,1]
points = [select('development',1,p,'restricted_emergence_ms') for p in (250,1000,2000)]
means = [float(r['mean'])/1000 for r in points]
lo = [m-float(r['ci95_low'])/1000 for m,r in zip(means,points)]
hi = [float(r['ci95_high'])/1000-m for m,r in zip(means,points)]
ax.errorbar([.25,1,2],means,yerr=[lo,hi],fmt='o-',capsize=4,color='#267f8e')
ax.set(xlabel='Absorption pulse period (s)',ylabel='Restricted mean emergence time (s)',title='Pulse sensitivity; paired seeds, 95% cluster intervals')
fig.text(.5,-.015,'All inputs are uncalibrated fixtures. 1,536 runs; exact mass/energy balance and host-step equivalence in every run.',ha='center',fontsize=10)
(DATA/'figures').mkdir(parents=True,exist_ok=True)
fig.savefig(DATA/'figures/nutrition_and_development.png',dpi=160,bbox_inches='tight',metadata={'Software':'AntWorld S3'})
path = DATA/'figures/nutrition_and_development.svg'
fig.savefig(path,bbox_inches='tight',metadata={'Date':None,'Creator':'AntWorld S3'})
path.write_text('\n'.join(line.rstrip() for line in path.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8',newline='\n')
print('Created S3 PNG and SVG figures')
