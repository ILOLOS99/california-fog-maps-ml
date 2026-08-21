library(data.table)
library(dplyr)
library(lightgbm)
library(tidyr)

set.seed(123456)

# THREAD CONFIGURATION (Same as training)
available_cores <- parallel::detectCores(logical = FALSE)
n_threads <- min(16, max(1, available_cores - 1))

# Set environment variables for deterministic behavior
Sys.setenv(OMP_NUM_THREADS = as.character(n_threads))
Sys.setenv(OPENBLAS_NUM_THREADS = as.character(n_threads))
Sys.setenv(MKL_NUM_THREADS = as.character(n_threads))

cat(sprintf("Running on %d threads (detected %d cores).\n", n_threads, available_cores))

# PATHS
input_file   <- "data/combined_stations_era5_CA_2019_2024_features.csv"
split_file   <- "R/hourly_evaluation/station_splits_lightgbm.rds"
model_file   <- "R/models/lightgbm/lightgbm_model_final.txt"
summary_file <- "R/models/lightgbm/session_summary.rds"
output_dir   <- "outputs/feature_importance/lightgbm"

dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

# LOAD DATA & MODEL
cat("Loading model and data...\n")

model_main     <- lgb.load(model_file)
model_summary  <- readRDS(summary_file)
station_splits <- readRDS(split_file)

dt <- fread(input_file)

features <- model_summary$features
test_stations <- station_splits$test

cat(sprintf("Using %d features\n", length(features)))

# TEST SET (all years 2019-2024 for test stations)
test_df <- dt %>% 
  filter(station %in% test_stations, year_local %in% 2019:2024) %>%
  mutate(fog_label = as.integer(fog_occurrence == "yes" | mist_occurrence == "yes"))

cat(sprintf("Test set (2019-2024): %d rows (%d fog/mist events, %.2f%%)\n", 
            nrow(test_df), sum(test_df$fog_label), 
            100 * mean(test_df$fog_label)))

# Use all test years (2019-2024)
shap_data <- test_df

# Built-in LightGBM Importance
cat("\n=== Part 1: LightGBM Built-in Importance ===\n")

importance_gain <- lgb.importance(model_main, percentage = TRUE)

write.csv(importance_gain, 
          file.path(output_dir, "importance_gain_test.csv"), 
          row.names = FALSE)

cat("Saved: importance_gain_test.csv\n")
cat("\nTop 10 features by Gain:\n")
print(head(importance_gain, 10))

# Compute SHAP Values (Native LightGBM)
cat("\n=== Part 2: Computing SHAP Values on Test Set ===\n")
cat(sprintf("Using native LightGBM SHAP on %d threads...\n", n_threads))

# Prepare feature matrix (using exact feature order from training)
shap_matrix <- as.matrix(shap_data[, features, with = FALSE])

cat(sprintf("SHAP matrix dimensions: %d rows x %d columns\n", 
            nrow(shap_matrix), ncol(shap_matrix)))

# Native LightGBM SHAP computation
shap_contrib <- predict(model_main, shap_matrix, type = 'contrib')

# Remove last column (bias/intercept term)
shap_values <- shap_contrib[, -ncol(shap_contrib)]

# Convert to data.frame with feature names
shap_values <- as.data.frame(shap_values)
colnames(shap_values) <- features

cat("SHAP computation complete.\n")

# Aggregate SHAP Importance
cat("\n=== Part 3: Aggregating SHAP Importance ===\n")

# Overall (both fog and non-fog)
importance_overall <- shap_values %>%
  summarise(across(everything(), ~mean(abs(.)))) %>%
  tidyr::pivot_longer(everything(), 
                      names_to = "Feature", 
                      values_to = "Mean_Abs_SHAP_Overall") %>%
  arrange(desc(Mean_Abs_SHAP_Overall))

# Fog events only
shap_fog <- shap_values[shap_data$fog_label == 1, ]
importance_fog <- shap_fog %>%
  summarise(across(everything(), ~mean(abs(.)))) %>%
  tidyr::pivot_longer(everything(), 
                      names_to = "Feature", 
                      values_to = "Mean_Abs_SHAP_Fog") %>%
  arrange(desc(Mean_Abs_SHAP_Fog))

# Non-fog events only
shap_nonfog <- shap_values[shap_data$fog_label == 0, ]
importance_nonfog <- shap_nonfog %>%
  summarise(across(everything(), ~mean(abs(.)))) %>%
  tidyr::pivot_longer(everything(), 
                      names_to = "Feature", 
                      values_to = "Mean_Abs_SHAP_NonFog") %>%
  arrange(desc(Mean_Abs_SHAP_NonFog))

# Combine all
importance_shap_combined <- importance_overall %>%
  left_join(importance_fog, by = "Feature") %>%
  left_join(importance_nonfog, by = "Feature") %>%
  arrange(desc(Mean_Abs_SHAP_Overall))

cat("\nTop 10 features by SHAP (Overall):\n")
print(head(importance_shap_combined, 10))

cat("\nTop 10 features by SHAP (Fog events):\n")
print(head(importance_shap_combined %>% arrange(desc(Mean_Abs_SHAP_Fog)), 10))

# Save Results
cat("\n=== Part 4: Saving Results ===\n")

# Save SHAP importance
write.csv(importance_shap_combined, 
          file.path(output_dir, "importance_shap_by_class_test.csv"), 
          row.names = FALSE)
cat("Saved: importance_shap_by_class_test.csv\n")

# Save raw SHAP values with metadata
shap_full <- shap_data %>%
  select(station, year_local, month_local, fog_label) %>%
  bind_cols(shap_values) 

saveRDS(shap_full, file.path(output_dir, "shap_values_raw_test.rds"))
cat("Saved: shap_values_raw_test.rds\n")

# Compare Gain vs SHAP rankings
comparison <- importance_gain %>%
  select(Feature, Gain) %>%
  left_join(importance_shap_combined %>% 
              select(Feature, Mean_Abs_SHAP_Overall, Mean_Abs_SHAP_Fog, Mean_Abs_SHAP_NonFog), 
            by = "Feature") %>%
  mutate(
    Rank_Gain = rank(-Gain),
    Rank_SHAP_Overall = rank(-Mean_Abs_SHAP_Overall),
    Rank_SHAP_Fog = rank(-Mean_Abs_SHAP_Fog),
    Rank_Diff = Rank_Gain - Rank_SHAP_Overall
  ) %>%
  arrange(Rank_SHAP_Overall)

write.csv(comparison, 
          file.path(output_dir, "importance_comparison_test.csv"), 
          row.names = FALSE)
cat("Saved: importance_comparison_test.csv\n")

# Create Beeswarm Plot Data
cat("\n=== Part 5: Creating Beeswarm Plot Data ===\n")

# Sample 10,000 observations for beeswarm plotting
n_sample <- 10000
sample_size <- min(n_sample, nrow(shap_data))

set.seed(123456)
sample_idx <- sample(1:nrow(shap_data), size = sample_size, replace = FALSE)

cat(sprintf("Sampling %d observations for beeswarm plots...\n", sample_size))

# Create beeswarm data for dewpoint_dep
beeswarm_dewpoint <- data.frame(
  station = shap_data$station[sample_idx],
  year_local = shap_data$year_local[sample_idx],
  month_local = shap_data$month_local[sample_idx],
  fog_label = shap_data$fog_label[sample_idx],
  feature_name = "dewpoint_dep",
  shap_value = shap_values$dewpoint_dep[sample_idx],
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
