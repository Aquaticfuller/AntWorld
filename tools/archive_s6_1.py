"""Preserve every CSV row, sharding large evidence files below Git's size limit."""
import argparse
import csv
import hashlib
import json
from pathlib import Path


def archive(source, target):
    target.mkdir(parents=True, exist_ok=False)
    manifest = {}
    for path in sorted(source.glob('*')):
        if path.suffix not in ('.csv', '.json'):
            continue
        digest = hashlib.sha256()
        rows, parts = 0, []
        if path.suffix == '.csv' and path.stat().st_size > 40000000:
            directory = target / path.stem
            directory.mkdir()
            output = None
            with path.open(encoding='utf-8', newline=None) as stream:
                header = next(stream)
                digest.update(header.encode())
                size = 40000000
                for line in stream:
                    if size >= 40000000:
                        if output:
                            output.close()
                        part = directory / f'part{len(parts):04d}.csv'
                        parts.append(part.relative_to(target).as_posix())
                        output = part.open('w', encoding='utf-8', newline='\n')
                        output.write(header)
                        size = len(header.encode())
                    output.write(line)
                    size += len(line.encode())
                    digest.update(line.encode())
                    rows += 1
            if output:
                output.close()
        else:
            text = path.read_text(encoding='utf-8')
            (target/path.name).write_text(text, encoding='utf-8', newline='\n')
            digest.update(text.encode())
            parts.append(path.name)
            if path.suffix == '.csv':
                rows = len(text.splitlines())-1
        manifest[path.name] = dict(rows=rows, normalized_lf_sha256=digest.hexdigest(), parts=parts)
    # Complete canonical binary facts remain in the source directory. Hash each
    # stream so the selected CSV projection cannot be mistaken for full history.
    facts = []
    for path in sorted(source.glob('*facts.bin')):
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            while block := stream.read(1048576):
                digest.update(block)
        assert path.stat().st_size % 159 == 0
        facts.append(dict(file=path.name, bytes=path.stat().st_size,
                          facts=path.stat().st_size//159, sha256=digest.hexdigest()))
    if facts:
        with (target/'canonical_facts.csv').open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, list(facts[0]), lineterminator='\n')
            writer.writeheader()
            writer.writerows(facts)
    (target/'archive.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(f'Archived {source}: {sum(x["rows"] for x in manifest.values())} unfiltered CSV rows')


def paths(base, name):
    path = base/f'{name}.csv'
    return [path] if path.exists() else sorted((base/name).glob('part*.csv'))


def rows(base, name):
    header = None
    for path in paths(base, name):
        with path.open(encoding='utf-8', newline='') as stream:
            reader = csv.DictReader(stream)
            if header is None:
                header = reader.fieldnames
            assert reader.fieldnames == header
            yield from reader


def verify(base):
    manifest = json.loads((base/'archive.json').read_text(encoding='utf-8'))
    for name, record in manifest.items():
        digest, count = hashlib.sha256(), 0
        for i, part in enumerate(record['parts']):
            with (base/part).open(encoding='utf-8', newline=None) as stream:
                for index, line in enumerate(stream):
                    if index == 0 and i:
                        continue
                    digest.update(line.encode())
                    count += 1
        assert digest.hexdigest() == record['normalized_lf_sha256'], name
        if name.endswith('.csv'):
            assert count-1 == record['rows'], name


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('target', type=Path)
    args = parser.parse_args()
    archive(args.source, args.target)
    verify(args.target)
