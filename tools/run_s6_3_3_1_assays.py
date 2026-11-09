"""Collect the frozen S6.3.3.1 comparison and audit every historical run."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from verify_s6_3_3_reproduction import read, verify

LAYOUTS = ('line', 'mirror', 'split', 'far', 'empty', 'sheltered')
ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8', newline='\n')


def collect(binary, root):
    root.mkdir(parents=True)
    manifest = dict(executable_sha256=sha(binary), batches=[])
    for policy in ('legacy','local'):
        for mode in ('retrieval-line',*(f'holdout-{layout}' for layout in LAYOUTS),'b01'):
            folder = root/policy/mode
            folder.parent.mkdir(exist_ok=True)
            command = [str(binary), str(folder), 'all', mode, policy]
            log = folder.with_suffix('.log')
            with log.open('xb') as stream:
                subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, check=True)
            expected = 40 if mode == 'b01' else 24
            assert len(read(folder/'runs.csv')) == expected, mode
            csv_files = {}
            for path in sorted(folder.glob('*.csv')):
                content_sha = sha(path)
                original = path.name
                if path.name == 'events.csv':
                    packed = path.with_suffix('.csv.gz')
                    with path.open('rb') as source, packed.open('xb') as out, gzip.GzipFile(
                            fileobj=out, filename='', mode='wb', mtime=0) as stream:
                        shutil.copyfileobj(source, stream)
                    path.unlink()
                    path = packed
                csv_files[path.name] = dict(sha256=sha(path), csv_sha256=content_sha, csv_name=original, bytes=path.stat().st_size)
            assert 'events.csv.gz' in csv_files and 'runs.csv' in csv_files
            manifest['batches'].append(dict(policy=policy, mode=mode, runs=expected, files=csv_files))
            save(root/'manifest.json', manifest)
            print(f'{policy}/{mode}: {expected} frozen runs', flush=True)
    assert sum(batch['runs'] for batch in manifest['batches']) == 416


def replay(binary, root, report):
    root.mkdir(parents=True)
    reference = ROOT/'experiments/s6_3_3/raw'
    cases = []
    for mode, n, count in (('primary',12,23),('sensitivity',6,18)):
        for index in range(n):
            ref = reference/(mode+'_'+str((7,19,43,71,101,137,181,223,269,313,367,421)[index]))
            path = root/ref.name
            with path.with_suffix('.log').open('xb') as stream:
                subprocess.run([str(binary),str(path),str(index),mode], stdout=stream, stderr=subprocess.STDOUT, check=True)
            events = verify(path,ref,count)
            cases.append(dict(fixture=ref.name,runs=count,exported_events=events,match=True,
                              event_sha256=sha(path/'events.csv'),historical_archive_sha256=sha(ref/'events.csv.gz')))
            save(report,dict(executable_sha256=sha(binary),cases=cases,matched_runs=sum(c['runs'] for c in cases)))
            print(f'{ref.name}: {count} exact run metrics and {events} events verified', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--historical-report', type=Path)
    args = parser.parse_args()
    if args.historical_report:
        replay(args.binary.resolve(), args.out, args.historical_report)
    else:
        collect(args.binary.resolve(), args.out)


if __name__ == '__main__':
    main()
