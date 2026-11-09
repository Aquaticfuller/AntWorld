"""Record executed local tests and immutable Core/test-source identity."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import shutil

ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'experiments/s6_3_2';OLD='accdb4c7037c792ac55e45277c9a16379828b09c'
def sha(data):return hashlib.sha256(data).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def main():
    records=[]
    for name in git('ls-tree','-r','--name-only',OLD,'cpp/src','cpp/include','cpp/tests').decode().splitlines():
        before=git('show',OLD+':'+name).replace(b'\r\n',b'\n');after=(ROOT/name).read_bytes().replace(b'\r\n',b'\n')
        assert before==after, 'Core or inherited test changed: '+name
        records.append(dict(path=name,normalized_sha256=sha(after)))
    folder=BASE/'verification';folder.mkdir(exist_ok=True);tests=[]
    for config in ('debug','release','sanitized'):
        source=ROOT/f'out/s6_3_2/verification/{config}.txt';content=source.read_text(encoding='utf-8')
        assert '100% tests passed, 0 tests failed out of 162' in content
        start=content.index('Internal ctest changing into directory:')
        log=content[start:];target=folder/f'{config}-ctest.txt';target.write_text(log,encoding='utf-8',newline='\n')
        tests.append(dict(configuration=config,passed=162,total=162,seconds=float(re.search(r'Total Test time \(real\) =\s*([\d.]+)',log)[1]),log=target.relative_to(BASE).as_posix(),sha256=sha(target.read_bytes())))
    source_manifest=BASE/'core_and_tests_identity.json';source_manifest.write_text(json.dumps(dict(baseline=OLD,comparison='All Core headers/sources and inherited test sources; LF-normalized bytes',files=records),indent=2)+'\n',encoding='utf-8')
    metadata=dict(stage='S6.3.2',recorded_utc=datetime.now(timezone.utc).isoformat(),reviewed_baseline=OLD,protocol_freeze='55e6871646f863d027f150911fa6c6f8a3db60c5',comparison_freeze='15e5c40',git_head_at_recording=git('rev-parse','HEAD').decode().strip(),compiler='LLVM-MinGW 20261104 / Clang 23.1.5',cmake='3.31.10',ninja='1.13.2',sqlite='3.54.1',tests=tests,unchanged_core_and_test_files=len(records),diagnostic_trajectories=30,care_worlds=18,legacy_queen_contrasts=18,biological_rule_changes=0,sanitizers_windows='ASan+UBSan; detect_leaks=0:halt_on_error=1; halt_on_error=1:print_stacktrace=1',sanitizers_linux_ci='ASan+UBSan; detect_leaks=1',audit_binary_sha256=sha((ROOT/'build/s6_3_2-release/antworld_s6_3_2_audit.exe').read_bytes()),ci_status='PENDING_PUBLICATION')
    target=BASE/'verification.json'
    if target.exists():
        previous=json.loads(target.read_text())
        for key in ('ci_status','ci_runs'):
            if key in previous:metadata[key]=previous[key]
    target.write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    print(f'PASS: {len(records)} Core and inherited test files unchanged; three executed 162-test suites recorded')
if __name__=='__main__':main()
