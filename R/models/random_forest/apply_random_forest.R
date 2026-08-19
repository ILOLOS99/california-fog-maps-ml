library(data.table)
library(ranger)

# FILES
model_file   <- "rf_model_final.rds"
summary_file <- "session_summary.rds"
input_file   <- "data/new_data.csv" # Your data path goes here.
output_file  <- "outputs/random_forest_predictions.csv"

dir.create("outputs", showWarnings = FALSE, recursive = TRUE)

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

# Drop rows with NA in any feature column
na_rows <- !complete.cases(x)
if (any(na_rows)) {
  cat(sprintf(
    "Dropping %d of %d rows due to NA in feature columns.\n",
    sum(na_rows), nrow(dt)
  ))
  dt <- dt[!na_rows]
  x  <- x[!na_rows]
}

pred <- predict(
  model,
  data = x
)$predictions[, 2]

dt[, pred_prob_fog_mist := pred]

# MONTHLY AGGREGATION (ensure at least 90% hourly data completeness for the month)
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
