"""Record completed local tests and optional observed CI results, without inferring passes."""
import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDS = [('Debug', 'debug', 137), ('Release', 'release', 137),
          ('ASan_UBSan', 'sanitized', 137), ('Clean_Release', 'clean-release', 137),
          ('Core_only_Release', 'core-only', 117)]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', required=True)
    p.add_argument('--ci', type=Path)
    args = p.parse_args()
    tests, builds = [], []
    inherited = {r['test'] for r in csv.DictReader((ROOT/'experiments/s6_1/executed_tests.csv').open())}
    assert len(inherited) == 135
    for configuration, tag, count in BUILDS:
        path = ROOT/f'build/s6_2-{tag}/Testing/Temporary/LastTest.log'
        # CTest's localized date banner can use the Windows ANSI code page;
        # test names/results below are ASCII. The raw-byte hash is retained.
        text = path.read_text(encoding='utf-8', errors='replace')
        starts = list(re.finditer(r'^\d+/\d+ Testing: ([^\r\n]+)', text, re.MULTILINE))
        assert len(starts) == count
        names = set()
        for i, match in enumerate(starts):
            block = text[match.end():starts[i+1].start() if i+1 < len(starts) else len(text)]
            assert 'Test Passed.' in block and 'Test Failed.' not in block
            names.add(match.group(1))
            tests.append(dict(configuration=configuration, test=match.group(1), result='Passed',
                              seconds=float(re.search(r'Test time =\s+([0-9.]+) sec', block).group(1)),
                              source_commit=args.source))
        if count == 137:
            assert inherited <= names and names-inherited == {'S6_2_NUTRITION_OBSERVER', 'S6_2_CHOICE_OBSERVER'}
        console = ROOT/f'out/s6_2-{tag}{"-corrected" if tag == "sanitized" else ""}-test.log'
        log = console.read_text(encoding='utf-8')
        assert f'100% tests passed, 0 tests failed out of {count}' in log
        builds.append(dict(configuration=configuration, tests=count, passed=count, failed=0,
                           total_ctest_seconds=float(re.search(r'Total Test time \(real\) =\s+([0-9.]+) sec', log).group(1)),
                           source_commit=args.source, last_test_log_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    target = ROOT/'experiments/s6_2'
    with (target/'executed_tests.csv').open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, list(tests[0]), lineterminator='\n')
        writer.writeheader(); writer.writerows(tests)
    failure = ROOT/'out/s6_2-sanitized-test.log'
    assert 'detect_leaks is not supported on this platform' in failure.read_text(encoding='utf-8')
    (target/'windows_sanitizer_unsupported_leaks.log').write_text(failure.read_text(encoding='utf-8'), encoding='utf-8', newline='\n')
    previous = json.loads((target/'verification.json').read_text()) if (target/'verification.json').exists() else {}
    report = dict(source_commit=args.source, local_builds=builds, test_rows=len(tests),
                  inherited_test_registrations=135, new_test_registrations=2,
                  toolchain=dict(clang='23.1.5', llvm_mingw='20261104-ucrt-x86_64', cmake='3.31.10', ninja='1.13.2', sqlite='3.54.1'),
                  windows_sanitizers='ASan/UBSan; detect_leaks=0 because the Windows runtime does not support LeakSanitizer',
                  initial_failure='All 137 Windows tests rejected at runtime startup with detect_leaks=1; retained log; corrected invocation passes 137.',
                  timing_note='Correctness tests may overlap builds and evidence analysis; these durations are not benchmark samples.')
    if 'github_ci' in previous:
        report['github_ci'] = previous['github_ci']
    if args.ci:
        ci = json.loads(args.ci.read_text(encoding='utf-8-sig'))
        assert ci['conclusion'] == 'success' and len(ci['jobs']) == 5
        assert all(j['conclusion'] == 'success' for j in ci['jobs'])
        report['github_ci'] = ci
    (target/'verification.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(f'PASS {len(tests)} actual CTest executions, 135 retained registrations')


if __name__ == '__main__':
    main()
