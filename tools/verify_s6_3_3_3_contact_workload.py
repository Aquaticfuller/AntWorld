"""Compare all protected contact identities in the current build with the qualified archive."""
import argparse
import json
from pathlib import Path
import subprocess

from verify_s6_3_3_1_reserve_workload import ROOT, read, sha

REFERENCE = ROOT/'experiments/s6_3_3_2/performance_portable/contacts/session1/contacts.csv'
KEYS = ('population','layout','policy','seed','simulation_ms','checkpoint_bytes','events','pending',
        'decisions','candidates','bucket_queries','tree_visits','maximum_candidates','state_hash',
        'trace_hash','continuation_equal')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--binary',type=Path,required=True)
    p.add_argument('--scratch',type=Path,required=True)
    p.add_argument('--receipt',type=Path,required=True)
    a = p.parse_args()
    a.scratch.mkdir(parents=True)
    plan = a.scratch/'identity_schedule.csv'
    with plan.open('x',encoding='utf-8',newline='') as f:
        f.write('sample,session,block,slot,warmup,population,layout,policy\n')
        for i,n in enumerate((128,512,2048)):
            for j,layout in enumerate(('dense','dispersed')):
                f.write(f'{2*i+j},0,0,{2*i+j},0,{n},{layout},bounded\n')
    subprocess.run([a.binary.resolve(),a.scratch.resolve(),plan.resolve(),'0'],check=True)
    reference = {(r['population'],r['layout']):{k:r[k] for k in KEYS} for r in read(REFERENCE)}
    identities = [{k:r[k] for k in KEYS} for r in read(a.scratch/'contacts.csv')]
    match = len(identities)==6 and all(r==reference[r['population'],r['layout']] for r in identities)
    receipt = dict(scope='Identity verification only. This run is outside formal timing admission.',
                   match=match, executable_sha256=sha(a.binary), reference_sha256=sha(REFERENCE), identities=identities)
    with a.receipt.open('x',encoding='utf-8',newline='\n') as f:
        json.dump(receipt,f,indent=2)
        f.write('\n')
    assert match, receipt
    print('Exact protected dense and dispersed contact workloads at all three populations.')


if __name__=='__main__':
    main()
