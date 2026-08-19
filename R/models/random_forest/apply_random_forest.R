library(data.table)
library(ranger)

# FILES
model_file   <- "rf_model_final.rds"
summary_file <- "session_summary.rds"
input_file   <- "data/new_data.csv" # Your data path goes here.
output_file  <- "outputs/random_forest_predictions.csv"

# LOAD MODEL + MODEL CONFIGURATION
model   <- readRDS(model_file)
summary <- readRDS(summary_file)

# LOAD PREPROCESSED DATA
dt <- fread(input_file)

# Check that all required predictors are present
missing_features <- setdiff(summary$features, names(dt))

if (length(missing_features) > 0) {
  stop(
    "Missing required predictors: ",
    paste(missing_features, collapse = ", ")
  )
}

# PREDICT HOURLY FOG/MIST PROBABILITY
x <- dt[, ..summary$features]

pred <- predict(
  model,
  data = x
)$predictions[, 2]

dt[, pred_prob_fog_mist := pred]

# MONTHLY AGGREGATION
monthly_predictions <- dt[
  ,
  .(
    pred_freq = mean(pred_prob_fog_mist, na.rm = TRUE)
  ),
  by = .(station, year_local, month_local)
]

# SAVE
fwrite(dt, output_file)

fwrite(
  monthly_predictions,
  "outputs/random_forest_monthly_predictions.csv"
)

cat("Predictions saved.\n")
