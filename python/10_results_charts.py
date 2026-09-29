"""10 - Publication charts for Figures 6 and 7 (also used in the README).

Figure 6: cumulative % of DS2020 vegetation lost, Section 1 vs all control segments, one panel per zone.
          Pooled like the Summary sheet: total ha lost / total DS2020 vegetation ha (units >= 1 ha).
Figure 7: event-study coefficients (matched sample, specification B) with 95% CIs, one panel per zone.

Inputs : data/tables/segment_zone_panel_DS2020_2026.csv, results/event_study.csv (from 04)
Outputs: results/Figure6_loss_trajectories.png, results/Figure7_event_study.png (300 dpi)
"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
import pandas as pd, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from paths import TAB, RES, ZONES

S1, CTRL, INK, MUTED, GRID = '#C8412F', '#2F6DB3', '#222222', '#6B6B6B', '#E3E3E3'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9, 'axes.edgecolor': MUTED,
                     'axes.labelcolor': INK, 'xtick.color': MUTED, 'ytick.color': MUTED,
                     'axes.spines.top': False, 'axes.spines.right': False})
YEARS = list(range(2020, 2027))

def start_line(ax):
    ax.axvline(2024.5, color=MUTED, lw=0.9, ls=':', label='Construction starts (Mar 2024)')

# ---------- Figure 6 ----------
d = pd.read_csv(TAB / 'segment_zone_panel_DS2020_2026.csv')
d = d[d.a_veg2020 >= 1e4]
g = d.groupby(['zone', 'treated', 'year'])[['a_veglost', 'a_veg2020']].sum()
g = (100 * g.a_veglost / g.a_veg2020).rename('pct').reset_index()
fig, axs = plt.subplots(1, 4, figsize=(10, 3.2), sharex=True)
for ax, (z, zl), lab in zip(axs, ZONES, 'abcd'):
    ends = {}
    for t, col, name, ls in [(1, S1, 'Section 1', '-'), (0, CTRL, 'Controls', '--')]:
        s = g[(g.zone == z) & (g.treated == t)].sort_values('year')
        ax.plot(s.year, s.pct, color=col, lw=2, ls=ls, marker='o', ms=4, label=name)
        ends[t] = s.pct.iloc[-1]
    gap = ax.get_ylim()[1] * 0.06          # keep the two end labels apart
    off = {1: 0, 0: 0}
    if abs(ends[1] - ends[0]) < gap:
        hi = 1 if ends[1] >= ends[0] else 0
        off[hi], off[1 - hi] = gap / 2, -gap / 2
    for t in (1, 0):
        ax.annotate(f'{ends[t]:.0f}%', (2026, ends[t]), xytext=(2026.25, ends[t] + off[t]), textcoords='data',
                    va='center', fontsize=8, color=INK)
    ax.set_title(f'({lab}) {zl}', loc='left', fontsize=9.5, color=INK, fontweight='bold')
    ax.set_xticks(YEARS[::2]); ax.set_xlim(2019.6, 2026.9)
    ax.grid(axis='y', color=GRID, lw=0.7); ax.set_ylim(bottom=0)
    start_line(ax)
axs[0].set_ylabel('% of DS2020 vegetation lost')
fig.supxlabel('Dry season', fontsize=9, color=INK, y=0.1)
fig.legend(*axs[0].get_legend_handles_labels(), loc='lower center', ncol=3, frameon=False, fontsize=8)
fig.tight_layout(rect=(0, 0.08, 1, 1))
fig.savefig(RES / 'Figure6_loss_trajectories.png', dpi=300, facecolor='white')

# ---------- Figure 7 ----------
es = pd.read_csv(RES / 'event_study.csv')
es = es[es.spec.str.startswith('B')]
fig, axs = plt.subplots(1, 4, figsize=(10, 3.2), sharex=True)
for ax, (z, zl), lab in zip(axs, ZONES, 'abcd'):
    s = es[es.zone == z].sort_values('year')
    ax.axhline(0, color=MUTED, lw=0.8)
    ax.vlines(s.year, s.ci_low, s.ci_high, color=S1, lw=1.6)
    ax.plot(s.year, s.estimate, 'o', color=S1, ms=5, mec='white', mew=1, label='Estimate ± 95% CI')
    ax.set_title(f'({lab}) {zl}', loc='left', fontsize=9.5, color=INK, fontweight='bold')
    ax.set_xticks(range(2021, 2027)); ax.set_xticklabels(['21', '22', '23', '24', '25', '26'])
    ax.set_xlim(2020.5, 2026.5); ax.grid(axis='y', color=GRID, lw=0.7)
    start_line(ax)
axs[0].set_ylabel('Section 1 − controls (pp)')
fig.supxlabel('Dry season (DS20xx; reference DS2024)', fontsize=9, color=INK, y=0.1)
fig.legend(*axs[0].get_legend_handles_labels(), loc='lower center', ncol=2, frameon=False, fontsize=8)
fig.tight_layout(rect=(0, 0.08, 1, 1))
fig.savefig(RES / 'Figure7_event_study.png', dpi=300, facecolor='white')
print('saved Figure6 and Figure7')
