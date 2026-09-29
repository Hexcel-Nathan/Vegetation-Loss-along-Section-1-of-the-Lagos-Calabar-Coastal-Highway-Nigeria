// ===== Lagos–Calabar Section 1: STEP 8 – random points for the accuracy check =====
var ASSET = 'projects/lekkiproject/assets/';
var units = ee.FeatureCollection(ASSET + 'segment_zones_all');
var aoi   = ee.FeatureCollection(ASSET + 'study_aoi').geometry();

var lc20 = ee.Image(ASSET + 'LC_DS2020');
var lc26 = ee.Image(ASSET + 'LC_DS2026');
var inUnits = ee.Image(0).byte().paint(units, 1);           // only inside the 628 units
var land = lc20.neq(5).or(lc26.neq(5));                      // leave out water in both years

// Strata from the map: 1 stable vegetation, 2 vegetation lost, 3 vegetation gained, 4 stable non-vegetation
var v20 = lc20.eq(1), v26 = lc26.eq(1);
var strata = ee.Image(4)
  .where(v20.and(v26), 1)
  .where(v20.and(v26.not()), 2)
  .where(v20.not().and(v26), 3)
  .rename('stratum').toInt()
  .updateMask(inUnits.and(land));

// Random points: more in the rarer change strata so they are tested properly
var pts = strata.stratifiedSample({
  numPoints: 0, classBand: 'stratum', region: aoi, scale: 10, seed: 2026,
  classValues: [1, 2, 3, 4], classPoints: [80, 100, 50, 70],
  geometries: true, tileScale: 16
}).randomColumn('r', 7).sort('r');

// Give each point a number 1..300 in random order
var list = pts.toList(pts.size());
var numbered = ee.FeatureCollection(ee.List.sequence(0, pts.size().subtract(1)).map(function (i) {
  var f = ee.Feature(list.get(i));
  var c = f.geometry().coordinates();
  return f.set({pt_id: ee.Number(i).add(1), lon: c.get(0), lat: c.get(1)});
}));

// Area of each stratum (hectares) – needed for the error-adjusted areas
var areas = ee.Image.pixelArea().divide(10000).addBands(strata).reduceRegion({
  reducer: ee.Reducer.sum().group({groupField: 1, groupName: 'stratum'}),
  geometry: aoi, scale: 10, maxPixels: 1e10, tileScale: 16
});
print('Stratum areas (ha) – copy these into your log:', areas);
print('Number of points (should be 300):', numbered.size());

// DOWNLOAD 1: blind points for labelling (no map class inside)
print('1) BLIND points for ArcGIS (shapefile zip):',
  numbered.select(['pt_id', 'lon', 'lat']).getDownloadURL({format: 'SHP', filename: 'accuracy_points_blind'}));
// DOWNLOAD 2: answer key (keep closed until labelling is finished)
print('2) Answer key – do NOT open, just send it to Claude:',
  numbered.select(['pt_id', 'stratum']).getDownloadURL({format: 'CSV', filename: 'accuracy_key'}));

Map.centerObject(units, 10);
Map.addLayer(numbered, {color: 'magenta'}, 'Accuracy points');
