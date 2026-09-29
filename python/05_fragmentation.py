"""05 - Vegetation fragmentation by segment-zone (DS2020, DS2024, DS2026)
and a difference-in-differences test on the matched sample.

Inputs  : data/rasters/LC_DS{year}_{side}.tif (1 veg, 2 sand/bare, 3 beach, 4 built, 5 water, 0 no data)
          data/vectors/segment_zones_all.shp, results/seg_cov_w.csv (matching weights from 04)
Outputs : results/fragmentation_by_unit.csv, fragmentation_summary.csv, fragmentation_did.csv
Landscape per segment: 'corridor' = footprint + 0-500 m, then 500 m-1 km and 1-5 km.
Metrics (8-neighbour patches, patches < 0.1 ha = 10 px removed first):
  PLAND  % of land that is vegetation
  PD     vegetation patches per 100 ha of land
  MPA    mean patch area (ha)
  ED     vegetation edge density (m per ha of land)
  LPI    largest patch as % of land
"""
import sys, numpy as np, pandas as pd, geopandas as gpd, rasterio, statsmodels.api as sm
from rasterio import features
from scipy import ndimage

sys.path.insert(0, __import__('os').path.dirname(__file__))
from paths import RAS, VEC, RES
ZON = VEC / 'segment_zones_all.shp'
COV = RES / 'seg_cov_w.csv'
YEARS, MIN_PX, PX_HA = [2020, 2024, 2026], 10, 0.01
EIGHT = np.ones((3, 3), int)

z = gpd.read_file(ZON).to_crs(32631)
z['land'] = z.zone.map({'F': 'corridor', 'B1': 'corridor', 'B2': 'B2', 'B3': 'B3'})
units = z.dissolve(by=['seg_id', 'land'], as_index=False)[['seg_id', 'land', 'side', 'treated', 'geometry']]

def metrics(lc, mask):
    land = mask & (lc >= 1) & (lc <= 4)
    n_land = land.sum()
    if n_land == 0:
        return None
    veg = mask & (lc == 1)
    lab, n = ndimage.label(veg, structure=EIGHT)
    sizes = ndimage.sum(veg, lab, index=np.arange(1, n + 1))
    keep_ids = np.where(sizes >= MIN_PX)[0] + 1
    veg = np.isin(lab, keep_ids)
    sizes = sizes[sizes >= MIN_PX]
    # edges between vegetation and any other cell inside the landscape (4-neighbour, 10 m each)
    mh, mv = mask[:, :-1] & mask[:, 1:], mask[:-1, :] & mask[1:, :]
    e = ((veg[:, :-1] != veg[:, 1:]) & mh).sum() + ((veg[:-1, :] != veg[1:, :]) & mv).sum()
    land_ha = n_land * PX_HA
    return dict(land_ha=land_ha, veg_ha=veg.sum() * PX_HA, PLAND=100 * veg.sum() / n_land,
                NP=len(sizes), PD=100 * len(sizes) / land_ha,
                MPA=(sizes.mean() * PX_HA) if len(sizes) else np.nan,
                ED=e * 10 / land_ha, LPI=(100 * sizes.max() / n_land) if len(sizes) else 0.0)

rows = []
for side in ['S1', 'W', 'E']:
    u = units[units.side == side].reset_index(drop=True)
    for y in YEARS:
        with rasterio.open(RAS / f'LC_DS{y}_{side}.tif') as r:
            lc = r.read(1)
            idx = features.rasterize(((g, i + 1) for i, g in enumerate(u.geometry)),
                                     out_shape=lc.shape, transform=r.transform, fill=0, dtype='int32')
        objs = ndimage.find_objects(idx)
        for i, sl in enumerate(objs):
            if sl is None:
                continue
            m = metrics(lc[sl], idx[sl] == i + 1)
            if m:
                rows.append(dict(seg_id=u.seg_id[i], land=u.land[i], side=side,
                                 treated=int(u.treated[i]), year=y, **m))
fr = pd.DataFrame(rows)
fr.to_csv(RES / 'fragmentation_by_unit.csv', index=False)

# ---------- summary: Section 1 vs matched controls ----------
w = pd.read_csv(COV)[['seg_id', 'match_w']]
fr = fr.merge(w, on='seg_id', how='left').fillna({'match_w': 0})
base = fr[fr.year == 2020][['seg_id', 'land', 'veg_ha']].rename(columns={'veg_ha': 'veg2020'})
fr = fr.merge(base, on=['seg_id', 'land'])
fr = fr[fr.veg2020 >= 1.0]                        # at least 1 ha of vegetation in 2020
m = fr[fr.match_w > 0]
M = ['PLAND', 'PD', 'MPA', 'ED', 'LPI']
summ = []
for land in ['corridor', 'B2', 'B3']:
    for y in YEARS:
        for t in [1, 0]:
            s = m[(m.land == land) & (m.year == y) & (m.treated == t)]
            vals = {}
            for k in M:
                ok = s[k].notna()
                vals[k] = np.average(s.loc[ok, k], weights=s.loc[ok, 'match_w']) if ok.any() else np.nan
            summ.append(dict(landscape=land, year=y, group='Section 1' if t else 'Matched controls', n=len(s), **vals))
summ = pd.DataFrame(summ)
summ.to_csv(RES / 'fragmentation_summary.csv', index=False)

# ---------- DiD on each metric (unit + year FE, matched weights, SE clustered by segment) ----------
res = []
for land in ['corridor', 'B2', 'B3']:
    s = m[m.land == land].copy()
    s['uid'] = s.seg_id + '_' + s.land
    for k in M:
        s2 = s.dropna(subset=[k]).reset_index(drop=True)
        X = pd.concat([pd.DataFrame({'t2020': ((s2.year == 2020) & (s2.treated == 1)).astype(float),
                                     't2026': ((s2.year == 2026) & (s2.treated == 1)).astype(float)}),
                       pd.get_dummies(s2.uid, dtype=float),
                       pd.get_dummies(s2.year, prefix='yr', drop_first=True, dtype=float)], axis=1)
        fit = sm.WLS(s2[k].astype(float), X, weights=s2.match_w).fit(
            cov_type='cluster', cov_kwds={'groups': pd.factorize(s2.seg_id)[0]})
        ci = fit.conf_int()
        # reference year DS2024: t2026 = extra change 2024->2026 in S1; -t2020 = extra change 2020->2024
        res.append(dict(landscape=land, metric=k, term='Before construction (2020→2024)',
                        estimate=-fit.params['t2020'], ci_low=-ci.loc['t2020', 1], ci_high=-ci.loc['t2020', 0],
                        p=fit.pvalues['t2020']))
        res.append(dict(landscape=land, metric=k, term='Construction (2024→2026)',
                        estimate=fit.params['t2026'], ci_low=ci.loc['t2026', 0], ci_high=ci.loc['t2026', 1],
                        p=fit.pvalues['t2026']))
        res[-1]['n_S1'] = res[-2]['n_S1'] = s2[s2.treated == 1].seg_id.nunique()
        res[-1]['n_ctrl'] = res[-2]['n_ctrl'] = s2[s2.treated == 0].seg_id.nunique()
res = pd.DataFrame(res)
res.to_csv(RES / 'fragmentation_did.csv', index=False)
pd.set_option('display.width', 200)
print(summ.round(2).to_string())
print(res.round(3).to_string())
