var ASSET = 'projects/lekkiproject/assets/';
var YEARS = [2020, 2021, 2022, 2023, 2024, 2025, 2026];
var units = ee.FeatureCollection(ASSET + 'segment_zones_all');

YEARS.forEach(function (y) {
  var img = ee.Image(ASSET + 'Composite_DS' + y);
  Map.addLayer(img, {bands: ['B4', 'B3', 'B2'], min: 0, max: 2500}, 'DS' + y, y === 2026);
  Map.addLayer(img.select('clear_n'), {min: 0, max: 20, palette: ['red', 'yellow', 'green']},
               'DS' + y + ' clear obs', false);
});
Map.addLayer(units.style({color: 'yellow', fillColor: '00000000', width: 1}), {}, 'Segment-zones');
Map.centerObject(units, 10);

// ---- Save all training polygons (drawn as Geometry Imports in this script) as one asset ----
// var training = vegetation.merge(sand).merge(built).merge(water).merge(road2026).merge(road2025);
// Export.table.toAsset({collection: training, description: 'training_points', assetId: ASSET + 'training_points'});
