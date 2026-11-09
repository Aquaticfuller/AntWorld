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
    ['tools/inventory_s6_3_2.py', '--check'],
    ['tools/provenance_s6_3_2.py', '--check'],
    ['tools/literature_measurements_s6_3_2.py', '--check'],
    ['tools/analyze_s6_3_2_biology.py', '--check'],
    ['tools/analyze_s6_3_2_performance.py', '--check'],
    ['tools/analyze_s6_3_2_quiet_completion.py', '--check'],
    ['tools/verify_s6_3_2_sources.py'],
    ['tools/build_s6_3_2_1_atlas.py', '--check'],
    ['tools/build_s6_3_3_evidence.py', '--check'],
    ['tools/analyze_s6_3_3.py', '--check'],
    ['tools/verify_s6_3_3_observer_correction.py', '--check'],
    ['tools/verify_s6_3_3_validation_guard.py', '--check'],
    ['tools/verify_s6_3_3_portable_allocation.py', '--check'],
    ['tools/analyze_s6_3_3_performance.py', '--check'],
    ['tools/verify_s6_3_3_1_archive.py'],
    ['tools/analyze_s6_3_3_1.py', '--density-only', '--density', 'experiments/s6_3_3_1/density.csv', '--check'],
    ['tools/analyze_s6_3_3_1_performance.py', '--check'],
    ['tools/analyze_s6_3_3_1_performance.py', '--raw', 'experiments/s6_3_3_1/performance_reserve',
     '--out', 'experiments/s6_3_3_1/performance_reserve/analysis', '--check'],
]
for check in checks:
    result = subprocess.run([sys.executable, *check], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding='utf-8', errors='replace')
    print(result.stdout, end='', flush=True)
    if result.returncode:
        message = result.stdout[-18000:].replace('%','%25').replace('\r','%0D').replace('\n','%0A')
        print(f'::error title=Evidence audit failed ({check[0]})::{message}', flush=True)
        sys.exit(result.returncode)
