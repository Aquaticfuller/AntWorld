"""Compare a complete first-N-seed S6 primary rerun with retained raw evidence."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASE = ('suite', 'seed', 'condition', 'mirror', 'encounter_budget')
HOST = {'setup_ms', 'advance_ms', 'save_ms', 'load_ms', 'database_bytes'}
FLOAT_FIELDS = {'path_m', 'x_m', 'y_m', 'z_m', 'final_x_m', 'final_y_m', 'final_z_m'}


def read(path):
    with path.open(encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream))


def first_seeds(path, n):
    # Archives are emitted in increasing seed order. Reading a complete prefix
    # also permits validating finished seeds while a different later seed runs.
    result = []
    with path.open(encoding='utf-8', newline='') as stream:
        for row in csv.DictReader(stream):
            if int(row['seed']) > n:
                break
            result.append(row)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('reproduced', type=Path)
    parser.add_argument('--reference', type=Path, default=ROOT/'experiments/s6/integrated')
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--schema-version',type=int,default=7)
    parser.add_argument('--physics-version',type=int,default=8)
    parser.add_argument('--checkpoint-byte-delta',type=int,default=0)
    parser.add_argument('--cross-platform', action='store_true',
                        help='Document-18 contract: exclude binary hashes; compare exported distances to 1e-12 m absolute tolerance')
    args = parser.parse_args()
    config = json.loads((args.reproduced/'configuration.json').read_text(encoding='utf-8'))
    reference = json.loads((args.reference/'configuration.json').read_text(encoding='utf-8'))
    assert config['suite'] == reference['suite'] == 'primary'
    n = config['seeds']
    assert 1 <= n <= reference['seeds']
    reference['seeds'] = n
    reference['schema_version']=args.schema_version
    reference['physics_version']=args.physics_version
    if 'nursing_correction_policy' in config:
        assert config['nursing_correction_policy']=='legacy', 'this verifier compares retained legacy semantics'
        reference['nursing_correction_policy']='legacy'
    assert config == reference, 'fixture changed'
    expected_cases = {('primary', str(s), c, str(m), '16') for s in range(1, n+1)
                      for c in ('supplied', 'protein_absent', 'food_absent', 'sealed') for m in (0, 1)}
    report = dict(source_commit=args.source_commit, first_seed=1, seeds=n, cases=len(expected_cases),
                  cross_platform=args.cross_platform, excluded_host_fields=sorted(HOST),
                  excluded_binary_fields=['state_hash', 'trace_hash'] if args.cross_platform else [],
                  distance_absolute_tolerance_m=1e-12 if args.cross_platform else 0,
                  schema_version=args.schema_version,physics_version=args.physics_version,
                  checkpoint_byte_delta=args.checkpoint_byte_delta,files={})
    for filename in ('summary.csv', 'individuals.csv', 'events.csv', 'geometry.csv',
                     'foods.csv', 'time_series.csv', 'event_counts.csv'):
        expected = first_seeds(args.reference/filename, n)
        actual = read(args.reproduced/filename)
        assert len(expected) == len(actual), (filename, 'row count', len(expected), len(actual))
        if filename == 'summary.csv':
            assert {tuple(r[k] for k in CASE) for r in actual} == expected_cases
            assert len(actual) == 3*len(expected_cases)
        differences = []
        for index, (a, b) in enumerate(zip(expected, actual, strict=True)):
            assert a.keys() == b.keys(), 'column mismatch'
            for field in a:
                if field in HOST or (args.cross_platform and field in ('state_hash', 'trace_hash')):
                    continue
                if field=='schema_version':
                    assert int(b[field])==args.schema_version
                    continue
                if field=='physics_version':
                    assert int(b[field])==args.physics_version
                    continue
                if field=='checkpoint_bytes':
                    assert int(b[field])==int(a[field])+args.checkpoint_byte_delta
                    continue
                if field=='state_hash' and (args.schema_version!=7 or args.physics_version!=8):
                    continue
                if args.cross_platform and field in FLOAT_FIELDS:
                    equal = math.isclose(float(a[field]), float(b[field]), abs_tol=1e-12, rel_tol=0)
                else:
                    equal = a[field] == b[field]
                if not equal:
                    differences.append(dict(row=index+2, field=field, expected=a[field], actual=b[field]))
                    if len(differences) == 10:
                        break
            if len(differences) == 10:
                break
        assert not differences, (filename, differences)
        report['files'][filename] = dict(rows=len(actual), semantic_match=True,
            normalized_lf_sha256=hashlib.sha256((args.reproduced/filename).read_text(encoding='utf-8').encode()).hexdigest())
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
