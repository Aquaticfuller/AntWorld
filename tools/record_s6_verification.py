"""Capture actual local CTest outcomes; never synthesize unexecuted passes."""
import csv
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = '3636f22458d0a6fc0c2c5cb22d776dda98d1d6a9'
BUILDS = [('Debug', 'build/debug', 'out/s6-final-debug.log', 124),
          ('Release', 'build/s6-release-final', 'out/s6-final-release.log', 124),
          ('ASan_UBSan', 'build/sanitized', 'out/s6-final-sanitized.log', 124),
          ('Clean_Release', 'build/s6-clean-release', 'out/s6-clean-build.log', 124),
          ('Core_only_Release', 'build/s6-core-only', 'out/s6-core-only.log', 105)]


def main():
    rows, builds = [], []
    for configuration, directory, console, expected in BUILDS:
        text = (ROOT/directory/'Testing/Temporary/LastTest.log').read_text(encoding='utf-8', errors='replace')
        starts = list(re.finditer(r'^\d+/\d+ Testing: ([^\r\n]+)', text, re.MULTILINE))
        assert len(starts) == expected, (configuration, len(starts))
        for i, match in enumerate(starts):
            block = text[match.end():starts[i+1].start() if i+1 < len(starts) else len(text)]
            assert 'Test Passed.' in block and 'Test Failed.' not in block, match.group(1)
            elapsed = float(re.search(r'Test time =\s+([0-9.]+) sec', block).group(1))
            rows.append(dict(configuration=configuration, test=match.group(1), result='Passed',
                             seconds=elapsed, source_commit=SOURCE))
        log = (ROOT/console).read_text(encoding='utf-8', errors='replace')
        assert f'100% tests passed, 0 tests failed out of {expected}' in log
        total = float(re.search(r'Total Test time \(real\) =\s+([0-9.]+) sec', log).group(1))
        builds.append(dict(configuration=configuration, tests=expected, passed=expected, failed=0,
                           total_ctest_seconds=total, source_commit=SOURCE))
    inherited = set()
    with (ROOT/'experiments/s5/executed_tests.csv').open(encoding='utf-8', newline='') as stream:
        inherited = {r['test'] for r in csv.DictReader(stream)}
    assert len(inherited) == 108
    for configuration, _, _, expected in BUILDS:
        names = {r['test'] for r in rows if r['configuration'] == configuration}
        assert len(names) == expected
        if expected == 124:
            assert inherited <= names and all(n.startswith('S6_') for n in names-inherited)
    target = ROOT/'experiments/s6'
    with (target/'executed_tests.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    tests_hash = hashlib.sha256((target/'executed_tests.csv').read_bytes()).hexdigest()
    ci = json.loads((ROOT/'out/s6-source-ci.json').read_text(encoding='utf-8-sig'))
    assert ci['source_commit'] == SOURCE and ci['conclusion'] == 'success'
    assert len(ci['jobs']) == 5 and all(job['conclusion'] == 'success' for job in ci['jobs'])
    hardware = json.loads((ROOT/'out/s6-hardware.json').read_text(encoding='utf-8-sig'))
    # Export English metadata; the original host-localized diagnostics remain in out/.
    hardware['os']['Caption'] = 'Microsoft Windows 11 Home'
    hardware['power_plan'] = 'Balanced (85d583c5-cf2e-4197-80fd-3789a227a72c)'
    report = dict(source_commit=SOURCE, local_builds=builds, test_rows=len(rows), test_rows_sha256=tests_hash,
                  inherited_test_registrations=108, new_test_registrations=16,
                  github_source_ci=ci, hardware=hardware,
                  toolchain=dict(clang='23.1.5', llvm_mingw='20261104-ucrt-x86_64',
                                 cmake='3.31.10', ninja='1.13.2', sqlite='3.54.1'),
                  timing_note='Correctness builds overlapped ecological experiments; CTest elapsed times are not isolated performance benchmarks.',
                  initial_ci_failure=dict(run_id=42529948612,
                      url='https://github.com/Aquaticfuller/AntWorld/actions/runs/42529948612',
                      source_commit='e7c36ef858ea92960381213b280f1e5723eca35e',
                      results={'Ubuntu Debug': 'failure: misleading indentation warning treated as error',
                               'Ubuntu Release': 'failure: misleading indentation warning treated as error',
                               'Windows Debug': 'failure: public annotation truncated; exact test diagnostic unavailable',
                               'Windows Release': 'success', 'Linux ASan/UBSan': 'success'},
                      correction='Reformat new code; freeze scalar contact-work records instead of moving nested debug-STL vectors during injected allocation failure. Improve public failure annotations. All five subsequent jobs passed; the original truncated Windows diagnostic cannot independently establish its exact cause.'))
    (target/'verification.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(f'PASS: captured {len(rows)} executed CTest results and all five successful source CI jobs')


if __name__ == '__main__':
    main()
