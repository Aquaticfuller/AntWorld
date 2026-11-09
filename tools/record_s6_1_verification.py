"""Capture completed S6.1 CTest logs and observed GitHub jobs, never assumed passes."""
import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDS = [('Debug', 's6_1-debug', 135), ('Release', 's6_1-release', 135),
          ('ASan_UBSan', 's6_1-sanitized', 135), ('Clean_Release', 's6_1-clean-release', 135),
          ('Core_only_Release', 's6_1-core-only', 115)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--ci', type=Path, required=True)
    args = parser.parse_args()
    rows, builds = [], []
    for configuration, directory, expected in BUILDS:
        path = ROOT/'build'/directory/'Testing/Temporary/LastTest.log'
        text = path.read_text(encoding='utf-8', errors='replace')
        starts = list(re.finditer(r'^\d+/\d+ Testing: ([^\r\n]+)', text, re.MULTILINE))
        assert len(starts) == expected, (configuration, len(starts))
        for i, match in enumerate(starts):
            block = text[match.end():starts[i+1].start() if i+1 < len(starts) else len(text)]
            assert 'Test Passed.' in block and 'Test Failed.' not in block, match.group(1)
            elapsed = float(re.search(r'Test time =\s+([0-9.]+) sec', block).group(1))
            rows.append(dict(configuration=configuration, test=match.group(1), result='Passed',
                             seconds=elapsed, source_commit=args.source))
        console = ROOT/'out'/f'{directory}-tests.log'
        log = console.read_text(encoding='utf-8', errors='replace')
        assert f'100% tests passed, 0 tests failed out of {expected}' in log
        elapsed = float(re.search(r'Total Test time \(real\) =\s+([0-9.]+) sec', log).group(1))
        builds.append(dict(configuration=configuration, tests=expected, passed=expected, failed=0,
                           total_ctest_seconds=elapsed, source_commit=args.source,
                           last_test_log_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    with (ROOT/'experiments/s6/executed_tests.csv').open(encoding='utf-8', newline='') as stream:
        inherited = {r['test'] for r in csv.DictReader(stream)}
    assert len(inherited) == 124
    for configuration, _, expected in BUILDS:
        names = {r['test'] for r in rows if r['configuration'] == configuration}
        assert len(names) == expected
        if expected == 135:
            assert inherited <= names and all(n.startswith('S6_1_') for n in names-inherited)
    target = ROOT/'experiments/s6_1'
    with (target/'executed_tests.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    ci = json.loads(args.ci.read_text(encoding='utf-8-sig'))
    assert ci['source_commit'] == args.source and ci['conclusion'] == 'success'
    assert len(ci['jobs']) == 5 and all(j['conclusion'] == 'success' for j in ci['jobs'])
    hardware = json.loads((ROOT/'experiments/s6/verification.json').read_text(encoding='utf-8'))['hardware']
    report = dict(source_commit=args.source, local_builds=builds, test_rows=len(rows),
                  test_rows_sha256=hashlib.sha256((target/'executed_tests.csv').read_bytes()).hexdigest(),
                  inherited_test_registrations=124, new_test_registrations=11, github_source_ci=ci,
                  hardware=hardware, toolchain=dict(clang='23.1.5', llvm_mingw='20261104-ucrt-x86_64',
                      cmake='3.31.10', ninja='1.13.2', sqlite='3.54.1'),
                  timing_note='Correctness builds may overlap ecology; their elapsed time is not an isolated benchmark.',
                  initial_ci_failure=dict(run_id=42544150073, source_commit='d60c8ff1e9d8eaa331b708439d149721325d9679',
                    url='https://github.com/Aquaticfuller/AntWorld/actions/runs/42544150073',
                    correction='Add explicit algorithm include and avoid range-loop pair copy in observer executable; no simulation rule changed.',
                    corrected_run=42544457489, corrected_all_five_jobs='success'))
    (target/'verification.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(f'PASS: {len(rows)} actual CTest executions, 124 inherited registrations, five successful CI jobs')


if __name__ == '__main__':
    main()
