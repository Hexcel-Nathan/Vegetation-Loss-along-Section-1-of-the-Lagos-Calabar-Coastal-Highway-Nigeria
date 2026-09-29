// 08 - Download everything for the local archive and the figures
//   imagery/     true-colour images of Section 1, every year (10 m)
//   classified/  land-cover maps, every year, split into West, Section 1, East (10 m)
//   training/    the training polygons used by the Random Forest
// Land-cover values: 1 vegetation, 2 sand/bare, 3 beach, 4 built-up, 5 water

var ASSET = 'projects/lekkiproject/assets/';
var YEARS = [2020, 2021, 2022, 2023, 2024, 2025, 2026];
var units = ee.FeatureCollection(ASSET + 'segment_zones_all');
var training = ee.FeatureCollection(ASSET + 'training_points');

function sideBox(side) {
  return units.filter(ee.Filter.eq('side', side)).geometry().bounds();
}
var boxes = {W: sideBox('W'), S1: sideBox('S1'), E: sideBox('E')};

// ---------------- imagery/ ----------------
print('========== IMAGERY folder ==========');
YEARS.forEach(function (y) {
  var rgb = ee.Image(ASSET + 'Composite_DS' + y)
    .visualize({bands: ['B4', 'B3', 'B2'], min: 0, max: 3500, gamma: 1.2});
  print('TrueColour_DS' + y + '_S1',
    rgb.getDownloadURL({name: 'TrueColour_DS' + y + '_S1', region: boxes.S1,
                        scale: 10, crs: 'EPSG:32631', format: 'GEO_TIFF'}));
});

// ---------------- classified/ ----------------
print('========== CLASSIFIED folder ==========');
YEARS.forEach(function (y) {
  var lc = ee.Image(ASSET + 'LC_DS' + y).toByte();
  ['W', 'S1', 'E'].forEach(function (side) {
    print('LC_DS' + y + '_' + side,
      lc.getDownloadURL({name: 'LC_DS' + y + '_' + side, region: boxes[side],
                         scale: 10, crs: 'EPSG:32631', format: 'GEO_TIFF'}));
  });
});

// ---------------- training/ ----------------
print('========== TRAINING folder ==========');
print('Number of training polygons:', training.size());
print('training_polygons (shapefile)',
  training.getDownloadURL({format: 'SHP', filename: 'training_polygons'}));
print('training_polygons (GeoJSON - use only if the shapefile link fails)',
  training.getDownloadURL({format: 'GEOJSON', filename: 'training_polygons'}));

Map.centerObject(units, 10);
Map.addLayer(training, {color: 'yellow'}, 'Training polygons');
