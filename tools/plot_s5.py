#!/usr/bin/env python3
"""Plot every S5 condition and day from the audited raw evidence; do not select fast runs."""
import csv
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / 'out/matplotlib'))
sys.path.insert(0, str(ROOT / '.tools/s2_1-python'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

DATA = ROOT / 'experiments/s5'
FIGURES = DATA / 'figures'
COLORS = {'repeated': '#326d91', 'interleaved': '#b35d24'}


def read(name):
    with (DATA / name).open(encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream))


def save(fig, name):
    fig.savefig(FIGURES / f'{name}.png', dpi=170,
                metadata={'Software': 'AntWorld S5 storage validation'})
    fig.savefig(FIGURES / f'{name}.svg', metadata={'Date': None, 'Creator': 'AntWorld S5 storage validation'})
    svg = FIGURES / f'{name}.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text(encoding='utf-8').splitlines()) + '\n',
                   encoding='utf-8', newline='\n')
    plt.close(fig)


def main():
    FIGURES.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'svg.hashsalt': 'AntWorld-S5', 'font.size': 10,
                         'axes.spines.top': False, 'axes.spines.right': False})
    summary = read('performance/summary.csv')
    fig, axes = plt.subplots(2, 2, figsize=(11.8, 8.2), layout='constrained')
    for condition, color in COLORS.items():
        for operation, style, label in (('checkpoint_restore', '-', 'core restore'),
                                         ('durable_load_validate', '--', 'durable restore + audit')):
            rows = [r for r in summary if r['condition'] == condition and r['operation'] == operation]
            x = [int(r['edits']) for r in rows]
            median = [float(r['p50_us']) / 1000 for r in rows]
            p95 = [float(r['p95_us']) / 1000 for r in rows]
            axes[0, 0].plot(x, median, style, marker='o', color=color, label=f'{condition}: {label}')
            axes[0, 0].fill_between(x, median, p95, color=color, alpha=.12)
        rows = [r for r in summary if r['condition'] == condition and r['operation'] == 'durable_save']
        x = [int(r['edits']) for r in rows]
        median = [float(r['p50_us']) / 1000 for r in rows]
        axes[0, 1].plot(x, median, marker='o', color=color, label=condition)
        axes[0, 1].fill_between(x, median, [float(r['p95_us']) / 1000 for r in rows], color=color, alpha=.12)
        axes[1, 0].plot(x, [int(r['max_database_bytes']) / 2**20 for r in rows], marker='o',
                       color=color, label=f'{condition}: main + WAL + SHM')
        rows = [r for r in summary if r['condition'] == condition and r['operation'] == 'post_wal_checkpoint_size']
        axes[1, 0].plot(x, [int(r['max_database_bytes']) / 2**20 for r in rows], '--', color=color,
                       label=f'{condition}: after WAL truncation')
        peaks = [max(int(r['max_peak_resident_bytes']) for r in summary
                     if r['condition'] == condition and int(r['edits']) == count) / 2**20 for count in x]
        axes[1, 1].plot(x, peaks, marker='o', color=color, label=condition)
    cp = [r for r in summary if r['condition'] == 'repeated' and r['operation'] == 'checkpoint_encode']
    axes[1, 0].plot([int(r['edits']) for r in cp], [int(r['checkpoint_bytes']) / 2**20 for r in cp],
                    ':', color='#31343b', label='Canonical checkpoint (both conditions)')
    for ax, title, unit in zip(axes.flat,
                                ('Restoration', 'Atomic first-generation save', 'Storage size', 'Whole-process peak RSS'),
                                ('Elapsed (ms)', 'Elapsed (ms)', 'Size (MiB)', 'Peak resident memory (MiB)')):
        ax.set(title=title, ylabel=unit, xlabel='Authoritative geometry edits')
        ax.set_xticks([1000, 5000, 10000], ['1,000', '5,000', '10,000'])
        ax.grid(alpha=.15)
        ax.legend(fontsize=8)
    fig.suptitle('S5 geometry history: complete 10-repeat matrix per condition\n'
                 'Timing lines: p50; shaded bands: p50-p95 (latency quantiles, not confidence intervals)', fontsize=12)
    fig.supxlabel('ENGINEERING_FIXTURE | Windows Release | warm OS cache | exact edits and facts retained | no general compaction', fontsize=9)
    save(fig, 'geometry_storage')

    raw = read('performance/long-history.csv')
    before = read('performance/long-history-before-query-index.csv')
    days = [int(r['day']) for r in raw]
    fig, axes = plt.subplots(1, 3, figsize=(13.4, 4.7), layout='constrained')
    axes[0].plot(days, [int(r['database_bytes']) / 2**20 for r in raw], color='#326d91', label='Main + WAL + SHM')
    axes[0].plot(days, [int(r['checkpoint_bytes']) / 2**20 for r in raw], color='#b35d24', label='One canonical checkpoint')
    axes[0].set(title='Growing retained history', ylabel='Size (MiB)')
    axes[1].plot(days, [float(r['save_us']) / 1000 for r in raw], color='#326d91', label='Daily save')
    loads = [r for r in raw if float(r['load_validate_us']) >= 0]
    axes[1].scatter([int(r['day']) for r in loads], [float(r['load_validate_us']) / 1000 for r in loads],
                    color='#b35d24', s=22, label='Monthly/final restore + audit')
    axes[1].set(title='Save and validated restore', ylabel='Elapsed (ms)')
    axes[2].plot(days, [float(r['query_us']) / 1000 for r in before], color='#b35d24', alpha=.7,
                 label='Before time-index fix')
    axes[2].plot(days, [float(r['query_us']) / 1000 for r in raw], color='#326d91', label='After time-index fix')
    axes[2].set(title='Current-day history query', ylabel='Elapsed (ms)', yscale='log')
    for ax in axes:
        ax.set_xlabel('Diagnostic storage day')
        ax.grid(alpha=.15)
        ax.legend(fontsize=8)
    fig.suptitle('365 diagnostic days: 100 actual diagnostic facts/day, daily saves, all days retained\n'
                 'One serial observation per day; this is not a biological year experiment', fontsize=12)
    fig.supxlabel('ENGINEERING_STORAGE_CLOCK | Two complete generations retained; factual history and metric samples are not pruned', fontsize=9)
    save(fig, 'long_history')
    print('Wrote S5 geometry and diagnostic-history figures (PNG and SVG)')


if __name__ == '__main__':
    main()
