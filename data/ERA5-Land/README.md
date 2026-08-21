# ERA5-Land Data

Hourly ERA5-Land meteorological and land-surface variables extracted at ASOS station locations in California for use in the machine learning workflow.

The ERA5-Land data are not stored directly in this repository. They can be reproduced using the provided Google Earth Engine (GEE) script.

## Files

- `unique_stations_with_latlon.csv` — All the unique ASOS station locations in California and Arizona to be used as sampling points in GEE.
- `extract_ERA5_Land_at_ASOS_stations.js` — GEE script used to extract hourly ERA5-Land data at California ASOS locations and export monthly CSV files.

## Data Source

ERA5-Land hourly data were accessed through the Google Earth Engine collection `ECMWF/ERA5_LAND/HOURLY`. The underlying ERA5-Land dataset is produced by the European Centre for Medium-Range Weather Forecasts (ECMWF) and distributed through the Copernicus Climate Change Service (C3S) Climate Data Store (CDS).

## Citations

Muñoz-Sabater, J. (2019). *ERA5-Land hourly data from 1950 to present*. Copernicus Climate Change Service (C3S) Climate Data Store (CDS). https://doi.org/10.24381/cds.e2161bac

Muñoz-Sabater, J., Dutra, E., Agustí-Panareda, A., Albergel, C., Arduini, G., Balsamo, G., et al. (2021). ERA5-Land: A state-of-the-art global reanalysis dataset for land applications. *Earth System Science Data, 13*(9), 4349–4383. https://doi.org/10.5194/essd-13-4349-2021

## Processing

The script:

1. Loads the hourly ERA5-Land collection for the selected year.
2. Detects the required ERA5-Land bands.
3. Retains one station per ERA5-Land grid cell, keeping the alphabetically first station when multiple stations occupy the same cell.
4. Samples ERA5-Land at the native projection and scale.
5. Converts 2-m air temperature and 2-m dew-point temperature from Kelvin to degrees Celsius.
6. Exports the resulting hourly station-level data as one CSV file per month.

## Running the Script

1. Upload `unique_stations_with_latlon.csv` to Google Earth Engine as a table asset.
2. Update `stationAssetId` in `extract_ERA5_Land_at_ASOS_stations.js` to the uploaded asset path.
3. Set `targetYear` to the desired year.
4. Run the script in the Google Earth Engine Code Editor.
5. Run the monthly export tasks created by the script.
6. Repeat for each year from 2019 through 2024.

The script exports files with the following naming convention:

`ERA5_combined_YYYY_MM.csv`

## ERA5-Land Variables

| Variable | Description | Units |
|---|---|---|
| `t2m_C` | 2-m air temperature | °C |
| `dewpoint_C` | 2-m dew-point temperature | °C |
| `u10_m_s` | 10-m eastward wind component | m s⁻¹ |
| `v10_m_s` | 10-m northward wind component | m s⁻¹ |
| `volumetric_soil_water_layer_1` | Volumetric soil water in soil layer 1 (0–7 cm) | m³ m⁻³ |
| `total_evaporation_hourly` | Hourly total evaporation | m of water equivalent |
| `total_precipitation_hourly` | Hourly total precipitation | m of water equivalent |
| `surface_net_solar_radiation_hourly` | Hourly surface net solar radiation | J m⁻² |
| `surface_net_thermal_radiation_hourly` | Hourly surface net thermal radiation | J m⁻² |
| `surface_latent_heat_flux_hourly` | Hourly surface latent heat flux | J m⁻² |
| `surface_sensible_heat_flux_hourly` | Hourly surface sensible heat flux | J m⁻² |
| `skin_temperature` | Skin temperature | K |
| `skin_reservoir_content` | Water stored in the vegetation canopy/interception reservoir | m water equivalent |
| `leaf_area_index_low_vegetation` | Leaf area index of low vegetation | m² m⁻² |
