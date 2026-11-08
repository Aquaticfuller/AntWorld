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
    message = result.stdout[-24000:].replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
    print(f'::error title=CTest failure summary::{message}')
sys.exit(result.returncode)
