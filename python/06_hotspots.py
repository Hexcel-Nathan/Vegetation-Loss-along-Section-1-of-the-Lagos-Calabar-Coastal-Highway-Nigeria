"""06 - Hotspots of vegetation loss in the Section 1 corridor (Getis-Ord Gi*).

Two periods, both using persistent loss to limit commission error:
  before construction : vegetation in DS2020, non-vegetation in both DS2023 and DS2024
  during construction : vegetation in DS2024, non-vegetation in both DS2025 and DS2026
Variable per hexagon: % of the starting vegetation lost (hexagons with >= 1 ha of starting
vegetation). Gi* uses a fixed distance band, 999 permutations, and Benjamini-Hochberg FDR (q = 0.05).
Sensitivity: 2, 5 and 10 ha hexagons; 500 m and 1000 m distance bands.

Inputs : data/rasters/LC_DS{2020,2023,2024,2025,2026}_S1.tif, data/vectors/segment_zones_all.shp
Outputs: results/hotspot_summary.csv, results/vectors/hotspots_S1_5ha.shp (the map in the paper)
"""
import sys, warnings, numpy as np, pandas as pd, geopandas as gpd, rasterio
warnings.filterwarnings("ignore")
from rasterio import features
from shapely.geometry import Polygon
from libpysal.weights import DistanceBand
from esda.getisord import G_Local
from statsmodels.stats.multitest import multipletests

sys.path.insert(0, __import__('os').path.dirname(__file__))
from paths import RAS, VEC, RES
ZON = VEC / 'segment_zones_all.shp'
np.random.seed(2026)

lc = {}
for y in [2020, 2023, 2024, 2025, 2026]:
    with rasterio.open(RAS / f'LC_DS{y}_S1.tif') as r:
        lc[y] = r.read(1); T = r.transform; shape = r.shape
veg = {y: lc[y] == 1 for y in lc}
nonveg = {y: (lc[y] >= 2) & (lc[y] <= 5) for y in lc}
valid = np.logical_and.reduce([lc[y] > 0 for y in lc])
pre_start = veg[2020] & valid
pre_loss = pre_start & nonveg[2023] & nonveg[2024]
con_start = veg[2024] & valid
con_loss = con_start & nonveg[2025] & nonveg[2026]

z = gpd.read_file(ZON).to_crs(32631)
s1 = z[z.side == 'S1']
area_geom = s1.union_all()
foot = s1[s1.zone == 'F'].union_all()

def hexgrid(bounds, area_ha):
    a = np.sqrt(2 * area_ha * 1e4 / (3 * np.sqrt(3)))          # side length (m)
    w, h = 2 * a, np.sqrt(3) * a
    x0, y0, x1, y1 = bounds
    hexes, col, x = [], 0, x0
    while x < x1 + w:
        y = y0 - (h / 2 if col % 2 else 0)
        while y < y1 + h:
            hexes.append(Polygon([(x + a * np.cos(t), y + a * np.sin(t)) for t in np.radians(range(0, 360, 60))]))
            y += h
        x += 1.5 * a; col += 1
    return gpd.GeoDataFrame(geometry=hexes, crs=32631)

def run(area_ha, band):
    g = hexgrid(area_geom.bounds, area_ha)
    g = g[g.intersects(area_geom)].copy()
    g['geometry'] = g.geometry.intersection(area_geom)
    g = g[g.area >= 0.5 * area_ha * 1e4].reset_index(drop=True)    # keep hexagons at least half inside
    idx = features.rasterize(((geom, i + 1) for i, geom in enumerate(g.geometry)),
                             out_shape=shape, transform=T, fill=0, dtype='int32')
    n = len(g) + 1
    cnt = lambda m: np.bincount(idx[m].ravel(), minlength=n)[1:] * 0.01   # ha
    g['pre_veg_ha'], g['pre_loss_ha'] = cnt(pre_start), cnt(pre_loss)
    g['con_veg_ha'], g['con_loss_ha'] = cnt(con_start), cnt(con_loss)
    g['dist_road_m'] = g.geometry.centroid.distance(foot)
    for p in ['pre', 'con']:
        ok = g[f'{p}_veg_ha'] >= 1.0
        g[f'{p}_pct'] = np.where(ok, 100 * g[f'{p}_loss_ha'] / g[f'{p}_veg_ha'].clip(lower=1e-9), np.nan)
        sub = g[ok]
        pts = np.column_stack([sub.geometry.centroid.x, sub.geometry.centroid.y])
        W = DistanceBand(pts, threshold=band, binary=True, silence_warnings=True)
        gi = G_Local(sub[f'{p}_pct'].values, W, star=True, permutations=999, seed=2026)
        q = multipletests(gi.p_sim, alpha=0.05, method='fdr_bh')[0]
        cls = np.where(q & (gi.Zs > 0), 'Hot spot', np.where(q & (gi.Zs < 0), 'Cold spot', 'Not significant'))
        g.loc[ok, f'{p}_giz'] = gi.Zs
        g.loc[ok, f'{p}_p'] = gi.p_sim
        g.loc[ok, f'{p}_cls'] = cls
        g[f'{p}_cls'] = g[f'{p}_cls'].fillna('Too little vegetation')
    return g

def describe(g, area_ha, band):
    out = []
    for p, lab in [('pre', 'Before construction (2020→2024)'), ('con', 'Construction (2024→2026)')]:
        hot = g[g[f'{p}_cls'] == 'Hot spot']
        out.append(dict(hex_ha=area_ha, band_m=band, period=lab, hexagons=int(g[f'{p}_pct'].notna().sum()),
                        hot=len(hot), cold=int((g[f'{p}_cls'] == 'Cold spot').sum()),
                        hot_within_500m_pct=100 * (hot.dist_road_m <= 500).mean() if len(hot) else np.nan,
                        all_within_500m_pct=100 * (g[g[f'{p}_pct'].notna()].dist_road_m <= 500).mean(),
                        median_hot_dist_m=hot.dist_road_m.median() if len(hot) else np.nan,
                        loss_ha=g[f'{p}_loss_ha'].sum()))
    return out

rows = []
for area_ha in [2, 5, 10]:
    for band in [500, 1000]:
        g = run(area_ha, band)
        rows += describe(g, area_ha, band)
        if area_ha == 5 and band == 500:
            g.to_file(RES / 'vectors' / 'hotspots_S1_5ha.shp')
res = pd.DataFrame(rows)
res.to_csv(RES / 'hotspot_summary.csv', index=False)
pd.set_option('display.width', 200)
print(res.round(1).to_string())
