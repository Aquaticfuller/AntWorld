#!/usr/bin/env python3
"""Run all repository/evidence audits and expose failed diagnostics in public CI annotations."""
import subprocess
import sys

checks = [
    ['tools/verify_handoff.py'], ['tools/check_repository.py'],
    ['tools/analyze_s2.py', 'experiments/s2', '--check'],
    ['tools/analyze_s2.py', 'experiments/s2_1/ablations', '--check'],
    ['tools/analyze_s2_1.py', '--check'],
    ['tools/analyze_s2.py', 'experiments/s2_2/ablations', '--check'],
    ['tools/analyze_s2_2.py', '--check'], ['tools/analyze_s3.py', '--check'],
    ['tools/analyze_s4.py', '--check'], ['tools/analyze_s5.py', '--check'],
    ['tools/analyze_s6.py', '--check'],
    ['tools/analyze_s6_1_performance.py', '--check'],
    ['tools/analyze_s6_1.py', '--check'],
    ['tools/analyze_s6_1_scarcity.py', '--check'],
    ['tools/analyze_s6_2_performance.py', '--check'],
    ['tools/analyze_s6_2_nutrition.py', '--check'],
    ['tools/analyze_s6_3.py', '--check'],
    ['tools/analyze_s6_3_performance.py', '--check'],
    ['tools/analyze_s6_3_1.py', '--check'],
    ['tools/analyze_s6_3_1_performance.py', '--check'],
]
for check in checks:
    result = subprocess.run([sys.executable, *check], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding='utf-8', errors='replace')
    print(result.stdout, end='', flush=True)
    if result.returncode:
        message = result.stdout[-18000:].replace('%','%25').replace('\r','%0D').replace('\n','%0A')
        print(f'::error title=Evidence audit failed ({check[0]})::{message}', flush=True)
        sys.exit(result.returncode)
