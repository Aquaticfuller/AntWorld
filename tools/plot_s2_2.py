#!/usr/bin/env python3
"""Render S2.2 mechanism, sensitivity and trajectory figures from audited raw evidence."""
import argparse
import csv
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--packages', type=Path)
args = parser.parse_args()
if args.packages:
    sys.path.insert(0, str(args.packages.resolve()))
os.environ.setdefault('MPLCONFIGDIR', str(ROOT/'out/s2_2-matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

DATA = ROOT/'experiments/s2_2'; OUTPUT = DATA/'figures'; OUTPUT.mkdir(exist_ok=True)
plt.rcParams.update({'font.size': 10, 'svg.fonttype': 'none', 'svg.hashsalt': 'antworld-s2.2', 'savefig.dpi': 150,
                     'axes.spines.top': False, 'axes.spines.right': False})
COLORS = {'s2.1': '#727e91', 's2.2': '#087f8c', 'absent': '#bc6341'}


def read(name):
    with (DATA/name).open(newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def save(fig, name):
    path = OUTPUT/f'{name}.svg'
    fig.savefig(path, metadata={'Date': None, 'Creator': 'AntWorld S2.2; ENGINEERING_FIXTURE'})
    path.write_text('\n'.join(line.rstrip() for line in path.read_text(encoding='utf-8').splitlines())+'\n', encoding='utf-8', newline='\n')
    fig.savefig(OUTPUT/f'{name}.png', metadata={'Software': 'AntWorld S2.2; ENGINEERING_FIXTURE'})
    plt.close(fig)


summary, paired = read('summary.csv'), read('paired.csv')


def pick(model, context, metric, treatment='present', age=0, persistence=20):
    return next(r for r in summary if (r['model'], r['context'], r['metric'], r['treatment'], int(r['age_ms']), int(r['persistence_weight'])) ==
                (model, context, metric, treatment, age, persistence))


fig, axs = plt.subplots(2, 2, figsize=(12, 8), layout='constrained')
fig.suptitle('Local trail influence exists; the correction permits recovery after departure\nENGINEERING_FIXTURE | 512 seeds x 2 reflections | unchanged response coefficient', fontsize=13)
for ax, contexts, metric, title in ((axs[0,0], ['y_symmetric', 'y_conflict', 'lost'], 'selected_marked', 'Initial marked choice / local correction'),
                                   (axs[0,1], ['straight', 'bend'], 'occupancy', 'Open-arena occupancy on line (24 moves)'),
                                   (axs[1,0], ['straight', 'bend'], 'streak3', 'At least three consecutive on-line moves')):
    for model, offset in [('s2.1', -.18), ('s2.2', .18)]:
        group = [pick(model, c, metric) for c in contexts]; y = np.array([float(r['mean'])*100 for r in group])
        error = np.array([[float(r['mean'])-float(r['ci_low']) for r in group], [float(r['ci_high'])-float(r['mean']) for r in group]])*100
        ax.errorbar(np.arange(len(contexts))+offset, y, yerr=error, fmt='o', capsize=4, color=COLORS[model], label=model)
    ax.plot(range(len(contexts)), [float(pick('s2.2', c, metric, 'absent')['mean'])*100 for c in contexts], 'x--', color=COLORS['absent'], label='Absent / blind')
    ax.set(xticks=range(len(contexts)), xticklabels=[c.replace('_', ' ') for c in contexts], title=title, ylabel='Percent (cluster normal 95% CI)', ylim=(-5, 100)); ax.legend(fontsize=8)
survival = read('departure_survival.csv'); ax = axs[1,1]
for context, style in [('straight', '-'), ('bend', '--')]:
    for treatment in ['present', 'absent']:
        group = [r for r in survival if r['model'] == 's2.2' and r['context'] == context and r['treatment'] == treatment]
        ax.step([int(r['step']) for r in group], [float(r['not_yet_departed'])*100 for r in group], where='post',
                color=COLORS['s2.2' if treatment == 'present' else 'absent'], linestyle=style, label=f'{context}, {treatment}')
ax.set(title='Initial departure unchanged by the correction', xlabel='Completed moves', ylabel='Not yet departed (%)', xlim=(0,24), ylim=(0,105)); ax.legend(fontsize=8)
save(fig, 'mechanisms')

fig, axs = plt.subplots(2, 2, figsize=(12, 8), layout='constrained')
fig.suptitle('Planned sensitivity and limits: local influence is not a food-direction signal\nENGINEERING_FIXTURE | response stays 180 | no coefficient selected from these outcomes', fontsize=13)
sensitivity = read('sensitivity_balanced.csv')
for ax, context in zip(axs[0], ['straight', 'bend']):
    for inertia, color in [(0, '#81956d'), (20, '#087f8c'), (40, '#aa6045')]:
        group = [next(r for r in sensitivity if r['model'] == 's2.2' and r['context'] == context and r['metric'] == 'occupancy' and int(r['persistence_weight']) == inertia and int(r['age_ms']) == age) for age in [0,60000,180000]]
        y = np.array([float(r['difference'])*100 for r in group])
        error = np.array([[float(r['difference'])-float(r['ci_low']) for r in group], [float(r['ci_high'])-float(r['difference']) for r in group]])*100
        ax.errorbar([0,60,180], y, yerr=error, fmt='o-', capsize=3, color=color, label=f'Persistence {inertia}')
    ax.axhline(0, color='gray', linestyle=':'); ax.set(title=f'{context}: paired occupancy, seeds 1-128', xlabel='Initial field age (s)', ylabel='Percentage points (95% CI)', xticks=[0,60,180]); ax.legend(fontsize=8)
effects = read('social_effects.csv')
for ax, metric, scale, label in [(axs[1,0], 'discovery_rate', 100, 'Discovery difference (percentage points)'), (axs[1,1], 'restricted_discovery_s', 1, 'Restricted discovery time difference (s)')]:
    for model, offset in [('s2.1', -5), ('s2.2', 5)]:
        group = [next(r for r in effects if r['model'] == model and r['metric'] == metric and int(r['age_ms']) == age) for age in [0,180000,600000]]
        y = np.array([float(r['difference'])*scale for r in group])
        error = np.array([[float(r['difference'])-float(r['ci_low']) for r in group], [float(r['ci_high'])-float(r['difference']) for r in group]])*scale
        ax.errorbar(np.array([0,180,600])+offset, y, yerr=error, fmt='o', capsize=4, color=COLORS[model], label=model)
    ax.axhline(0, color='gray', linestyle=':'); ax.set(title='Original autonomous scout / naive-worker experiment', xlabel='Release delay (s)', ylabel=label+'\nPaired seed-cluster bootstrap 95% CI'); ax.legend(fontsize=8)
save(fig, 'sensitivity_and_social')

# First declared seed and unreflected orientation; no selection by success.
raw = read('baseline/local.csv') + read('fixed/local.csv')
fig, axs = plt.subplots(2, 3, figsize=(12, 8), layout='constrained')
fig.suptitle('Actual policy trajectories on a controlled, directionless substrate\nENGINEERING_FIXTURE | fixed seed 1, unreflected | 24 local moves | no food in assay', fontsize=13)
for row, context in enumerate(['straight', 'bend']):
    for column, (model, treatment) in enumerate([('s2.1','absent'), ('s2.1','present'), ('s2.2','present')]):
        r = next(r for r in raw if r['model'] == model and r['context'] == context and r['treatment'] == treatment and r['seed'] == '1' and r['mirror'] == '0' and r['primary'] == '1')
        points = np.array([tuple(map(int, p.split(':'))) for p in r['trajectory'].split(';')]); ax = axs[row,column]
        if context == 'straight': ax.plot([40,40], [0,48], color='#d6b76b', linewidth=5, alpha=.6, label='Reference substrate')
        else: ax.plot([40,40,66], [0,26,26], color='#d6b76b', linewidth=5, alpha=.6, label='Reference substrate')
        ax.plot(points[:,0], points[:,1], '.-', color=COLORS['absent' if treatment == 'absent' else model], linewidth=1.3)
        ax.scatter(*points[0], marker='s', s=35, color='black', label='Start'); ax.scatter(*points[-1], marker='x', s=50, color='black', label='End')
        ax.set(title=f'{context} | {model} | {treatment}', xlabel='Cell X (0.01 m)', ylabel='Cell Z', xlim=(15,66), ylim=(0,48), aspect='equal')
        if row == 0 and column == 0: ax.legend(fontsize=7)
save(fig, 'trajectories')
print('PASS rendered S2.2 figures (three SVG and three PNG files)')
