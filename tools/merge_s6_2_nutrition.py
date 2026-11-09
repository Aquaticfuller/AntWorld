"""Merge disjoint fixed seed partitions without dropping or reordering any case."""
import argparse
import csv
import hashlib
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('output', type=Path)
    p.add_argument('parts', type=Path, nargs='+')
    p.add_argument('--source-commit', required=True)
    p.add_argument('--binary', type=Path, required=True)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    cases, provenance = set(), []
    for name in ('summary', 'gifts', 'decisions', 'individuals'):
        header = None
        with (args.output/(name+'.csv')).open('w', encoding='utf-8', newline='') as output:
            for part in args.parts:
                path = part/(name+'.csv')
                provenance.append(dict(source=path.as_posix(), bytes=path.stat().st_size,
                                       sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
                with path.open(encoding='utf-8', newline='') as stream:
                    reader = csv.DictReader(stream)
                    if header is None:
                        header = reader.fieldnames
                        writer = csv.DictWriter(output, header, lineterminator='\n')
                        writer.writeheader()
                    assert header == reader.fieldnames
                    for row in reader:
                        if name == 'summary':
                            key = tuple(row[k] for k in ('seed', 'workers', 'source_protein_ug', 'policy'))
                            assert key not in cases
                            cases.add(key)
                        writer.writerow(row)
    assert cases == {(str(s), str(w), str(p), arm) for s in range(1, 17)
                     for w in (8, 32, 128) for p in (500, 2000) for arm in ('legacy', 'combined')}
    data = dict(source_commit=args.source_commit, scope='ENGINEERING_FIXTURE',
                protocol_commit='3f6d1a9', cases=len(cases), schema=8, physics=9,
                binary_sha256=hashlib.sha256(args.binary.read_bytes()).hexdigest(),
                parts=provenance)
    (args.output/'configuration.json').write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8')
    print(f'PASS {len(cases)} complete cases merged')


if __name__ == '__main__':
    main()
