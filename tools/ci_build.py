#!/usr/bin/env python3
"""Run the CI build and publish bounded compiler diagnostics as annotations."""
import subprocess
import sys

configuration = sys.argv[1] if len(sys.argv) > 1 else 'Debug'
result = subprocess.run(
    ['cmake', '--build', 'build/ci', '--config', configuration, '--parallel', '4'],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace',
)
print(result.stdout, end='')
if result.returncode:
    lines = result.stdout.splitlines()
    selected = set()
    for index, line in enumerate(lines):
        if 'error:' in line or 'warning:' in line or 'fatal error' in line or 'error C' in line or 'warning C' in line:
            selected.update(range(max(0, index-1), min(len(lines), index+5)))
    details = '\n'.join(lines[index] for index in sorted(selected))[-20000:] or '\n'.join(lines[-30:])
    escaped = details.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
    print(f'::error title=C++ build diagnostics::{escaped}')
sys.exit(result.returncode)
