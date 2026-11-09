"""Host-only diagnostic scopes; these instrumented timings never enter acceptance ratios."""
import argparse
import json
import subprocess
from pathlib import Path
from archive_s6_3 import digest
from analyze_s6_3 import emit


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--binary',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--kind',choices=('contacts','births'),required=True)
    p.add_argument('--source',required=True)
    p.add_argument('--affinity',default='1')
    args = p.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    rows = []
    for repeat in range(3):
        for layout in (('dense','dispersed') if args.kind=='contacts' else ('dense',)):
            for n in ((128,512,2048) if repeat%2==0 else (2048,512,128)):
                rows.append(dict(sample=len(rows),session=1,block=repeat,slot=len(rows),warmup=0,
                                 population=n,layout=layout,policy='bounded'))
    emit(args.out/'schedule.csv',rows)
    metadata = dict(kind=args.kind,binary_sha256=digest(args.binary),source_commit=args.source,
                    role='Instrumented attribution only; excluded from performance acceptance.',affinity=args.affinity)
    (args.out/'configuration.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    subprocess.run([str(args.binary.resolve()),str(args.out),str(args.out/'schedule.csv'),args.affinity],check=True)


if __name__ == '__main__':
    main()
