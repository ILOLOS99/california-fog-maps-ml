// ========== USER SETTINGS ==========
var stationAssetId = 'projects/YOUR_PROJECT/assets/unique_stations_with_latlon';
var targetYear     = 2019;
var driveFolder    = 'GEE_exports_combined';

// ========== Load stations — California only ==========
var raw = ee.FeatureCollection(stationAssetId)
  .filter(ee.Filter.eq('state', 'CA'));
print('Raw station count (CA only):', raw.size());

var firstFeature  = ee.Feature(raw.first());
var originalProps = firstFeature.propertyNames().getInfo();
print('Original properties:', originalProps);

// ========== Load ERA5-Land — get native projection ==========
var era5 = ee.ImageCollection('ECMWF/ERA5_LAND/HOURLY')
  .filterDate(ee.Date.fromYMD(targetYear, 1, 1),
              ee.Date.fromYMD(targetYear, 1, 1).advance(1, 'year'));

var sampleImg   = ee.Image(era5.first());
var nativeProj  = sampleImg.select(0).projection();
var nativeScale = nativeProj.nominalScale();
print('ERA5-Land native scale (m):', nativeScale);
print('Sample band names:', sampleImg.bandNames());

// ========== Robust band detection ==========
function chooseBand(img, candidates) {
  var names = img.bandNames();
  return ee.List(candidates).iterate(function(c, found) {
    found = ee.String(found);
    return ee.Algorithms.If(found.length().gt(0), found,
             ee.Algorithms.If(names.contains(ee.String(c)), ee.String(c), found));
  }, ee.String(''));
}

var t2mBand      = chooseBand(sampleImg, ['temperature_2m','2m_temperature','t2m']);
var td2mBand     = chooseBand(sampleImg, ['dewpoint_temperature_2m','2m_dewpoint_temperature','d2m']);
var u10Band      = chooseBand(sampleImg, ['u_component_of_wind_10m','10m_u_component_of_wind','u10']);
var v10Band      = chooseBand(sampleImg, ['v_component_of_wind_10m','10m_v_component_of_wind','v10']);
var swvl1Band    = chooseBand(sampleImg, ['volumetric_soil_water_layer_1','swvl1']);
var tevapBand    = chooseBand(sampleImg, ['total_evaporation_hourly','total_evaporation','e']);
var netSolBand   = chooseBand(sampleImg, ['surface_net_solar_radiation_hourly','surface_net_solar_radiation']);
var netThermBand = chooseBand(sampleImg, ['surface_net_thermal_radiation_hourly','surface_net_thermal_radiation']);
var skinBand     = chooseBand(sampleImg, ['skin_temperature','skinTemperature']);
var latentBand   = chooseBand(sampleImg, ['surface_latent_heat_flux_hourly','surface_latent_heat_flux']);
var sensibleBand = chooseBand(sampleImg, ['surface_sensible_heat_flux_hourly','surface_sensible_heat_flux']);
var srcBand      = chooseBand(sampleImg, ['skin_reservoir_content','src']);
var laiBand      = chooseBand(sampleImg, ['leaf_area_index_low_vegetation','lai_low_vegetation']);
var tpBand       = chooseBand(sampleImg, ['total_precipitation_hourly','total_precipitation','tp']);

print('Detected bands:', {
  t2m: t2mBand, dewpoint: td2mBand, u10: u10Band, v10: v10Band,
  swvl1: swvl1Band, total_evap: tevapBand,
  net_solar: netSolBand, net_thermal: netThermBand,
  skin_temp: skinBand, latent: latentBand, sensible: sensibleBand,
  skin_reservoir: srcBand, lai_low: laiBand, precip: tpBand
});

// Validate all bands found
var allBands = [t2mBand, td2mBand, u10Band, v10Band, swvl1Band, tevapBand,
                netSolBand, netThermBand, skinBand, latentBand, sensibleBand,
                srcBand, laiBand, tpBand];
var missing = ee.List(allBands)
  .map(function(b){ return ee.String(b).length().eq(0); }).contains(true);
missing.evaluate(function(isMissing){
  if (isMissing) {
    print('ERROR: Band detection failed. Check band names:');
    print(sampleImg.bandNames());
  } else {
    print('Band detection OK — all 14 bands found.');
  }
});

// ========== SPATIAL DEDUPLICATION: one station per ERA5 pixel ==========
// Multiply first then floor to avoid floating point division errors
// Station geometries are never modified — only pixel_id is added
var stationsWithPixel = raw.map(function(f) {
  var coord = f.geometry().coordinates();
  var lon   = ee.Number(coord.get(0));
  var lat   = ee.Number(coord.get(1));

  var pixX  = lon.multiply(10).floor().divide(10);
  var pixY  = lat.multiply(10).floor().divide(10);
  var pixId = pixX.format('%.1f').cat('_').cat(pixY.format('%.1f'));

  return f.set('pixel_id', pixId);
});

var pixelIds = stationsWithPixel.aggregate_array('pixel_id').distinct();
print('Unique ERA5 pixels occupied:', pixelIds.size());

// Keep alphabetically first station per pixel
var keptList = pixelIds.map(function(pid) {
  return stationsWithPixel
    .filter(ee.Filter.eq('pixel_id', pid))
    .sort('station')
    .first();
});
var keptStations = ee.FeatureCollection(keptList);
var keptIds      = keptStations.aggregate_array('station');

// Removed stations
var removedStations = stationsWithPixel.filter(
  ee.Filter.inList('station', keptIds).not()
);

print('Stations kept (one per pixel):', keptStations.size());
print('Stations removed (pixel duplicates):', removedStations.size());

var pts = keptStations;

// ========== Output field definitions ==========
var appended = [
  'time_utc', 'date',
  't2m_C', 'dewpoint_C', 'u10_m_s', 'v10_m_s',
  'volumetric_soil_water_layer_1', 'total_evaporation_hourly', 'total_precipitation_hourly',
  'surface_net_solar_radiation_hourly', 'surface_net_thermal_radiation_hourly',
  'surface_latent_heat_flux_hourly', 'surface_sensible_heat_flux_hourly',
  'skin_temperature', 'skin_reservoir_content',
  'leaf_area_index_low_vegetation'
];
var outFields = originalProps.concat(appended);
print('Output columns:', outFields);

// ========== Sampling function at native ERA5 resolution ==========
function sampleImage(img) {
  var out = img.select([
    ee.String(t2mBand), ee.String(td2mBand),
    ee.String(u10Band),  ee.String(v10Band),
    ee.String(swvl1Band), ee.String(tevapBand), ee.String(tpBand),
    ee.String(netSolBand), ee.String(netThermBand),
    ee.String(latentBand), ee.String(sensibleBand),
    ee.String(skinBand), ee.String(srcBand),
    ee.String(laiBand)
  ]).rename([
    't2m_K', 'dewpoint_K',
    'u10_m_s', 'v10_m_s',
    'volumetric_soil_water_layer_1', 'total_evaporation_hourly', 'total_precipitation_hourly',
    'surface_net_solar_radiation_hourly', 'surface_net_thermal_radiation_hourly',
    'surface_latent_heat_flux_hourly', 'surface_sensible_heat_flux_hourly',
    'skin_temperature', 'skin_reservoir_content',
    'leaf_area_index_low_vegetation'
  ]);

  // Convert K → °C
  var t2mC      = out.select('t2m_K').subtract(273.15).rename('t2m_C');
  var dewpointC = out.select('dewpoint_K').subtract(273.15).rename('dewpoint_C');
  var outFinal  = out.addBands(t2mC).addBands(dewpointC)
                     .select(appended.slice(2));

  var sampled = outFinal.sampleRegions({
    collection: pts,
    scale: nativeScale,
    projection: nativeProj,
    geometries: true
  });

  var time = img.get('system:time_start');
  return sampled.map(function(f) {
    return ee.Feature(f.geometry(), f.toDictionary())
      .set('time_utc', ee.Date(time).format('yyyy-MM-dd HH:mm:ss'))
      .set('date',     ee.Date(time).format('yyyy-MM-dd'));
  });
}

// ========== Monthly export loop ==========
ee.List.sequence(1, 12).getInfo().forEach(function(m) {
  var mm     = m < 10 ? '0' + m : '' + m;
  var mStart = ee.Date.fromYMD(targetYear, m, 1);
  var mEnd   = mStart.advance(1, 'month');
  var era5_m = era5.filterDate(mStart, mEnd);

  print('Month ' + targetYear + '-' + mm + ' image count:', era5_m.size());

  var sampledMonth = ee.FeatureCollection(
    era5_m.map(function(img) { return sampleImage(img); })
  ).flatten();

  Export.table.toDrive({
    collection: sampledMonth.select(outFields),
    description: 'ERA5_combined_' + targetYear + '_' + mm,
    folder: driveFolder,
    fileNamePrefix: 'ERA5_combined_' + targetYear + '_' + mm,
    fileFormat: 'CSV'
  });

  print('Export task created for ' + targetYear + '-' + mm);
});

// ========== VISUALIZATION ==========
// Build ERA5 pixel rectangles from pixel_id floor coordinates
// pixX and pixY are the SW corner of each 0.1° cell
var pixelGrid = ee.FeatureCollection(
  pixelIds.map(function(pid) {
    pid = ee.String(pid);
    var parts = pid.split('_');
    var x = ee.Number.parse(parts.get(0));
    var y = ee.Number.parse(parts.get(1));
    return ee.Feature(
      ee.Geometry.Rectangle([x, y, x.add(0.1), y.add(0.1)])
    ).set('pixel_id', pid);
  })
);

print('ERA5 pixels containing stations:', pixelGrid.size());

Map.centerObject(raw, 6);
Map.setOptions('SATELLITE');

// ERA5 pixel fill
Map.addLayer(pixelGrid, {color: '1a73e8'}, 'ERA5-Land native pixels');

// Pixel outlines
Map.addLayer(
  ee.Image().byte().paint({featureCollection: pixelGrid, color: 1, width: 1}).selfMask(),
  {palette: ['ffffff'], opacity: 0.8},
  'Pixel borders'
);

// California boundary
Map.addLayer(
  ee.FeatureCollection('TIGER/2018/States').filter(ee.Filter.eq('NAME', 'California')),
  {color: 'ffffff', fillColor: '00000000'},
  'California boundary'
);

// Removed stations (red)
Map.addLayer(removedStations, {color: 'FF4136'}, 'Removed stations (pixel duplicates)');

// Kept stations (green)
Map.addLayer(keptStations, {color: '2ECC40'}, 'Kept stations (one per pixel)');

// ========== Legend ==========
var legend = ui.Panel({
  style: {position: 'bottom-left', padding: '10px 14px', backgroundColor: '#1a1a2e'}
});

legend.add(ui.Label('ERA5-Land Sampling — ' + targetYear, {
  fontWeight: 'bold', fontSize: '14px', color: '#ffffff', margin: '0 0 10px 0'
}));

var makeRow = function(color, label) {
  return ui.Panel([
    ui.Label({style: {backgroundColor: color, padding: '8px', margin: '2px 8px 2px 0',
                      border: '1px solid rgba(255,255,255,0.2)'}}),
    ui.Label(label, {color: '#eeeeee', fontSize: '12px', margin: '4px 0'})
  ], ui.Panel.Layout.flow('horizontal'));
};

legend.add(makeRow('#1a73e8', 'ERA5-Land native pixel (0.1°)'));
legend.add(makeRow('#2ECC40', 'Station kept (one per pixel)'));
legend.add(makeRow('#FF4136', 'Station removed (pixel duplicate)'));
legend.add(ui.Label('Dedup: alphabetically first station kept per pixel',
  {color: '#aaaaaa', fontSize: '11px', fontStyle: 'italic', margin: '8px 0 2px 0'}));
legend.add(ui.Label('Sampling: native ERA5-Land projection & scale',
  {color: '#aaaaaa', fontSize: '11px', fontStyle: 'italic', margin: '2px 0 0 0'}));

Map.add(legend);

print('Script complete. Open Tasks tab to run exports for year', targetYear);
