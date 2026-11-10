"""Verify the same-colony density traces and summarize independent timing scopes."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import subprocess

from analyze_s6_3_2_performance import describe
from analyze_s6_3_3_1_performance import digest, emit, read

ROOT=Path(__file__).resolve().parents[1]/'experiments/s6_3_3_2/td11'
TIMES=('advance_ms','checkpoint_ms','restore_ms')
SCOPES=(('advance','neighborhood'),('advance','care_opportunities'),
        ('advance','fact_history'),('encode','checkpoint_history'))


def arm(root):
    receipt=json.loads((root/'receipt.json').read_text(encoding='utf-8'))
    for file,sha in receipt['files'].items():
        assert digest(root/file)==sha, file
    rows=read(root/'samples.csv')
    profile=read(root/'profile.csv')
    assert len(rows)==receipt['samples']==64 and len(profile)==receipt['profile_rows']==2304
    by_sample=defaultdict(dict)
    for row in profile:
        key=(row['phase'],row['category'])
        assert key not in by_sample[row['sample']]
        by_sample[row['sample']][key]=row
    for row in rows:
        scopes=by_sample[row['sample']]
        assert int(scopes['advance','care_opportunities']['work'])==int(row['opportunities'])
        assert int(scopes['encode','checkpoint_history']['work'])==int(row['journal_facts'])
        assert row['restore_equal']=='1' and int(row['state_hash']) and int(row['trace_hash'])
    return rows,by_sample


def collect(root, binaries):
    root.mkdir(parents=True)
    for mode, binary in zip(('reference','indexed'),binaries):
        folder=root/mode
        subprocess.run([binary.resolve(),folder.resolve()], check=True)
        receipt=dict(mode='Release ANTWORLD_PROFILE=ON', executable_sha256=digest(binary), samples=64,
                     profile_rows=2304, files={name:digest(folder/name) for name in ('samples.csv','profile.csv')})
        (folder/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8',newline='\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--check',action='store_true')
    parser.add_argument('--collect',type=Path,nargs=2,metavar=('REFERENCE','INDEXED'))
    parser.add_argument('--portable',type=Path)
    args=parser.parse_args()
    if args.collect:
        collect(args.root,args.collect)
    roots={mode:arm(args.root/mode) for mode in ('reference','indexed')}
    before,after=(rows for rows,_ in roots.values())
    for a,b in zip(before,after):
        assert all(a[k]==b[k] for k in a if k not in TIMES), (a['sample'],a['layout'])
    if args.portable:
        corrected, profiles=arm(args.portable)
        for previous,current in zip(after,corrected):
            assert all(previous[k]==current[k] for k in previous if k not in TIMES), current['sample']
            key=('advance','neighborhood')
            assert profiles[current['sample']][key]['work']==roots['indexed'][1][previous['sample']][key]['work']
        print('PASS: corrected care query preserves all 64 indexed cases and candidate counts')
    metrics=[]
    for mode,(rows,profile) in roots.items():
        cells=defaultdict(list)
        for row in rows:
            if row['warmup']=='0':
                cells[row['layout'],row['caregivers'],row['brood_per_caregiver']].append(row)
        assert len(cells)==16
        for (layout,caregivers,brood),selected in cells.items():
            assert len(selected)==3
            group=dict(mode=mode,layout=layout,caregivers=caregivers,brood_per_caregiver=brood)
            for name in (*TIMES,'opportunities','journal_facts','encoded_history_bytes','checkpoint_bytes',
                         'completed_brood_handling','brood_moves'):
                metrics.append(dict(**group,phase='case',metric=name,
                                    **describe([float(r[name]) for r in selected])))
            for phase,category in SCOPES:
                scope=[profile[r['sample']][phase,category] for r in selected]
                for field in ('calls','inclusive_ns','exclusive_ns','work'):
                    metrics.append(dict(**group,phase=phase,metric=f'{category}_{field}',
                                        **describe([int(r[field]) for r in scope])))
    emit(args.root/'summary.csv',metrics,args.check)
    print('PASS: all 64 density state and trace identities match')
    for r in metrics:
        if r['caregivers']=='128' and r['brood_per_caregiver']=='4' and r['metric'] in (
                'advance_ms','neighborhood_work','neighborhood_inclusive_ns',
                'care_opportunities_inclusive_ns','checkpoint_history_inclusive_ns'):
            print(r['mode'],r['layout'],r['metric'],r['p50'])


if __name__=='__main__':
    main()
