"""Verify that the opportunity-label correction did not tune biological outcomes."""
import argparse,csv,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'experiments/s6_3_3'
def read(path):
    with path.open(newline='') as f:return list(csv.DictReader(f))
def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args();cases=0;groups=[]
    archive=BASE/'pre_observer_correction'
    for record in json.loads((archive/'archive_manifest.json').read_text()):
        folder=archive/record['directory']
        files=record.get('files',{'receipt.json':record.get('receipt_sha256')})
        for name,digest in files.items():
            assert hashlib.sha256((folder/name).read_bytes()).hexdigest()==digest,(folder,name)
    for receipt in sorted((BASE/'pre_observer_correction').glob('*/receipt.json')):
        old=receipt.parent;new=BASE/'raw'/old.name
        prior=json.loads(receipt.read_text());assert prior['returncode']==0
        for name,digest in prior['files'].items():assert hashlib.sha256((old/name).read_bytes()).hexdigest()==digest
        for name in ['windows.csv','scans.csv']:assert read(old/name)==read(new/name),(old.name,name)
        before,after=read(old/'runs.csv'),read(new/'runs.csv');assert len(before)==len(after)
        for x,y in zip(before,after):
            for field in x:
                if field not in ['advance_ms','checkpoint_ms','restore_ms','checkpoint_bytes','events']:assert x[field]==y[field],(old.name,field)
            cases+=1
        groups.append(old.name)
    assert cases==105
    result=dict(completed_preliminary_cases=cases,groups=groups,unchanged='All scans/window endpoints, biological configurations, paths, contact/retrieval endpoints and conservation/restore flags',excluded_from_comparison='Wall times, event counts and encoded size; observer labels legitimately alter history size',partial_cases='Retained under pre_observer_correction, never declared completed replicates')
    target=BASE/'analysis/observer_correction.json';text=json.dumps(result,indent=2)+'\n'
    if a.check:assert target.read_text()==text
    else:target.write_text(text,encoding='utf-8')
    print(text)
if __name__=='__main__':main()
