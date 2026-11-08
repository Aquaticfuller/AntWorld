#!/usr/bin/env python3
"""Validate and summarize the balanced S2 ENGINEERING_FIXTURE experiment CSVs."""
import argparse
import csv
import io
import math
import statistics
from pathlib import Path

METRICS = (
    'coverage', 'first_discovery_ms', 'deliveries', 'delivery_per_started_trip',
    'collection_success', 'revisits', 'mean_outbound_moves_per_collection',
    'edge_reuse_fraction', 'trail_moves', 'memory_moves', 'failed_actions',
    'memory_failures', 'stored_ug', 'active_trail_cells', 'trail_units',
    'deposited_units', 'evaporated_units',
)
TREATMENTS = ('none', 'trails', 'memory', 'both')


def table(header, rows):
    stream = io.StringIO(newline='')
    writer = csv.writer(stream, lineterminator='\n')
    writer.writerow(header)
    writer.writerows(rows)
    return stream.getvalue()


def analyze(root):
    with (root / 'summary.csv').open(newline='') as file:
        summaries = list(csv.DictReader(file))
    indexed = {(r['layout'], int(r['seed']), r['treatment']): r for r in summaries}
    seeds = sorted({key[1] for key in indexed})
    assert seeds == list(range(1, len(seeds) + 1))
    expected = {(layout, seed, treatment) for layout in ('open', 'barrier')
                for seed in seeds for treatment in TREATMENTS}
    assert set(indexed) == expected and len(summaries) == len(expected)
    durations = {int(r['simulated_ms']) for r in summaries}
    assert len(durations) == 1
    duration = durations.pop()
    samples = {}
    with (root / 'timeseries.csv').open(newline='') as file:
        for row in csv.DictReader(file):
            key = (row['layout'], int(row['seed']), row['treatment'])
            assert key in expected and row['scope'] == 'ENGINEERING_FIXTURE'
            assert int(row['workers']) == 12
            assert all(math.isfinite(float(row[column])) for column in METRICS)
            assert sum(int(row[column]) for column in ('available_ug', 'carried_ug', 'stored_ug')) == 8000000
            assert 0 <= float(row['coverage']) <= 1
            assert 0 <= float(row['delivery_per_started_trip']) <= 1
            if row['trails_enabled'] == '0':
                assert all(float(row[column]) == 0 for column in ('trail_units', 'deposited_units', 'active_trail_cells', 'trail_moves'))
            if row['memory_enabled'] == '0':
                assert int(row['memory_moves']) == 0
            history = samples.setdefault(key, [])
            assert int(row['simulated_ms']) == len(history) * 30000
            if history:
                for column in ('visited_cells', 'collections', 'deliveries', 'moves', 'deposited_units'):
                    assert float(row[column]) >= float(history[-1][column])
            history.append(row)
    assert set(samples) == expected
    assert all(len(rows) == duration // 30000 + 1 and rows[-1] == indexed[key] for key, rows in samples.items())
    aggregate, comparisons = [], []
    for layout in ('open', 'barrier'):
        for treatment in TREATMENTS:
            for metric in METRICS:
                values = [float(indexed[layout, seed, treatment][metric]) for seed in seeds]
                # -1 means a censored discovery or an undefined conditional metric.
                measured = [v for v in values if v >= 0]
                aggregate.append((layout, treatment, metric, len(values), len(measured),
                                  statistics.mean(measured) if measured else '',
                                  statistics.stdev(measured) if len(measured) > 1 else 0,
                                  min(measured) if measured else '', max(measured) if measured else ''))
                if treatment != 'none':
                    pairs = [(float(indexed[layout, seed, treatment][metric]),
                              float(indexed[layout, seed, 'none'][metric])) for seed in seeds]
                    deltas = [a - b for a, b in pairs if a >= 0 and b >= 0]
                    comparisons.append((layout, treatment, 'none', metric, len(deltas),
                                        statistics.mean(deltas) if deltas else '',
                                        statistics.stdev(deltas) if len(deltas) > 1 else 0,
                                        sum(d > 0 for d in deltas), sum(d == 0 for d in deltas),
                                        sum(d < 0 for d in deltas)))
    return {
        'aggregate.csv': table(('layout', 'treatment', 'metric', 'runs', 'observed_runs', 'mean', 'sample_sd', 'min', 'max'), aggregate),
        'paired_differences.csv': table(('layout', 'treatment', 'baseline', 'metric', 'paired_runs', 'mean_difference',
                                         'sample_sd_difference', 'positive', 'equal', 'negative'), comparisons),
    }, len(summaries), sum(map(len, samples.values()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    outputs, runs, samples = analyze(args.directory)
    for name, text in outputs.items():
        target = args.directory / name
        if args.check:
            assert target.read_text(encoding='utf-8') == text, f'stale analysis: {target}'
        else:
            target.write_text(text, encoding='utf-8', newline='\n')
    print(f'PASS S2 CSV audit: {runs} balanced runs, {samples} time samples, conserved mass and feature ablations')


if __name__ == '__main__':
    main()
