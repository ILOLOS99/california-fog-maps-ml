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
library(xgboost)
library(ggplot2)
library(ParBayesianOptimization)
library(purrr)

cat(sprintf("Running on %d threads (detected %d cores).\n", n_threads, available_cores))

# CONFIG
in_file <- "data/combined_stations_era5_CA_2019_2024_features.csv"
out_dir <- "outputs/xgboost"

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

train_mat   <- as.matrix(train_df[, features, with = FALSE])
train_label <- train_df$fog_label

dtrain <- xgb.DMatrix(data = train_mat, label = train_label)

# BAYESIAN HYPERPARAMETER TUNING

cat("\n--- Step 1: Bayesian Hyperparameter Tuning ---\n")

set.seed(123456)
stations_train_set   <- unique(train_df$station)
station_folds_global <- sample(rep(1:5, length.out = length(stations_train_set)))

xgb_bayes_cv <- function(eta, max_depth, min_child_weight, gamma,
                         subsample, colsample_bytree, lambda, alpha, scale_pos_weight) {
  set.seed(123456)
  
  try_params <- list(
    booster          = "gbtree",
    objective        = "binary:logistic",
    eval_metric      = "logloss",
    eta              = eta,
    max_depth        = as.integer(max_depth),
    min_child_weight = min_child_weight,
    gamma            = gamma,
    subsample        = subsample,
    colsample_bytree = colsample_bytree,
    lambda           = lambda,
    alpha            = alpha,
    scale_pos_weight = scale_pos_weight,
    tree_method      = "hist",
    max_bin          = 256,
    nthread          = n_threads
  )
  
  fold_scores <- numeric(5)
  
  for (fold in 1:5) {
    val_stations <- stations_train_set[station_folds_global == fold]
    tr_stations  <- stations_train_set[station_folds_global != fold]
    val_year     <- train_years[fold]
    
    fold_train <- train_df %>% filter(station %in% tr_stations,  year_local != val_year)
    fold_valid <- train_df %>% filter(station %in% val_stations, year_local == val_year)
    
    if (nrow(fold_valid) < 500)
      warning(sprintf("Fold %d has only %d validation samples", fold, nrow(fold_valid)))
    
    d_tr <- xgb.DMatrix(
      data  = as.matrix(fold_train[, features, with = FALSE]),
      label = fold_train$fog_label
    )
    d_val <- xgb.DMatrix(
      data  = as.matrix(fold_valid[, features, with = FALSE]),
      label = fold_valid$fog_label
    )
    
    model_fold <- xgb.train(
      params                = try_params,
      data                  = d_tr,
      nrounds               = 2000,
      watchlist             = list(valid = d_val),
      early_stopping_rounds = 100,
      verbose               = 0
    )
    
    fold_scores[fold] <- model_fold$evaluation_log$valid_logloss[model_fold$best_iteration]
  }
  
  avg_score <- mean(fold_scores)
  cat(sprintf("→ Avg=%.6f, Min=%.6f, Max=%.6f\n", avg_score, min(fold_scores), max(fold_scores)))
  return(list(Score = -avg_score, Pred = 0))
}

set.seed(123456)
opt_res <- bayesOpt(
  FUN = xgb_bayes_cv,
  bounds = list(
    eta              = c(0.005, 0.1),
    max_depth        = c(3L, 12L),
    min_child_weight = c(1, 50),
    gamma            = c(0, 5),
    subsample        = c(0.5, 0.9),
    colsample_bytree = c(0.5, 0.9),
    lambda           = c(0, 5),
    alpha            = c(0, 5),
    scale_pos_weight = c(1, 20)
  ),
  initPoints = 15,
  iters.n    = 45,
  acq         = "ucb",
  verbose     = 2,
  saveFile   = file.path(out_dir, "bo_checkpoint.rds")
)

saveRDS(opt_res, file.path(out_dir, "bayesian_optimization_results.rds"))


best_par <- getBestPars(opt_res)

best_params <- list(
  booster          = "gbtree",
  objective        = "binary:logistic",
  eval_metric      = "logloss",
  eta              = best_par[["eta"]],
  max_depth        = as.integer(best_par[["max_depth"]]),
  min_child_weight = best_par[["min_child_weight"]],
  gamma            = best_par[["gamma"]],
  subsample        = best_par[["subsample"]],
  colsample_bytree = best_par[["colsample_bytree"]],
  lambda           = best_par[["lambda"]],
  alpha            = best_par[["alpha"]],
  scale_pos_weight = best_par[["scale_pos_weight"]],
  tree_method      = "hist",
  max_bin          = 256,
  nthread          = n_threads
)

cat("\nBest Parameters:\n")
print(best_params)
saveRDS(best_params, file.path(out_dir, "best_params.rds"))

# Find optimal nrounds
cat("\nFinding optimal nrounds...\n")
best_iters  <- numeric(5)
fold_scores <- numeric(5)

for (fold in 1:5) {
  val_stations <- stations_train_set[station_folds_global == fold]
  tr_stations  <- stations_train_set[station_folds_global != fold]
  val_year     <- train_years[fold]
  
  fold_train <- train_df %>% filter(station %in% tr_stations,  year_local != val_year)
  fold_valid <- train_df %>% filter(station %in% val_stations, year_local == val_year)
  
  cat(sprintf("Fold %d: val_year=%d, train_rows=%d, valid_rows=%d\n",
              fold, val_year, nrow(fold_train), nrow(fold_valid)))
  
  d_tr <- xgb.DMatrix(
    data  = as.matrix(fold_train[, features, with = FALSE]),
    label = fold_train$fog_label
  )
  d_val <- xgb.DMatrix(
    data  = as.matrix(fold_valid[, features, with = FALSE]),
    label = fold_valid$fog_label
  )
  
  model_fold <- xgb.train(
    params                = best_params,
    data                  = d_tr,
    nrounds               = 5000,
    watchlist             = list(valid = d_val),
    early_stopping_rounds = 100,
    verbose               = 1
  )
  
  best_iters[fold]  <- model_fold$best_iteration
  fold_scores[fold] <- model_fold$evaluation_log$valid_logloss[model_fold$best_iteration]
  cat(sprintf("  → best_iter=%d, score=%.6f\n", model_fold$best_iteration, fold_scores[fold]))
}

best_nrounds <- as.integer(median(best_iters))
avg_cv_score <- mean(fold_scores)
cat(sprintf("\nOptimal nrounds: %d | Avg CV score: %.6f\n", best_nrounds, avg_cv_score))

# TRAIN FINAL MODEL

cat("\n--- Step 2: Training Final Model ---\n")

set.seed(123456)
xgb_mod <- xgb.train(
  params    = best_params,
  data      = dtrain,
  nrounds   = best_nrounds,
  watchlist = list(train = dtrain),
  verbose   = 1
)

xgb.save(xgb_mod, file.path(out_dir, "xgboost_model_final.model"))


# PREDICT ON TEST SET

cat("\n--- Step 3: Test Predictions ---\n")

if (nrow(test_df) > 0) {
  test_mat <- as.matrix(test_df[, features, with = FALSE])
  raw_test <- predict(xgb_mod, test_mat)
  
  combined <- test_df %>%
    mutate(
      pred_prob_fogmist = raw_test,
      obs_fogmist       = fog_label
    )
  
  saveRDS(combined, file.path(out_dir, "test_predictions_all_years.rds"))
  cat(sprintf("Saved test predictions: %d rows\n", nrow(combined)))
  
  monthly_agg <- combined %>%
    group_by(station, year_local, month_local) %>%
    summarise(
      obs_freq  = mean(obs_fogmist),
      pred_freq = mean(pred_prob_fogmist),
      n         = n(),
      .groups   = "drop"
    ) %>%
    semi_join(monthly_completeness, by = c("station", "year_local", "month_local"))
  
  write_csv(monthly_agg, file.path(out_dir, "monthly_all_years.csv"))
}

# STEP 4: REPRODUCIBILITY LOG

cat("\n--- Saving Session Info ---\n")

session_summary <- list(
  r_version    = R.version.string,
  seed         = 123456,
  n_threads    = n_threads,
  train_years  = train_years,
  test_year    = test_year,
  n_features   = length(features),
  features     = features,
  best_nrounds = best_nrounds,
  best_params  = best_params,
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
