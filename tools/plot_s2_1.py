#!/usr/bin/env python3
"""Render S2.1 scientific figures from audited CSVs; optional pinned matplotlib environment."""
import argparse
import csv
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--packages', type=Path, help='Optional pip --target directory')
args = parser.parse_args()
if args.packages:
    sys.path.insert(0, str(args.packages.resolve()))
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / 'out/s2_1-matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

DATA = ROOT / 'experiments/s2_1'
OUTPUT = DATA / 'figures'
OUTPUT.mkdir(exist_ok=True)
plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False,
                     'svg.fonttype': 'none', 'svg.hashsalt': 'antworld-s2.1', 'savefig.dpi': 160})
COLORS = {'s2-baseline': '#697a91', 's2.1': '#167f80', 'absent': '#b15c3d'}


def rows(name):
    with (DATA / name).open(newline='', encoding='utf-8') as file:
        return list(csv.DictReader(file))


def save(fig, name):
    svg = OUTPUT / f'{name}.svg'
    fig.savefig(svg, metadata={'Date': None, 'Creator': 'AntWorld S2.1; ENGINEERING_FIXTURE'})
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text(encoding='utf-8').splitlines())+'\n', encoding='utf-8', newline='\n')
    fig.savefig(OUTPUT / f'{name}.png', metadata={'Software': 'AntWorld S2.1; ENGINEERING_FIXTURE'})
    plt.close(fig)


summary, effects, survival = rows('social_summary.csv'), rows('paired_effects.csv'), rows('survival.csv')
fig, axs = plt.subplots(2, 2, figsize=(12.5, 8.5), layout='constrained')
fig.suptitle('S2.1 social recruitment: no reliable discovery benefit demonstrated\nENGINEERING_FIXTURE | 64 seeds x 2 orientations | 180 s novice window', fontsize=14)
delays = [0, 180000, 600000]
ax = axs[0, 0]
for model, offset in [('s2-baseline', -0.12), ('s2.1', 0.12)]:
    selected = [next(r for r in summary if r['model'] == model and int(r['release_delay_ms']) == d and r['treatment'] == 'present') for d in delays]
    y = np.array([float(r['discovery_rate'])*100 for r in selected])
    lower = np.array([float(r['cluster_ci_low'])*100 for r in selected])
    upper = np.array([float(r['cluster_ci_high'])*100 for r in selected])
    ax.errorbar(np.arange(3)+offset, y, yerr=[y-lower, upper-y], fmt='o-', capsize=4, color=COLORS[model], label=model)
reference = next(r for r in summary if r['model'] == 's2.1' and r['treatment'] == 'absent' and r['release_delay_ms'] == '0')
ax.axhline(float(reference['discovery_rate'])*100, color=COLORS['absent'], ls='--', label='Absent / blind: 74 of 128')
ax.set(xticks=range(3), xticklabels=['Fresh', '3 min old', '10 min old'], ylabel='Novices discovering food (%)', ylim=(30, 85), title='Discovery rate (seed-cluster 95% intervals)')
ax.legend(fontsize=9, loc='lower left')
ax = axs[0, 1]
for model, treatment, label, style, color in [
    ('s2-baseline', 'present', 'S2, fresh trail', '-', COLORS['s2-baseline']),
    ('s2.1', 'present', 'S2.1, fresh trail', '-', COLORS['s2.1']),
    ('s2.1', 'absent', 'No trail / blind', '--', COLORS['absent']),
]:
    selected = [r for r in survival if r['model'] == model and r['treatment'] == treatment and r['release_delay_ms'] == '0']
    ax.step([int(r['time_ms'])/1000 for r in selected], [float(r['undiscovered_fraction'])*100 for r in selected],
            where='post', label=label, color=color, ls=style)
ax.set(xlabel='Seconds after novice activation', ylabel='Still undiscovered (%)', xlim=(0, 180), ylim=(0, 102), title='Discovery survival (non-discoverers retained)')
ax.legend(fontsize=9)
for ax, metric, scale, ylabel, title in [
    (axs[1, 0], 'discovery_rate', 100, 'Present minus absent (percentage points)', 'Paired discovery effect'),
    (axs[1, 1], 'restricted_mean_discovery_s', 1, 'Present minus absent (seconds)', 'Paired restricted mean discovery time'),
]:
    for model, offset in [('s2-baseline', -0.12), ('s2.1', 0.12)]:
        selected = [next(r for r in effects if r['model'] == model and r['metric'] == metric and int(r['release_delay_ms']) == d) for d in delays]
        y = np.array([float(r['mean_difference'])*scale for r in selected])
        lo = np.array([float(r['ci_low'])*scale for r in selected]); hi = np.array([float(r['ci_high'])*scale for r in selected])
        ax.errorbar(np.arange(3)+offset, y, yerr=[y-lo, hi-y], fmt='o', capsize=4, color=COLORS[model], label=model)
    ax.axhline(0, color='#777777', lw=1, ls='--')
    ax.set(xticks=range(3), xticklabels=['Fresh', '3 min old', '10 min old'], ylabel=ylabel, title=title)
    ax.text(0.02, 0.02, '4,096 bootstrap draws; resample seed pairs', transform=ax.transAxes, fontsize=8)
save(fig, 'recruitment')

fields = rows('fixed/fields.csv')
fig, axs = plt.subplots(1, 3, figsize=(13, 4.3), layout='constrained')
fig.suptitle('An actual scout return trace decays without reinforcement\nENGINEERING_FIXTURE | Fixed illustration: seed 1, east | Field at novice release', fontsize=13)
for ax, delay, title in zip(axs, delays, ['Fresh', '3 min after scout retirement', '10 min after scout retirement']):
    grid = np.zeros((15, 21))
    for row in fields:
        if row['seed'] == '1' and row['orientation'] == 'east' and row['treatment'] == 'present' and int(row['release_delay_ms']) == delay and row['elapsed_ms'] == '0':
            x, z = int(row['cell_x']), int(row['cell_z'])
            if x >= 0:
                grid[z, x] = float(row['units'])
    image = ax.imshow(grid, origin='lower', vmin=0, vmax=1, cmap='magma', extent=(-0.5, 20.5, -0.5, 14.5), interpolation='nearest')
    ax.scatter([10], [7], marker='s', s=55, facecolors='none', edgecolors='#2ed8e6', linewidths=2)
    ax.scatter([18], [7], marker='*', s=95, color='#69df74')
    ax.set(title=f'{title}\nTotal: {grid.sum():.3f} units', xlabel='Cell X (0.01 m spacing)', ylabel='Cell Z')
    ax.text(0.02, 0.02, 'Square: nest   Star: food', color='white', transform=ax.transAxes, fontsize=8)
fig.colorbar(image, ax=axs, shrink=0.78, label='Local trail units (same scale in all panels)')
save(fig, 'trail_fields')

ablations = rows('ablation_summary.csv')
fig, axs = plt.subplots(2, 2, figsize=(12, 8), layout='constrained')
fig.suptitle('Original S2 ablations retained: memory gains persist, trail-only gains vary\nENGINEERING_FIXTURE | 16 seeds per cell | 12 workers | 30 simulated minutes', fontsize=13)
treatments = ['none', 'trails', 'memory', 'both']
for column, layout in enumerate(['open', 'barrier']):
    for row_index, (metric, scale, ylabel) in enumerate([('deliveries', 1, 'Completed deliveries'), ('coverage', 100, 'Visited walkable cells (%)')]):
        ax = axs[row_index, column]
        for model, offset in [('s2-baseline', -0.18), ('s2.1', 0.18)]:
            selected = [next(r for r in ablations if r['model'] == model and r['layout'] == layout and r['treatment'] == t and r['metric'] == metric) for t in treatments]
            ax.bar(np.arange(4)+offset, [float(r['mean'])*scale for r in selected], width=0.34,
                   yerr=[float(r['sample_sd'])*scale for r in selected], capsize=3, color=COLORS[model], label=model, alpha=0.9)
        ax.set(xticks=range(4), xticklabels=['Neither', 'Trails only', 'Memory only', 'Both'], ylabel=ylabel, title=f'{layout.capitalize()} surface: mean +/- sample SD')
        ax.set_ylim(bottom=0)
        if row_index == 1:
            ax.set_ylim(0, 100)
        if row_index == 0:
            ax.legend(fontsize=9)
save(fig, 'ablations')
print(f'PASS rendered six figure files in {OUTPUT.relative_to(ROOT)}')
