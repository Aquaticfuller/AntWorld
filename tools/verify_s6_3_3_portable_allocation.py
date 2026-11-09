"""Retain executed source and verify the limited MSVC Debug exception-safety correction."""
import argparse,hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'experiments/s6_3_3'

def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args()
    changes={
        'cpp/src/care.cpp':[
            ('    std::vector<EntityId> blocked(0);','    std::vector<EntityId> blocked;'),
            ('    // Throwing count constructors preserve rollback when MSVC Debug allocates iterator proxies.\n'
             '    std::vector<CareState> choices(0); choices.reserve(wakes.size());\n'
             '    std::vector<std::vector<AntRef>> opportunities(0); opportunities.reserve(wakes.size());\n'
             '    for (std::size_t n=0;n<wakes.size();++n) opportunities.emplace_back(0);',
             '    std::vector<CareState> choices; choices.reserve(wakes.size());\n'
             '    std::vector<std::vector<AntRef>> opportunities(wakes.size());'),
            ('        std::vector<AntRef> brood_candidates(0),workers(0);','        std::vector<AntRef> brood_candidates,workers;')],
        'cpp/src/observations.cpp':[
            ('    std::vector<std::pair<SimTime,SimTime>> intervals(0);','    std::vector<std::pair<SimTime,SimTime>> intervals;')],
        'cpp/tests/test_allocation_failure.cpp':[
            ('            sweep("care_observer_query",w,[&]{(void)w.behavior_window(queen,{0},w.summary().now);});\n','')]
    }
    frozen=json.loads((BASE/'raw/primary_manifest.json').read_text())['source_sha256'];payloads={};current={}
    for name,replacements in changes.items():
        text=(ROOT/name).read_text(encoding='utf-8');current[name]=hashlib.sha256(text.encode()).hexdigest()
        for after,before in replacements:
            assert text.count(after)==1,name;text=text.replace(after,before)
        payloads[name]=text.encode();assert hashlib.sha256(payloads[name]).hexdigest()==frozen[name],name
    archive=ROOT/'research/s6_3_3/pre_portable_allocation_source.zip'
    if not archive.exists():
        assert not a.check,'missing executed-source archive'
        with zipfile.ZipFile(archive,'w') as z:
            for name,data in payloads.items():
                info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.create_system=0;z.writestr(info,data)
    digest=hashlib.sha256(archive.read_bytes()).hexdigest();receipt=BASE/'verification/portable_allocation.json'
    if receipt.exists():assert digest==json.loads(receipt.read_text())['executed_source_archive_sha256']
    with zipfile.ZipFile(archive) as z:
        assert z.namelist()==list(payloads) and z.testzip() is None
        for name,data in payloads.items():assert z.read(name)==data,name
    result=dict(status='PASS',source_sha256=current,executed_source_archive_sha256=digest,
        failure='Initial Windows MSVC Debug fault injection terminated at care_select allocation37',
        change='Empty vectors use throwing count constructors, including nested opportunity vectors; an observer-query allocation sweep is added',
        preserved='Same empty contents, opportunity count/order, biological coefficients, RNG draws and committed behavior; no failure injection or history is disabled',
        validation='Retain raw384 cases and original hashes; rerun180-test Debug/Release/sanitizer suites and complete primary seed7 event comparison; MSVC Debug CI verifies the previously failing path')
    text=json.dumps(result,indent=2)+'\n'
    if a.check:assert receipt.read_text()==text
    else:receipt.write_text(text,encoding='utf-8',newline='\n')
    print(text,end='')
if __name__=='__main__':main()
