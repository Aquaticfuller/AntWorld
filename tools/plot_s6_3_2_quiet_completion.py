"""Plot the predeclared completion extension without replacing historical figures."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analyze_s6_3_1 import read

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'experiments/s6_3_2'
plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False,
                     'savefig.dpi': 180, 'svg.hashsalt': 'AntWorld-S632-quiet-1'})
blocks = [r for r in read(BASE/'completion_analysis/paired_ratios.csv') if r['phase'] == 'birth_advance']
summary = next(r for r in read(BASE/'completion_analysis/growth.csv') if r['phase'] == 'birth_advance')
latency = [r for r in read(BASE/'completion_analysis/latency.csv') if r['phase'] == 'birth_advance' and r['session'] == 'pooled']
fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
for session, color, label in [('1', '#226b89', 'Session 1: quiet extension'), ('2', '#bd8735', 'Session 2: original'), ('3', '#629785', 'Session 3: original')]:
    rows = [r for r in blocks if r['session'] == session]
    axes[0].scatter([int(r['block']) for r in rows], [float(r['ratio']) for r in rows], color=color, label=label)
axes[0].axhline(6, color='#b34b3c', linestyle='--', label='Frozen target')
axes[0].axhline(float(summary['ratio_of_p50']), color='black', label='Pooled p50 ratio')
axes[0].set(title='Funded births: every balanced block', xlabel='Block', ylabel='2048 / 512 advance ratio')
axes[0].legend(fontsize=8)
for i, metric in enumerate(('p50', 'p95', 'p99')):
    axes[1].plot([int(r['population']) for r in latency], [float(r[metric]) for r in latency], marker='o', label=metric)
axes[1].set(title='Complete extension: all measured rows', xlabel='Funded births', ylabel='Advance wall time (ms)')
axes[1].legend()
for ax in axes:
    ax.grid(alpha=.15)
fig.text(.5, .015, '168 planned rows; no timed reruns or exclusions. Original incomplete series and historical failures remain archived.', ha='center', fontsize=8, color='#555555')
fig.tight_layout(rect=(0, .045, 1, .97))
out = BASE/'figures/quiet_birth_completion'
for extension in ('png', 'svg'):
    fig.savefig(out.with_suffix('.'+extension), metadata={'Date': None} if extension == 'svg' else None)
plt.close(fig)
svg = out.with_suffix('.svg')
svg.write_text('\n'.join(x.rstrip() for x in svg.read_text().splitlines())+'\n', encoding='utf-8')
