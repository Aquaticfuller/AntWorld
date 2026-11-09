"""Render frozen S6.1 scientific summaries from audited data, without seed selection."""
import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from archive_s6_1 import rows

ROOT = Path(__file__).resolve().parents[1]
COLORS = {'legacy': '#64748b', 'combined': '#0f766e'}


def save(fig, base, name):
    fig.savefig(base/f'{name}.png', dpi=180, bbox_inches='tight')
    svg = base/f'{name}.svg'
    fig.savefig(svg, bbox_inches='tight', metadata={'Date': None})
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text(encoding='utf-8').splitlines())+'\n',
                   encoding='utf-8', newline='\n')
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT/'experiments/s6_1')
    args = parser.parse_args()
    base = args.root
    target = base/'figures'
    target.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size': 9, 'axes.spines.top': False, 'axes.spines.right': False,
                         'svg.hashsalt': 'antworld-s6.1'})
    stats = list(rows(base/'analysis', 'ecology'))
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.6), constrained_layout=True)
    matrix_limit = max(1, *(abs(float(r['mean']))/1000 for r in stats if r['suite'] == 'matrix' and
                           r['comparison'] == 'minus_legacy' and r['metric'] == 'unmet_integral_ug_s'))
    for ax, arm in zip(axes, ('gift_first', 'local_continuation', 'combined'), strict=True):
        values, intervals = np.zeros((3, 3)), {}
        for i, workers in enumerate((8, 32, 128)):
            for j, protein in enumerate((0, 500, 2000)):
                r = next(r for r in stats if r['suite'] == 'matrix' and r['policy'] == arm and
                         r['comparison'] == 'minus_legacy' and r['metric'] == 'unmet_integral_ug_s' and
                         r['workers'] == str(workers) and r['source_protein_ug'] == str(protein))
                values[i, j] = float(r['mean'])/1000
                intervals[i, j] = float(r['ci95_low'])/1000, float(r['ci95_high'])/1000
        limit = matrix_limit
        ax.imshow(values, cmap='RdBu_r', vmin=-limit, vmax=limit)
        for (i, j), bounds in intervals.items():
            ax.text(j, i, f'{values[i,j]:.1f}\n[{bounds[0]:.1f}, {bounds[1]:.1f}]', ha='center', va='center',
                    fontsize=8, color='white' if abs(values[i,j]) > .6*limit else 'black')
        ax.set(title=arm.replace('_', ' '), xticks=range(3), xticklabels=(0, 500, 2000),
               yticks=range(3), yticklabels=(8, 32, 128), xlabel='Source protein (ug)', ylabel='Initial adult workers')
    fig.suptitle('ENGINEERING_FIXTURE: unmet-demand exposure difference from legacy (1000 ug*s)\n16 paired seeds; 95% intervals; shared color scale; negative means less unmet demand')
    save(fig, target, 'nutrition_matrix')

    fig, axes = plt.subplots(2, 2, figsize=(10, 7), constrained_layout=True)
    conditions = ('supplied', 'protein_absent', 'food_absent', 'sealed')
    for ax, (metric, label, scale) in zip(axes.flat, (
            ('emerged', 'Cumulative emergences / 12 seeded brood', 1),
            ('unmet_integral_ug_s', 'Unmet demand (1000 ug*s)', 1000),
            ('given_protein_ug', 'Protein actually transferred (ug)', 1),
            ('dead_crop_protein_ug', 'Protein retained in dead crops (ug)', 1)), strict=True):
        for offset, policy in ((-.12, 'legacy'), (.12, 'combined')):
            selected = [next(r for r in stats if r['suite'] == 'integrated' and r['condition'] == c and
                             r['policy'] == policy and r['comparison'] == 'endpoint' and r['metric'] == metric)
                        for c in conditions]
            center = np.array([float(r['mean'])/scale for r in selected])
            low = np.array([float(r['ci95_low'])/scale for r in selected])
            high = np.array([float(r['ci95_high'])/scale for r in selected])
            ax.errorbar(np.arange(4)+offset, center, yerr=(center-low, high-center), fmt='o', capsize=3,
                        color=COLORS[policy], label=policy)
        ax.set(xticks=range(4), xticklabels=('Supplied', 'No protein', 'No food', 'Sealed'), ylabel=label)
        ax.grid(axis='y', alpha=.2)
    axes[0, 0].legend()
    fig.suptitle('ENGINEERING_FIXTURE: integrated 600 s outcomes\n32 seeds; mirror means within seed; 95% bootstrap intervals; all conditions retained')
    save(fig, target, 'integrated_outcomes')

    fig, axes = plt.subplots(2, 2, figsize=(10, 7), constrained_layout=True)
    for ax, (metric, label, scale) in zip(axes.flat, (
            ('active_fraction', 'Initial adult active-program time (%)', .01),
            ('away_fraction', 'Initial adult time away from depot (%)', .01),
            ('blocked_fraction', 'Travel/cargo-blocked reconsiderations (%)', .01),
            ('excavated_q3', 'Actual excavated volume (fixture q^3)', 1)), strict=True):
        for offset, policy in ((-.12, 'legacy'), (.12, 'combined')):
            selected = [next(r for r in stats if r['suite'] == 'integrated' and r['condition'] == c and
                             r['policy'] == policy and r['comparison'] == 'endpoint' and r['metric'] == metric)
                        for c in conditions]
            center = np.array([float(r['mean'])/scale for r in selected])
            low = np.array([float(r['ci95_low'])/scale for r in selected])
            high = np.array([float(r['ci95_high'])/scale for r in selected])
            ax.errorbar(np.arange(4)+offset, center, yerr=(center-low, high-center), fmt='o', capsize=3,
                        color=COLORS[policy], label=policy)
        ax.set(xticks=range(4), xticklabels=('Supplied', 'No protein', 'No food', 'Sealed'), ylabel=label)
        ax.grid(axis='y', alpha=.2)
    axes[0, 0].legend()
    fig.suptitle('ENGINEERING_FIXTURE: task residence and spatial feedback\n32 seeds with paired mirrors; active ownership is not continuous locomotion')
    save(fig, target, 'behavior_feedback')

    fig, axes = plt.subplots(2, 2, figsize=(10, 6), constrained_layout=True)
    seed7 = [r for r in rows(base/'observer_integrated', 'time_series') if r['seed'] == '7' and
             r['condition'] == 'supplied' and r['mirror'] == '0']
    for ax, (metric, label) in zip(axes.flat, (('unmet_protein_ug', 'Unmet larval protein (ug)'),
                ('adult_crop_protein_ug', 'Living adult crop protein (ug)'),
                ('given_protein_ug', 'Cumulative transferred protein (ug)'), ('emerged', 'Cumulative emergences')), strict=True):
        for policy in ('legacy', 'combined'):
            selected = [r for r in seed7 if r['policy'] == policy]
            ax.plot([int(r['time_ms'])/1000 for r in selected], [int(r[metric]) for r in selected],
                    label=policy, color=COLORS[policy])
        ax.set(xlabel='Simulated seconds', ylabel=label)
        ax.grid(alpha=.2)
    axes[0, 0].legend()
    fig.suptitle('ENGINEERING_FIXTURE: reviewed seed 7, unmirrored supplied case\nDiagnostic example designated before corrections; full multi-seed results shown separately')
    save(fig, target, 'seed7_nutrition')

    timing = list(rows(base/'analysis', 'performance'))
    profile = list(rows(base/'analysis', 'profile'))
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), constrained_layout=True)
    for policy, color in (('exhaustive', '#64748b'), ('bounded', '#0f766e')):
        selected = [next(r for r in timing if r['archive'] == 'performance_final' and r['layout'] == 'dense' and
                         r['population'] == str(n) and r['policy'] == policy and r['metric'] == 'advance_ms') for n in (128, 512, 2048)]
        for field, style in (('p50', '-o'), ('p95', '--'), ('p99', ':')):
            axes[0].plot((128, 512, 2048), [float(r[field]) for r in selected], style, color=color, label=f'{policy} {field}')
    axes[0].set(xscale='log', yscale='log', xlabel='Workers', ylabel='Advance latency (ms)',
                title='Final dense fixture; 10 repeats\n512 to 2048 growth: 24.23x; limit 6x FAILED')
    axes[0].set_xticks((128, 512, 2048), labels=('128', '512', '2048'))
    axes[0].legend(fontsize=7)
    axes[0].grid(alpha=.2)
    # Plot measured exclusive category totals per matrix, not absolute before /
    # after speedup: host speed and instrumentation overhead varied materially.
    all_categories = sorted({r['category'] for r in profile})
    bottom = np.zeros(2)
    for category in all_categories:
        values = []
        for archive in ('profile_before', 'profile_after'):
            selected = [r for r in profile if r['archive'] == archive and r['population'] == '2048' and
                        r['layout'] == 'dense' and r['policy'] == 'bounded' and r['phase'] == 'advance']
            total = sum(float(r['exclusive_ms_p50']) for r in selected)
            values.append(100*float(next(r for r in selected if r['category'] == category)['exclusive_ms_p50'])/total)
        axes[1].bar(('Before', 'After'), values, bottom=bottom, label=category)
        bottom += values
    axes[1].set(ylabel='Share of summed category medians (%)', title='Instrumented dense 2048; attribution only')
    axes[1].legend(fontsize=6, bbox_to_anchor=(1, 1), loc='upper left')
    fig.suptitle('ENGINEERING_FIXTURE: fixed events, candidates, collision checks and history retained')
    save(fig, target, 'contact_performance')
    print(f'Wrote five PNG/SVG figure pairs in {target}')


if __name__ == '__main__':
    main()
