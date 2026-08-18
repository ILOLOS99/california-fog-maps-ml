# Raw ASOS data

Hourly observations from Automated Surface Observing System (ASOS) stations, including various meteorological parameters, from all available ASOS stations in California and Arizona. Arizona stations will be filtered out later in the pipeline.
Multiple ASOS reports occurring within the same station-hour were aggregated into a single hourly record.

## Data Source

Iowa Environmental Mesonet (IEM), 2025: ASOS Surface Weather Observations. Iowa State University. Available online at: https://mesonet.agron.iastate.edu/request/download.phtml

## Files

- `ca_az_hourly_2019.csv`
- `ca_az_hourly_2020.csv`
- `ca_az_hourly_2021.csv`
- `ca_az_hourly_2022.csv`
- `ca_az_hourly_2023.csv`
- `ca_az_hourly_2024.csv`

## Variables

| Variable | Description |
|---|---|
| `station` | ASOS station identifier |
| `station_name` | Full ASOS station name |
| `state` | U.S. state (`CA` or `AZ`) |
| `latitude` | Station latitude (decimal degrees) |
| `longitude` | Station longitude (decimal degrees) |
| `elevation_m` | Station elevation (m) |
| `date_local` | Calendar date in the station's local time zone |
| `hour_local` | Local hour of day (0–23) |
| `timezone` | Time zone used to convert the original UTC observation time to local time |
| `n_obs` | Number of sub-hourly ASOS reports aggregated into the hourly record |
| `dew_point_c` | Mean dew-point temperature of reports within the hour (°C) |
| `air_temp_c` | Mean air temperature of reports within the hour (°C) |
| `wind_speed_ms` | Mean wind speed of reports within the hour (m s⁻¹) |
| `precipitation_mm` | Maximum reported hourly precipitation value within the station-hour (mm) |
| `cloud_coverage` | Most frequently reported primary cloud-cover category (`skyc1`) within the hour |
| `fog_occurrence` | `yes` if at least one report within the hour contained the ASOS weather code `FG`; otherwise `no` |
| `mist_occurrence` | `yes` if at least one report within the hour contained the ASOS weather code `BR`; otherwise `no` |
| `has_dew_point` | `TRUE` if at least one report within the hour contained a dew-point observation |
| `has_air_temp` | `TRUE` if at least one report within the hour contained an air-temperature observation |
| `has_wind_speed` | `TRUE` if at least one report within the hour contained a wind-speed observation |
| `has_precipitation` | `TRUE` if at least one report within the hour contained a precipitation observation |
| `has_cloud_coverage` | `TRUE` if at least one report within the hour contained a primary cloud-cover observation |
| `has_fog_mist_data` | `TRUE` if at least one report within the hour had valid data on whether fog/mist occurred or not, which was determined according to the fog/mist data-availability criterion described below |

## Fog/Mist Data Availability Criterion
For each individual ASOS report, `has_fog_mist_data` was considered `FALSE` when either:

1. both the present-weather code (`wxcodes`) and visibility (`vsby`) were missing; or
2. the present-weather code was missing and either air temperature (`tmpf`) or dew-point temperature (`dwpf`) was also missing.

Otherwise, the report was considered to contain sufficient information for the fog/mist analysis.

At the hourly level, `has_fog_mist_data` was set to `TRUE` when at least one report within that station-hour satisfied this criterion.
