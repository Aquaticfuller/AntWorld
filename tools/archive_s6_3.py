"""Losslessly retain every S6.3 observation and canonical fact; never filter outcomes."""
import argparse
import gzip
import hashlib
import json
import shutil
from pathlib import Path


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def archive(source, target):
    target.mkdir(parents=True, exist_ok=False)
    manifest = {}
    for path in sorted(source.rglob('*')):
        if not path.is_file() or path.suffix not in ('.csv', '.bin', '.aw', '.sqlite'):
            continue
        relative = path.relative_to(source).as_posix()
        record = dict(bytes=path.stat().st_size, sha256=digest(path))
        if path.suffix in ('.aw', '.sqlite'):
            # The checkpoint and DB duplicate the same complete facts. Keep their
            # verification hashes; reproducible commands reconstruct these views.
            record['retention'] = 'local duplicate state/database; complete facts and observations archived'
        else:
            dest = target/relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            if path.suffix == '.bin' or path.stat().st_size > 1000000:
                dest = Path(str(dest)+'.gz')
                with path.open('rb') as inp, dest.open('wb') as out:
                    with gzip.GzipFile(filename='', mode='wb', fileobj=out, mtime=0) as zipped:
                        shutil.copyfileobj(inp, zipped, 1048576)
            else:
                shutil.copyfile(path, dest)
            record.update(archive=dest.relative_to(target).as_posix(), archive_sha256=digest(dest))
            if path.suffix == '.bin':
                assert record['bytes'] % 159 == 0
                record['facts'] = record['bytes']//159
        manifest[relative] = record
    (target/'archive.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    print(source.name, len(manifest), 'unfiltered files', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('target', type=Path)
    args = parser.parse_args()
    archive(args.source, args.target)


if __name__ == '__main__':
    main()
