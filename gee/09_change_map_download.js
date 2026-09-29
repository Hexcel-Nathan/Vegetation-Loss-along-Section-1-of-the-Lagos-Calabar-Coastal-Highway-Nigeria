// 09 - Vegetation change map DS2020 -> DS2026 (Section 1), for the land-cover figure
// Values: 1 vegetation kept, 2 vegetation lost, 3 vegetation gained,
//         4 never vegetation, 5 water in both years

var ASSET = 'projects/lekkiproject/assets/';
var units = ee.FeatureCollection(ASSET + 'segment_zones_all');
var s1 = units.filter(ee.Filter.eq('side', 'S1')).geometry().bounds();

var lc20 = ee.Image(ASSET + 'LC_DS2020');
var lc26 = ee.Image(ASSET + 'LC_DS2026');
var v20 = lc20.eq(1);
var v26 = lc26.eq(1);

var change = ee.Image(4)
  .where(v20.and(v26), 1)
  .where(v20.and(v26.not()), 2)
  .where(v20.not().and(v26), 3)
  .where(lc20.eq(5).and(lc26.eq(5)), 5)
  .updateMask(lc20.mask())
  .rename('change')
  .toByte();

print('Change_2020_2026_S1 (10 m):',
  change.getDownloadURL({name: 'Change_2020_2026_S1', region: s1,
                         scale: 10, crs: 'EPSG:32631', format: 'GEO_TIFF'}));

Map.centerObject(s1, 11);
Map.addLayer(change, {min: 1, max: 5,
  palette: ['2E7D32', 'E6550D', 'A1D99B', 'D9D9D9', 'C6DBEF']}, 'Change 2020-2026');
