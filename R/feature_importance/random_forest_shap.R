library(data.table)
library(dplyr)
library(ranger)
library(fastshap)
library(tidyr)

# CONFIGURATION
N_SAMPLES_PER_CLASS <- 1000 
NSIM <- 100          
SEED_VAL <- 123456   
SEED_CHECK <- 789012 

set.seed(SEED_VAL)

# PATHS
input_file      <- "data/combined_stations_era5_CA_2019_2024_features.csv"
split_file      <- "R/hourly_evaluation/station_splits_random_forest.rds"
model_file      <- "rf_model_final.rds"
output_dir      <- "outputs/feature_importance/random_forest"

dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

# LOAD DATA & MODEL
cat("Loading data and model...\n")
dt <- fread(input_file)
splits <- readRDS(split_file)

# Download rf_model_final.rds from Zenodo and place it in the working directory before running this script.
model_rf <- readRDS(model_file)

features <- model_rf$forest$independent.variable.names

# Disable ranger's internal parallelism
cat("Disabling nested parallelism in ranger model...\n")
model_rf$num.threads <- 1

# Prepare Test Data
test_df <- dt %>%
  filter(
    station %in% splits$test,
    year_local %in% 2019:2024
  ) %>%
  mutate(
    fog_label = as.integer(
      fog_occurrence == "yes" | mist_occurrence == "yes"
    )
  )

# Calculate class distribution
prior_pos <- mean(test_df$fog_label == 1)
prior_neg <- mean(test_df$fog_label == 0)


cat(sprintf("Class distribution: %.2f%% Fog, %.2f%% Non-Fog\n", 
            prior_pos*100, prior_neg*100))

# BALANCED SAMPLING
cat("\n=== Part 1: Balanced Sampling ===\n")

set.seed(SEED_VAL) 

shap_input_df <- test_df %>%
  group_by(fog_label) %>%
  slice_sample(n = N_SAMPLES_PER_CLASS) %>%
  ungroup() %>%
  arrange(station, year_local, month_local)

X_explain <- shap_input_df %>% select(all_of(features)) %>% as.data.frame()

cat(sprintf("Explaining %d rows (%d Fog, %d Non-Fog)\n", 
            nrow(X_explain), N_SAMPLES_PER_CLASS, N_SAMPLES_PER_CLASS))

# PREDICTION WRAPPER
pfun <- function(object, newdata) {
  predict(object, data = newdata)$predictions[, 2]
}

# RUN FASTSHAP TWICE 
cat("\n=== Part 3: Computing SHAP with Two Seeds ===\n")
cat(sprintf("Processing %d samples with nsim=%d...\n", nrow(X_explain), NSIM))

# RUN 1
cat("\nRun 1 (Seed ", SEED_VAL, ")...\n", sep = "")
set.seed(SEED_VAL)
start_time <- Sys.time()

shap_run1 <- fastshap::explain(
  model_rf,
  X            = X_explain,
  pred_wrapper = pfun,
  nsim         = NSIM,
  adjust       = TRUE,
  parallel     = FALSE
)

time1 <- as.numeric(difftime(Sys.time(), start_time, units = "mins"))
cat(sprintf("✓ Completed in %.2f minutes\n", time1))

# RUN 2
cat("\nRun 2 (Seed ", SEED_CHECK, ")...\n", sep = "")
set.seed(SEED_CHECK)
start_time <- Sys.time()

shap_run2 <- fastshap::explain(
  model_rf,
  X            = X_explain,
  pred_wrapper = pfun,
  nsim         = NSIM,
  adjust       = TRUE,
  parallel     = FALSE
)

time2 <- as.numeric(difftime(Sys.time(), start_time, units = "mins"))
cat(sprintf("✓ Completed in %.2f minutes\n", time2))

# STABILITY ANALYSIS
cat("\n=== Part 4: Stability Analysis ===\n")

feature_cors <- sapply(1:ncol(shap_run1), function(i) {
  cor(shap_run1[, i], shap_run2[, i])
})

names(feature_cors) <- features

cat("\nStability Results:\n")
cat(sprintf("  Mean correlation:   %.4f\n", mean(feature_cors)))
cat(sprintf("  Median correlation: %.4f\n", median(feature_cors)))
cat(sprintf("  Min correlation:    %.4f\n", min(feature_cors)))
cat(sprintf("  Max correlation:    %.4f\n", max(feature_cors)))

low_stability <- names(feature_cors[feature_cors < 0.90])
if (length(low_stability) > 0) {
  cat("\nFeatures with correlation < 0.90:\n")
  print(sort(feature_cors[low_stability]))
  warning("Some features show low stability. Consider increasing nsim.")
} else {
  cat("\n✓ All features show high stability (r > 0.90)\n")
}

# COMPUTE IMPORTANCE FROM BOTH RUNS
cat("\n=== Part 5: Computing Feature Importance from Both Runs ===\n")

colnames(shap_run1) <- features
colnames(shap_run2) <- features
shap_vals1 <- as.data.frame(shap_run1)
shap_vals2 <- as.data.frame(shap_run2)

importance_run1 <- shap_vals1 %>%
  summarise(across(everything(), ~mean(abs(.), na.rm = TRUE))) %>%
  pivot_longer(everything(), names_to = "Feature", values_to = "Mean_Abs_SHAP_Seed1")

importance_run2 <- shap_vals2 %>%
  summarise(across(everything(), ~mean(abs(.), na.rm = TRUE))) %>%
  pivot_longer(everything(), names_to = "Feature", values_to = "Mean_Abs_SHAP_Seed2")

importance_global <- importance_run1 %>%
  left_join(importance_run2, by = "Feature") %>%
  mutate(
    Mean_Abs_SHAP_Average = (Mean_Abs_SHAP_Seed1 + Mean_Abs_SHAP_Seed2) / 2,
    Correlation           = feature_cors[Feature]
  ) %>%
  arrange(desc(Mean_Abs_SHAP_Average)) %>%
  mutate(
    Rank                 = row_number(),
    Relative_Importance  = Mean_Abs_SHAP_Average / sum(Mean_Abs_SHAP_Average) * 100
  )

cat("\nTop 15 Features (Global Importance, Averaged Across Seeds):\n")
print(head(importance_global, 15), digits = 4)

write.csv(importance_global,
          file.path(output_dir, "importance_global.csv"),
          row.names = FALSE)

stability_report <- data.frame(
  Feature     = names(feature_cors),
  Correlation = feature_cors,
  Stable      = feature_cors >= 0.95
) %>% arrange(Correlation)

write.csv(stability_report,
          file.path(output_dir, "stability_check.csv"),
          row.names = FALSE)

shap_export <- shap_input_df %>%
  select(station, year_local, month_local, fog_label) %>%
  bind_cols(shap_vals1) %>%
  bind_cols(shap_vals2)

names(shap_export) <- c("station", "year_local", "month_local", "fog_label",
                        paste0(features, "_seed1"),
                        paste0(features, "_seed2"))

saveRDS(
  shap_export,
  file.path(output_dir, "shap_values_raw_both_seeds.rds")
)

# SUMMARY
cat("\n=== ANALYSIS COMPLETE ===\n")
cat(sprintf("Total samples analyzed: %d\n",         nrow(shap_vals1)))
cat(sprintf("Total features: %d\n",                 ncol(shap_vals1)))
cat(sprintf("SHAP stability (mean r): %.4f\n",      mean(feature_cors)))
cat(sprintf("Total computation time: %.2f minutes\n", time1 + time2))
cat(sprintf("\nResults saved to: %s\n", output_dir))
cat("\nFiles created:\n")
cat("  - importance_global.csv (with SHAP from both seeds + average)\n")
cat("  - stability_check.csv (per-feature correlations)\n")
cat("  - shap_values_raw_both_seeds.rds (raw SHAP values from both seeds)\n")
