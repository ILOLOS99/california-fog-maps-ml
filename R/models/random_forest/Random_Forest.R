# ---------------- REPRODUCIBILITY ----------------
set.seed(123456)
RNGkind("L'Ecuyer-CMRG")

available_cores <- parallel::detectCores(logical = FALSE)
n_threads <- min(16, max(1, available_cores - 1))

Sys.setenv(OMP_NUM_THREADS      = as.character(n_threads))
Sys.setenv(OPENBLAS_NUM_THREADS = as.character(n_threads))
Sys.setenv(MKL_NUM_THREADS      = as.character(n_threads))


# LIBRARIES
library(data.table)
setDTthreads(n_threads)
library(dplyr)
library(readr)
library(tibble)
library(ranger)
library(ggplot2)

cat(sprintf("Running on %d threads (detected %d cores).\n", n_threads, available_cores))

# CONFIG
in_file <- "data/combined_stations_era5_CA_2019_2024_features.csv"
out_dir <- "outputs/random_forest"

dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

train_years <- 2019:2023
test_year   <- 2024

# LOAD 
cat("Loading dataset...\n")
dt <- fread(in_file)
cat("Rows:", nrow(dt), "| Cols:", ncol(dt), "\n")

monthly_completeness <- dt %>%
  group_by(station, year_local, month_local) %>%
  summarise(
    total_hours     = n(),
    hours_with_data = sum(has_fog_mist_data == TRUE, na.rm = TRUE),
    completeness    = hours_with_data / total_hours,
    .groups         = "drop"
  ) %>%
  filter(completeness >= 0.90)

# PREP LABELS
dt <- dt %>%
  mutate(
    fog_label = as.integer(fog_occurrence == "yes" | mist_occurrence == "yes")
  )

# FEATURES
features <- c(
  # Static terrain
  "proximity_to_coast_km",
  "elevation_m",
  "slope_30m",
  "slope_mean_500m",
  "northness",
  "northness_500m",
  "northness_1000m",
  "eastness",
  "eastness_500m",
  "eastness_1000m",
  "tpi_500m",
  "tpi_1000m",
  "tpi_5000m",
  
  # Dynamic ERA5 (no lags)
  "volumetric_soil_water_layer_1",
  "dewpoint_C",
  "v10_m_s",
  "u10_m_s",
  "wind_speed",
  "t2m_C",
  "skin_temperature",
  "dewpoint_dep",
  "vpd_kpa",
  "air_skin_diff",
  "wind_dpdep_interaction",
  "surface_net_thermal_radiation_hourly",
  "surface_net_solar_radiation_hourly",
  "surface_sensible_heat_flux_hourly",
  "total_evaporation_hourly",
  "total_precipitation_hourly",
  
  # Dynamic ERA5 (lags)
  "total_precipitation_hourly_lag1",
  "total_evaporation_hourly_lag1",
  "surface_net_solar_radiation_hourly_lag1",
  "surface_sensible_heat_flux_hourly_lag1",
  
  # Trend features
  "cooling_rate_3h",
  "moisture_trend_3h",
  
  # Cyclical time
  "sin_hour",
  "cos_hour",
  "sin_month",
  "cos_month"
)

# Verify all features exist
missing_feats <- setdiff(features, names(dt))
if (length(missing_feats) > 0) {
  stop(sprintf("Missing features: %s", paste(missing_feats, collapse = ", ")))
}
cat("All", length(features), "features verified.\n")

# FILTER TO ROWS WITH OBSERVATIONS 
dt <- dt %>% filter(has_fog_mist_data == TRUE)
cat("Rows with fog observations:", nrow(dt), "\n")

dt_model <- dt %>%
  filter(complete.cases(across(all_of(features))))
cat("Rows after dropping NA features:", nrow(dt_model), "\n")

# STATION SPLIT
set.seed(123456)
stations <- sort(unique(dt_model$station))
n        <- length(stations)

n_train <- floor(0.70 * n)

shuf           <- sample(stations, n)
train_stations <- shuf[1:n_train]
test_stations  <- shuf[(n_train + 1):n]

saveRDS(
  list(train = train_stations, test = test_stations),
  file.path(out_dir, "station_splits.rds")
)

cat(sprintf("Stations — Train: %d | Test: %d\n",
            length(train_stations), length(test_stations)))

# SUBSET
train_df <- dt_model %>% filter(station %in% train_stations, year_local %in% train_years)
test_df  <- dt_model %>% filter(station %in% test_stations)

cat(sprintf("Train: %d rows | Test: %d rows\n",
            nrow(train_df), nrow(test_df)))

# FIXED HYPERPARAMETERS (LITERATURE-BASED)

cat("\n--- Step 1: Using Fixed Hyperparameters from Literature ---\n")

best_params <- list(
  num.trees       = 500L,
  mtry            = as.integer(floor(sqrt(length(features)))),
  min.node.size   = 1L,
  max.depth       = NULL,
  sample.fraction = 0.632
)

cat(sprintf("  num.trees:        %d (Breiman 2001)\n",            best_params$num.trees))
cat(sprintf("  mtry:             %d (sqrt rule, Breiman 2001)\n", best_params$mtry))
cat(sprintf("  min.node.size:    %d (standard for classification)\n", best_params$min.node.size))
cat(sprintf("  max.depth:        %s (no limit - full trees)\n",
            ifelse(is.null(best_params$max.depth), "NULL", best_params$max.depth)))
cat(sprintf("  sample.fraction:  %.3f (bootstrap rate, Efron 1983)\n", best_params$sample.fraction))

saveRDS(best_params, file.path(out_dir, "fixed_params.rds"))

# TRAIN FINAL MODEL 

cat("\n--- Step 2: Training Final Model ---\n")

# Convert fog_label to factor for treeshap compatibility
train_df$fog_label <- factor(train_df$fog_label, levels = c(0, 1))

set.seed(123456)
model_main <- ranger(
  formula                   = fog_label ~ .,
  data                      = train_df %>% select(all_of(c(features, "fog_label"))),
  num.trees                 = best_params$num.trees,
  mtry                      = best_params$mtry,
  min.node.size             = best_params$min.node.size,
  max.depth                 = best_params$max.depth,
  sample.fraction           = best_params$sample.fraction,
  probability               = TRUE,
  num.threads               = n_threads,
  seed                      = 123456,
  importance                = "impurity",
  verbose                   = TRUE,
  respect.unordered.factors = "order",
  write.forest              = TRUE,
  keep.inbag                = TRUE
)

saveRDS(model_main, file.path(out_dir, "rf_model_final.rds"))

# PREDICT ON TEST SET

cat("\n--- Step 3: Test Predictions ---\n")

if (nrow(test_df) > 0) {
  test_preds <- predict(model_main, data = test_df %>% select(all_of(features)))
  raw_test   <- test_preds$predictions[, 2]
  
  combined <- test_df %>%
    mutate(
      pred_prob_fog_mist = raw_test,
      obs_fog_mist       = fog_label
    )
  
  saveRDS(combined, file.path(out_dir, "test_predictions_all_years.rds"))
  cat(sprintf("Saved test predictions: %d rows\n", nrow(combined)))
  
  monthly_agg <- combined %>%
    group_by(station, year_local, month_local) %>%
    summarise(
      obs_freq  = mean(obs_fog_mist),
      pred_freq = mean(pred_prob_fog_mist),
      n         = n(),
      .groups   = "drop"
    ) %>%
    semi_join(monthly_completeness, by = c("station", "year_local", "month_local"))
  
  write_csv(monthly_agg, file.path(out_dir, "monthly_all_years.csv"))
  cat(sprintf("Monthly aggregations: %d station-months\n", nrow(monthly_agg)))
}

# REPRODUCIBILITY LOG 

cat("\n--- Saving Session Info ---\n")

session_summary <- list(
  r_version    = R.version.string,
  seed         = 123456,
  n_threads    = n_threads,
  train_years  = train_years,
  test_year    = test_year,
  n_features   = length(features),
  features     = features,
  fixed_params = best_params,
  param_sources = list(
    num_trees       = "Breiman (2001) - Random Forests",
    mtry            = "Breiman (2001), Liaw & Wiener (2002) - sqrt rule for classification",
    min_node_size   = "Standard RF practice for classification",
    max_depth       = "Standard RF practice - no depth limit",
    sample_fraction = "Efron (1983) - bootstrap sampling rate"
  ),
  timestamp    = Sys.time()
)

saveRDS(session_summary, file.path(out_dir, "session_summary.rds"))
sink(file.path(out_dir, "session_info.txt"))
print(sessionInfo())
cat("\n=== Model Configuration ===\n")
str(session_summary)
sink()

cat("\n=== PIPELINE COMPLETE ===\n")
cat("Results saved in:", out_dir, "\n")
