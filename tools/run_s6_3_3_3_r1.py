"""Collect isolated R1 ecology cases while retaining every completed and failed fact."""
import argparse
import csv
import gzip
import hashlib
import itertools
import shutil
import sqlite3
import struct
import subprocess
import time
from pathlib import Path

from analyze_s6_3_3_3_ecology import split_facts
from run_s6_3_3_3_assays import read, save, sha

SEEDS = (7, 19, 43)
POPULATIONS = (4, 16)
SPACES = ('coarse', 'fine', 'chamber', 'underground')
FOODS = ('balanced', 'empty')
POLICIES = ('control', 'care')
TABLES = ('runs', 'days', 'individuals', 'timings', 'abort')


def planned():
    for food in FOODS:
        for space, workers, seed, policy in itertools.product(SPACES, POPULATIONS, SEEDS, POLICIES):
            yield f'{seed}_{workers}_{space}_{food}_{policy}', space


def pack_canonical(source, target, count):
    digest = hashlib.sha256()
    index = 0
    with target.open('xb') as result, gzip.GzipFile(
            fileobj=result, mode='wb', filename='', mtime=0, compresslevel=4) as stream:
        for index, record in enumerate(source, 1):
            assert struct.unpack_from('<Q', record)[0] == index
            length = struct.pack('<I', len(record))
            digest.update(length)
            digest.update(record)
            stream.write(length)
            stream.write(record)
    assert index == count
    return dict(raw_sha256=digest.hexdigest(), sha256=sha(target), rows=count,
                bytes=target.stat().st_size)


def file_records(source):
    with source.open('rb') as stream:
        while size := stream.read(4):
            length, = struct.unpack('<I', size)
            assert length in (159, 210)
            record = stream.read(length)
            assert len(record) == length
            yield record


def db_records(source):
    with sqlite3.connect(source.resolve().as_uri() + '?mode=ro', uri=True) as database:
        for (record,) in database.execute('SELECT payload FROM events ORDER BY world,id'):
            yield record


def save_tables(source, target, names=None):
    for name in TABLES:
        path = source / f'{name}.csv'
        if not path.is_file():
            continue
        if names is None:
            shutil.copyfile(path, target / path.name)
            continue
        with path.open('rb') as records:
            header = next(records)
            for key, lines in itertools.groupby(records, lambda line: line.split(b',', 1)[0]):
                run = key.decode('ascii')
                if run in names:
                    with (target / run / path.name).open('xb') as out:
                        out.write(header)
                        out.writelines(lines)


def record_attempt(folder, name, state):
    state['run'] = name
    state['files'] = {p.name: sha(p) for p in sorted(folder.iterdir()) if p.is_file()}
    save(folder / 'attempt.json', state)


def import_batch(source, target, spaces):
    """Reuse only the completed prefix of a frozen batch."""
    finished = {r['run']: r for r in read(source / 'runs.csv')
                if r['space'] in spaces and not (target / r['run']).exists()}
    if not finished:
        return
    staging = target / ('import-' + source.name)
    staging.mkdir()
    # The last partial case is deliberately ignored here and will get its own isolated attempt.
    with (source / 'events.csv').open('rb') as raw, (staging / 'events.csv').open('xb') as selected:
        selected.write(next(raw))
        for key, lines in itertools.groupby(raw, lambda line: line.split(b',', 1)[0]):
            if key.decode('ascii') in finished:
                selected.writelines(lines)
    packed = split_facts(staging / 'events.csv', staging, {k: int(v['events']) for k, v in finished.items()})
    for name in finished:
        (target / name).mkdir()
    save_tables(source, target, finished)
    for name, row in finished.items():
        folder = target / name
        (staging / f'{name}.csv.gz').replace(folder / 'events.csv.gz')
        canonical = pack_canonical(db_records(source / f'{name}.sqlite'), folder / 'events.facts.gz',
                                   int(row['events']))
        record_attempt(folder, name, dict(status='COMPLETE', origin=source.name, facts=packed[name],
                                          canonical=canonical))
    (staging / 'events.csv').unlink()
    staging.rmdir()


def run_case(binary, scratch, target, name, space, remove_store):
    work = scratch / name
    folder = target / name
    assert not work.exists() and not folder.exists(), name
    mode = 'r1-depot' if space == 'underground' else 'r1-matrix'
    log = scratch / f'{name}.log'
    start = time.monotonic()
    with log.open('xb') as stream:
        result = subprocess.run([binary, work, mode, name], stdout=stream, stderr=subprocess.STDOUT)
    elapsed = time.monotonic() - start
    rows = read(work / 'runs.csv')
    aborted = read(work / 'abort.csv')
    state = dict(status='COMPLETE' if not result.returncode else 'FAILED',
                 origin='isolated', exit_code=result.returncode, elapsed_s=round(elapsed, 3),
                 executable_sha256=sha(binary))
    if state['status'] == 'COMPLETE':
        assert len(rows) == 1 and rows[0]['run'] == name and not aborted
    if aborted:
        assert len(aborted) == 1 and not rows and result.returncode
        state.update(failure_stage=aborted[0]['stage'], last_full_day=int(aborted[0]['last_full_day']))
    folder.mkdir()
    save_tables(work, folder)
    shutil.copyfile(log, folder / 'console.log')
    expected = ({name: int(rows[0]['events'])} if rows else
                {name: int(aborted[0]['committed_events'])} if aborted else {})
    packed = split_facts(work / 'events.csv', folder, expected)
    if packed:
        assert set(packed) == {name}
        (folder / f'{name}.csv.gz').replace(folder / 'events.csv.gz')
        state['facts'] = packed[name]
        state['canonical'] = pack_canonical(file_records(work / 'events.facts'), folder / 'events.facts.gz',
                                            packed[name]['rows'])
    record_attempt(folder, name, state)
    if remove_store and packed:
        # Remove only this collector's duplicates after independent byte-level archive verification.
        with gzip.open(folder / 'events.facts.gz', 'rb') as stream:
            assert hashlib.file_digest(stream, 'sha256').hexdigest() == sha(work / 'events.facts')
        if state['status'] == 'COMPLETE':
            store = work / f'{name}.sqlite'
            assert store.resolve().parent == work.resolve() and store.is_file() and not store.is_symlink()
            store.unlink()
        (work / 'events.facts').unlink()
        (work / 'events.csv').unlink()
    print(name, state['status'], state.get('facts', {}).get('rows', 0), state['elapsed_s'], flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary', type=Path)
    parser.add_argument('scratch', type=Path)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--import-batch', type=Path, action='append', default=[])
    parser.add_argument('--select', choices=('all', 'import-only', 'balanced', 'planar-empty', 'mixed-empty'), default='all')
    parser.add_argument('--spaces', choices=SPACES, nargs='+', default=SPACES)
    parser.add_argument('--workers', type=int, choices=POPULATIONS, nargs='+', default=POPULATIONS)
    parser.add_argument('--min-free-gib', type=float, default=9)
    parser.add_argument('--remove-verified-duplicate', action='store_true')
    args = parser.parse_args()
    args.scratch.mkdir(parents=True, exist_ok=True)
    args.archive.mkdir(parents=True, exist_ok=True)
    for folder in args.import_batch:
        import_batch(folder, args.archive, args.spaces)
    if args.select == 'import-only':
        return
    for name, space in planned():
        if space not in args.spaces or int(name.split('_')[1]) not in args.workers:
            continue
        if args.select == 'balanced' and '_balanced_' not in name:
            continue
        if args.select == 'planar-empty' and (space not in ('coarse', 'fine') or '_empty_' not in name):
            continue
        if args.select == 'mixed-empty' and (space not in ('chamber', 'underground') or '_empty_' not in name):
            continue
        if (args.archive / name / 'attempt.json').exists():
            continue
        if shutil.disk_usage(args.scratch).free < args.min_free_gib * 1024**3:
            raise RuntimeError('Insufficient scratch storage for the next isolated attempt')
        run_case(args.binary.resolve(), args.scratch.resolve(), args.archive, name, space,
                 args.remove_verified_duplicate)


if __name__ == '__main__':
    main()
