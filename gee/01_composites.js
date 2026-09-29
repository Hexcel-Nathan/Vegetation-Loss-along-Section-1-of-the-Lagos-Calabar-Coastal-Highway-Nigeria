// ===== Lagos–Calabar Section 1: STAGE 1 – yearly dry-season composites (saved to Assets) =====
var ASSET = 'projects/lekkiproject/assets/';

var aoi   = ee.FeatureCollection(ASSET + 'study_aoi').geometry();
var units = ee.FeatureCollection(ASSET + 'segment_zones_all');
var YEARS = [2020, 2021, 2022, 2023, 2024, 2025, 2026];   // DSyyyy = Nov(yyyy-1) to Mar(yyyy)

function composite(year) {
  var start = ee.Date.fromYMD(year - 1, 11, 1);
  var end   = ee.Date.fromYMD(year, 4, 1);
  var cs = ee.ImageCollection('GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED');
  var col = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
    .filterBounds(aoi)
    .filterDate(start, end)
    .linkCollection(cs, ['cs_cdf'])
    .map(function (img) {
      return img.updateMask(img.select('cs_cdf').gte(0.60))
                .select(['B2', 'B3', 'B4', 'B8', 'B11'])
                .divide(10000);
    });
  var med   = col.median();
  var ndvi  = med.normalizedDifference(['B8', 'B4']).rename('NDVI');
  var clear = col.select('B4').count().rename('clear_n');
  return {img: med.addBands(ndvi).clip(aoi), clear: clear.unmask(0).clip(aoi)};
}

Map.centerObject(aoi, 10);

YEARS.forEach(function (y) {
  var c = composite(y);
  Map.addLayer(c.img, {bands: ['B4', 'B3', 'B2'], min: 0, max: 0.25}, 'DS' + y + ' RGB', y === 2020);
  Map.addLayer(c.clear, {min: 0, max: 20, palette: ['red', 'yellow', 'green']}, 'DS' + y + ' clear obs', false);
  var out = c.img.multiply(10000).toInt16().addBands(c.clear.toInt16());
  Export.image.toAsset({
    image: out,
    description: 'Composite_DS' + y,
    assetId: ASSET + 'Composite_DS' + y,
    region: aoi,
    scale: 10,
    crs: 'EPSG:32631',
    maxPixels: 1e10
  });
});

Map.addLayer(units.style({color: 'yellow', fillColor: '00000000', width: 1}), {}, 'Segment-zones');
print('Done. Open the Tasks tab and click RUN on each Composite_DS task.');
