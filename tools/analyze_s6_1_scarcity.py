"""Post-hoc endpoint diagnosis of negative scarcity controls; no model fitting."""
import argparse
from collections import Counter, defaultdict
from pathlib import Path

from archive_s6_1 import rows
from analyze_s6 import emit

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT/'experiments/s6_1')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    groups = defaultdict(list)
    for r in rows(args.root/'matrix', 'individuals'):
        if r['workers'] in ('8', '128') and r['source_protein_ug'] == '500' and r['policy'] in ('legacy', 'combined') and r['seed_stage'] != '3':
            groups[int(r['workers']), r['policy'], int(r['seed'])].append(r)
    assert len(groups) == 64
    data = []
    for (workers, policy, seed), people in sorted(groups.items()):
        assert len(people) == 12
        protein = [int(p['crop_protein_ug'])+int(p['tissue_protein_ug']) for p in people]
        # The fixed fixture's threshold is 100 ug, not a species calibration.
        data.append(dict(workers=workers, policy=policy, seed=seed, source_protein_ug=500,
                         duration_ms=180000, fully_provisioned=sum(x >= 100 for x in protein),
                         partially_provisioned=sum(0 < x < 100 for x in protein),
                         no_protein=sum(x == 0 for x in protein), brood_protein_ug=sum(protein),
                         fully_provisioned_without_emergence=sum(
                             int(p['crop_protein_ug'])+int(p['tissue_protein_ug']) >= 100 and p['adult_ms'] == '-1' for p in people)))
    failures = defaultdict(Counter)
    for r in rows(args.root/'matrix', 'events'):
        if r['workers'] == '32' and r['source_protein_ug'] == '2000' and r['scheduled_kind'] == '12' and r['kind'] != '21':
            failures[r['policy'], int(r['seed'])][int(r['outcome'])] += 1
    failed_rows = []
    for policy in ('legacy', 'gift_first', 'local_continuation', 'combined'):
        for seed in range(1, 17):
            counts = failures[policy, seed]
            assert set(counts) <= {17}, 'update diagnosis for newly observed failure outcomes'
            failed_rows.append(dict(policy=policy, seed=seed, workers=32, source_protein_ug=2000,
                                    duration_ms=180000, empty_compatible_inventory_resolutions=counts[17]))
    emit(args.root/'analysis/scarcity_diagnosis.csv', data, args.check)
    emit(args.root/'analysis/failed_gift_diagnosis.csv', failed_rows, args.check)
    print('PASS post-hoc scarcity endpoints and all declared default-cell gift failures; no fitted parameters')


if __name__ == '__main__':
    main()
