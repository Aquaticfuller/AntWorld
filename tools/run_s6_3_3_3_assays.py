"""Collect the frozen paired B01 and B02 closure arms with exact event exports."""
import argparse
import gzip
import json
from pathlib import Path
import shutil
import subprocess

from run_s6_3_3_1_assays import ROOT, save, sha
from verify_s6_3_3_reproduction import read

SEEDS = (7, 19, 43, 71, 101, 137)
ARMS = {'b02': 60, 'b01': 18}
BASE = ROOT/'experiments/s6_3_3_3'


def pack(folder):
    files = {}
    for path in sorted(folder.glob('*.csv')):
        original = sha(path)
        if path.name == 'events.csv':
            packed = path.with_suffix('.csv.gz')
            with path.open('rb') as source, packed.open('xb') as out, gzip.GzipFile(
                    fileobj=out, mode='wb', filename='', mtime=0, compresslevel=6) as stream:
                shutil.copyfileobj(source, stream)
            path.unlink()
            path = packed
        files[path.name] = dict(sha256=sha(path), csv_sha256=original, bytes=path.stat().st_size)
    return files


def collect(binary, root):
    root.mkdir(parents=True)
    receipt = dict(executable_sha256=sha(binary), arms=[])
    for arm, count in ARMS.items():
        (root/arm).mkdir()
        for index, seed in enumerate(SEEDS):
            folder = root/arm/str(seed)
            with folder.with_suffix('.log').open('xb') as log:
                subprocess.run([binary, folder, str(index), 'fidelity-closure-'+arm, 'fidelity'],
                               stdout=log, stderr=subprocess.STDOUT, check=True)
            runs = read(folder/'runs.csv')
            assert len(runs)==count and {int(r['seed']) for r in runs}=={seed}
            assert all(r['conserved']==r['continuation_equal']=='1' for r in runs)
            receipt['arms'].append(dict(arm=arm, seed=seed, runs=count, files=pack(folder)))
            save(root/'manifest.json', receipt)
            print(arm, seed, count, flush=True)


def verify(root):
    receipt = json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    assert [(x['arm'], x['seed'], x['runs']) for x in receipt['arms']]==[
        (arm, seed, n) for arm,n in ARMS.items() for seed in SEEDS]
    for item in receipt['arms']:
        folder = root/item['arm']/str(item['seed'])
        for name, info in item['files'].items():
            path = folder/name
            assert path.stat().st_size==info['bytes'] and sha(path)==info['sha256'], path
    print('Verified all 468 frozen biological diagnostic runs.', flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raw', type=Path, default=BASE/'assays')
    p.add_argument('--binary', type=Path)
    args = p.parse_args()
    if args.binary:
        collect(args.binary.resolve(),args.raw.resolve())
    verify(args.raw)


if __name__=='__main__':
    main()
