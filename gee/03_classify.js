// ===== Lagos–Calabar Section 1: STAGE 2 – classify all seven years =====
var ASSET = 'projects/lekkiproject/assets/';

var aoi      = ee.FeatureCollection(ASSET + 'study_aoi').geometry();
var units    = ee.FeatureCollection(ASSET + 'segment_zones_all');
var beach    = ee.FeatureCollection(ASSET + 'beach_zone_2020');
var training = ee.FeatureCollection(ASSET + 'training_points');
var YEARS = [2020, 2021, 2022, 2023, 2024, 2025, 2026];

// Classes: 1 vegetation, 2 bare/cleared sand, 3 beach (assigned after), 4 built, 5 water
var PALETTE = ['2e7d32', 'd7a86e', 'fff176', 'e53935', '1e88e5'];
var BANDS = ['B2', 'B3', 'B4', 'B8', 'B11', 'NDVI', 'NDWI', 'MNDWI', 'NDBI',
             'VV', 'VH', 'VV_VH', 'elev', 'slope'];

var dem = ee.Image('USGS/SRTMGL1_003');
var terrain = dem.rename('elev').addBands(ee.Terrain.slope(dem).rename('slope'));
var beachImg = ee.Image(0).byte().paint(beach, 1);

// Sentinel-1 radar, same dry-season window
function radar(year) {
  var col = ee.ImageCollection('COPERNICUS/S1_GRD')
    .filterBounds(aoi)
    .filterDate(ee.Date.fromYMD(year - 1, 11, 1), ee.Date.fromYMD(year, 4, 1))
    .filter(ee.Filter.eq('instrumentMode', 'IW'))
    .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
    .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH'))
    .select(['VV', 'VH']);
  var med = col.median();
  return med.addBands(med.select('VV').subtract(med.select('VH')).rename('VV_VH'));
}

// Feature stack for one year
function stack(year) {
  var img = ee.Image(ASSET + 'Composite_DS' + year)
              .select(['B2', 'B3', 'B4', 'B8', 'B11', 'NDVI']).toFloat();
  var ndwi  = img.normalizedDifference(['B3', 'B8']).rename('NDWI');
  var mndwi = img.normalizedDifference(['B3', 'B11']).rename('MNDWI');
  var ndbi  = img.normalizedDifference(['B11', 'B8']).rename('NDBI');
  return ee.Image.cat([img, ndwi, mndwi, ndbi, radar(year), terrain]).clip(aoi);
}

// Sample up to 150 pixels per class per year from the polygons valid for that year
function samplesFor(polys) {
  return ee.FeatureCollection(YEARS.map(function (y) {
    var p = polys.filter(ee.Filter.or(ee.Filter.eq('year', 0), ee.Filter.eq('year', y)));
    var label = ee.Image(0).paint(p, 'class').rename('class').selfMask().toInt();
    return stack(y).addBands(label).stratifiedSample({
      numPoints: 150, classBand: 'class', region: aoi, scale: 10,
      seed: y, tileScale: 8, geometries: false
    });
  })).flatten();
}

// 1) Quick check: train on 70% of polygons, test on the other 30%
var split = training.randomColumn('r', 42);
var trainS = samplesFor(split.filter(ee.Filter.lt('r', 0.7)));
var testS  = samplesFor(split.filter(ee.Filter.gte('r', 0.7)));
var rfCheck = ee.Classifier.smileRandomForest(300).train(trainS, 'class', BANDS);
var em = testS.classify(rfCheck).errorMatrix('class', 'classification');
// Runs as a background task (too heavy to print directly). Result saved as asset 'quick_check'.
Export.table.toAsset({
  collection: ee.FeatureCollection([ee.Feature(aoi.centroid(1), {
    overall_accuracy: em.accuracy(),
    error_matrix: ee.String.encodeJSON(em.array().toList()),
    order_of_classes: ee.String.encodeJSON(em.order())
  })]),
  description: 'quick_check',
  assetId: ASSET + 'quick_check'
});

// 2) Final model: all polygons
var rf = ee.Classifier.smileRandomForest(300).train(samplesFor(training), 'class', BANDS);

// 3) Classify each year, split beach from other sand, apply one temporal rule
var maps = {};
YEARS.forEach(function (y) {
  var c = stack(y).classify(rf).rename('lc');
  c = c.where(c.eq(2).and(beachImg.eq(1)), 3);
  maps[y] = c.toByte();
});
for (var i = 1; i < YEARS.length; i++) {
  var prev = maps[YEARS[i - 1]], cur = maps[YEARS[i]];
  maps[YEARS[i]] = cur.where(prev.eq(4).and(cur.eq(1)), 4);   // built -> vegetation in one year is implausible
}

// 4) Display and export
Map.centerObject(units, 10);
YEARS.forEach(function (y) {
  Map.addLayer(maps[y], {min: 1, max: 5, palette: PALETTE}, 'LC DS' + y, y === 2020 || y === 2026);
  Export.image.toAsset({
    image: maps[y], description: 'LC_DS' + y, assetId: ASSET + 'LC_DS' + y,
    region: aoi, scale: 10, crs: 'EPSG:32631', maxPixels: 1e10,
    pyramidingPolicy: {'.default': 'mode'}
  });
});
Map.addLayer(units.style({color: 'yellow', fillColor: '00000000', width: 1}), {}, 'Segment-zones', false);
print('Legend: green = vegetation, tan = bare/cleared sand, yellow = beach, red = built, blue = water');
