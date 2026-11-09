"""Render S6.2 scientific figures from all frozen raw cases, without seed selection."""
import argparse
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from analyze_s6 import read
from analyze_s6_2_nutrition import interval

ROOT = Path(__file__).resolve().parents[1]
COLORS = {'legacy': '#9b5f34', 'combined': '#15758b'}


def save(fig, target, name):
    fig.savefig(target/(name+'.png'), dpi=160)
    svg = target/(name+'.svg')
    fig.savefig(svg, metadata={'Date': None})
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text(encoding='utf-8').splitlines())+'\n', encoding='utf-8', newline='\n')
    plt.close(fig)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=ROOT/'experiments/s6_2')
    args = p.parse_args()
    base, data = args.root, args.root/'analysis'
    target = base/'figures'
    target.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size': 9, 'axes.spines.top': False, 'axes.spines.right': False,
                         'svg.hashsalt': 'antworld-s6.2'})
    paired = read(data/'paired_blocks.csv')
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), constrained_layout=True)
    for ax, layout in zip(axes, ('dense', 'dispersed')):
        for session in range(1, 4):
            rows = [r for r in paired if r['layout'] == layout and r['session'] == str(session)]
            ax.plot([int(r['block']) for r in rows], [float(r['ratio']) for r in rows], 'o-', ms=3,
                    label=f'Session {session}')
        ax.axhline(6, color='#b33e39', ls='--', label='Frozen limit 6x')
        ax.set(title=layout.title(), xlabel='Balanced block (ABBA / BAAB)', ylabel='Paired mean advance ratio: 2048 / 512',
               ylim=(4.2, 6.3), xticks=(1, 3, 6, 9, 12))
        ax.grid(alpha=.2)
    axes[0].legend(fontsize=8)
    fig.suptitle('Fixed binary, seed, affinity and events: all 72 measured blocks\nNo Core optimization or semantic changes in S6.2')
    save(fig, target, 'balanced_growth')

    phase = read(data/'latency.csv')
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), constrained_layout=True)
    for ax, layout in zip(axes, ('dense', 'dispersed')):
        for offset, size, color in ((-.17, '512', '#467099'), (.17, '2048', '#178c78')):
            rows = [next(r for r in phase if r['mode'] == 'primary' and r['session'] == 'pooled' and
                         r['population'] == size and r['layout'] == layout and r['phase'] == name)
                    for name in ('setup', 'advance', 'encode', 'restore')]
            center = np.array([float(r['p50']) for r in rows])
            upper = np.array([float(r['p99']) for r in rows])
            ax.bar(np.arange(4)+offset, center, width=.32, color=color, label=size+' workers')
            ax.errorbar(np.arange(4)+offset, center, yerr=(np.zeros(4), upper-center), fmt='none', color='black', capsize=2)
        ax.set(title=layout.title(), xticks=range(4), xticklabels=('Setup', 'Advance', 'Encode', 'Restore'), ylabel='Wall time (ms): p50 bar, p99 whisker')
    axes[0].legend()
    fig.suptitle('72 samples per size/layout; setup is excluded from the advance scaling gate\nTails are descriptive, not production latency guarantees')
    save(fig, target, 'separate_phases')

    profile = read(data/'profile.csv')
    categories = ['candidate_sampling', 'physiology', 'policy', 'event_scheduler', 'transaction_journal',
                  'spatial_validation', 'fact_history', 'advance', 'contact_index']
    fig, ax = plt.subplots(figsize=(9, 4.4), constrained_layout=True)
    for offset, size in ((-.17, '512'), (.17, '2048')):
        values = [float(next(r['exclusive_ms'] for r in profile if r['layout'] == 'dense' and
                             r['population'] == size and r['phase'] == 'advance' and r['category'] == c)) for c in categories]
        ax.barh(np.arange(len(categories))+offset, values, height=.32, label=size+' workers')
    ax.set(yticks=range(len(categories)), yticklabels=[c.replace('_', ' ') for c in categories], xlabel='Measured exclusive milliseconds (mean of 8 runs)')
    ax.invert_yaxis()
    ax.legend()
    fig.suptitle('Dense advance attribution: instrumented latency is not acceptance latency\nIndex maintenance is zero for stationary workers; setup maintenance is reported separately')
    save(fig, target, 'exclusive_attribution')

    fig, axes = plt.subplots(3, 1, figsize=(10, 6), sharex=True, constrained_layout=True)
    for session in range(1, 4):
        rows = read(base/f'performance/primary/session{session}/hwinfo_corrected.csv')
        start = float(rows[0]['utc_ns'])
        x = [(float(r['utc_ns'])-start)/1e9 for r in rows]
        for ax, metric, label in zip(axes, ('p0_temperature_c', 'package_power_w', 'p0_t0_effective_clock_mhz'),
                                      ('P-core 0 temperature (C)', 'CPU package power (W)', 'P0 T0 effective frequency (MHz)')):
            ax.plot(x, [float(r[metric]) for r in rows], '.-', ms=3, label=f'Session {session}')
            ax.set(ylabel=label)
            ax.grid(alpha=.2)
    axes[0].legend(ncol=3)
    axes[-1].set(xlabel='Seconds from first sensor sample in each session')
    fig.suptitle('HWiNFO: all complete samples, approximately 2 s cadence\nCorrected column mapping; interval readings include idle gaps; no instantaneous phase temperature claim')
    save(fig, target, 'hardware_telemetry')

    paired = read(data/'nutrition_paired.csv')
    fig, axes = plt.subplots(2, 2, figsize=(10, 6.8), constrained_layout=True)
    for ax, metric, label in zip(axes.flat, ('given_protein_ug', 'new_brood_emerged', 'unmet_integral_ug_s', 'adult_crop_protein_ug'),
                                ('Protein delivered (ug)', 'New emergence / 10 unsupplied brood', 'Unmet exposure (1000 ug*s)', 'Protein retained in adult crops (ug)')):
        scale = 1000 if metric == 'unmet_integral_ug_s' else 1
        for offset, protein, color in ((-.12, '500', '#aa6441'), (.12, '2000', '#15758b')):
            selected = [next(r for r in paired if r['workers'] == str(w) and r['source_protein_ug'] == protein and r['metric'] == metric) for w in (8, 32, 128)]
            y = np.array([float(r['mean'])/scale for r in selected])
            low = np.array([float(r['ci_low'])/scale for r in selected])
            high = np.array([float(r['ci_high'])/scale for r in selected])
            ax.errorbar(np.arange(3)+offset, y, yerr=(y-low, high-y), fmt='o', capsize=3, color=color, label=protein+' ug source')
        ax.axhline(0, color='#777', lw=.8)
        ax.set(xticks=range(3), xticklabels=(8, 32, 128), xlabel='Initial adult workers', ylabel=label)
        ax.grid(axis='y', alpha=.2)
    axes[0, 0].legend(fontsize=8)
    fig.suptitle('ENGINEERING_FIXTURE: combined minus legacy, 180 s\nAll 16 paired seeds per condition; 95% paired bootstrap intervals; negative results retained')
    save(fig, target, 'scarcity_controls')

    people = read(base/'nutrition/individuals.csv')
    fig, axes = plt.subplots(2, 2, figsize=(10, 8), constrained_layout=True)
    for ax, (workers, arm) in zip(axes.flat, ((8, 'legacy'), (8, 'combined'), (128, 'legacy'), (128, 'combined'))):
        matrix = []
        for seed in range(1, 17):
            selected = sorted((r for r in people if r['seed'] == str(seed) and r['workers'] == str(workers) and
                               r['source_protein_ug'] == '500' and r['policy'] == arm and r['seed_stage'] in ('0', '1')),
                              key=lambda r: int(r['entity_id']))
            assert len(selected) == 10
            matrix.append([int(r['received_protein_ug']) for r in selected])
        image = ax.imshow(matrix, vmin=0, vmax=100, cmap='cividis', aspect='auto')
        ax.set(title=f'{workers} workers / {arm}', xlabel='Brood identity rank (4 eggs then 6 larvae)', ylabel='Seed',
               xticks=range(10), xticklabels=range(1, 11), yticks=range(0, 16, 3), yticklabels=range(1, 17, 3))
    fig.colorbar(image, ax=list(axes.flat), label='Actual protein gifts (ug); fixture requirement = 100')
    fig.suptitle('ENGINEERING_FIXTURE: all scarcity recipients, source protein = 500 ug\nInitial pupal tissue and later adult self-intake excluded; no seed selection')
    save(fig, target, 'recipient_allocation')

    gifts = read(base/'nutrition/gifts.csv')
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), constrained_layout=True)
    for ax, workers in zip(axes, (8, 128)):
        for arm in ('legacy', 'combined'):
            selected = [r for r in gifts if r['workers'] == str(workers) and r['source_protein_ug'] == '500' and r['policy'] == arm]
            means, low, high = [], [], []
            ticks = list(range(0, 181, 5))
            for time in ticks:
                per_seed = [sum(int(r['protein_ug']) for r in selected if r['seed'] == str(s) and int(r['time_ms']) <= time*1000) for s in range(1, 17)]
                stats = interval(per_seed)
                means.append(stats['mean']); low.append(stats['ci_low']); high.append(stats['ci_high'])
            ax.plot(ticks, means, label=arm, color=COLORS[arm])
            ax.fill_between(ticks, low, high, color=COLORS[arm], alpha=.15)
        ax.set(title=f'{workers} workers', xlabel='Simulation seconds', ylabel='Cumulative actual protein transfer (ug)', ylim=(0, 520))
        ax.axhline(500, color='#777', ls='--', lw=.8)
        ax.grid(alpha=.2)
    axes[0].legend()
    fig.suptitle('ENGINEERING_FIXTURE: exact ordered gifts, 500 ug source\n16 seeds; pointwise 95% bootstrap intervals; incomplete provisioning remains visible')
    save(fig, target, 'transfer_timeline')

    choice = read(data/'choice_distribution.csv')
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
    for ax, metric, expected in zip(axes, ('chosen', 'included'), (1/16, 16/17)):
        for permutation in range(4):
            rows = [r for r in choice if r['axis'] == 'id_rank' and r['metric'] == metric and r['permutation'] == str(permutation)]
            means = np.array([float(r['mean']) for r in rows])
            low = np.array([float(r['ci_low']) for r in rows]); high = np.array([float(r['ci_high']) for r in rows])
            ax.errorbar(np.arange(16)+(permutation-1.5)*.15, means, yerr=(means-low, high-means), fmt='.', ms=3, capsize=1, alpha=.8, label=f'Permutation {permutation}')
        ax.axhline(expected, color='#777', ls='--', label='Uniform eligibility expectation')
        ax.set(title=metric.title()+' fraction', xlabel='Recipient ID rank', ylabel='Fraction per actual nursing decision', xticks=range(0, 16, 3))
    axes[1].legend(fontsize=7, loc='lower right')
    fig.suptitle('ENGINEERING_FIXTURE: 64 seeds, 4 label/mirror permutations, 64 actual gifts per case\nSeed-cluster 95% intervals; endpoints are not independent tests of perfect uniformity')
    save(fig, target, 'equal_demand_choices')
    print('PASS eight figures rendered from complete frozen evidence')


if __name__ == '__main__':
    main()
