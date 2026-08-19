# LightGBM Fog/Mist Model

This directory contains the LightGBM training code and reproducibility metadata used for monthly fog frequency mapping in California.

The model predicts hourly fog (including mist) occurrence probabilities, which are subsequently aggregated to monthly frequencies.

## Files

- `LightGBM.R` — trains the LightGBM model and generates predictions for held-out test stations. Model training is computationally intensive and is intended to be run in a high-performance computing (HPC) environment.
- `apply_lightgbm.R` — example code demonstrating how to load and apply the trained LightGBM model to preprocessed predictor data for a location and time of your choosing. Importantly, the input data must contain all the predictors listed in `session_summary.rds`.
- `session_summary.rds` — stores the predictor list and model configuration.
- `lightgbm_model_final.txt` — trained LightGBM model.

## Model Training

The model uses the feature dataset produced by the preprocessing workflow:

`data/combined_stations_era5_CA_2019_2024_features.csv`

Stations are randomly divided into 70% training and 30% held-out test stations using a fixed seed (`123456`). Model fitting uses observations from 2019–2023.

The LightGBM model is fitted using Bayesian hyperparameter optimization and spatio-temporal cross-validation.

## Requirements
- lightgbm == 4.6.0 — exact version match strongly recommended. Model compatibility across LightGBM versions is not guaranteed; loading `lightgbm_model_final.txt` with a different lightgbm version may fail outright or silently produce incorrect predictions.

Before running `apply_lightgbm.R` on a new machine, confirm the installed version matches:

    packageVersion("lightgbm")
