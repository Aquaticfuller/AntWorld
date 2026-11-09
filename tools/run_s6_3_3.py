"""Run every frozen S6.3.3 seed; retain raw records and failed attempts without overwrite."""
import argparse, csv, gzip, hashlib, json, pathlib, subprocess, time
ROOT=pathlib.Path(__file__).resolve().parents[1]
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--binary',type=pathlib.Path,required=True)
    p.add_argument('--out',type=pathlib.Path,default=ROOT/'experiments/s6_3_3/raw'); p.add_argument('--mode',choices=['primary','sensitivity'],required=True)
    a=p.parse_args(); a.binary=a.binary.resolve(); a.out.mkdir(parents=True,exist_ok=True)
    manifest=a.out/(a.mode+'_manifest.json')
    frozen=dict(binary_sha256=sha(a.binary),protocol_sha256=sha(ROOT/'docs/52_S6_3_3_Queen_Care_Protocol.md'),
        source_sha256={str(x.relative_to(ROOT)).replace('\\','/'):sha(x) for x in sorted((ROOT/'cpp').rglob('*')) if x.suffix in {'.cpp','.hpp'}},
        mode=a.mode,seeds=[7,19,43,71,101,137,181,223,269,313,367,421][:12 if a.mode=='primary' else 6])
    if manifest.exists(): assert json.loads(manifest.read_text())==frozen,'Frozen executable/source changed'
    else: manifest.write_text(json.dumps(frozen,indent=2)+'\n',encoding='utf-8')
    for index,seed in enumerate(frozen['seeds']):
        directory=a.out/(a.mode+'_'+str(seed)); receipt=directory/'receipt.json'
        if receipt.exists():
            data=json.loads(receipt.read_text()); assert data['returncode']==0,'Prior failure requires explicit review'
            for name,digest in data['files'].items(): assert sha(directory/name)==digest
            continue
        assert not directory.exists(),'Unfinished run retained; use another output directory after diagnosis'
        directory.mkdir(); start=time.perf_counter()
        result=subprocess.run([str(a.binary),str(directory),str(index),a.mode],capture_output=True,text=True)
        (directory/'stdout.txt').write_text(result.stdout+result.stderr,encoding='utf-8')
        files={}
        for path in sorted(directory.glob('*.csv')):
            with path.open(newline='') as f:
                rows=csv.reader(f); n=len(next(rows)); assert all(len(r)==n for r in rows),path
            if path.name=='events.csv':
                target=path.with_suffix('.csv.gz')
                with path.open('rb') as src,target.open('wb') as dst,gzip.GzipFile(filename='',fileobj=dst,mode='wb',mtime=0) as zipped:
                    while chunk:=src.read(1024*1024): zipped.write(chunk)
                assert gzip.decompress(target.read_bytes())==path.read_bytes()
                path.unlink() # Only this newly generated, losslessly archived raw file.
                path=target
            files[path.name]=sha(path)
        receipt.write_text(json.dumps(dict(seed=seed,mode=a.mode,returncode=result.returncode,elapsed_s=time.perf_counter()-start,files=files),indent=2)+'\n',encoding='utf-8')
        print(a.mode,seed,result.returncode,flush=True)
        if result.returncode: raise SystemExit(result.returncode)
if __name__=='__main__': main()
