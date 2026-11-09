"""Plot published endpoints and coverage; no fitting or figure digitization.

Optional illustration tool. Authoritative data and CI require only stdlib.
Reproduction environment: matplotlib 3.10.7 (Agg backend).
"""
import argparse
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT/'research/s6_3_2_1/figures')
    args = parser.parse_args()
    cache=ROOT/'out/s6_3_2_1/matplotlib-cache'
    cache.mkdir(parents=True,exist_ok=True)
    os.environ.setdefault('MPLCONFIGDIR',str(cache))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    data = ROOT/'research/s6_3_2_1'
    coverage = json.loads((data/'coverage.json').read_text())
    measurements = json.loads((data/'measurements.json').read_text())
    args.output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.size':11, 'axes.spines.top':False, 'axes.spines.right':False})
    colors = ['#226c91','#72b2a1','#d4d9df']
    fig,ax = plt.subplots(figsize=(10,4.8),layout='constrained')
    for i,axis in enumerate(['life_stage','behavior','environment','physiology']):
        rows = [r for r in coverage if r['Axis']==axis]
        a = sum(r['Status']=='DIRECT_QUANTITATIVE' for r in rows)
        b = sum(r['Status'] in ['DIRECT_QUALITATIVE','DIRECT_OBSERVATIONAL'] for r in rows)
        left = 0
        for j,value in enumerate([a,b,len(rows)-a-b]):
            ax.barh(i,value,left=left,color=colors[j],label=['Direct quantitative','Other direct','Partial / unresolved'][j] if i==0 else '')
            if value: ax.text(left+value/2,i,str(value),ha='center',va='center',color='white' if j==0 else '#142333')
            left += value
    ax.set_yticks(range(4),['Life stage','Behavior','Environment','Physiology'])
    ax.invert_yaxis();ax.set_xlabel('Frozen coverage slots (84 total)');ax.set_xlim(0,27)
    ax.set_title('Endpoint coverage is not complete mechanism validation',loc='left',pad=18)
    ax.legend(loc='lower center',bbox_to_anchor=(.5,-.32),ncol=3,frameon=False)
    fig.savefig(args.output/'coverage.png',dpi=160,bbox_inches='tight');plt.close(fig)

    fig,ax = plt.subplots(figsize=(9,5.4),layout='constrained')
    fig.get_layout_engine().set(rect=(0,.09,1,.91))
    for pop,color in [('Borisovka','#226c91'),('St_Petersburg','#ad6330')]:
        rows=[r for r in measurements if r['SourceId']=='B06' and r['Measurement']=='total duration' and r['Population']==pop and r['Value']!='NOT_OBSERVED']
        ax.plot([float(r['Temperature'].split()[0]) for r in rows],[float(r['Value']) for r in rows],'o-',label=pop.replace('_',' '),color=color)
    ax.axhline(7,color='#8b3a55',linestyle='--',label='Unchanged supplied-tissue fixture: 7 days')
    ax.set(xlabel='Constant assay temperature (C)',ylabel='First-brood egg-to-worker duration (days)',ylim=(0,80))
    ax.set_title('B06 Table 2: published means, not a new model fit',loc='left',pad=15)
    ax.legend(frameon=False,loc='upper right')
    fig.text(.12,.01,'Cold arms without completion remain in CSV; dispersion type unresolved, so no CI is invented.',fontsize=9)
    fig.savefig(args.output/'development.png',dpi=160,bbox_inches='tight');plt.close(fig)

    fig,ax = plt.subplots(figsize=(9,5.5),layout='constrained')
    fig.get_layout_engine().set(rect=(0,.09,1,.91))
    rows=[r for r in measurements if r['RecordId'] in [f'N27-T1-{i:02}' for i in range(1,5)]]
    ax.bar(range(4),[float(r['Mean']) for r in rows],yerr=[float(r['SD']) for r in rows],capsize=5,color=['#226c91','#72b2a1','#226c91','#72b2a1'])
    ax.set_xticks(range(4),['Worker\nClark 20 C\nn=33','Worker\nSable room 25 C\nn=15','Queen\nClark 20 C\nn=8','Queen\nSable room 25 C\nn=4'])
    ax.set_ylabel('uL O2 per individual per hour (mean +/- SD)')
    ax.set_title('N27 Table 1: caste, device and temperature remain distinct',loc='left',pad=15)
    fig.text(.12,.01,'L. niger only. Measurement samples; workers pooled. Not matched-temperature device contrasts.',fontsize=9)
    fig.savefig(args.output/'respiration.png',dpi=160,bbox_inches='tight');plt.close(fig)
    print('WROTE three evidence figures; matplotlib',matplotlib.__version__)


if __name__=='__main__': main()
