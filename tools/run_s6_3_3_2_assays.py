"""Run and archive the frozen fidelity assays or replay the complete prior stage."""
import argparse
import gzip
import shutil
import subprocess
from pathlib import Path

from run_s6_3_3_1_assays import LAYOUTS, ROOT, save, sha
from verify_s6_3_3_reproduction import read, verify


ARMS = {
    'b02': 72, 'robustness': 144, 'sensitivity': 180,
    'b01': 40, 'b01-sensitivity': 36, 'integration': 12,
}


def execute(binary, folder, mode, policy):
    folder.parent.mkdir(parents=True, exist_ok=True)
    with folder.with_suffix('.log').open('xb') as stream:
        subprocess.run([binary, folder, 'all', mode, policy], stdout=stream,
                       stderr=subprocess.STDOUT, check=True)


def collect(binary, root):
    root.mkdir(parents=True)
    receipt = dict(executable_sha256=sha(binary), arms=[])
    for arm, expected in ARMS.items():
        folder = root/arm
        execute(binary, folder, 'fidelity-'+arm, 'fidelity')
        profiles = read(folder/'profiles.csv')
        outcomes = read(folder/('ecology.csv' if arm == 'integration' else 'runs.csv'))
        assert len(profiles) == len(outcomes) == expected, arm
        assert len({r['run'] for r in profiles}) == expected, arm
        files = {}
        for path in sorted(folder.glob('*.csv')):
            source_sha = sha(path)
            if path.name == 'events.csv':
                packed = path.with_suffix('.csv.gz')
                with path.open('rb') as source, packed.open('xb') as output, gzip.GzipFile(
                        fileobj=output, mode='wb', filename='', mtime=0, compresslevel=6) as stream:
                    shutil.copyfileobj(source, stream)
                path.unlink()
                path = packed
            files[path.name] = dict(sha256=sha(path), csv_sha256=source_sha, bytes=path.stat().st_size)
        receipt['arms'].append(dict(arm=arm, runs=expected, files=files))
        save(root/'manifest.json', receipt)
        print(f'{arm}: {expected} runs archived', flush=True)


def replay(binary, scratch, report):
    old = ROOT/'experiments/s6_3_3_1/raw'
    receipt = dict(executable_sha256=sha(binary), cases=[])
    for policy in ('legacy', 'local'):
        for mode in ('retrieval-line', *(f'holdout-{layout}' for layout in LAYOUTS), 'b01'):
            case = dict(policy=policy, mode=mode, runs=40 if mode == 'b01' else 24)
            folder = scratch/policy/mode
            try:
                execute(binary, folder, mode, policy)
                events = verify(folder, old/policy/mode, case['runs'])
                case.update(match=True, events=events)
                (folder/'events.csv').unlink()
            except (AssertionError, subprocess.CalledProcessError) as exc:
                case.update(match=False, first_mismatch=str(exc))
            receipt['cases'].append(case)
            save(report, receipt)
            print(case, flush=True)
    assert sum(c['runs'] for c in receipt['cases']) == 416
    assert all(c['match'] for c in receipt['cases']), 'see replay receipt'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('binary', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--replay-report', type=Path)
    args = p.parse_args()
    if args.replay_report:
        replay(args.binary.resolve(), args.output.resolve(), args.replay_report)
    else:
        collect(args.binary.resolve(), args.output.resolve())


if __name__ == '__main__':
    main()
