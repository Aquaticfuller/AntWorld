"""Archive every admission/timing row; keep localized HWiNFO originals private."""
import argparse
import csv
from datetime import datetime, timezone, timedelta
import hashlib
import io
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
def sha(data): return hashlib.sha256(data).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--destination',type=Path,default=ROOT/'experiments/s6_3_2/performance');args=p.parse_args()
    mapping=json.loads((ROOT/'experiments/s6_2/hwinfo_columns_v2.json').read_text())
    for kind in ('contacts','births'):
        source=args.source/kind
        if not source.exists():continue
        target=args.destination/kind;target.mkdir(parents=True,exist_ok=True)
        conf=json.loads((source/'configuration.json').read_text());zone=timezone(timedelta(minutes=conf['before']['timezone_minutes']))
        shutil.copyfile(source/'configuration.json',target/'configuration.json')
        for folder in sorted(source.glob('session*')):
            dest=target/folder.name;dest.mkdir(exist_ok=True)
            for path in folder.iterdir():
                if path.suffix in ('.json','.csv','.log'):shutil.copyfile(path,dest/path.name)
            if not (folder/'receipt.json').exists():continue
            receipt=json.loads((folder/'receipt.json').read_text());raw=(folder/'hwinfo_after.raw').read_bytes()
            reader=csv.reader(io.StringIO(raw.decode('utf-8-sig')));fields=next(reader)
            assert sha(json.dumps(fields,ensure_ascii=True).encode())==mapping['source_header_sha256']
            rows=[];incomplete=0
            for number,row in enumerate(reader,2):
                if not row or row[0]=='Date':continue
                if len(row)!=len(fields):incomplete+=1;continue
                at=datetime.strptime(row[0]+' '+row[1],'%d.%m.%Y %H:%M:%S.%f').replace(tzinfo=zone)
                ns=int(at.timestamp()*1e9)
                if not receipt['started_utc_ns']-3e9<=ns<=receipt['ended_utc_ns']+3e9:continue
                record=dict(utc_ns=ns,source_line=number)
                for item in mapping['columns']:
                    v=row[item['index']];record[item['label']]=1 if v in ('Yes',chr(0x662f)) else 0 if v in ('No',chr(0x5426)) else float(v) if v else ''
                rows.append(record)
            assert rows
            with (dest/'hwinfo.csv').open('w',encoding='utf-8',newline='') as f:
                w=csv.DictWriter(f,list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
            provenance=dict(source_prefix_bytes=len(raw),source_prefix_sha256=sha(raw),mapping_sha256=sha(json.dumps(mapping,sort_keys=True).encode()),retained_rows=len(rows),incomplete_rows=incomplete,timezone_offset_minutes=conf['before']['timezone_minutes'],selection='Every sensor row in run interval plus 3 s bracketing; no value filtering')
            (dest/'hwinfo_provenance.json').write_text(json.dumps(provenance,indent=2)+'\n',encoding='utf-8')
            print(kind,folder.name,len(rows),'sensor rows; all raw timing rows retained')
if __name__=='__main__':main()
