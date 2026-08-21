library(data.table)
library(dplyr)
library(xgboost)
library(tidyr)

set.seed(123456)

# THREAD CONFIGURATION (Same as training)
available_cores <- parallel::detectCores(logical = FALSE)
n_threads <- min(16, max(1, available_cores - 1))

Sys.setenv(OMP_NUM_THREADS      = as.character(n_threads))
Sys.setenv(OPENBLAS_NUM_THREADS = as.character(n_threads))
Sys.setenv(MKL_NUM_THREADS      = as.character(n_threads))

cat(sprintf("Running on %d threads (detected %d cores).\n", n_threads, available_cores))

# PATHS
input_file  <- "data/combined_stations_era5_CA_2019_2024_features.csv"
split_file  <- "R/hourly_evaluation/station_splits_xgboost.rds"
model_file  <- "R/models/xgboost/xgboost_model_final.model"
summary_file <- "R/models/xgboost/session_summary.rds"
output_dir  <- "outputs/feature_importance/xgboost"

dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

# LOAD DATA & MODEL
cat("Loading model and data...\n")

xgb_mod       <- xgb.load(model_file)
model_summary <- readRDS(summary_file)
station_splits <- readRDS(split_file)

dt <- fread(input_file)

features <- model_summary$features
test_stations <- station_splits$test

cat(sprintf("Using %d features\n", length(features)))

# Test SET 
test_df <- dt %>%
  filter(station %in% test_stations, year_local %in% 2019:2024) %>%
  mutate(fog_label = as.integer(fog_occurrence == "yes" | mist_occurrence == "yes"))

cat(sprintf("Test set (2019-2024): %d rows (%d fog/mist events, %.2f%%)\n",
            nrow(test_df), sum(test_df$fog_label),
            100 * mean(test_df$fog_label)))

shap_data <- test_df

# Built-in XGBoost Importance
cat("\n=== Part 1: XGBoost Built-in Importance ===\n")

importance_gain <- xgb.importance(feature_names = features, model = xgb_mod)

write.csv(importance_gain,
          file.path(output_dir, "importance_gain_test.csv"),
          row.names = FALSE)

cat("Saved: importance_gain_test.csv\n")
cat("\nTop 10 features by Gain:\n")
print(head(importance_gain, 10))

# Compute SHAP Values (Native XGBoost)
cat("\n=== Part 2: Computing SHAP Values on Test Set ===\n")
cat(sprintf("Using native XGBoost SHAP on %d threads...\n", n_threads))

shap_matrix <- as.matrix(shap_data[, features, with = FALSE])
dshap       <- xgb.DMatrix(data = shap_matrix)

cat(sprintf("SHAP matrix dimensions: %d rows x %d columns\n",
            nrow(shap_matrix), ncol(shap_matrix)))

shap_contrib <- predict(xgb_mod, dshap, predcontrib = TRUE, nthread = n_threads)

# Remove last column (bias/intercept term)
shap_values           <- as.data.frame(shap_contrib[, -ncol(shap_contrib)])
colnames(shap_values) <- features

cat("SHAP computation complete.\n")

# Aggregate SHAP Importance
cat("\n=== Part 3: Aggregating SHAP Importance ===\n")

importance_overall <- shap_values %>%
  summarise(across(everything(), ~mean(abs(.)))) %>%
  tidyr::pivot_longer(everything(),
                      names_to  = "Feature",
                      values_to = "Mean_Abs_SHAP_Overall") %>%
  arrange(desc(Mean_Abs_SHAP_Overall))

shap_fog <- shap_values[shap_data$fog_label == 1, ]
importance_fog <- shap_fog %>%
  summarise(across(everything(), ~mean(abs(.)))) %>%
  tidyr::pivot_longer(everything(),
                      names_to  = "Feature",
                      values_to = "Mean_Abs_SHAP_Fog") %>%
  arrange(desc(Mean_Abs_SHAP_Fog))

shap_nonfog <- shap_values[shap_data$fog_label == 0, ]
importance_nonfog <- shap_nonfog %>%
  summarise(across(everything(), ~mean(abs(.)))) %>%
  tidyr::pivot_longer(everything(),
                      names_to  = "Feature",
                      values_to = "Mean_Abs_SHAP_NonFog") %>%
  arrange(desc(Mean_Abs_SHAP_NonFog))

importance_shap_combined <- importance_overall %>%
  left_join(importance_fog,    by = "Feature") %>%
  left_join(importance_nonfog, by = "Feature") %>%
  arrange(desc(Mean_Abs_SHAP_Overall))

cat("\nTop 10 features by SHAP (Overall):\n")
print(head(importance_shap_combined, 10))

cat("\nTop 10 features by SHAP (Fog events):\n")
print(head(importance_shap_combined %>% arrange(desc(Mean_Abs_SHAP_Fog)), 10))

# Save Results
cat("\n=== Part 4: Saving Results ===\n")

write.csv(importance_shap_combined,
          file.path(output_dir, "importance_shap_by_class_test.csv"),
          row.names = FALSE)
cat("Saved: importance_shap_by_class_test.csv\n")

shap_full <- shap_data %>%
  select(station, year_local, month_local, fog_label) %>%
  bind_cols(shap_values)

saveRDS(shap_full, file.path(output_dir, "shap_values_raw_test.rds"))
cat("Saved: shap_values_raw_test.rds\n")

comparison <- importance_gain %>%
  select(Feature, Gain) %>%
  left_join(importance_shap_combined %>%
              select(Feature, Mean_Abs_SHAP_Overall, Mean_Abs_SHAP_Fog, Mean_Abs_SHAP_NonFog),
            by = "Feature") %>%
  mutate(
    Rank_Gain         = rank(-Gain),
    Rank_SHAP_Overall = rank(-Mean_Abs_SHAP_Overall),
    Rank_SHAP_Fog     = rank(-Mean_Abs_SHAP_Fog),
    Rank_Diff         = Rank_Gain - Rank_SHAP_Overall
  ) %>%
  arrange(Rank_SHAP_Overall)

write.csv(comparison,
          file.path(output_dir, "importance_comparison_test.csv"),
          row.names = FALSE)
cat("Saved: importance_comparison_test.csv\n")

# Create Beeswarm Plot Data
cat("\n=== Part 5: Creating Beeswarm Plot Data ===\n")

n_sample   <- 10000
sample_size <- min(n_sample, nrow(shap_data))

set.seed(123456)
sample_idx <- sample(1:nrow(shap_data), size = sample_size, replace = FALSE)

cat(sprintf("Sampling %d observations for beeswarm plots...\n", sample_size))

beeswarm_dewpoint <- data.frame(
  station       = shap_data$station[sample_idx],
  year_local    = shap_data$year_local[sample_idx],
  month_local   = shap_data$month_local[sample_idx],
  fog_label     = shap_data$fog_label[sample_idx],
  feature_name  = "dewpoint_dep",
  shap_value    = shap_values$dewpoint_dep[sample_idx],
  feature_value = shap_data$dewpoint_dep[sample_idx]
) %>%
  arrange(shap_value)

write.csv(beeswarm_dewpoint,
          file.path(output_dir, "dewpoint_dep_beeswarm_test.csv"),
          row.names = FALSE)
cat("Saved: dewpoint_dep_beeswarm_test.csv\n")

cat(sprintf("  SHAP range: [%.4f, %.4f]\n",
            min(beeswarm_dewpoint$shap_value),
            max(beeswarm_dewpoint$shap_value)))
cat(sprintf("  Feature range: [%.4f, %.4f]\n",
            min(beeswarm_dewpoint$feature_value, na.rm = TRUE),
            max(beeswarm_dewpoint$feature_value, na.rm = TRUE)))
cat(sprintf("  Fog events: %d (%.1f%%)\n",
            sum(beeswarm_dewpoint$fog_label),
            100 * mean(beeswarm_dewpoint$fog_label)))

cat("\n=== FEATURE IMPORTANCE ANALYSIS COMPLETE (TEST SET) ===\n")
cat("Results saved in:", output_dir, "\n")
