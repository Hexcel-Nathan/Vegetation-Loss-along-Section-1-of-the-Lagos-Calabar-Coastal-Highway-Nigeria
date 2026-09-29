"""02 - Baseline (DS2020) covariates for every 1 km segment, used for matching (Section 3.7).

For each segment the four zones are pooled and the DS2020 land-cover areas turned into shares:
  veg       vegetation / land            (land = everything except water, DS2020)
  built     built-up / land
  bare      (sand/bare + beach) / land
  waterfrac water / total area of the segment's cells
  elev      area-weighted mean SRTM elevation (m)
  dcbd_km   straight-line distance from the segment midpoint to Lagos Island CBD (3.3896 E, 6.4549 N)

Inputs : data/tables/segment_zone_panel_DS2020_2026.csv (from gee/04 + gee/05)
         data/vectors/S1_segments.shp, results/vectors/C_segments.shp (from 01)
Output : results/seg_cov.csv  (checked against the copy in data/tables that the paper used)
"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, pandas as pd, geopandas as gpd
from pyproj import Transformer
from paths import TAB, VEC, RES

d = pd.read_csv(TAB / 'segment_zone_panel_DS2020_2026.csv')
cols = ['a_total', 'a_veg', 'a_built', 'a_sand', 'a_water', 'a_beach', 'elev_x_area', 'a_land2020']
b = (d[d.year == 2020].groupby(['seg_id', 'treated', 'side'], as_index=False)[cols].sum())
b['veg'] = b.a_veg / b.a_land2020
b['built'] = b.a_built / b.a_land2020
b['bare'] = (b.a_sand + b.a_beach) / b.a_land2020
b['waterfrac'] = b.a_water / b.a_total
b['elev'] = b.elev_x_area / b.a_total

segs = pd.concat([gpd.read_file(VEC / 'S1_segments.shp')[['seg_id', 'geometry']],
                  gpd.read_file(RES / 'vectors' / 'C_segments.shp')[['seg_id', 'geometry']]])
mid = segs.set_index('seg_id').geometry.interpolate(0.5, normalized=True)
cx, cy = Transformer.from_crs(4326, 32631, always_xy=True).transform(3.3896, 6.4549)
b['dcbd_km'] = b.seg_id.map(np.hypot(mid.x - cx, mid.y - cy) / 1000)

b = b[['seg_id', 'treated', 'side'] + cols[:-2] + ['elev_x_area', 'a_land2020', 'veg', 'built', 'bare', 'waterfrac', 'elev', 'dcbd_km']]
b.to_csv(RES / 'seg_cov.csv', index=False)

ref = pd.read_csv(TAB / 'seg_cov.csv').set_index('seg_id')
chk = b.set_index('seg_id').loc[ref.index]
diff = max(np.abs(chk[v] - ref[v]).max() for v in ['veg', 'built', 'bare', 'waterfrac', 'elev', 'dcbd_km'])
print(f'{len(b)} segments written; max difference from the published covariates = {diff:.2e}')
