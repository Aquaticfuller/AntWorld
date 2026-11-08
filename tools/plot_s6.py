"""Render static S6 scientific figures from all audited seeds and timing samples."""
import csv
import os
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR', str(ROOT/'out/matplotlib'))
sys.path.insert(0, str(ROOT/'.tools/s2_1-python'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from analyze_s6 import resamples

DATA = ROOT/'experiments/s6'
FIGURES = DATA/'figures'
COLORS = {'supplied': '#176e87', 'protein_absent': '#c67c29',
          'food_absent': '#a5404b', 'sealed': '#6551a3'}
LABELS = {'supplied': 'Supplied', 'protein_absent': 'Protein absent',
          'food_absent': 'Food absent', 'sealed': 'Sealed access'}


def read(name):
    with (DATA/name).open(encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream))


def save(fig, name):
    fig.savefig(FIGURES/f'{name}.png', dpi=170, metadata={'Software': 'AntWorld S6 validation'})
    fig.savefig(FIGURES/f'{name}.svg', metadata={'Date': None, 'Creator': 'AntWorld S6 validation'})
    svg = FIGURES/f'{name}.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text(encoding='utf-8').splitlines())+'\n',
                   encoding='utf-8', newline='\n')
    plt.close(fig)


def band(ax, rows, condition, field, label, color, scale=1):
    # Mirrors are paired within seed; execution modes are never independent N.
    grouped = defaultdict(list)
    for r in rows:
        if r['condition'] == condition:
            grouped[(int(r['seed']), int(r['time_ms']))].append(float(r[field])/scale)
    seeds = sorted({s for s, _ in grouped})
    times = sorted({t for _, t in grouped})
    values = np.array([[np.mean(grouped[(s, t)]) for t in times] for s in seeds])
    means = values[np.array(resamples(len(seeds)))].mean(axis=1)
    low, high = np.quantile(means, [.025, .975], axis=0)
    x = np.array(times)/1000
    ax.plot(x, values.mean(axis=0), color=color, label=label)
    ax.fill_between(x, low, high, color=color, alpha=.15, linewidth=0)


def nutrition():
    rows = read('analysis/nutrition.csv')
    fig, axes = plt.subplots(2, 2, figsize=(11.7, 8.1), layout='constrained')
    for ax, stage in zip(axes[0], ('egg', 'larva')):
        for policy, label, color, dx in [('legacy', 'Legacy proportional gift', '#a5404b', -.08),
                                         ('local_demand', 'Local deficit cap', '#176e87', .08)]:
            data = [r for r in rows if r['archive'] == 'nutrition_final' and r['stage'] == stage
                    and r['policy'] == policy and r['metric'] == 'adult_brood']
            data.sort(key=lambda r: int(r['protein_per_nurse_ug']))
            y = np.array([float(r['mean']) for r in data])
            err = np.array([[float(r['mean'])-float(r['ci95_low']) for r in data],
                            [float(r['ci95_high'])-float(r['mean']) for r in data]])
            ax.errorbar(np.array([0, 100, 400])+dx*70, y, yerr=err, marker='o', capsize=4, color=color, label=label)
        ax.set(title=f'Initially {stage}: emergence at 180 s', xticks=[0, 100, 400], xticklabels=['0', '100', '400'],
               xlabel='Initial protein per nurse (ug)', ylabel='Adult brood / 4', ylim=(-.15, 4.4))
        ax.legend(fontsize=8)
    surplus = read('analysis/surplus.csv')
    conditions = ('contact', 'wall', 'range', 'no_response', 'no_protein')
    for stage, color, dx in [('adult', '#176e87', -.09), ('pupa', '#c67c29', .09)]:
        data = [next(r for r in surplus if r['archive'] == 'surplus' and r['condition'] == c
                     and r['initial_donor_stage'] == stage and r['metric'] == 'adult_recipients') for c in conditions]
        y = np.array([float(r['success_rate']) for r in data])
        err = np.array([[float(r['success_rate'])-float(r['success_wilson95_low']) for r in data],
                        [float(r['success_wilson95_high'])-float(r['success_rate']) for r in data]])
        axes[1, 0].errorbar(np.arange(5)+dx, y, yerr=err, color=color, marker='o', capsize=3, linestyle='none',
                           label=f'Initially {stage} donor')
        data = [next(r for r in surplus if r['archive'] == 'surplus_sensitivity' and r['initial_donor_stage'] == stage
                     and r['encounter_budget'] == str(b) and r['metric'] == 'protein_transferred_ug') for b in (8, 16, 32)]
        axes[1, 1].plot(np.arange(3)+dx, [float(r['mean']) for r in data], marker='o', color=color,
                        label=f'Initially {stage} donor')
    axes[1, 0].set(title='Adult-surplus assay: both recipients emerge', ylim=(-.08, 1.15),
                   xticks=range(5), xticklabels=['Contact', 'Wall', 'Range', 'No response', 'No protein'], ylabel='Fraction of 64 cases')
    axes[1, 0].tick_params(axis='x', labelsize=8)
    axes[1, 1].set(title='Surplus sensitivity: all 16 seeds per budget', xticks=range(3), xticklabels=['8', '16', '32'],
                   xlabel='Encounter budget', ylabel='Protein actually transferred (ug)', ylim=(0, 240))
    axes[1, 0].legend(fontsize=8)
    axes[1, 1].legend(fontsize=8)
    for ax in axes.flat:
        ax.grid(alpha=.16)
    fig.suptitle('S6 local nutrient redistribution: supply-limited failures retained\n'
                 'Top: 95% seed bootstrap intervals (64 seeds); lower left: Wilson intervals', fontsize=12)
    fig.supxlabel('ENGINEERING_FIXTURE | Real crop transfers; unchanged physiological rates | No global allocation', fontsize=9)
    save(fig, 'nutrition_and_surplus')


def ecology():
    series = read('integrated/time_series.csv')
    raw = [r for r in read('integrated/summary.csv') if r['mode'] == 'normal']
    fig, axes = plt.subplots(2, 3, figsize=(14.1, 8.1), layout='constrained')
    fields = [('population.alive', 'Living identities', 'Individuals', 1),
              ('life.emerged', 'Actual adult emergence', 'Cumulative individuals', 1),
              ('body.energy', 'Body energy remaining (dead included)', 'Joules', 1e9),
              ('geometry.edit_count', 'Actual geometry history', 'Ordered edits', 1)]
    for ax, (field, title, unit, scale) in zip(axes.flat, fields):
        for condition in COLORS:
            band(ax, series, condition, field, LABELS[condition], COLORS[condition], scale)
        ax.set(title=title, xlabel='Simulated time (s)', ylabel=unit)
    axes[0, 0].legend(fontsize=8)
    for x, condition in enumerate(COLORS):
        data = [r for r in raw if r['condition'] == condition]
        paired = defaultdict(list)
        for r in data:
            paired[int(r['seed'])].append(float(r['life.deaths']))
        values = [np.mean(paired[s]) for s in sorted(paired)]
        offsets = np.linspace(-.16, .16, len(values))
        axes[1, 1].scatter(x+offsets, values, color=COLORS[condition], s=14, alpha=.7)
        axes[1, 1].plot([x-.2, x+.2], [np.mean(values)]*2, color='black', linewidth=2)
        for field, offset, label, marker in [('checkpoint_bytes', -.12, 'Canonical checkpoint', 'o'),
                                            ('database_bytes', .12, 'SQLite + WAL + SHM', 'x')]:
            values = [int(r[field])/2**20 for r in data]
            axes[1, 2].scatter(x+offset+np.linspace(-.05, .05, len(values)), values,
                              color=COLORS[condition], s=12, marker=marker, alpha=.5,
                              label=label if x == 0 else None)
    labels = ['Supplied', 'No protein', 'No food', 'Sealed']
    axes[1, 1].set(title='Deaths at 600 s: all paired seeds', xticks=range(4), xticklabels=labels, ylabel='Deaths / 45 seeded identities', ylim=(-1, 46))
    axes[1, 2].set(title='Retained evidence size at 600 s', xticks=range(4), xticklabels=labels, ylabel='MiB', yscale='log')
    axes[1, 2].legend(fontsize=8)
    for ax in axes.flat:
        ax.grid(alpha=.16)
    fig.suptitle('S6 integrated ecology: finite resources do not guarantee survival\n'
                 '32 seeds; mirrors averaged within seed; time-course bands are 95% bootstrap intervals', fontsize=12)
    fig.supxlabel('ENGINEERING_FIXTURE | Three exact-continuation modes per case | Every seed and death retained', fontsize=9)
    save(fig, 'ecology_and_history')


def contacts():
    fig, axes = plt.subplots(2, 2, figsize=(11.7, 8.1), layout='constrained')
    for ax, archive, title, layout in [(axes[0, 0], 'contact_initial', 'Initial dense measurement (retained)', 'dense'),
                                      (axes[0, 1], 'performance', 'Final dense measurement', 'dense'),
                                      (axes[1, 0], 'performance', 'Final dispersed measurement', 'dispersed')]:
        raw = read(archive+'/contacts.csv')
        for policy, color in [('exhaustive', '#a5404b'), ('bounded', '#176e87')]:
            medians = []
            for n in (128, 512, 2048):
                values = [float(r['advance_ms']) for r in raw if int(r['population']) == n and r['layout'] == layout and r['policy'] == policy]
                medians.append(np.median(values))
                ax.scatter(n*np.linspace(.94, 1.06, 10), values, color=color, alpha=.35, s=12)
            ax.plot([128, 512, 2048], medians, marker='o', color=color, label=policy)
        ax.set(title=title, xscale='log', yscale='log', xticks=[128, 512, 2048], xticklabels=['128', '512', '2,048'],
               xlabel='Workers', ylabel='Advance 10 simulated seconds (ms)')
        ax.legend(fontsize=8)
    raw = read('performance/contacts.csv')
    for policy, color in [('exhaustive', '#a5404b'), ('bounded', '#176e87')]:
        maximums = [max(int(r['maximum_candidates']) for r in raw if int(r['population']) == n and r['layout'] == 'dense' and r['policy'] == policy) for n in (128, 512, 2048)]
        axes[1, 1].plot([128, 512, 2048], maximums, marker='o', color=color, label=policy)
    axes[1, 1].axhline(16, color='black', linestyle=':', label='Frozen budget 16')
    axes[1, 1].set(title='Dense candidate work: structural bound', xscale='log', yscale='log',
                   xticks=[128, 512, 2048], xticklabels=['128', '512', '2,048'], xlabel='Workers', ylabel='Maximum inspected candidates / decision')
    axes[1, 1].legend(fontsize=8)
    for ax in axes.flat:
        ax.grid(alpha=.16)
    fig.suptitle('S6 contact scaling: all ten repetitions, no timing samples discarded\n'
                 'Lines show medians; dots show measured host variation; initial missed target remains evidence', fontsize=12)
    fig.supxlabel('ENGINEERING_FIXTURE | Candidate cap does not bound total scheduler, allocator or geometry cost', fontsize=9)
    save(fig, 'contact_scaling')


def continuation():
    series = read('long/time_series.csv')
    fig, axes = plt.subplots(1, 3, figsize=(14.0, 4.9), layout='constrained')
    for condition in ('supplied', 'food_absent'):
        band(axes[0], series, condition, 'population.alive', LABELS[condition], COLORS[condition])
    axes[0].set(title='1,800 s continuation: all eight seeds', xlabel='Simulated time (s)', ylabel='Living identities')
    axes[0].legend(fontsize=8)
    rows = read('analysis/ecology.csv')
    for metric, label, color in [('population.alive', 'Living identities', '#176e87'),
                                  ('life.emerged', 'Cumulative emergence', '#c67c29')]:
        data = [r for r in rows if r['suite'] == 'sensitivity' and r['comparison'] == 'endpoint' and r['metric'] == metric]
        data.sort(key=lambda r: int(r['encounter_budget']))
        means = [float(r['mean']) for r in data]
        err = [[float(r['mean'])-float(r['ci95_low']) for r in data], [float(r['ci95_high'])-float(r['mean']) for r in data]]
        axes[1].errorbar(range(3), means, yerr=err, color=color, capsize=4, marker='o', label=label)
    axes[1].set(title='Encounter sensitivity: 16 seeds, 600 s', xticks=range(3), xticklabels=['8', '16', '32'], xlabel='Encounter budget', ylabel='Individuals')
    axes[1].legend(fontsize=8)
    for archive, marker, label in [('integrated', 'o', '600 s: 256 cases'), ('long', 'x', '1800 s: 16 cases')]:
        raw = [r for r in read(archive+'/summary.csv') if r['mode'] == 'normal']
        axes[2].scatter([int(r['events'])/1000 for r in raw], [int(r['database_bytes'])/2**20 for r in raw], marker=marker,
                        s=18, alpha=.5, label=label)
    axes[2].set(title='Storage retains full event history', xlabel='Committed facts (thousands)', ylabel='SQLite + WAL + SHM (MiB)')
    axes[2].legend(fontsize=8)
    for ax in axes:
        ax.grid(alpha=.16)
    fig.suptitle('S6 sensitivity and finite-resource continuation\n95% seed bootstrap intervals; no biological coefficient tuning', fontsize=12)
    fig.supxlabel('ENGINEERING_FIXTURE | 1,800 s is not a months-long ecological or storage validation', fontsize=9)
    save(fig, 'sensitivity_and_continuation')


def main():
    FIGURES.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'svg.hashsalt': 'AntWorld-S6', 'font.size': 10,
                         'axes.spines.top': False, 'axes.spines.right': False})
    nutrition()
    ecology()
    contacts()
    continuation()
    print('Wrote four S6 scientific figures (PNG and SVG)')


if __name__ == '__main__':
    main()
