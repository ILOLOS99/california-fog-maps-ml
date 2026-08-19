# XGBoost Model

This directory contains the XGBoost training code and reproducibility metadata used for monthly fog frequency mapping in California.

The model predicts hourly fog (including mist) occurrence probabilities, which are subsequently aggregated to monthly frequencies.

## Files

- `XGBoost.R` — trains the XGBoost model and generates predictions for held-out test stations. Model training is computationally intensive and is intended to be run in a high-performance computing (HPC) environment. 
- `apply_xgboost.R` — example code demonstrating how to load and apply the trained XGBoost model to preprocessed predictor data for a location and time of your choosing. Importantly, the input data must contain all the predictors listed in `session_summary.rds`.
- `session_summary.rds` — stores the predictor list and model configuration.
- `xgboost_model_final.model` — trained XGBoost model.

## Model Training

The model uses the feature dataset produced by the preprocessing workflow:

`data/combined_stations_era5_CA_2019_2024_features.csv`

Stations are randomly divided into 70% training and 30% held-out test stations using a fixed seed (`123456`). Model fitting uses observations from 2019–2023.

The XGBoost model is fitted using Bayesian hyperparameter optimization and spatio-temporal cross-validation.

## Requirements

xgboost == 1.7.11.1 — exact version match strongly recommended. XGBoost does not guarantee model binary compatibility across versions; loading `xgboost_model_final.model` with a different xgboost version may fail outright or silently produce incorrect predictions.

Before running `apply_xgboost.R` on a new machine, confirm the installed version matches:

    packageVersion("xgboost")
