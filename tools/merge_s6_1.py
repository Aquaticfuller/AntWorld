"""Merge complete, disjoint seed intervals without changing any experimental row."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

from archive_s6_1 import archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target', type=Path)
    parser.add_argument('parts', type=Path, nargs='+')
    args = parser.parse_args()
    configs = [(p, json.loads((p/'configuration.json').read_text(encoding='utf-8'))) for p in args.parts]
    configs.sort(key=lambda item: item[1]['first_seed'])
    reference = {k: v for k, v in configs[0][1].items() if k not in ('first_seed', 'seeds')}
    next_seed = 1
    manifest = []
    for path, config in configs:
        assert {k: v for k, v in config.items() if k not in ('first_seed', 'seeds')} == reference
        assert config['first_seed'] == next_seed, 'gap, overlap or incomplete prefix'
        count = config['seeds']
        with (path/'summary.csv').open(encoding='utf-8', newline='') as stream:
            summary = list(csv.DictReader(stream))
        assert {int(r['seed']) for r in summary} == set(range(next_seed, next_seed+count))
        suite = config['suite']
        per_seed = (36 if suite == 'matrix' else 16 if suite == 'integrated' else 8
                    if suite == 'sensitivity' and 'schema' in config else 24 if suite == 'primary' else 6)
        assert len(summary) == count*per_seed, 'incomplete interval'
        manifest.append(dict(directory=path.as_posix(), first_seed=next_seed, seeds=count,
                             summary_rows=len(summary), summary_sha256=hashlib.sha256((path/'summary.csv').read_bytes()).hexdigest()))
        next_seed += count
    maximum = 16 if reference['suite'] in ('matrix', 'sensitivity') else 8 if reference['suite'] == 'long' else 32
    assert next_seed == maximum+1, 'frozen grid incomplete'
    args.target.mkdir(parents=True, exist_ok=False)
    file_sets = [{p.name for p in directory.glob('*.csv')} for directory, _ in configs]
    assert all(s == file_sets[0] for s in file_sets)
    for name in sorted(file_sets[0]):
        header = None
        with (args.target/name).open('w', encoding='utf-8', newline='\n') as output:
            for directory, _ in configs:
                with (directory/name).open(encoding='utf-8', newline=None) as stream:
                    first_line = next(stream)
                    if header is None:
                        header = first_line
                        output.write(header)
                    assert first_line == header, 'schema mismatch'
                    for line in stream:
                        output.write(line)
    configuration = dict(reference, first_seed=1, seeds=maximum)
    (args.target/'configuration.json').write_text(json.dumps(configuration, indent=2)+'\n', encoding='utf-8', newline='\n')
    (args.target/'execution_intervals.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8', newline='\n')
    # Retain binaries in their original directories. An index gives their exact
    # location and checksum; no factual history is moved, erased or resampled.
    facts = []
    for directory, _ in configs:
        for path in sorted(directory.glob('*facts.bin')):
            digest = hashlib.sha256()
            with path.open('rb') as stream:
                while block := stream.read(1048576):
                    digest.update(block)
            size = path.stat().st_size
            assert size % 159 == 0
            facts.append(dict(file=path.as_posix(), bytes=size, facts=size//159, sha256=digest.hexdigest()))
    if facts:
        with (args.target/'canonical_facts.csv').open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, list(facts[0]), lineterminator='\n')
            writer.writeheader()
            writer.writerows(facts)
    print(f'Merged every seed 1..{maximum}: {args.target}; original full histories retained in {len(configs)} intervals')


if __name__ == '__main__':
    main()
