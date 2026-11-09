"""Verify the protected birth fixture against all three historical workload identities."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT/'experiments/s6_3_1/performance/births-reserve/session1/births.csv'
KEYS = ('layout','population','births','events','pending','checkpoint_bytes','state_hash','trace_hash',
        'exact_restore','mass_balanced','energy_balanced')


def read(path):
    with path.open(encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--scratch', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    assert args.binary.name == 'antworld_s6_3_1_birth_benchmark.exe'
    archive = {r['population']: {k:r[k] for k in KEYS} for r in read(REFERENCE)}
    args.scratch.mkdir(parents=True)
    plan = args.scratch/'identity_plan.csv'
    with plan.open('x', encoding='utf-8', newline='') as f:
        f.write('sample,session,block,slot,warmup,population,layout,policy\n')
        for i,n in enumerate((128,512,2048)):
            f.write(f'{i},0,0,{i},0,{n},dense,bounded\n')
    subprocess.run([str(args.binary.resolve()),str(args.scratch),str(plan),'0'], check=True)
    rows = [{k:r[k] for k in KEYS} for r in read(args.scratch/'births.csv')]
    match = len(rows) == 3 and all(r == archive[r['population']] for r in rows)
    receipt = dict(match=match,rows=len(rows),executable_sha256=sha(args.binary),reference_sha256=sha(REFERENCE),
                   scope='Untimed-for-acceptance workload identity smoke. Incidental native phase times stay local.',
                   identities=rows)
    with args.receipt.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(receipt,stream,indent=2)
        stream.write('\n')
    assert match, receipt
    print('Exact protected birth workload identity at all three populations.')


if __name__ == '__main__':
    main()
