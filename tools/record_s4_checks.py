#!/usr/bin/env python3
"""Record observed CTest log totals; missing or failed execution never becomes PASS."""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--source-commit', required=True)
args = parser.parse_args()
checks = {}
commands = {
    'debug': './tools/build_windows.ps1 -Configuration Debug',
    'release': './tools/build_windows.ps1 -Configuration Release',
    'sanitized': './tools/build_windows.ps1 -Configuration Debug -BuildDirectory build/sanitized -Sanitizers',
    'clean-source': 'git archive SOURCE_COMMIT cpp scenarios; configure and build Release; ctest --output-on-failure',
}
for name, command in commands.items():
    text = (ROOT/'out'/f's4-{name}.log').read_text(encoding='utf-8-sig')
    passed = re.search(r'100% tests passed, 0 tests failed out of (\d+)',text)
    elapsed = re.search(r'Total Test time \(real\) =\s*([\d.]+) sec',text)
    assert passed and elapsed and int(passed[1]) == 89, f'{name}: missing successful 89-test execution'
    checks[name] = dict(status='PASS',tests=int(passed[1]),elapsed_seconds=float(elapsed[1]),command=command)
record = dict(source_commit=args.source_commit,compiler='LLVM-MinGW 20261104 Clang 23.1.5',
              sanitizers='AddressSanitizer and UndefinedBehaviorSanitizer, halt_on_error=1',checks=checks)
(ROOT/'experiments/s4/verification.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(record,indent=2))
