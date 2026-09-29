/*******************************************************************************
 * Lagos–Calabar Coastal Highway, Section 1 — annual dry-season land cover panel
 * Google Earth Engine (Code Editor, JavaScript)
 *
 * Implements Sections 3.2–3.5 of the manuscript and exports the segment–zone
 * table used for the difference-in-differences models (Section 3.7, done in R).
 *
 * BEFORE RUNNING — upload these assets (Assets > NEW > Shapefile) and edit the
 * paths in the CONFIG block:
 *   1. units      : segment_zones_all — one polygon per segment–zone. Properties:
 *                   unit_id, seg_id (e.g. "T12" / "C05"), zone ("F","B1","B2","B3"),
 *                   treated (1 = Section 1, 0 = control)
 *   2. aoi        : study_aoi — segment_zones_all dissolved and buffered by 1 km
 *   3. beachZone  : beach_zone_2020 — DS2020 beach zone, treated AND control coast
 *   4. trainPts   : training_points (needed for STAGE 2 only). Properties:
 *                   class : 0 mangrove, 1 other vegetation, 2 sand/bare (spectral),
 *                           4 built-up, 5 water   (3 = beach is assigned later)
 *                   year  : 2020…2026 for year-specific points,
 *                           0 for stable points (sampled in every year)
 ******************************************************************************/

// ------------------------------- CONFIG -------------------------------------
var ASSET = 'projects/YOUR_PROJECT/assets/';           // <-- edit
var STAGE = 1;   // 1 = export yearly composites only (Step 5)
                 // 2 = classify, export maps, panel table and validation points (Step 7+)
var units     = ee.FeatureCollection(ASSET + 'segment_zones_all');
var aoi       = ee.FeatureCollection(ASSET + 'study_aoi').geometry();
var beachZone = ee.FeatureCollection(ASSET + 'beach_zone_2020');
var trainPts  = ee.FeatureCollection(ASSET + 'training_points');

var YEARS = [2020, 2021, 2022, 2023, 2024, 2025, 2026];  // DS year = Nov(t-1)–Mar(t)
var CS_THRESHOLD = 0.60;       // Cloud Score+ clear-sky threshold
var MIN_CLEAR = 3;             // flag pixels with fewer clear observations
var SCALE = 10;
var EXPORT_FOLDER = 'LagosCalabar_S1';

var CLASS_NAMES = ['mangrove', 'other_veg', 'bare_cleared', 'beach', 'built', 'water'];
var PALETTE     = ['1b5e20', '8bc34a', 'd7a86e', 'fff59d', 'e53935', '1e88e5'];

// ------------------------- STATIC LAYERS ------------------------------------
var dem = ee.Image('USGS/SRTMGL1_003').clip(aoi);
var terrain = dem.rename('elev').addBands(ee.Terrain.slope(dem).rename('slope'));
var beachImg = ee.Image(0).byte().paint(beachZone, 1).rename('beach');

// --------------------------- COMPOSITES -------------------------------------
function dsWindow(year) {
  return {start: ee.Date.fromYMD(year - 1, 11, 1), end: ee.Date.fromYMD(year, 4, 1)};
}

function s2Composite(year) {
  var w = dsWindow(year);
  var cs = ee.ImageCollection('GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED');
  var col = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
    .filterBounds(aoi)
    .filterDate(w.start, w.end)
    .linkCollection(cs, ['cs_cdf'])
    .map(function (img) {
      return img.updateMask(img.select('cs_cdf').gte(CS_THRESHOLD))
                .select(['B2','B3','B4','B5','B6','B7','B8','B8A','B11','B12'])
                .divide(10000);
    });
  var med = col.median();
  var clear = col.select('B4').count().rename('clear_n');
  var idx = ee.Image.cat([
    med.normalizedDifference(['B8', 'B4']).rename('NDVI'),
    med.normalizedDifference(['B3', 'B8']).rename('NDWI'),    // McFeeters 1996
    med.normalizedDifference(['B3', 'B11']).rename('MNDWI'),  // Xu 2006
    med.normalizedDifference(['B11', 'B8']).rename('NDBI')    // Zha et al. 2003
  ]);
  return {img: med.addBands(idx).clip(aoi), clear: clear.unmask(0).clip(aoi)};
}

function s1Composite(year) {
  var w = dsWindow(year);
  var col = ee.ImageCollection('COPERNICUS/S1_GRD')
    .filterBounds(aoi)
    .filterDate(w.start, w.end)
    .filter(ee.Filter.eq('instrumentMode', 'IW'))
    .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
    .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH'))
    .select(['VV', 'VH']);
  var med = col.median();
  return med.addBands(med.select('VV').subtract(med.select('VH')).rename('VV_VH')) // dB ratio
            .clip(aoi);
}

var stacks = {}, clears = {};
YEARS.forEach(function (y) {
  var s2 = s2Composite(y);
  stacks[y] = s2.img.addBands(s1Composite(y)).addBands(terrain);
  clears[y] = s2.clear;
});
var BANDS = stacks[2020].bandNames();

Map.centerObject(aoi, 11);

// ------------------ STAGE 1: EXPORT COMPOSITES FOR LABELLING ----------------
// Six bands scaled to integers (reflectance x 10000; NDVI x 10000) + clear-obs count.
// Load these into ArcGIS Pro to label training points year by year (Step 6).
if (STAGE === 1) {
  YEARS.forEach(function (y) {
    var out = stacks[y].select(['B2','B3','B4','B8','B11','NDVI'])
      .multiply(10000).toInt16().addBands(clears[y].toInt16());
    Export.image.toDrive({image: out, description: 'Composite_DS' + y, folder: EXPORT_FOLDER,
                          region: aoi, scale: SCALE, crs: 'EPSG:32631', maxPixels: 1e10});
    Map.addLayer(stacks[y], {bands: ['B4','B3','B2'], min: 0, max: 0.25}, 'DS' + y + ' RGB', y === 2020);
    Map.addLayer(clears[y], {min: 0, max: 20, palette: ['red','yellow','green']}, 'DS' + y + ' clear obs', false);
  });
  print('STAGE 1: open the Tasks tab and click RUN on each Composite_DS task.');
}

if (STAGE === 2) {

// ----------------------- POOLED RANDOM FOREST -------------------------------
// Stable points (year = 0) are sampled from every year's composite;
// year-specific points only from their own year.
var samples = ee.FeatureCollection(YEARS.map(function (y) {
  var pts = trainPts.filter(ee.Filter.or(ee.Filter.eq('year', 0), ee.Filter.eq('year', y)));
  return stacks[y].sampleRegions({collection: pts, properties: ['class'],
                                  scale: SCALE, tileScale: 4, geometries: false});
})).flatten();

var rf = ee.Classifier.smileRandomForest({numberOfTrees: 300})  // √p per split by default
  .train({features: samples, classProperty: 'class', inputProperties: BANDS});

print('Training samples (all years):', samples.size());
print('RF out-of-bag / explain:', rf.explain());

// Classify, then split spectral sand (2) into beach (3) vs bare/cleared (2)
var maps = {};
YEARS.forEach(function (y) {
  var c = stacks[y].classify(rf).rename('lc');
  c = c.where(c.eq(2).and(beachImg.eq(1)), 3);
  maps[y] = c.toByte();
});

// Temporal rule: built-up (4) → mangrove (0) in one year is implausible → keep 4
for (var i = 1; i < YEARS.length; i++) {
  var prev = maps[YEARS[i - 1]], cur = maps[YEARS[i]];
  maps[YEARS[i]] = cur.where(prev.eq(4).and(cur.eq(0)), 4);
}

// ------------------------------ DISPLAY -------------------------------------
Map.addLayer(stacks[2026], {bands: ['B4','B3','B2'], min: 0, max: 0.25}, 'DS2026 RGB', false);
Map.addLayer(maps[2020], {min: 0, max: 5, palette: PALETTE}, 'LC DS2020');
Map.addLayer(maps[2026], {min: 0, max: 5, palette: PALETTE}, 'LC DS2026');
Map.addLayer(units.style({color: 'black', fillColor: '00000000', width: 1}), {}, 'Segment–zones');

// ----------------------- SEGMENT–ZONE PANEL TABLE ---------------------------
// Per unit and year: area of each class, flagged (low clear-obs) area,
// DS2020 vegetated area, and DS2020-vegetation now non-vegetated (cumulative loss).
var area = ee.Image.pixelArea();
var veg2020 = maps[2020].lte(1);  // classes 0,1

var panel = ee.FeatureCollection(YEARS.map(function (y) {
  var m = maps[y];
  var img = ee.Image.cat(CLASS_NAMES.map(function (n, k) {
    return area.updateMask(m.eq(k)).rename('a_' + n);
  })).unmask(0)
    .addBands(area.updateMask(clears[y].lt(MIN_CLEAR)).unmask(0).rename('a_flagged'))
    .addBands(area.updateMask(veg2020).unmask(0).rename('a_veg2020'))
    .addBands(area.updateMask(veg2020.and(m.gt(1))).unmask(0).rename('a_veglost'));
  return img.reduceRegions({collection: units, reducer: ee.Reducer.sum(),
                            scale: SCALE, tileScale: 8})
            .map(function (f) { return f.set('year', y).setGeometry(null); });
})).flatten();

Export.table.toDrive({collection: panel, description: 'segment_zone_panel_DS2020_2026',
                      folder: EXPORT_FOLDER, fileFormat: 'CSV'});

// Mean elevation per unit (matching covariate, Step 9)
Export.table.toDrive({
  collection: dem.rename('elev_mean').reduceRegions({collection: units, reducer: ee.Reducer.mean(),
                                                     scale: 30, tileScale: 4})
                 .map(function (f) { return f.setGeometry(null); }),
  description: 'segment_zone_elevation', folder: EXPORT_FOLDER, fileFormat: 'CSV'});

// --------------------------- MAP EXPORTS ------------------------------------
YEARS.forEach(function (y) {
  Export.image.toDrive({image: maps[y], description: 'LC_DS' + y, folder: EXPORT_FOLDER,
                        region: aoi, scale: SCALE, crs: 'EPSG:32631', maxPixels: 1e10});
});

// ---------------- OLOFSSON VALIDATION SAMPLES (Section 3.6) -----------------
// 1) Stratified sample of DS2020 and DS2026 maps (map classes as strata)
[2020, 2026].forEach(function (y) {
  var pts = maps[y].rename('map_class').stratifiedSample({
    numPoints: 100, classBand: 'map_class', region: aoi, scale: SCALE,
    seed: y, geometries: true, tileScale: 4});   // adjust per-stratum n after Olofsson formula
  Export.table.toDrive({collection: pts, description: 'validation_points_DS' + y,
                        folder: EXPORT_FOLDER, fileFormat: 'SHP'});
});

// 2) Change-map strata: 0 stable veg, 1 veg loss, 2 veg gain, 3 stable non-veg
var veg2026 = maps[2026].lte(1);
var change = ee.Image(3).where(veg2020.and(veg2026), 0)
                        .where(veg2020.and(veg2026.not()), 1)
                        .where(veg2020.not().and(veg2026), 2)
                        .rename('change').toByte().clip(aoi);
Map.addLayer(change, {min: 0, max: 3, palette: ['2e7d32', 'd50000', '00e5ff', 'bdbdbd']},
             'Change DS2020–DS2026', false);
Export.table.toDrive({
  collection: change.stratifiedSample({numPoints: 100, classBand: 'change', region: aoi,
                                       scale: SCALE, seed: 42, geometries: true, tileScale: 4}),
  description: 'validation_points_change', folder: EXPORT_FOLDER, fileFormat: 'SHP'});

// Stratum areas (needed for Olofsson area-weighted estimators)
print('Change-map stratum areas (ha):', area.divide(1e4).addBands(change).reduceRegion({
  reducer: ee.Reducer.sum().group({groupField: 1, groupName: 'stratum'}),
  geometry: aoi, scale: SCALE, maxPixels: 1e10, tileScale: 4}));
}  // end STAGE 2
