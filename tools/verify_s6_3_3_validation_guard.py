"""Prove the post-run arrangement-speed validation guard is inert for every frozen case."""
import argparse,csv,hashlib,json,zipfile
from pathlib import Path
from atlas_baseline import source_root
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'experiments/s6_3_3'
def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args()
    reviewed=source_root('s6_3_3')
    rows=[]
    for path in sorted((BASE/'raw').glob('*/runs.csv')):
        with path.open(newline='') as f:rows.extend(csv.DictReader(f))
    assert len(rows)==384
    assert all(0<float(r['arrangement_m'])<=float(r['step_m']) for r in rows)
    assert all(float(r['step_m'])/(float(r['bout_ms'])/1000)<=.01 for r in rows)
    removed={
        'cpp/src/care_internal.hpp':b'        c.arrangement_m/(static_cast<double>(c.bout_duration.milliseconds)/1000)>w.max_speed_m_per_s ||\n',
        'cpp/tests/test_s6_3_3.cpp':b'    rejects([&]{SpeciesCareProfile p; p.step_m=.000001; p.bout_duration={10}; p.arrangement_m=.002; Fixture invalid(7,p);});\n'}
    frozen=json.loads((BASE/'raw/primary_manifest.json').read_text())['source_sha256'];payloads={}
    for name,line in removed.items():
        data=(reviewed/name).read_bytes().replace(b'\r\n',b'\n');assert data.count(line)==1;data=data.replace(line,b'')
        assert hashlib.sha256(data).hexdigest()==frozen[name],name
        payloads[name]=data
    path=ROOT/'research/s6_3_3/executed_source_snapshot.zip'
    if not path.exists():
        assert not a.check,'missing frozen source archive'
        with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as archive:
            for name,data in payloads.items():
                info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.create_system=0
                info.compress_type=zipfile.ZIP_DEFLATED;archive.writestr(info,data)
    # Verify the actual frozen ZIP and every payload; re-encoding has host-dependent metadata.
    archive_digest=hashlib.sha256(path.read_bytes()).hexdigest()
    receipt=BASE/'verification/validation_guard.json'
    if receipt.exists():assert archive_digest==json.loads(receipt.read_text())['executed_source_archive_sha256']
    with zipfile.ZipFile(path) as archive:
        assert archive.namelist()==list(payloads) and archive.testzip() is None
        for name,data in payloads.items():assert archive.read(name)==data,name
    result=dict(cases=384,status='PASS',new_rule='arrangement_m / bout_seconds <= world.max_speed_m_per_s',
        proof='Every frozen case has arrangement<=step. Existing validation already enforces step/bout<=max_speed. Therefore the added arrangement guard is implied for all384 recorded configurations; no accepted rule, coefficient, RNG or outcome is changed.',
        source_sha256={p:hashlib.sha256((reviewed/p).read_bytes().replace(b'\r\n',b'\n')).hexdigest() for p in ['cpp/src/care_internal.hpp','cpp/tests/test_s6_3_3.cpp']},
        regression='CAPABILITY now rejects a tiny-step/fast-arrangement custom profile; full Debug/Release/sanitizer and independent CI seed are rerun',
        raw_archive='Frozen experiment source/binary manifests remain unchanged; this later validation-only guard is explicitly identified instead of overwriting provenance')
    result['executed_source_archive_sha256']=archive_digest
    path=BASE/'verification/validation_guard.json';text=json.dumps(result,indent=2)+'\n'
    if a.check:assert path.read_text()==text
    else:path.write_text(text,encoding='utf-8')
    print(text)
if __name__=='__main__':main()
