"""Verify the archived assay bytes, legacy replay receipt and density continuity."""
import json

from analyze_s6_3_3_1 import HOLDOUT, HISTORICAL, LAYOUTS, POLICIES, REFERENCE, STAGE, read, sha


def main():
    root = STAGE/'raw'
    manifest = json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    seen = set()
    total = 0
    for batch in manifest['batches']:
        policy,mode = batch['policy'],batch['mode']
        assert (policy,mode) not in seen
        seen.add((policy,mode))
        path = root/policy/mode
        assert len(read(path/'runs.csv')) == batch['runs']
        for file,item in batch['files'].items():
            data = path/file
            assert data.stat().st_size == item['bytes'] and sha(data) == item['sha256'], data
            assert sha(data,file.endswith('.gz')) == item['csv_sha256'], data
        total += batch['runs']
    assert seen == {(p,m) for p in POLICIES for m in ('retrieval-line','b01',*(f'holdout-{x}' for x in LAYOUTS))}
    assert total == 416 and len(HOLDOUT) == 12
    replay = json.loads((STAGE/'historical_replay.json').read_text(encoding='utf-8'))
    assert replay['matched_runs'] == sum(r['runs'] for r in replay['cases']) == 384
    assert {r['fixture'] for r in replay['cases']} == {
        *(f'primary_{s}' for s in HISTORICAL),*(f'sensitivity_{s}' for s in HISTORICAL[:6])}
    assert sum(r['exported_events'] for r in replay['cases']) == 45443005
    assert replay['executable_sha256'] == manifest['executable_sha256']
    for row in replay['cases']:
        assert row['match']
        assert sha(REFERENCE/'raw'/row['fixture']/'events.csv.gz') == row['historical_archive_sha256']
    before,after = (read(STAGE/name) for name in ('density_before_trace_receipt.csv','density.csv'))
    assert len(before) == len(after) == 128
    for x,y in zip(before,after):
        assert x['trace_hash'] == '0' and int(y['trace_hash']) and y['restore_equal'] == '1'
        for field in x.keys()-{'advance_ms','checkpoint_ms','restore_ms','trace_hash'}:
            assert x[field] == y[field], field
    print('PASS: 416 new runs, 384 legacy replays, all archive hashes and 128 repeated density rows')


if __name__ == '__main__':
    main()
