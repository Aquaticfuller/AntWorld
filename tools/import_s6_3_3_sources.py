"""Import explicitly supplied CC0 Dryad factual tables; never publish paper full text."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
NAMES=['Reversibility_of_worker_effect_3_days.txt','Reversibility_of_worker_effect_2.5_years.txt',
       'Effect_of_worker_cues_wire_mesh_BORIS_output.txt','Effect_of_worker_cues_wire_mesh_design_info.txt',
       'Effect_of_number_of_workers_5_larvae.txt','Effect_of_worker_emergence.txt','Effect_of_worker_presence_and_food.txt']
def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('zip',type=Path); args=p.parse_args()
    directory=ROOT/'experiments/s6_3_3/literature'; directory.mkdir(parents=True,exist_ok=True)
    digest=lambda x:hashlib.sha256(x).hexdigest()
    second='qm114cj' in args.zip.name
    receipt=dict(dataset_doi='10.5061/dryad.qm114cj' if second else '10.5061/dryad.pnvx0k6wd',paper_doi='10.1002/ece3.4475' if second else '10.1111/1365-2435.14536',license='CC0-1.0',
        supplied_archive_sha256=digest(args.zip.read_bytes()),tables=[])
    with zipfile.ZipFile(args.zip) as archive:
        for name in (['Copie+de+Lasius+all+data_check.csv','colony+productivity.csv'] if second else NAMES):
            raw=archive.read(name); text=raw.decode('utf-8-sig').replace('\r\r\n','\n').replace('\r\n','\n')
            rows=list(csv.DictReader(io.StringIO(text),delimiter=',' if second else '\t'))
            target=directory/(('B02_retrieval' if 'all+data' in name else 'B02_productivity')+'.csv' if second else Path(name).stem+'.csv')
            with target.open('w',newline='',encoding='utf-8') as stream:
                writer=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n'); writer.writeheader(); writer.writerows(rows)
            receipt['tables'].append(dict(source_file=name,source_sha256=digest(raw),csv=target.name,csv_sha256=digest(target.read_bytes()),rows=len(rows),
                extraction='REPOSITORY_MEASUREMENT; delimiter/newline normalization only; missing values retained',
                locator=('B02 pp10411-10412 Methods2.2-2.3' if second else 'B01 Methods2.1.4/2.2')+'; Dryad file '+name+'; each original table row retained'))
    (directory/('B02_manifest.json' if second else 'manifest.json')).write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt,indent=2))
if __name__=='__main__': main()
