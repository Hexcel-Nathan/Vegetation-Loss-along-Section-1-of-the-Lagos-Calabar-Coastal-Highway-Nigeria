var ASSET = 'projects/lekkiproject/assets/';
var panel = ee.FeatureCollection(ASSET + 'panel_table');
print('Rows (should be 4396):', panel.size());
var url = panel.getDownloadURL({
  format: 'CSV',
  filename: 'segment_zone_panel_DS2020_2026',
  selectors: ['unit_id', 'seg_id', 'zone', 'treated', 'side', 'year',
              'a_total', 'a_veg', 'a_sand', 'a_beach', 'a_built', 'a_water',
              'a_flagged', 'a_veg2020', 'a_land2020', 'a_veglost', 'elev_x_area']
});
print('Click this link to download the CSV:', url);
