"""09 - Figure 2 (analytical workflow), drawn with matplotlib.

python python/09_figure2_workflow.py          -> results/Figure2_workflow.png
python python/09_figure2_workflow.py --markup -> results/Figure2_workflow_markup.png
   (the same diagram with the boxes that changed in the final version outlined, used as a guide
    for redrawing the figure by hand in draw.io)
"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from paths import RES

MARKUP = '--markup' in sys.argv
plt.rcParams['font.family'] = 'DejaVu Serif'
C = {'data': ('#DADADA', '#333333'), 'proc': ('#C5E3F6', '#2B6CB0'), 'acc': ('#FBE0D0', '#C05621'),
     'stat': ('#C9EFC9', '#2F7D32'), 'out': ('#13263F', '#13263F')}

fig = plt.figure(figsize=(12, 11.5), dpi=200)
ax = fig.add_axes([0.01, 0.01, 0.98, 0.98]); ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis('off')

def box(x, y, w, h, title, body, kind, note=None):
    fc, ec = C[kind]
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.3,rounding_size=1.6', fc=fc, ec=ec, lw=1.5))
    tc = 'white' if kind == 'out' else '#111'
    ax.text(x + w / 2, y + h - 2.0, title, ha='center', va='top', fontsize=12, fontweight='bold', color=tc)
    ax.text(x + w / 2, y + h - 5.2, body, ha='center', va='top', fontsize=9.6, color=tc, linespacing=1.4)
    if MARKUP and note:
        ax.add_patch(FancyBboxPatch((x - 0.9, y - 0.9), w + 1.8, h + 1.8, boxstyle='round,pad=0.3,rounding_size=2',
                                    fc='none', ec='#E4007C', lw=2.4, ls='--'))
        ax.text(x + w + 1.4, y + h - 0.5, note, fontsize=8.5, color='#E4007C', fontweight='bold', va='top', ha='left')

def arr(x1, y1, x2, y2):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle='-|>', mutation_scale=15, lw=1.4, color='#111'))

ax.text(22, 98.5, 'REMOTE SENSING', ha='center', va='top', fontsize=13, fontweight='bold')
ax.text(72, 98.5, 'STUDY DESIGN', ha='center', va='top', fontsize=13, fontweight='bold')
W, H = 40, 10.5
L, Rx = 2, 52
box(L, 83, W, H, 'Satellite data', 'Sentinel-2 SR (Cloud Score+ ≥ 0.60)\nSentinel-1 GRD (VV, VH) · SRTM DEM', 'data',
    note='FIX:\nadd\nSentinel-1\n& SRTM')
box(L, 68, W, H, 'Dry-season composites', 'DS2020–DS2026 (1 Nov – 31 Mar)\nmedian reflectance + indices', 'proc')
box(L, 53, W, H, 'Random Forest classification', '300 trees, training polygons\nvegetation, sand/bare, beach, built-up, water', 'proc')
box(L, 38, W, H, 'Accuracy assessment', '300 stratified points (Wayback, PlanetScope)\nerror-adjusted areas (Olofsson et al., 2014)', 'acc',
    note='FIX:\n"et al.,\n2014"')
box(Rx, 83, W, H, 'Road geometry', 'Centreline + construction footprint\n(Wayback, PlanetScope; mean width 69 m)', 'data')
box(Rx, 68, W, H, 'Section 1 units', '47 × 1 km segments × 4 zones:\nfootprint, 0–500 m, 0.5–1 km, 1–5 km', 'proc')
box(Rx, 53, W, H, 'Control units', '24 coastal stretches screened\n66 western + 44 eastern segments', 'proc')
box(Rx, 38, W, H, 'Analysis units', '157 segments × 4 zones\n= 628 segment–zone units', 'acc')
for x in (L + W / 2, Rx + W / 2):
    for y in (83, 68, 53):
        arr(x, y - 0.4, x, y - 4.1)
box(20, 22, 56, 9.5, 'Panel table', '% of DS2020 vegetation lost, per unit and year (DS2020–DS2026)', 'stat')
arr(L + W / 2, 37.6, 38, 31.9); arr(Rx + W / 2, 37.6, 58, 31.9)
box(2, 3, 44, 13, 'Matching & difference-in-differences',
    'Mahalanobis matching (k = 2); event-study\nand pooled DiD (unit + year fixed effects,\nclustered SE, wild bootstrap)', 'stat')
box(50, 3, 30, 13, 'Spatial pattern',
    'Hotspots of persistent loss\n(Getis-Ord Gi*, FDR)\nVegetation fragmentation\n(patch metrics, matched DiD)', 'stat',
    note=None)
arr(40, 21.6, 26, 16.4); arr(56, 21.6, 64, 16.4)
box(84, 3, 14.5, 28.5, 'Results', 'Construction-\nattributable\nvegetation loss,\nits location and\nfragmentation\nby zone', 'out')
arr(80.4, 9.5, 83.6, 9.5)
# Matching -> Results, routed underneath the Spatial pattern box
ax.plot([24, 24, 91.2], [2.6, 0.8, 0.8], color='#111', lw=1.4)
arr(91.2, 0.8, 91.2, 2.6)
if MARKUP:
    ax.add_patch(FancyBboxPatch((49.1, 2.1), 31.8, 14.8, boxstyle='round,pad=0.3,rounding_size=2',
                                fc='none', ec='#E4007C', lw=2.4, ls='--'))
    ax.text(66.5, 21.8, 'NEW box\n+ both arrows\ninto Results', fontsize=8.5, color='#E4007C', fontweight='bold', ha='left', va='top')
out = RES / ('Figure2_workflow_markup.png' if MARKUP else 'Figure2_workflow.png')
fig.savefig(out, dpi=200, facecolor='white')
print('saved', out)
