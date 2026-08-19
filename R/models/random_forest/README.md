# Random Forest Model

This directory contains the Random Forest training code and reproducibility metadata used for monthly fog frequency mapping in California.

The model predicts hourly fog (including mist) occurrence probabilities, which are subsequently aggregated to monthly frequencies.

## Files

- `Random_Forest.R` — trains the Random Forest model and generates predictions for held-out stations. Model training is computationally intensive and is intended to be run in a high-performance computing (HPC) environment.
- `apply_random_forest.R` — example code demonstrating how to load and apply the trained Random Forest model to preprocessed predictor data for a location and time of your choosing. Importantly, the input data must contain all the predictors listed in `session_summary.rds`.
- `session_summary.rds` — stores the predictor list and model configuration.

The trained model (`rf_model_final.rds`) is archived on Zenodo because of its file size:

**DOI:** https://doi.org/10.5281/zenodo.22016730

## Model Training

The model uses the feature dataset produced by the preprocessing workflow:

`data/combined_stations_era5_CA_2019_2024_features.csv`

Stations are randomly divided into 70% training and 30% held-out test stations using a fixed seed (`123456`). Model fitting uses observations from 2019–2023.

The Random Forest is fitted with the `ranger` package using 500 trees and fixed literature-based hyperparameters.

The complete predictor set and model configuration are stored in `session_summary.rds`.
