#!/usr/bin/env python3
"""Run CTest and expose its failure summary as a GitHub check annotation."""
import subprocess
import sys

result = subprocess.run(
    ['ctest', '--test-dir', 'build/ci', '-C', sys.argv[1], '--output-on-failure'],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace',
)
print(result.stdout, end='')
if result.returncode:
    # Public check annotations remain readable when downloading full logs needs authentication.
    # Some public API clients retain only the first 4096 characters. Put the
    # actual failed tests and their diagnostics first, not thousands of passes.
    lines = result.stdout.splitlines()
    failures = []
    for index, line in enumerate(lines):
        if '***Failed' in line or '***Exception' in line or '***Timeout' in line:
            block = [line]
            for following in lines[index+1:]:
                if following.strip().startswith('Start '):
                    break
                block.append(following)
            failures.append('\n'.join(block))
    detail = '\n\n'.join(failures)[:2800] + '\n\n' + result.stdout[-900:]
    message = detail.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
    print(f'::error title=CTest failure summary::{message}')
sys.exit(result.returncode)
