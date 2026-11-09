"""Archive all raw S6.3.1 CSV rows with hashes for duplicate native histories/saves."""
import argparse
import gzip
import hashlib
import json
import shutil
from pathlib import Path


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()


def archive(source,target):
    target.mkdir(parents=True,exist_ok=False)
    manifest={}
    for path in sorted(source.rglob('*')):
        if not path.is_file():continue
        rel=path.relative_to(source).as_posix()
        row=dict(bytes=path.stat().st_size,sha256=digest(path))
        if path.suffix in ('.bin','.aw','.sqlite'):
            row['retention']='Local complete native duplicate; immutable hash and reproduction command retained. CSV is selected evidence, not the entire fact journal.'
            if path.suffix=='.bin':
                assert row['bytes']%159==0
                row['facts']=row['bytes']//159
        else:
            dest=target/rel;dest.parent.mkdir(parents=True,exist_ok=True)
            if row['bytes']>1000000:
                dest=Path(str(dest)+'.gz')
                with path.open('rb') as inp,dest.open('wb') as out:
                    with gzip.GzipFile(filename='',fileobj=out,mode='wb',mtime=0) as zipped:shutil.copyfileobj(inp,zipped)
            else:shutil.copyfile(path,dest)
            row.update(archive=dest.relative_to(target).as_posix(),archive_sha256=digest(dest))
        manifest[rel]=row
    (target/'archive.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(target,len(manifest),'files accounted',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('target',type=Path)
    args=p.parse_args();archive(args.source,args.target)
