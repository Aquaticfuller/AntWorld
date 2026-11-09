"""Losslessly archive only interrupted preliminary CSVs; preserve completed receipts."""
import gzip,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'experiments/s6_3_3/pre_observer_correction'
def main():
    records=[]
    for folder in sorted(BASE.glob('*_*')):
        if not folder.is_dir():continue
        receipt=folder/'receipt.json'
        if receipt.exists():
            data=json.loads(receipt.read_text());assert data['returncode']==0
            for name,digest in data['files'].items():assert hashlib.sha256((folder/name).read_bytes()).hexdigest()==digest
            records.append(dict(directory=folder.name,status='COMPLETED_PRELIMINARY',receipt_sha256=hashlib.sha256(receipt.read_bytes()).hexdigest()));continue
        path=folder/'events.csv';target=folder/'events.csv.gz'
        if path.exists():
            if target.exists():
                partial=folder/'events.csv.gz.incomplete';assert not partial.exists()
                target.rename(partial) # Preserve the gzip stream interrupted during suspension.
            raw=path.read_bytes()
            with target.open('wb') as f,gzip.GzipFile(fileobj=f,filename='',mode='wb',mtime=0) as z:z.write(raw)
            assert gzip.decompress(target.read_bytes())==raw
            path.unlink() # Only this newly losslessly archived interrupted event file.
        records.append(dict(directory=folder.name,status='INTERRUPTED; NOT A COMPLETED REPLICATE',files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir() if p.is_file()}))
    (BASE/'archive_manifest.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8');print(json.dumps(records))
if __name__=='__main__':main()
