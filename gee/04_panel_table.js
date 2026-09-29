// ===== Lagos–Calabar Section 1: STAGE 3 – results table (every unit, every year) =====
var ASSET = 'projects/lekkiproject/assets/';
var units = ee.FeatureCollection(ASSET + 'segment_zones_all');
var YEARS = [2020, 2021, 2022, 2023, 2024, 2025, 2026];

// Show the quick accuracy check result in the Console
print('Quick check (held-out polygons):', ee.FeatureCollection(ASSET + 'quick_check_v2'));

var area   = ee.Image.pixelArea();                        // m² per pixel
var lc2020 = ee.Image(ASSET + 'LC_DS2020');
var veg20  = lc2020.eq(1);
var land20 = lc2020.neq(5);
var elev   = ee.Image('USGS/SRTMGL1_003');

var panel = ee.FeatureCollection(YEARS.map(function (y) {
  var m = ee.Image(ASSET + 'LC_DS' + y);
  var clear = ee.Image(ASSET + 'Composite_DS' + y).select('clear_n');
  var img = ee.Image.cat([
    area.rename('a_total'),
    area.updateMask(m.eq(1)).rename('a_veg'),
    area.updateMask(m.eq(2)).rename('a_sand'),
    area.updateMask(m.eq(3)).rename('a_beach'),
    area.updateMask(m.eq(4)).rename('a_built'),
    area.updateMask(m.eq(5)).rename('a_water'),
    area.updateMask(clear.lt(3)).rename('a_flagged'),
    area.updateMask(veg20).rename('a_veg2020'),
    area.updateMask(land20).rename('a_land2020'),
    area.updateMask(veg20.and(m.neq(1))).rename('a_veglost'),
    area.multiply(elev).rename('elev_x_area')
  ]).unmask(0);
  return img.reduceRegions({collection: units, reducer: ee.Reducer.sum(), scale: 10, tileScale: 16})
            .map(function (f) {
              return f.set('year', y).setGeometry(f.geometry().centroid(1));
            });
})).flatten();

Export.table.toAsset({collection: panel, description: 'panel_table', assetId: ASSET + 'panel_table'});
print('Now open Tasks and click RUN on panel_table.');
