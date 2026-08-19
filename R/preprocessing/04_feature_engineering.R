library(data.table)
library(dplyr)


in_file  <- "data/combined_stations_era5_CA_2019_2024_terrain_coast.csv"
out_file <- "data/combined_stations_era5_CA_2019_2024_features.csv"


# LOAD

cat("Loading data...\n")
dt <- fread(file = in_file)
cat("Rows:", nrow(dt), "| Cols:", ncol(dt), "\n\n")


# CLEAN DUPLICATE METADATA COLUMNS FROM JOINS

if ("station_name.x" %in% names(dt) & "station_name.y" %in% names(dt)) {
  dt[, station_name := fcoalesce(station_name.y, station_name.x)]
  dt[, c("station_name.x", "station_name.y") := NULL]
}
if ("state.x" %in% names(dt) & "state.y" %in% names(dt)) {
  dt[, state := fcoalesce(state.y, state.x)]
  dt[, c("state.x", "state.y") := NULL]
}


# DATETIME + SORT

cat("Building datetime and sorting...\n")
dt[, datetime := as.POSIXct(
  paste(year_local, month_local, day_local, hour_local, sep = "-"),
  format = "%Y-%m-%d-%H",
  tz = "America/Los_Angeles"
)]
setorder(dt, station, datetime)


# BASIC DERIVED

cat("Computing basic derived variables...\n")
dt[, wind_speed   := sqrt(u10_m_s^2 + v10_m_s^2)]
dt[, dewpoint_dep := t2m_C - dewpoint_C]


# CYCLICAL TIME FEATURES

cat("Computing cyclical time features...\n")
dt[, sin_hour  := sin(2 * pi * hour_local  / 24)]
dt[, cos_hour  := cos(2 * pi * hour_local  / 24)]
dt[, sin_month := sin(2 * pi * month_local / 12)]
dt[, cos_month := cos(2 * pi * month_local / 12)]


# PHYSICS FEATURES

cat("Computing physics features...\n")

# VPD
A <- 17.27; B <- 237.7
dt[, es      := 0.6108 * exp((A * t2m_C)     / (B + t2m_C))]
dt[, ea      := 0.6108 * exp((A * dewpoint_C) / (B + dewpoint_C))]
dt[, vpd_kpa := es - ea]
dt[, c("es", "ea") := NULL]

# Radiative cooling proxy
dt[, air_skin_diff := t2m_C - skin_temperature]

# Wind x dewpoint depression interaction
dt[, wind_dpdep_interaction := wind_speed * dewpoint_dep]


# 3-HOUR TREND FEATURES (with gap protection)

cat("Computing 3-hour trend features...\n")

dt[, t2m_lag3 := shift(t2m_C,     n = 3), by = station]
dt[, dew_lag3 := shift(dewpoint_C, n = 3), by = station]
dt[, time_diff3 := as.numeric(datetime - shift(datetime, n = 3), units = "secs"), by = station]

dt[, cooling_rate_3h   := fifelse(time_diff3 == 10800, t2m_lag3 - t2m_C,      NA_real_)]
dt[, moisture_trend_3h := fifelse(time_diff3 == 10800, dewpoint_C - dew_lag3, NA_real_)]
dt[, c("t2m_lag3", "dew_lag3", "time_diff3") := NULL]


# 1-HOUR LAG FEATURES (with gap protection)

cat("Computing 1-hour lag features...\n")

lag_vars <- c(
  "dewpoint_dep", "dewpoint_C", "t2m_C",
  "u10_m_s", "v10_m_s", "wind_speed",
  "surface_net_solar_radiation_hourly",
  "surface_net_thermal_radiation_hourly",
  "total_evaporation_hourly",
  "total_precipitation_hourly",
  "volumetric_soil_water_layer_1",
  "skin_temperature",
  "surface_latent_heat_flux_hourly",
  "surface_sensible_heat_flux_hourly"
)
lag_vars <- intersect(lag_vars, names(dt))

dt[, paste0(lag_vars, "_lag1") :=
     lapply(.SD, shift, n = 1),
   by = station,
   .SDcols = lag_vars]

dt[, time_diff1 := as.numeric(datetime - shift(datetime, n = 1), units = "secs"), by = station]
dt[time_diff1 != 3600, paste0(lag_vars, "_lag1") := NA]
dt[, time_diff1 := NULL]


# SUMMARY

cat("Total columns in output:", ncol(dt), "\n")
cat("Total rows in output:   ", nrow(dt), "\n\n")


# SAVE

cat("Saving to:\n ", out_file, "\n")
fwrite(dt, out_file)
cat("\n✓ COMPLETE\n")
