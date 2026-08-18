library(dplyr)
library(readr)
library(lubridate)
library(purrr)


era5_root    <- "data/ERA5-Land"
station_root <- "data/ASOS"
out_file     <- "data/combined_stations_era5_CA_2019_2024.csv"

years    <- 2019:2024
tz_local <- "America/Los_Angeles"


# READ & STACK ALL ERA5 MONTHLY FILES

message("=== Reading ERA5 monthly files ===")

era5_file_df <- expand.grid(year = years, month = 1:12) %>%
  arrange(year, month) %>%
  mutate(
    mm   = sprintf("%02d", month),
    path = file.path(era5_root, year,
                     paste0("ERA5_combined_", year, "_", mm, ".csv"))
  ) %>%
  filter(file.exists(path))

message("ERA5 files found: ", nrow(era5_file_df))
if (nrow(era5_file_df) == 0) stop("No ERA5 files found — check era5_root.")

era5_raw <- map_dfr(era5_file_df$path, \(p) {
  read_csv(p, show_col_types = FALSE) %>%
    mutate(across(any_of("station"), as.character))
})
message("ERA5 total rows read: ", nrow(era5_raw))


# CONVERT ERA5 UTC → LOCAL TIME + FILTER CA

message("Converting ERA5 UTC → local time (", tz_local, ") ...")

era5_vars <- c(
  "t2m_C", "dewpoint_C",
  "u10_m_s", "v10_m_s",
  "volumetric_soil_water_layer_1",
  "total_evaporation_hourly",
  "total_precipitation_hourly",
  "surface_net_solar_radiation_hourly",
  "surface_net_thermal_radiation_hourly",
  "surface_latent_heat_flux_hourly",
  "surface_sensible_heat_flux_hourly",
  "skin_temperature",
  "skin_reservoir_content",
  "leaf_area_index_low_vegetation"
)

era5 <- era5_raw %>%
  filter(state == "CA") %>%
  mutate(
    station        = as.character(station),
    datetime_utc   = force_tz(time_utc, tzone = "UTC"),        
    datetime_local = with_tz(datetime_utc, tzone = tz_local),
    date_local     = as_date(datetime_local),
    year_local     = year(datetime_local),
    month_local    = month(datetime_local),
    day_local      = day(datetime_local),
    hour_local     = hour(datetime_local)
  ) %>%
  select(
    station, station_name, state,
    any_of("elevation_m"),
    date_local, year_local, month_local, day_local, hour_local,
    any_of(era5_vars)
  ) %>%
  filter(!is.na(station), !is.na(date_local), !is.na(hour_local))

message("ERA5 rows after processing (CA only): ", nrow(era5))
message("ERA5 unique stations: ", n_distinct(era5$station))


# READ & STACK STATION YEARLY FILES — CA ONLY

message("\n=== Reading station yearly files (CA only) ===")

station_file_df <- data.frame(
  path = file.path(station_root, paste0("ca_az_hourly_", years, ".csv"))
) %>%
  filter(file.exists(path))

message("Station files found: ", nrow(station_file_df))
if (nrow(station_file_df) == 0) stop("No station files found — check station_root.")

station_obs_cols <- c(
  "n_obs",
  "dew_point_c", "air_temp_c", "wind_speed_ms",
  "precipitation_mm", "cloud_coverage",
  "fog_occurrence", "mist_occurrence",
  "has_dew_point", "has_air_temp", "has_wind_speed",
  "has_precipitation", "has_cloud_coverage", "has_fog_mist_data"
)

stations <- map_dfr(station_file_df$path, \(p) {
  read_csv(p, show_col_types = FALSE) %>%
    mutate(across(any_of("station"), as.character))
}) %>%
  filter(state == "CA") %>%
  mutate(
    station     = as.character(station),
    date_local  = as_date(date_local),                         
    hour_local  = as.integer(hour_local),
    year_local  = year(date_local),
    month_local = month(date_local),
    day_local   = day(date_local)
  ) %>%
  filter(!is.na(station), !is.na(date_local), !is.na(hour_local))

message("Station rows after cleaning (CA only): ", nrow(stations))
message("Station unique stations: ", n_distinct(stations$station))


# BUILD STATION METADATA LOOKUP

station_meta <- stations %>%
  distinct(station, station_name, state, latitude, longitude, timezone)

message("Station metadata lookup: ", nrow(station_meta), " unique stations")


# Join ERA5 with station metadata and hourly ASOS observations

message("\n=== Joining ===")

merged <- era5 %>%
  left_join(station_meta, by = "station") %>%
  left_join(
    stations %>%
      select(station, date_local, year_local, month_local,
             day_local, hour_local, any_of(station_obs_cols)),
    by = c("station", "date_local", "year_local",
           "month_local", "day_local", "hour_local")
  )

message("Rows in output:    ", nrow(merged))
message("Columns in output: ", ncol(merged))


# DIAGNOSTICS

n_with_obs <- sum(!is.na(merged$air_temp_c))
message("ERA5 rows WITH station obs:    ", n_with_obs,
        " (", round(100 * n_with_obs / nrow(merged), 1), "%)")
message("ERA5 rows WITHOUT station obs: ", nrow(merged) - n_with_obs,
        " (", round(100 * (1 - n_with_obs / nrow(merged)), 1), "%)")

n_missing_latlon <- sum(is.na(merged$latitude) | is.na(merged$longitude))
message("ERA5 rows missing lat/lon: ", n_missing_latlon,
        if (n_missing_latlon == 0) " ✓ all good" else
          " ← stations in ERA5 not found in station files")

missing_by_station <- merged %>%
  group_by(station) %>%
  summarise(
    total_hours    = n(),
    hours_with_obs = sum(!is.na(air_temp_c)),
    pct_coverage   = round(100 * hours_with_obs / total_hours, 1),
    .groups        = "drop"
  ) %>%
  arrange(pct_coverage)

message("\nStations with lowest obs coverage (top 10):")
print(head(missing_by_station, 10))


# SAVE

message("\nWriting to:\n  ", out_file)
write_csv(merged, out_file)
message("\n✓ COMPLETE — ", nrow(merged), " rows  x  ", ncol(merged), " columns saved.")
