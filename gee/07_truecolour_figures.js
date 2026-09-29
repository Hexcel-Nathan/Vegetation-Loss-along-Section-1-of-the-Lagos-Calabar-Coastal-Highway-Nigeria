var ASSET = 'projects/lekkiproject/assets/';
var units = ee.FeatureCollection(ASSET + 'segment_zones_all');
var img = ee.Image(ASSET + 'Composite_DS2026');
var rgb = img.visualize({bands: ['B4', 'B3', 'B2'], min: 0, max: 3500, gamma: 1.2});
var coast = units.geometry().bounds().buffer(3000).bounds();
print('1) Whole coast, true colour (30 m):', rgb.getDownloadURL({
  name: 'TrueColour_DS2026_coast', region: coast, scale: 30, crs: 'EPSG:32631', format: 'GEO_TIFF'}));
var s1 = units.filter(ee.Filter.eq('side', 'S1')).geometry().bounds();
print('2) Section 1, true colour (10 m):', rgb.getDownloadURL({
  name: 'TrueColour_DS2026_S1', region: s1, scale: 10, crs: 'EPSG:32631', format: 'GEO_TIFF'}));
Map.centerObject(units, 10);
Map.addLayer(rgb, {}, 'DS2026 true colour');
