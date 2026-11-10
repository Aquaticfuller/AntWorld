"""Separate the care workload phases and test reversible block archives of the original facts."""
import argparse
import hashlib
import json
import lzma
from pathlib import Path
import shutil
import struct
import time
import zlib

from analyze_s6_3_3 import q
from analyze_s6_3_3_2 import group, read, write
from run_s6_3_3_3_assays import BASE, save, sha

RECORDS_PER_BLOCK = 4096
PHASES = ('setup_ms','advance_ms','checkpoint_ms','restore_ms','sqlite_save_ms','sqlite_load_ms','journal_encode_ms',
          'rss_bytes','process_peak_bytes')
IDENTITY = ('seed','sim_ms','opportunities','started','completed','transfers','placements','switches','facts',
            'journal_bytes','checkpoint_bytes','sqlite_bytes','state_hash','trace_hash','restore_equal','conserved')
CODECS = {
    'zlib6':(lambda raw:zlib.compress(raw,level=6),zlib.decompress),
    'lzma0':(lambda raw:lzma.compress(raw,preset=0),lzma.decompress),
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def timed(operation, arg):
    start = time.perf_counter_ns()
    result = operation(arg)
    return result, time.perf_counter_ns()-start


def record_blocks(stream):
    count, raw = 0, bytearray()
    while prefix := stream.read(4):
        assert len(prefix)==4
        size, = struct.unpack('<I',prefix)
        assert size in (159,210), size
        record = stream.read(size)
        assert len(record)==size
        raw.extend(prefix)
        raw.extend(record)
        count += 1
        if count==RECORDS_PER_BLOCK:
            yield bytes(raw)
            raw, count = bytearray(), 0
    if count:
        yield bytes(raw)


def check_records(raw, first):
    at, expected = 0, first
    while at<len(raw):
        size, identifier = struct.unpack_from('<IQ',raw,at)
        assert identifier==expected
        assert size in (159,210)
        expected += 1
        at += 4+size
    assert at==len(raw)
    return expected-first


def compression(source, archives, samples):
    summary, index = [], []
    for row in samples:
        label = '_'.join(row[key] for key in ('mode','layout','workers'))
        path = source/f'{label}.facts'
        counts = {codec:dict(raw_bytes=0, packed_bytes=0, encode_ns=0, decode_ns=0, blocks=0)
                  for codec in CODECS}
        identifier, offset = 1, 0
        original_hash = hashlib.sha256()
        with path.open('rb') as stream, (archives/f'{label}.facts.zlib').open('xb') as packed:
            for block_number, raw in enumerate(record_blocks(stream)):
                n = check_records(raw,identifier)
                original_hash.update(raw)
                for codec,(encode,decode) in CODECS.items():
                    block, encode_ns = timed(encode,raw)
                    decoded, decode_ns = timed(decode,block)
                    assert decoded==raw
                    stats = counts[codec]
                    if codec=='zlib6':
                        index.append(dict(case=label, block=block_number, first_id=identifier, last_id=identifier+n-1,
                                          raw_offset=offset, raw_bytes=len(raw), packed_offset=stats['packed_bytes'],
                                          packed_bytes=len(block), raw_sha256=digest(raw)))
                        packed.write(block)
                    stats['raw_bytes'] += len(raw)
                    stats['packed_bytes'] += len(block)
                    stats['encode_ns'] += encode_ns
                    stats['decode_ns'] += decode_ns
                    stats['blocks'] += 1
                identifier += n
                offset += len(raw)
        assert identifier-1==int(row['facts']) and offset==int(row['journal_bytes'])
        assert original_hash.hexdigest()==sha(path)
        for codec,stats in counts.items():
            summary.append(dict(case=label, codec=codec, facts=identifier-1, **stats,
                                raw_to_packed=stats['raw_bytes']/stats['packed_bytes'],
                                raw_sha256=original_hash.hexdigest()))
    return summary, index


def decode_archive(path, index, target=None, deep=True):
    raw_hash, count, last = hashlib.sha256(), 0, 0
    seek_samples = []
    with path.open('rb') as packed:
        for row in index:
            assert int(row['first_id'])==last+1
            last = int(row['last_id'])
            if not deep and row is not index[0] and row is not index[-1]:
                continue
            start = time.perf_counter_ns()
            packed.seek(int(row['packed_offset']))
            raw = zlib.decompress(packed.read(int(row['packed_bytes'])))
            seek_samples.append(time.perf_counter_ns()-start)
            assert len(raw)==int(row['raw_bytes']) and digest(raw)==row['raw_sha256']
            n = check_records(raw,int(row['first_id']))
            assert n==last-int(row['first_id'])+1
            count += n
            raw_hash.update(raw)
            if target is not None:
                target.write(raw)
    return raw_hash.hexdigest(),count,seek_samples


def stats(rows, fields):
    return {f'{field}_{tag}':q([float(r[field]) for r in rows],p)
            for field in fields for tag,p in (('p50',.50),('p95',.95),('p99',.99))}


def compare(native, profile, dest):
    inputs = {'unprofiled':native,'profiled':profile}
    measurements, scopes = [], []
    for name, source in inputs.items():
        measurements += [dict(build=name,**r) for r in read(source/'samples.csv')]
        scopes += [dict(build=name,**r) for r in read(source/'profile.csv')]
    cases = group(measurements,lambda r:(r['mode'],r['layout'],int(r['workers'])))
    assert len(cases)==12 and len(measurements)==96
    summary, profile_summary, representatives = [], [], []
    for (mode,layout,n), rows in sorted(cases.items()):
        identities = {tuple(r[k] for k in IDENTITY) for r in rows}
        assert len(identities)==1 and len(rows)==8, (mode,layout,n)
        identity = dict(zip(IDENTITY,next(iter(identities))))
        metadata = dict(mode=mode,layout=layout,workers=n)
        representatives.append(next(r for r in rows if r['build']=='unprofiled' and r['replicate']=='1'))
        for build in inputs:
            selected = [r for r in rows if r['build']==build and r['warmup']=='0']
            assert len(selected)==3 and all(r['profiled']==str(int(build=='profiled')) for r in selected)
            summary.append(dict(build=build, **metadata, n=len(selected), **identity, **stats(selected,PHASES)))
            if build=='profiled':
                ids = {r['sample'] for r in selected}
                matching = group((r for r in scopes if r['build']==build and r['sample'] in ids),
                                 lambda r:(r['phase'],r['category']))
                for (phase,category), values in sorted(matching.items()):
                    assert len(values)==3
                    profile_summary.append(dict(**metadata, phase=phase, category=category,
                                                **stats(values,('calls','inclusive_ns','exclusive_ns','work'))))
    write(dest/'samples.csv',measurements)
    write(dest/'profile.csv',scopes)
    write(dest/'summary.csv',summary)
    write(dest/'profile_summary.csv',profile_summary)
    return representatives


def analyze(native, profile, dest, system, persistence):
    dest.mkdir(parents=True)
    archives = dest/'facts'
    archives.mkdir()
    reps = compare(native,profile,dest)
    packed, index = compression(native,archives,reps)
    verify_rows = []
    for label,blocks in sorted(group(index,lambda r:r['case']).items()):
        path = archives/f'{label}.facts.zlib'
        raw_hash,count,ns = decode_archive(path,blocks)
        reference = next(r for r in packed if r['case']==label and r['codec']=='zlib6')
        assert raw_hash==reference['raw_sha256'] and count==reference['facts']
        verify_rows.append(dict(case=label, facts=count, raw_sha256=raw_hash, archive_sha256=sha(path),
                                blocks=len(ns), seek_read_decode_p50_ns=q(ns,.50),
                                seek_read_decode_p95_ns=q(ns,.95), seek_read_decode_p99_ns=q(ns,.99)))
    write(dest/'archive_compression.csv',packed)
    write(dest/'archive_index.csv',index)
    write(dest/'archive_seek.csv',verify_rows)
    if persistence:
        replays = read(persistence)
        assert len(replays)==len(reps)
        cases = {'_'.join(r[k] for k in ('mode','layout','workers')):r for r in reps}
        for replay in replays:
            ref = cases[replay['case']]
            assert all(replay[k]==ref[k] for k in ('facts','state_hash','trace_hash','sqlite_bytes','restore_equal'))
        shutil.copyfile(persistence,dest/'persistence.csv')
    if system:
        shutil.copyfile(system,dest/'system.json')
    manifest = {str(p.relative_to(dest).as_posix()):sha(p) for p in sorted(dest.rglob('*')) if p.is_file()}
    save(dest/'manifest.json',manifest)


def verify(dest, extract=None, deep=False):
    manifest = json.loads((dest/'manifest.json').read_text(encoding='utf-8'))
    for file, expected in manifest.items():
        assert sha(dest/file)==expected, file
    receipts = {r['case']:r for r in read(dest/'archive_seek.csv')}
    if extract:
        extract.mkdir(parents=True)
    for label,index in sorted(group(read(dest/'archive_index.csv'),lambda r:r['case']).items()):
        path = dest/'facts'/f'{label}.facts.zlib'
        if extract:
            with (extract/f'{label}.facts').open('xb') as target:
                raw_hash,count,_ = decode_archive(path,index,target)
        else:
            raw_hash,count,_ = decode_archive(path,index,deep=deep)
        if deep or extract:
            assert raw_hash==receipts[label]['raw_sha256'] and count==int(receipts[label]['facts'])
    print('Verified 96 native samples and 12 indexed fact archives.')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--native',type=Path)
    p.add_argument('--profile',type=Path)
    p.add_argument('--system',type=Path)
    p.add_argument('--persistence',type=Path)
    p.add_argument('--out',type=Path,default=BASE/'density')
    p.add_argument('--deep',action='store_true')
    p.add_argument('--extract',type=Path)
    a = p.parse_args()
    if a.native:
        assert a.profile
        analyze(a.native,a.profile,a.out,a.system,a.persistence)
    verify(a.out,a.extract,a.deep)


if __name__=='__main__':
    main()
